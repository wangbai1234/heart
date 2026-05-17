"""
Drift LLM Client - thin wrapper over Anthropic Haiku tool-use call.

Implements design doc §4.2 (LLM prompt template).

Author: 心屿团队
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .drift_detector import ReleasedResponse
    from .schema_validator import SoulSpec

# ============================================================
# LLM Response
# ============================================================

@dataclass(frozen=True)
class LLMDriftResult:
    """LLM drift evaluation result."""
    drift_score: float
    drift_type: str
    violations: list[dict[str, str]]  # [{sample_excerpt, detected_pattern, expected_pattern}]
    required_patterns: list[str]
    timeout_occurred: bool = False


# ============================================================
# Tool schema (per design doc §4.2)
# ============================================================

_TOOL_SCHEMA = {
    "name": "report_drift",
    "description": "报告角色一致性审计结果",
    "input_schema": {
        "type": "object",
        "required": ["drift_score", "drift_type", "violations", "required_patterns"],
        "properties": {
            "drift_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "漂移分数 0-1，0=完美贴合，0.3=局部偏离，0.5+=明显OOC",
            },
            "drift_type": {
                "type": "string",
                "enum": [
                    "voice_dna_loss",
                    "anti_pattern_match",
                    "style_out_of_bounds",
                    "tone_inconsistent",
                    "none",
                ],
                "description": "漂移类型",
            },
            "violations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["sample_excerpt", "detected_pattern", "expected_pattern"],
                    "properties": {
                        "sample_excerpt": {
                            "type": "string",
                            "maxLength": 80,
                            "description": "从回复中逐字引用的文本片段（≤40字）",
                        },
                        "detected_pattern": {
                            "type": "string",
                            "description": "检测到的偏离模式",
                        },
                        "expected_pattern": {
                            "type": "string",
                            "description": "应有的正确模式",
                        },
                    },
                },
            },
            "required_patterns": {
                "type": "array",
                "minItems": 0,
                "maxItems": 2,
                "items": {"type": "string"},
                "description": "下一句话必须体现的模式（最多2条）",
            },
        },
    },
}


# ============================================================
# Prompt builder
# ============================================================

def _build_system_prompt(soul: SoulSpec) -> str:
    """Build soul-derived system prompt header.

    This is pre-compiled once per (character, version) and cached.
    Only the 5-response section varies per request.
    """
    # Voice_DNA top 5
    voice_dna_lines = []
    for i, vd in enumerate(soul.identity_anchor.voice_dna[:5], 1):
        examples_str = "\n    ".join(vd.examples[:2] if vd.examples else [])
        voice_dna_lines.append(
            f"{i}. {vd.pattern}\n    示例: {examples_str}"
        )
    voice_dna_block = "\n".join(voice_dna_lines)

    # Hard_never
    hard_never_list = "\n".join(
        f"- {word}" for word in soul.identity_anchor.anti_patterns.hard_never[:10]
    )

    # Cognitive style bounds
    sent_len = soul.cognitive_style.expression.sentence_length
    verbosity = soul.cognitive_style.expression.verbosity
    emotion_direct = soul.cognitive_style.expression.emotional_directness

    sent_len_baseline = sent_len.baseline
    sent_len_bound = f"{sent_len.evolution_bound[0]} ~ {sent_len.evolution_bound[1]}"
    verbosity_baseline = f"{verbosity.baseline:.2f}"
    verbosity_bound = f"{verbosity.evolution_bound[0]:.2f} ~ {verbosity.evolution_bound[1]:.2f}"
    emotion_baseline = f"{emotion_direct.baseline:.2f}"
    emotion_bound = f"{emotion_direct.evolution_bound[0]:.2f} ~ {emotion_direct.evolution_bound[1]:.2f}"

    return f"""你是「角色一致性审计员」。你的任务是评估 5 段 AI 助手回复是否符合该角色的灵魂规范。
你不评估内容好坏，只评估"是不是这个角色在说话"。

【角色】{soul.display_name}
【灵魂签名 voice_dna（前 5 条）】
{voice_dna_block}

【绝不说 hard_never】
{hard_never_list}

【认知风格 bound】
- 句长：基线 {sent_len_baseline}，允许范围 {sent_len_bound}
- 啰嗦度：基线 {verbosity_baseline}，范围 {verbosity_bound}
- 情感直接度：基线 {emotion_baseline}，范围 {emotion_bound}

