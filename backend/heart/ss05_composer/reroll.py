"""
Reroll Handler — SS05 Persona Composition Runtime §3.10 (§3.4)

Manages LLM re-generation attempts when the Anti-Pattern Filter or Critic Agent
rejects a response. Orchestrates the reroll/fallback decision loop.

Per runtime_specs/05_persona_composition_runtime.md:
- §3.4: Reroll & Fallback 流程
- INV-PC-6: critic_agent.fail_count(turn) ≤ MAX_REROLL_COUNT (=2)
- INV-PC-9: Critic Agent 验证失败 → reroll, 超过 max → fallback
- PC-9: 命中 hard_never → 拦截 + reroll
- IMM-PC-2: Anti-pattern fallback 不能机械化, 必须 Soul-flavored

Design contract:
- max_attempts = 2 (2 rerolls before fallback)
- On reroll: tighten constraints via reinforce-anchor injection
- All re-attempts call ModelRouter.call_main()
- 3rd reject (after 2 rerolls exhausted) → fallback library response
- Fallback responses are Soul-flavored per appendix C
- Must be async (wraps ModelRouter which is async)

Author: 心屿团队
"""

from __future__ import annotations

import inspect
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

import structlog

from heart.infra.llm import get_model_router

logger = structlog.get_logger()

# ============================================================
# Constants
# ============================================================

# Per INV-PC-6: MAX_REROLL_COUNT = 2
_DEFAULT_MAX_ATTEMPTS = 2

# Per spec appendix C: Fallback Response Library
_FALLBACK_LIBRARY: Dict[str, Dict[str, List[str]]] = {
    "rin": {
        "casual_thinking": [
            "……让我想想。",
            "嗯。",
            "……稍等。",
        ],
        "avoiding_topic": [
            "……换个话题。",
            "无聊。",
        ],
        "cant_compute": [
            "……不知道。",
            "你说呢。",
        ],
        "apologetic": [
            "……抱歉，刚才走神了。",
        ],
    },
    "dorothy": {
        "casual_thinking": [
            "诶嘿嘿，桃桃在想~",
            "嗯——",
            "等等等等~",
        ],
        "avoiding_topic": [
            "啊啊我们聊点别的吧！",
        ],
        "cant_compute": [
            "诶？桃桃不懂啦~",
            "你能再说一遍吗~",
        ],
        "apologetic": [
            "诶嘿嘿桃桃刚才走神啦~",
        ],
    },
}

# Default category when nothing more specific matches
_DEFAULT_FALLBACK_CATEGORY = "apologetic"

# ============================================================
# Data types
# ============================================================


@dataclass
class RerollAttempt:
    """Record of a single reroll attempt for audit trail.

    Per §4.1 CompositionContext.reroll_history.
    """

    attempt_number: int
    """1-indexed attempt number (1 = first reroll, 2 = second)."""

    violated_patterns: List[str] = field(default_factory=list)
    """Patterns that triggered this reroll."""

    anchor_injected: bool = False
    """Whether a reinforce-anchor was injected for this attempt."""

    llm_response: str = ""
    """The LLM's response from this attempt (empty if not yet completed)."""

    llm_latency_ms: float = 0.0
    """Latency of this attempt's LLM call in milliseconds."""


@dataclass
class RerollResult:
    """Final outcome of the reroll/fallback decision loop.

    Either:
    - reroll_succeeded:  A reroll produced a clean response.
    - fallback:          All rerolls exhausted, fallback library used.
    """

    response_text: str
    """The final response text — either reroll output or fallback."""

    action: str = ""
    """'reroll_succeeded' | 'fallback'."""

    total_attempts: int = 0
    """Total number of reroll attempts made (0 if passed on first try)."""

    reroll_history: List[RerollAttempt] = field(default_factory=list)
    """Audit trail of reroll attempts."""


# ============================================================
# RerollHandler
# ============================================================


