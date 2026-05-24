"""LLM-as-Judge for Voice Drift Regression.

Per docs/design/soul_drift_regression.md §3.5.
Uses ModelRouter.cheap tier + strict JSON mode.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger()


@dataclass
class VoiceJudgment:
    """Structured output from LLM-as-Judge evaluation."""

    prompt_id: str
    character: str
    vd_matches: list[str] = field(default_factory=list)
    tone_scores: dict[str, float] = field(default_factory=dict)
    inertia_distance_from_baseline: float = 0.0
    semantic_similarity_to_baseline_intent: float = 1.0
    free_text_critique: str = ""
    verdict_summary_for_humans: str = ""
    anti_pattern_hits: list[str] = field(default_factory=list)
    raw_judge_response: str = ""
    parse_error: Optional[str] = None


class VoiceJudge:
    """LLM-as-Judge: evaluates a candidate response against an established voice profile.

    Uses ModelRouter.cheap tier to minimize cost (~$0.005 per judgment).
    """

    def __init__(self, model_router):
        """Initialize with a ModelRouter instance.

        Args:
            model_router: heart.infra.llm.router.ModelRouter instance.
        """
        self._router = model_router

    def build_judge_prompt(
        self,
        character: str,
        soul_spec: dict,
        user_message: str,
        baseline_responses: list[str],
        candidate_response: str,
    ) -> str:
        """Build the judge prompt from soul_spec voice_dna and baseline.

        Returns the system_prompt string (user_message goes as user message).
        """
        voice_dna = soul_spec.get("voice_dna", [])
        anti_patterns = soul_spec.get("anti_patterns", {})
        humor = soul_spec.get("humor_profile", {})

        # Build voice_dna list for prompt
        vd_lines = []
        for vd in voice_dna:
            vd_id = vd.get("id", "?")
            pattern = vd.get("pattern", "").strip()
            examples = vd.get("examples", [])
            ex_str = "; ".join(examples[:2]) if examples else ""
            vd_lines.append(f"  {vd_id}: {pattern} (e.g. {ex_str})")

        # Build hard_never list for context (judge doesn't check — regex does)
        hard_never = anti_patterns.get("hard_never", [])
        hn_str = ", ".join(hard_never[:20]) if hard_never else "none"

        # Build humor profile
        humor_str = ", ".join(f"{k}={v}" for k, v in humor.items()) if humor else "none"

        # Build baseline samples
        baseline_str = "\n".join(
            f"  {i + 1}. {resp}" for i, resp in enumerate(baseline_responses)
        )

        prompt = f"""You are evaluating a candidate response against an established voice profile.

Character: {character}
Character display name: {soul_spec.get("display_name", {}).get("zh", character)}

Voice DNA (check which patterns are exhibited by the candidate):
{chr(10).join(vd_lines)}

Humor profile (quantitative axes):
  {humor_str}

Anti-patterns (you do NOT need to check these — regex does):
  hard_never: {hn_str}

Context — user message that produced the response:
  "{user_message}"

Baseline responses (canonical "this is how she sounds"):
{baseline_str}

Candidate response to evaluate:
  "{candidate_response}"

Output ONLY valid JSON, no prose, no markdown fences:
{{
  "vd_matches": ["vd-001", "vd-003"],
  "tone_scores": {{"dryness": 0.85, "sarcasm": 0.50, "warmth_in_humor": 0.10}},
  "inertia_distance_from_baseline": 0.12,
  "semantic_similarity_to_baseline_intent": 0.81,
  "free_text_critique": "新回复比 baseline 更暖；baseline 更冷。",
  "verdict_summary_for_humans": "Slight warmth drift; not severe."
}}"""
        return prompt

    async def evaluate(
        self,
        prompt_id: str,
        character: str,
        soul_spec: dict,
        user_message: str,
        baseline_responses: list[str],
        candidate_response: str,
    ) -> VoiceJudgment:
        """Evaluate a single candidate response.

        Returns a VoiceJudgment with parsed scores.

        Args:
            prompt_id: Canonical prompt ID (e.g. "cp-001").
            character: Character ID ("rin" or "dorothy").
            soul_spec: Loaded soul spec dict.
            user_message: The user message that produced the candidate.
            baseline_responses: Baseline response samples (1-3).
            candidate_response: The response to evaluate.

        Returns:
            VoiceJudgment dataclass.
        """
        system_prompt = self.build_judge_prompt(
            character, soul_spec, user_message, baseline_responses, candidate_response
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Evaluate the candidate. Output only JSON."},
        ]

        try:
            raw = await self._router.call_cheap(
                messages=messages,
                temperature=0.0,
                max_tokens=1024,
                json_mode=True,
                agent_name="voice_judge",
            )
            result = self._parse(raw, prompt_id, character)
        except Exception as e:
            logger.error("voice_judge call failed", error=str(e))
            result = VoiceJudgment(
                prompt_id=prompt_id,
                character=character,
                parse_error=str(e),
            )

        return result

    def _parse(self, raw: str, prompt_id: str, character: str) -> VoiceJudgment:
        """Parse LLM judge JSON output. Handles markdown fences."""
        # Strip markdown fences if present
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            return VoiceJudgment(
                prompt_id=prompt_id,
                character=character,
                parse_error=f"JSON parse error: {e}",
                raw_judge_response=raw,
            )

        return VoiceJudgment(
            prompt_id=prompt_id,
            character=character,
            vd_matches=data.get("vd_matches", []),
            tone_scores=data.get("tone_scores", {}),
            inertia_distance_from_baseline=data.get("inertia_distance_from_baseline", 0.0),
            semantic_similarity_to_baseline_intent=data.get(
                "semantic_similarity_to_baseline_intent", 1.0
            ),
            free_text_critique=data.get("free_text_critique", ""),
            verdict_summary_for_humans=data.get("verdict_summary_for_humans", ""),
            raw_judge_response=raw,
        )


def scan_anti_patterns(response: str, soul_spec: dict) -> list[str]:
    """Scan a response for anti_pattern hits using regex/substring matching.

    Uses hard_never (substring) and forbidden_patterns (regex) from soul_spec.
    This runs BEFORE the LLM judge — it's deterministic.

    Returns list of hit descriptions.
    """
    anti_patterns = soul_spec.get("anti_patterns", {})
    hits = []

    # Check hard_never (substring)
    hard_never = anti_patterns.get("hard_never", [])
    for pattern in hard_never:
        if isinstance(pattern, str) and pattern in response:
            hits.append(f"hard_never: '{pattern}'")

    # Check forbidden_patterns (regex)
    forbidden = anti_patterns.get("forbidden_patterns", [])
    for fp in forbidden:
        if isinstance(fp, dict):
            regex = fp.get("regex", "")
            desc = fp.get("description", regex)
            try:
                if re.search(regex, response):
                    # Skip if exception applies
                    exception = fp.get("exception", "")
                    if exception and exception in response:
                        continue
                    hits.append(f"forbidden: {desc}")
            except re.error:
                logger.warning("invalid regex in forbidden_patterns", regex=regex)

    return hits
