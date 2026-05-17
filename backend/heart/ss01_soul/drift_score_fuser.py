"""
Drift Score Fuser - EMA fusion + hysteresis logic.

Implements design doc §4.3 (score computation) and §4.4 (REINFORCE trigger).

Author: 心屿团队
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .anti_pattern_scanner import AntiPatternHits


# Constants from design doc §4.3
_EMA_ALPHA = 0.5
_DECAY_FACTOR = 0.90

# Deterministic floors (§4.3)
_HARD_NEVER_FLOOR = 0.60
_FORBIDDEN_PATTERN_FLOOR = 0.45
_SOFT_NEVER_FLOOR = 0.25

# REINFORCE trigger thresholds (§4.4)
_REINFORCE_SCORE_THRESHOLD = 0.3
_REINFORCE_PREV_EMA_THRESHOLD = 0.2
_REINFORCE_MIN_VIOLATIONS = 2


def compute_final_score(
    llm_score: float | None,
    prefilter_hits: AntiPatternHits,
    prev_ema: float,
) -> float:
    """Compute final drift score with EMA fusion and deterministic floors.

    Per design doc §4.3:
        1. raw = llm_score (or decay × prev_ema if skipped)
        2. Apply deterministic floors based on prefilter hits
        3. EMA fusion: final = α × raw + (1-α) × prev_ema

    Args:
        llm_score: LLM-reported drift score [0, 1], or None if LLM skipped
        prefilter_hits: pre-filter scan results
        prev_ema: previous drift_score (SAS.current_drift_score)

    Returns:
        final drift_score in [0, 1]
    """
    # 1. Raw signal
    if llm_score is None:
        raw = prev_ema * _DECAY_FACTOR
    else:
        raw = llm_score

    # 2. Deterministic floors (LLM might be too lenient)
    if prefilter_hits.hard_never_count > 0:
        raw = max(raw, _HARD_NEVER_FLOOR)
    elif prefilter_hits.forbidden_pattern_count > 0:
        raw = max(raw, _FORBIDDEN_PATTERN_FLOOR)
    elif prefilter_hits.soft_never_count > 0:
        raw = max(raw, _SOFT_NEVER_FLOOR)

    # 3. EMA fusion
    final = _EMA_ALPHA * raw + (1 - _EMA_ALPHA) * prev_ema

    return min(1.0, max(0.0, final))


def should_emit_reinforce(
    final_score: float,
    prev_ema: float,
    prefilter_hits: AntiPatternHits,
    llm_violations_count: int,
) -> bool:
    """Decide whether to emit REINFORCE evidence.

    Per design doc §4.4 hysteresis:
        final_score ≥ 0.3 AND (
            deterministic hit present OR
            prev_ema ≥ 0.2 OR
            llm_violations ≥ 2
        )

    A single LLM spike with no deterministic backing and quiet history
    won't trigger REINFORCE — only update drift_score.

    Args:
        final_score: fused drift score
        prev_ema: previous drift_score
        prefilter_hits: pre-filter results
        llm_violations_count: number of LLM-reported violations

    Returns:
        True if REINFORCE should be emitted
    """
    if final_score < _REINFORCE_SCORE_THRESHOLD:
        return False

    # Hysteresis: need supporting evidence
    deterministic_hit = (
        prefilter_hits.hard_never_count > 0
        or prefilter_hits.forbidden_pattern_count > 0
        or prefilter_hits.soft_never_count > 0
    )

    prev_concern = prev_ema >= _REINFORCE_PREV_EMA_THRESHOLD
    strong_llm_evidence = llm_violations_count >= _REINFORCE_MIN_VIOLATIONS

    return deterministic_hit or prev_concern or strong_llm_evidence