【你的评估规则】
1. drift_score 含义：0 = 完美贴合角色；0.3 = 出现局部偏离需要校准；
   0.5 = 明显不像该角色；0.8+ = 已严重 OOC。
2. 单次审计偏向保守。除非证据明确，drift_score 不要超过 0.4。
3. violations[].sample_excerpt 必须从输入回复中**逐字引用**（≤ 40 字），不要改写。
4. required_patterns 是给"重新校准 prompt"用的，要写成可以直接拼接到
   "下一句话必须体现 X" 这种句式后的短语。最多 2 条，可以为空。
5. 如果一切正常，drift_score = 0.0，violations = []，drift_type = "none"。"""


def _format_responses(responses: list[ReleasedResponse]) -> str:
    """Format responses for user message."""
    lines = ["【最近 5 段助手回复】"]
    for i, resp in enumerate(responses):
        offset = len(responses) - 1 - i
        lines.append(f"[T-{offset}]  {resp.text}")

    lines.append("\n调用 report_drift 工具返回结构化结果。")
    return "\n".join(lines)


# ============================================================
# DriftLLMClient
# ============================================================

class DriftLLMClient:
    """Wrapper over Anthropic Haiku for drift evaluation.

    Pre-compiles system prompts at __init__ for each (character, version).
    """

    def __init__(self, anthropic_client=None):
        """Initialize LLM client.

        Args:
            anthropic_client: for testing; defaults to real Anthropic client.
        """
        self._client = anthropic_client
        self._system_prompts: dict[tuple[str, str], str] = {}

    def _get_system_prompt(self, soul: SoulSpec) -> str:
        """Get or build cached system prompt for soul."""
        key = (soul.character_id, soul.spec_version)
        if key not in self._system_prompts:
            self._system_prompts[key] = _build_system_prompt(soul)
        return self._system_prompts[key]

    def evaluate_drift(
        self,
        soul: SoulSpec,
        responses: list[ReleasedResponse],
        timeout_seconds: float = 3.0,
    ) -> LLMDriftResult:
        """Evaluate drift via Haiku tool-use.

        Args:
            soul: Soul Spec
            responses: sampled responses (3-5)
            timeout_seconds: LLM call timeout

        Returns:
            LLMDriftResult (timeout_occurred=True on timeout/error)
        """
        # Lazy-load Anthropic SDK (only when LLM is actually called)
        if self._client is None:
            try:
                import anthropic
                api_key = os.environ.get("ANTHROPIC_API_KEY")
                if not api_key:
                    # Fallback timeout — no API key configured
                    return LLMDriftResult(
                        drift_score=0.0,
                        drift_type="none",
                        violations=[],
                        required_patterns=[],
                        timeout_occurred=True,
                    )
                self._client = anthropic.Anthropic(
                    api_key=api_key,
                    timeout=timeout_seconds,
                )
            except ImportError:
                # anthropic SDK not installed — fail gracefully
                return LLMDriftResult(
                    drift_score=0.0,
                    drift_type="none",
                    violations=[],
                    required_patterns=[],
                    timeout_occurred=True,
                )

        system_prompt = self._get_system_prompt(soul)
        user_message = _format_responses(responses)

        try:
            response = self._client.messages.create(
                model="claude-haiku-4.5-20250514",
                max_tokens=1024,
                temperature=0.0,
                system=system_prompt,
                tools=[_TOOL_SCHEMA],
                tool_choice={"type": "tool", "name": "report_drift"},
                messages=[{"role": "user", "content": user_message}],
            )

            # Extract tool call
            tool_use = next(
                (block for block in response.content if block.type == "tool_use"),
                None,
            )
            if not tool_use or tool_use.name != "report_drift":
                # Malformed response — treat as timeout
                return LLMDriftResult(
                    drift_score=0.0,
                    drift_type="none",
                    violations=[],
                    required_patterns=[],
                    timeout_occurred=True,
                )

            result = tool_use.input
            return LLMDriftResult(
                drift_score=float(result.get("drift_score", 0.0)),
                drift_type=result.get("drift_type", "none"),
                violations=result.get("violations", []),
                required_patterns=result.get("required_patterns", []),
                timeout_occurred=False,
            )

        except Exception:
            # Timeout / network error / parse error — fail gracefully
            return LLMDriftResult(
                drift_score=0.0,
                drift_type="none",
                violations=[],
                required_patterns=[],
                timeout_occurred=True,
            )
