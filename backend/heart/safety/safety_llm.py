"""
Safety LLM Classifier — cheap-model semantic safety classification.

Called only when heuristic flags MEDIUM+ (avoid unnecessary LLM cost).
Uses ModelRouter.call_cheap() with strict JSON output for refined classification
and reasoning trace.

Spec: /runtime_specs/07_agent_orchestration.md §3.4.2, §5.2
Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
import structlog
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING, ClassVar

from heart.safety.safety_agent import (
    SafetyClassification,
    SafetyClassificationLevel,
)

if TYPE_CHECKING:
    from heart.infra.llm_cost_tracker import LLMCostTracker

logger = structlog.get_logger()


# ============================================================
# Data models
# ============================================================

@dataclass(frozen=True)
class SafetyLLMResult:
    """LLM safety classification result with reasoning trace.

    Holds the parsed JSON output from the cheap LLM safety classifier.
    Use to_safety_classification() to convert for merging with heuristic results.
    """

    level: SafetyClassificationLevel
    confidence: float  # 0.0 ~ 1.0
    triggered_categories: tuple[str, ...] = ()
    reason: str = ""
    recommended_action: str = "normal_reply"
    reasoning_trace: str = ""
    raw_response: str = ""

    def to_safety_classification(self, message_hash: str = "") -> SafetyClassification:
        """Convert to SafetyClassification for merging with heuristic result."""
        return SafetyClassification(
            level=self.level,
            confidence=self.confidence,
            triggered_categories=self.triggered_categories,
            reason=self.reason,
            recommended_action=self.recommended_action,
            message_hash=message_hash,
        )


# ============================================================
# Prompt template
# ============================================================

_SAFETY_LLM_SYSTEM_PROMPT = """你是一个安全内容分类器。你的任务是分析用户消息，判断其安全等级并给出理由。

安全等级定义（从低到高）：
- none: 完全无害的日常对话
- low: 轻微负面情绪或边缘话题，但不构成安全风险
- medium: 涉及敏感话题、不当行为暗示，需要谨慎回应
- high: 明显的违规内容、仇恨言论、暴力威胁
- purple_care_required: 自杀倾向、自残意图、严重心理健康危机

触发类别（可多选）：
- self_harm: 自残/自杀相关内容
- violence: 暴力/威胁
- hate_speech: 仇恨言论
- harassment: 骚扰/霸凌
- sexual_minors: 涉及未成年人的性内容
- sexual_explicit: 露骨的性内容
- illegal_activity: 违法活动
- substance_abuse: 药物/物质滥用
- radicalization: 极端化/恐怖主义
- emotional_distress: 严重情绪困扰
- edge_content: 边界模糊内容
- none: 无风险

推荐动作：
- normal_reply: 正常回复
- controlled_reply: 谨慎回复
- deflect: 转移话题
- reject: 拒绝回复
- suicide_care: 自杀关怀路径