class RerollHandler:
    """Manages the reroll-or-fallback decision loop.

    This is the central coordinator invoked after Anti-Pattern Filter
    or Critic Agent detects a violation that requires regeneration.

    Usage:
        >>> handler = RerollHandler(max_attempts=2)
        >>> result = await handler.handle(
        ...     messages=messages,
        ...     violated_patterns=["宝宝", "加油"],
        ...     soul=soul_spec,
        ... )
        >>> # result.response_text is the final response
        >>> # result.action is "reroll_succeeded" or "fallback"

    Thread-safe — all per-request state is parameter-passed.
    """

    def __init__(self, max_attempts: int = _DEFAULT_MAX_ATTEMPTS):
        """Initialize the reroll handler.

        Args:
            max_attempts: Maximum number of reroll attempts before fallback.
                          Defaults to 2 (per INV-PC-6).
        """
        if max_attempts < 0:
            raise ValueError(f"max_attempts must be >= 0, got {max_attempts}")
        self._max_attempts = max_attempts

    @property
    def max_attempts(self) -> int:
        """Public read access to the configured max attempts."""
        return self._max_attempts

    # ---- Decision helpers ----

    def should_reroll(self, reroll_count: int) -> bool:
        """Check whether another reroll attempt is still allowed.

        Per §3.4 Reroll Decision:
            reroll_count < MAX_REROLL (=2) → 继续
            reroll_count >= MAX_REROLL → 进入 Fallback

        Args:
            reroll_count: Number of reroll attempts already made.

        Returns:
            True if another reroll is permitted.
        """
        return reroll_count < self._max_attempts

    # ---- Constraint tightening ----

    def tighten_constraints(
        self,
        messages: List[Dict[str, str]],
        violated_patterns: List[str],
        reinforce_content: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Inject a reinforce-anchor message into the conversation for the reroll.

        Per §3.4 Reroll Path:
            "在 prompt 中追加 ANTI-DRIFT REINFORCE Block:
             '上一次回复违反了你的灵魂。请重试，并避免：{detected_patterns}'"

        The reinforced message is appended as a new system-level message
        that tightens the character's constraints before the next generation.

        Args:
            messages: The current message list (system + history + user).
            violated_patterns: The specific patterns that triggered rejection.
            reinforce_content: Optional override for the reinforce text.
                               If None, builds from violated_patterns.

        Returns:
            A new message list with the reinforce injection appended.
            The original list is not mutated.
        """
        if not violated_patterns:
            return list(messages)

        # Build the reinforce message
        if reinforce_content is not None:
            reinforce_text = reinforce_content
        else:
            pattern_list = "、".join(violated_patterns)
            reinforce_text = f"上一次回复违反了你的灵魂。请重试，并避免：{pattern_list}"

        reinforce_message: Dict[str, str] = {
            "role": "system",
            "content": reinforce_text,
        }

        # Append reinforce after the system messages but before the user turn.
        # Strategy: insert as the last system message so it acts as a
        # constraint override for the model.
        #
        # We look for the boundary between system and non-system messages
        # and insert there. If all messages are system (unusual), append at end.
        result = list(messages)
        insert_at: Optional[int] = None
        for i, msg in enumerate(result):
            if msg.get("role") != "system":
                insert_at = i
                break

        if insert_at is not None:
            result.insert(insert_at, reinforce_message)
        else:
            result.append(reinforce_message)

        return result

    # ---- Reroll execution ----

    async def _call_llm(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Call the main LLM via ModelRouter.

        All re-attempts must go through ModelRouter.call_main()
        per the implementation contract.

        Args:
            messages: The conversation messages.
            temperature: Optional temperature override.
            max_tokens: Optional max_tokens override.

        Returns:
            The LLM's response text.
        """
        router = await get_model_router()
        return await router.call_main(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            agent_name="RerollHandler",
        )

    async def reroll(
        self,
        messages: List[Dict[str, str]],
        violated_patterns: List[str],
        soul: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        reinforce_content: Optional[str] = None,
    ) -> str:
        """Execute a single reroll attempt with tightened constraints.

        Steps:
        1. Tighten constraints by injecting reinforce-anchor message.
        2. Call main LLM via ModelRouter.
        3. Return the new response.

        Args:
            messages: The original message list (before violation).
            violated_patterns: Patterns that triggered the reroll.
            soul: Optional soul spec dict (reserved for future per-character tuning).
            temperature: Temperature override for the reroll (defaults to main model config).
            max_tokens: Max tokens override for the reroll.
            reinforce_content: Optional explicit reinforce message override.

        Returns:
            The new LLM response from the reroll attempt.
        """
        # 1. Tighten constraints
        tightened = self.tighten_constraints(
            messages=messages,
            violated_patterns=violated_patterns,
            reinforce_content=reinforce_content,
        )

        # 2. Call LLM
        response = await self._call_llm(
            messages=tightened,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response

    # ---- Fallback selection ----

    def select_fallback(
        self,
        character_id: str,
        category: str = _DEFAULT_FALLBACK_CATEGORY,
    ) -> str:
        """Select a Soul-flavored fallback response from the library.

        Per §3.4 Fallback Path + appendix C:
        - Rin apologetic: "……抱歉，刚才走神了。"
        - Dorothy apologetic: "诶嘿嘿桃桃刚才走神啦~"
        - Must be immediate, Soul-flavored, not mechanical (IMM-PC-2).

        Falls back to a generic minimal response if character/category unknown.

        Args:
            character_id: The character identifier (e.g. "rin", "dorothy").
            category: Fallback category: "apologetic" | "casual_thinking" |
                      "avoiding_topic" | "cant_compute". Defaults to "apologetic".

        Returns:
            A Soul-flavored fallback response string.
        """
        char_lib = _FALLBACK_LIBRARY.get(character_id)
        if char_lib is None:
            logger.warning(
                f"No fallback library for character '{character_id}', using generic fallback."
            )
            return "……"

        candidates = char_lib.get(category)
        if not candidates:
            logger.warning(
                f"No fallback category '{category}' for character '{character_id}', "
                f"falling back to '{_DEFAULT_FALLBACK_CATEGORY}'."
            )
            candidates = char_lib.get(_DEFAULT_FALLBACK_CATEGORY, ["……"])

        # Random selection for variety within the category (IMM-PC-2)
        return random.choice(candidates)

    # ---- Main orchestration ----

    async def handle(
        self,
        messages: List[Dict[str, str]],
        violated_patterns: List[str],
        soul: Optional[Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        filter_fn: Optional[Callable] = None,
    ) -> RerollResult:
        """Orchestrate the full reroll-or-fallback loop.

        This is the primary entry point. It:
        1. Checks whether a reroll is warranted (violated_patterns non-empty).
        2. Loops up to max_attempts times:
           a. Tightens constraints (inject reinforce-anchor).
           b. Calls main LLM via ModelRouter.
           c. Optionally re-filters the output via filter_fn.
           d. If clean, returns reroll_succeeded.
        3. If all rerolls exhausted, selects a Soul-flavored fallback.

        Args:
            messages: The conversation message list at the point of violation.
            violated_patterns: The patterns detected by Anti-Pattern Filter.
            soul: Optional soul spec dict. Used to derive character_id for fallback.
            temperature: Temperature override for reroll attempts.
            max_tokens: Max tokens override for reroll attempts.
            filter_fn: Optional callable (text) -> FilterResult for
                       re-checking reroll output against anti-patterns.
                       If None, all reroll attempts are assumed clean.

        Returns:
            RerollResult with the final response and audit trail.
        """
        character_id = self._extract_character_id(soul)

        # Quick return: no violations → nothing to reroll
        if not violated_patterns:
            logger.warning("handle() called with empty violated_patterns — no reroll needed.")
            return RerollResult(
                response_text="",
                action="reroll_succeeded",
                total_attempts=0,
            )

        history: List[RerollAttempt] = []
        current_violations = list(violated_patterns)

        for attempt_num in range(1, self._max_attempts + 1):
            # --- Tighten constraints ---
            attempt = RerollAttempt(
                attempt_number=attempt_num,
                violated_patterns=list(current_violations),
                anchor_injected=True,
            )

            tightened = self.tighten_constraints(
                messages=messages,
                violated_patterns=current_violations,
            )

            # --- Call LLM ---
            call_start = time.perf_counter()
            try:
                response = await self._call_llm(
                    messages=tightened,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:
                logger.error(
                    f"Reroll attempt {attempt_num}/{self._max_attempts} LLM call failed: {exc}"
                )
                attempt.llm_response = ""
                attempt.llm_latency_ms = (time.perf_counter() - call_start) * 1000
                history.append(attempt)
                continue

            attempt.llm_response = response
            attempt.llm_latency_ms = (time.perf_counter() - call_start) * 1000
            history.append(attempt)

            # --- Re-filter (optional) ---
            if filter_fn is not None:
                try:
                    if inspect.iscoroutinefunction(filter_fn):
                        filter_result = await filter_fn(response)
                    else:
                        filter_result = filter_fn(response)
                except Exception as exc:
                    logger.warning(
                        f"Reroll attempt {attempt_num}: filter_fn raised {exc}, treating as pass."
                    )
                    return RerollResult(
                        response_text=response,
                        action="reroll_succeeded",
                        total_attempts=attempt_num,
                        reroll_history=history,
                    )

                if filter_result.passed:
                    return RerollResult(
                        response_text=response,
                        action="reroll_succeeded",
                        total_attempts=attempt_num,
                        reroll_history=history,
                    )
                # Still violated — update patterns for next attempt
                current_violations = [v.pattern for v in filter_result.violations]
            else:
                # No filter_fn → assume clean
                return RerollResult(
                    response_text=response,
                    action="reroll_succeeded",
                    total_attempts=attempt_num,
                    reroll_history=history,
                )

        # --- All attempts exhausted → fallback ---
        logger.warning(
            f"All {self._max_attempts} reroll attempts exhausted for "
            f"character '{character_id}'. Using fallback library."
        )
        fallback_text = self.select_fallback(
            character_id=character_id,
            category=_DEFAULT_FALLBACK_CATEGORY,
        )

        return RerollResult(
            response_text=fallback_text,
            action="fallback",
            total_attempts=self._max_attempts,
            reroll_history=history,
        )

    # ---- Internal helpers ----

    @staticmethod
    def _extract_character_id(soul: Optional[Dict[str, Any]]) -> str:
        """Extract character_id from a soul spec dict."""
        if soul is None:
            return "unknown"
        if isinstance(soul, dict):
            return soul.get("character_id", "unknown")
        return "unknown"


# ============================================================
# Module-level convenience
# ============================================================


def get_fallback(
    character_id: str,
    category: str = _DEFAULT_FALLBACK_CATEGORY,
) -> str:
    """Select a Soul-flavored fallback response (synchronous convenience).

    Args:
        character_id: Character identifier ("rin", "dorothy", etc.).
        category: Fallback category.

    Returns:
        A Soul-flavored fallback response string.
    """
    handler = RerollHandler()
    return handler.select_fallback(character_id, category)


def list_fallback_categories(character_id: str) -> List[str]:
    """List available fallback categories for a character.

    Args:
        character_id: Character identifier.

    Returns:
        List of category names, or empty list if character unknown.
    """
    char_lib = _FALLBACK_LIBRARY.get(character_id)
    if char_lib is None:
        return []
    return list(char_lib.keys())
