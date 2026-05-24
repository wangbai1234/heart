"""5-Dim Drift Scoring for Voice Drift Regression.

Per docs/design/soul_drift_regression.md §3.3.
Aggregates per-prompt judgments into a single drift_score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import structlog

from .voice_judge import VoiceJudgment

logger = structlog.get_logger()


@dataclass
class DriftResult:
    """Aggregated drift result for a full regression run."""

    character: str
    drift_score: float
    prompt_results: list[PromptDriftResult] = field(default_factory=list)
    total_anti_pattern_hits: int = 0
    verdict: str = "PASS"
    verdict_color: str = "green"

    @property
    def passed(self) -> bool:
        return self.verdict_color == "green"

    @property
    def warning(self) -> bool:
        return self.verdict_color == "yellow"

    @property
    def failed(self) -> bool:
        return self.verdict_color == "red"


@dataclass
class PromptDriftResult:
    """Per-prompt drift result."""

    prompt_id: str
    drift_score: float
    anti_pattern_hits: list[str] = field(default_factory=list)
    d1_match_ratio: float = 0.0
    d2_severity: float = 0.0
    d3_tone_distance: float = 0.0
    d4_inertia_distance: float = 0.0
    d5_embedding_distance: float = 0.0
    verdict: str = "PASS"


class DriftScorer:
    """Aggregates per-prompt VoiceJudgments into a drift_score.

    Weights are loaded from config/voice_drift/thresholds.yaml.
    """

    def __init__(
        self,
        dimension_weights: dict[str, float] | None = None,
        drift_threshold: float = 0.15,
        drift_fail_threshold: float = 0.30,
        anti_pattern_tolerance: int = 0,
    ):
        """Initialize with configurable weights and thresholds.

        Args:
            dimension_weights: Dict mapping dim name to weight. Defaults to design spec.
            drift_threshold: Score above this → WARN.
            drift_fail_threshold: Score above this → FAIL.
            anti_pattern_tolerance: Max anti_pattern hits before hard fail.
        """
        self.weights = dimension_weights or {
            "D1_voice_dna": 0.30,
            "D2_anti_pattern": 0.30,
            "D3_tone": 0.15,
            "D4_inertia": 0.10,
            "D5_semantic": 0.15,
        }
        self.drift_threshold = drift_threshold
        self.drift_fail_threshold = drift_fail_threshold
        self.anti_pattern_tolerance = anti_pattern_tolerance

    def compute_prompt_score(
        self,
        judgment: VoiceJudgment,
        voice_dna_ids: list[str],
    ) -> PromptDriftResult:
        """Compute per-prompt drift score from a VoiceJudgment.

        Args:
            judgment: Parsed LLM-as-Judge output.
            voice_dna_ids: List of voice_dna IDs from the soul spec (e.g. ["vd-001", ...]).

        Returns:
            PromptDriftResult with per-dim scores.
        """
        # D1: voice_dna match ratio (higher = better, so drift = 1 - ratio)
        total_vd = len(voice_dna_ids) if voice_dna_ids else 1
        matched = len(set(judgment.vd_matches) & set(voice_dna_ids))
        d1_ratio = matched / total_vd

        # D2: anti_pattern severity (0 if no hits, progressively higher)
        n_hits = len(judgment.anti_pattern_hits)
        d2_severity = min(1.0, n_hits * 0.25)  # 4+ hits = max severity

        # D3: tone L2 distance from baseline
        # Average the absolute differences from expected midpoints
        tone_scores = judgment.tone_scores
        if tone_scores:
            # Normalize: each tone axis is 0-1, average deviation from 0.5 midpoint
            d3_distance = sum(abs(v - 0.5) for v in tone_scores.values()) / max(
                len(tone_scores), 1
            )
        else:
            d3_distance = 0.5

        # D4: inertia distance
        d4_distance = min(1.0, abs(judgment.inertia_distance_from_baseline))

        # D5: semantic distance (1 - similarity)
        d5_distance = 1.0 - judgment.semantic_similarity_to_baseline_intent

        # Weighted drift score
        drift = (
            self.weights["D1_voice_dna"] * (1.0 - d1_ratio)
            + self.weights["D2_anti_pattern"] * d2_severity
            + self.weights["D3_tone"] * d3_distance
            + self.weights["D4_inertia"] * d4_distance
            + self.weights["D5_semantic"] * d5_distance
        )

        # Verdict
        if n_hits > self.anti_pattern_tolerance:
            verdict = "HARD_FAIL"
        elif drift > self.drift_fail_threshold:
            verdict = "FAIL"
        elif drift > self.drift_threshold:
            verdict = "WARN"
        else:
            verdict = "PASS"

        return PromptDriftResult(
            prompt_id=judgment.prompt_id,
            drift_score=drift,
            anti_pattern_hits=judgment.anti_pattern_hits,
            d1_match_ratio=d1_ratio,
            d2_severity=d2_severity,
            d3_tone_distance=d3_distance,
            d4_inertia_distance=d4_distance,
            d5_embedding_distance=d5_distance,
            verdict=verdict,
        )

    def aggregate(
        self,
        prompt_results: list[PromptDriftResult],
        character: str,
    ) -> DriftResult:
        """Aggregate per-prompt results into a final DriftResult.

        Args:
            prompt_results: List of per-prompt drift scores.
            character: Character ID.

        Returns:
            DriftResult with aggregate score and verdict.
        """
        if not prompt_results:
            return DriftResult(character=character, drift_score=0.0, verdict="PASS")

        avg_drift = sum(r.drift_score for r in prompt_results) / len(prompt_results)
        total_anti = sum(len(r.anti_pattern_hits) for r in prompt_results)

        # Overall verdict (hard fail on any anti_pattern, then threshold)
        has_hard_fail = any(r.verdict == "HARD_FAIL" for r in prompt_results)
        has_fail = any(r.verdict == "FAIL" for r in prompt_results)
        has_warn = any(r.verdict == "WARN" for r in prompt_results)

        if has_hard_fail or total_anti > self.anti_pattern_tolerance:
            verdict = "HARD_FAIL"
            color = "red"
        elif avg_drift > self.drift_fail_threshold or has_fail:
            verdict = "FAIL"
            color = "red"
        elif avg_drift > self.drift_threshold or has_warn:
            verdict = "WARN"
            color = "yellow"
        else:
            verdict = "PASS"
            color = "green"

        return DriftResult(
            character=character,
            drift_score=avg_drift,
            prompt_results=prompt_results,
            total_anti_pattern_hits=total_anti,
            verdict=verdict,
            verdict_color=color,
        )