仅返回 JSON，不包含任何其他文字：
{
  "level": "<none|low|medium|high|purple_care_required>",
  "confidence": <0.0~1.0>,
  "triggered_categories": ["<category>", ...],
  "reason": "<简短理由，一句话>",
  "recommended_action": "<normal_reply|controlled_reply|deflect|reject|suicide_care>",
  "reasoning_trace": "<逐步推理过程，说明为何如此分类>"
}"""

_SAFETY_LLM_USER_PROMPT_TEMPLATE = (
    "请对以下用户消息进行安全分类：\n\n用户消息: {user_message}"
)


# ============================================================
# Safety LLM Classifier
# ============================================================

class SafetyLLMClassifier:
    """Cheap-model semantic safety classifier.

    Called only when heuristic flags MEDIUM+ to avoid unnecessary LLM cost.
    Uses ModelRouter.call_cheap() with json_mode=True for strict JSON output.

    Cost cap: max DAILY_CALL_LIMIT LLM calls per user per day.
    On cap exceeded or LLM failure, returns None (caller falls back to heuristic).

    Usage:
        classifier = SafetyLLMClassifier(cost_tracker=tracker)
        result = await classifier.classify("用户消息", user_id="u1")
        if result:
            classification = result.to_safety_classification()
    """

    DAILY_CALL_LIMIT: ClassVar[int] = 10
    TIMEOUT_SECONDS: ClassVar[float] = 3.0
    TEMPERATURE: ClassVar[float] = 0.0
    MAX_TOKENS: ClassVar[int] = 300
    AGENT_NAME: ClassVar[str] = "SafetyLLMClassifier.classify"

    def __init__(
        self,
        daily_call_limit: int = 10,
        cost_tracker: "LLMCostTracker | None" = None,
    ):
        """Initialize SafetyLLMClassifier.

        Args:
            daily_call_limit: Max LLM calls per user per day (default 10).
            cost_tracker: Optional LLMCostTracker for cost recording.
        """
        self._daily_call_limit = daily_call_limit
        self._cost_tracker = cost_tracker
        self._call_counter: dict[str, dict[str, int]] = {}

    # -------- Cost gate --------

    def _can_call_llm(self, user_id: str) -> bool:
        """Check if user is under the daily LLM call cap.

        Args:
            user_id: User identifier.

        Returns:
            True if under cap.
        """
        if not user_id:
            return True

        today = date.today().isoformat()

        if user_id not in self._call_counter:
            self._call_counter[user_id] = {}

        user_counter = self._call_counter[user_id]

        old_dates = [d for d in user_counter if d != today]
        for d in old_dates:
            del user_counter[d]

        today_count = user_counter.get(today, 0)
        return today_count < self._daily_call_limit

    def _increment_counter(self, user_id: str) -> None:
        """Increment the daily call counter for a user.

        Args:
            user_id: User identifier.
        """
        if not user_id:
            return

        today = date.today().isoformat()

        if user_id not in self._call_counter:
            self._call_counter[user_id] = {}

        self._call_counter[user_id][today] = (
            self._call_counter[user_id].get(today, 0) + 1
        )

    # -------- LLM call --------

    async def _call_llm(self, user_message: str, user_id: str = "") -> str | None:
        """Call cheap model via ModelRouter with json_mode=True.

        Args:
            user_message: User message to classify.
            user_id: User ID for cost tracking.

        Returns:
            LLM raw response text, or None on timeout/error.
        """
        from heart.infra.llm.router import get_model_router

        try:
            router = await get_model_router()
            response_text = await asyncio.wait_for(
                router.call_cheap(
                    messages=[
                        {"role": "system", "content": _SAFETY_LLM_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": _SAFETY_LLM_USER_PROMPT_TEMPLATE.format(
                                user_message=user_message
                            ),
                        },
                    ],
                    temperature=self.TEMPERATURE,
                    max_tokens=self.MAX_TOKENS,
                    json_mode=True,
                    agent_name=self.AGENT_NAME,
                ),
                timeout=self.TIMEOUT_SECONDS,
            )

            if self._cost_tracker:
                await self._record_cost(user_id, response_text)

            return response_text

        except asyncio.TimeoutError:
            logger.warning(
                "SafetyLLMClassifier: LLM call timed out after %ss",
                self.TIMEOUT_SECONDS,
            )
            return None
        except Exception:
            logger.warning(
                "SafetyLLMClassifier: LLM call error", exc_info=True
            )
            return None

    async def _record_cost(self, user_id: str, response_text: str) -> None:
        """Record LLM call cost to cost tracker.

        Args:
            user_id: User identifier.
            response_text: LLM response for token estimation.
        """
        if self._cost_tracker is None:
            return

        try:
            from heart.infra.llm_cost_tracker import LLMCall

            est_output_tokens = max(1, len(response_text) // 2)
            est_input_tokens = 1500

            call = LLMCall(
                model="deepseek-chat",
                prompt_tokens=est_input_tokens,
                completion_tokens=est_output_tokens,
                user_id=user_id,
                agent_name=self.AGENT_NAME,
                provider="deepseek",
            )
            await self._cost_tracker.record(call)
        except Exception:
            logger.debug(
                "SafetyLLMClassifier: cost tracking skipped", exc_info=True
            )

    # -------- JSON parsing --------

    def _parse_response(self, raw: str) -> SafetyLLMResult | None:
        """Parse LLM JSON response into SafetyLLMResult.

        Args:
            raw: Raw LLM response text.

        Returns:
            SafetyLLMResult or None on parse failure.
        """
        if not raw or not raw.strip():
            logger.warning("SafetyLLMClassifier: empty LLM response")
            return None

        try:
            data = json.loads(raw.strip())
        except json.JSONDecodeError:
            logger.warning("SafetyLLMClassifier: JSON parse error", exc_info=True)
            return None

        if not isinstance(data, dict):
            logger.warning("SafetyLLMClassifier: response is not a JSON object")
            return None

        level_str = data.get("level", "")
        if not level_str or not level_str.strip():
            logger.warning("SafetyLLMClassifier: empty 'level' field")
            return None
        try:
            level = SafetyClassificationLevel.from_string(level_str)
        except Exception:
            logger.warning(
                "SafetyLLMClassifier: invalid level: %r", level_str
            )
            return None
        # Reject if from_string fell back to NONE on an unrecognized string
        normalized = level_str.strip().upper()
        expected_values = {lvl.value.upper() for lvl in SafetyClassificationLevel}
        expected_values.update({"PURPLE", "PURPLE_CARE_REQUIRED"})
        if normalized not in expected_values:
            logger.warning(
                "SafetyLLMClassifier: unrecognized level: %r", level_str
            )
            return None

        confidence = data.get("confidence")
        if not isinstance(confidence, (int, float)):
            logger.warning(
                "SafetyLLMClassifier: missing or invalid 'confidence'"
            )
            return None
        confidence = max(0.0, min(1.0, float(confidence)))

        categories_raw = data.get("triggered_categories", [])
        if isinstance(categories_raw, list):
            categories = tuple(str(c) for c in categories_raw if c)
        else:
            categories = ()

        reason = str(data.get("reason", ""))
        action = str(data.get("recommended_action", "normal_reply"))
        reasoning_trace = str(data.get("reasoning_trace", ""))

        return SafetyLLMResult(
            level=level,
            confidence=confidence,
            triggered_categories=categories,
            reason=reason,
            recommended_action=action,
            reasoning_trace=reasoning_trace,
            raw_response=raw.strip(),
        )

    # -------- Public API --------

    async def classify(
        self,
        user_message: str,
        user_id: str = "",
    ) -> SafetyLLMResult | None:
        """Classify a user message via cheap LLM.

        Enforces daily cost cap and timeout. Returns None on failure
        (caller falls back to heuristic-only classification).

        Args:
            user_message: User message to classify.
            user_id: User ID for cost cap tracking.

        Returns:
            SafetyLLMResult with refined classification and reasoning trace,
            or None if LLM call skipped/failed.
        """
        # Cost gate
        if not self._can_call_llm(user_id):
            logger.info(
                "SafetyLLMClassifier: daily cap (%d) exceeded for user %s",
                self._daily_call_limit,
                user_id,
            )
            return None

        # Call LLM
        raw = await self._call_llm(user_message, user_id=user_id)
        if raw is None:
            return None

        # Increment counter on successful call (call reached the API)
        self._increment_counter(user_id)

        # Parse response
        result = self._parse_response(raw)
        if result is None:
            logger.warning("SafetyLLMClassifier: failed to parse LLM response")
            return None

        logger.debug(
            "SafetyLLMClassifier: classified as %s (confidence=%.2f, categories=%s)",
            result.level.value,
            result.confidence,
            result.triggered_categories,
        )

        return result
