"""
Drift LLM Client - ModelRouter-based drift evaluation

Implements design doc §4.2 (LLM prompt template).
Uses json_mode instead of tool-use for compatibility with DeepSeek.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

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
# JSON output schema for drift evaluation
# ============================================================

_JSON_SCHEMA_INSTRUCTION = """你的输出必须是纯 JSON，符合以下 schema:
{
  "drift_score": <0-1 之间的数字>,
  "drift_type": <"voice_dna_loss" | "anti_pattern_match" | "style_out_of_bounds" | "tone_inconsistent" | "none">,
  "violations": [
    {
      "sample_excerpt": "<从回复中逐字引用的片段，≤40字>",
      "detected_pattern": "<检测到的偏离模式>",
      "expected_pattern": "<应有的正确模式>"
    }
  ],
  "required_patterns": [<最多2个强化模式，可为空>]
}
"""


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
        examples_str = "\n    ".join(str(ex) for ex in vd.examples[:2]) if vd.examples else ""
        voice_dna_lines.append(f"{i}. {vd.pattern}\n    示例: {examples_str}")
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
    emotion_bound = (
        f"{emotion_direct.evolution_bound[0]:.2f} ~ {emotion_direct.evolution_bound[1]:.2f}"
    )

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
5. 如果一切正常，drift_score = 0.0，violations = []，drift_type = "none"。

{_JSON_SCHEMA_INSTRUCTION}"""


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
    """ModelRouter-based drift evaluation via DeepSeek cheap model.

    Pre-compiles system prompts at __init__ for each (character, version).
    Uses json_mode for structured output (compatible with DeepSeek).
    """

    def __init__(self):
        """Initialize LLM client (async)."""
        self._system_prompts: dict[tuple[str, str], str] = {}

    def _get_system_prompt(self, soul: SoulSpec) -> str:
        """Get or build cached system prompt for soul."""
        key = (soul.character_id, soul.spec_version)
        if key not in self._system_prompts:
            self._system_prompts[key] = _build_system_prompt(soul)
        return self._system_prompts[key]

    async def evaluate_drift(
        self,
        soul: SoulSpec,
        responses: list[ReleasedResponse],
        timeout_seconds: float = 3.0,
    ) -> LLMDriftResult:
        """Evaluate drift via ModelRouter (DeepSeek cheap model).

        Args:
            soul: Soul Spec
            responses: sampled responses (3-5)
            timeout_seconds: LLM call timeout

        Returns:
            LLMDriftResult (timeout_occurred=True on timeout/error)
        """
        from heart.infra.llm.router import get_model_router

        system_prompt = self._get_system_prompt(soul)
        user_message = _format_responses(responses)

        try:
            router = await get_model_router()
            response_text = await asyncio.wait_for(
                router.call_cheap(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    temperature=0.0,
                    max_tokens=1024,
                    json_mode=True,
                    agent_name="DriftDetector.evaluate_drift",
                ),
                timeout=timeout_seconds,
            )

            # Parse JSON response
            result_data = json.loads(response_text)
            return LLMDriftResult(
                drift_score=float(result_data.get("drift_score", 0.0)),
                drift_type=result_data.get("drift_type", "none"),
                violations=result_data.get("violations", []),
                required_patterns=result_data.get("required_patterns", []),
                timeout_occurred=False,
            )

        except asyncio.TimeoutError:
            # LLM call timed out
            return LLMDriftResult(
                drift_score=0.0,
                drift_type="none",
                violations=[],
                required_patterns=[],
                timeout_occurred=True,
            )
        except (json.JSONDecodeError, KeyError, ValueError):
            # Malformed JSON response — fail gracefully
            return LLMDriftResult(
                drift_score=0.0,
                drift_type="none",
                violations=[],
                required_patterns=[],
                timeout_occurred=True,
            )
        except Exception:
            # Other errors (network, config, etc.)
            return LLMDriftResult(
                drift_score=0.0,
                drift_type="none",
                violations=[],
                required_patterns=[],
                timeout_occurred=True,
            )
