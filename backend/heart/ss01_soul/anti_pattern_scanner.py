"""
Anti-Pattern Scanner - pre-filter signals A/B/C for drift detection.

Target: 70% LLM skip rate. Three signals:
  A. Deterministic anti-pattern hits (hard_never, forbidden_patterns, soft_never)
  B. Voice_DNA frequency check (high-freq markers)
  C. Sentence length distribution vs cognitive_style bounds

Any one trips → escalate to LLM. All clean → skip.

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .drift_detector import ReleasedResponse
    from .drift_fingerprint import DriftFingerprint
    from .schema_validator import SoulSpec


@dataclass(frozen=True)
class AntiPatternHits:
    """Pre-filter scan results."""
    hard_never_count: int = 0
    forbidden_pattern_count: int = 0
    soft_never_count: int = 0
    voice_dna_marker_miss: bool = False       # Signal B tripped
    sentence_length_out_of_bounds: bool = False  # Signal C tripped

    def any_signal_tripped(self) -> bool:
        """True if any signal requires LLM escalation."""
        return (
            self.hard_never_count > 0
            or self.forbidden_pattern_count > 0
            or self.soft_never_count > 0
            or self.voice_dna_marker_miss
            or self.sentence_length_out_of_bounds
        )


# ============================================================
# Signal A — Deterministic anti-pattern hits
# ============================================================

def _scan_literals(
    text: str,
    literals: frozenset[str],
    exclude: frozenset[str] = frozenset(),
) -> int:
    """Count literal substring hits, excluding allow-listed words.

    Args:
        text: response text to scan
        literals: set of forbidden literal substrings
        exclude: rare-unlock-words to skip (when conditions met)

    Returns:
        count of hits
    """
    # Simple MVP: case-sensitive substring search
    # For production, consider Aho-Corasick for large literal sets
    hits = 0
    active_literals = literals - exclude
    for literal in active_literals:
        if literal in text:
            hits += 1
    return hits


def _scan_regexes(text: str, patterns: tuple[re.Pattern, ...]) -> int:
    """Count regex pattern hits."""
    hits = 0
    for pattern in patterns:
        if pattern.search(text):
            hits += 1
    return hits


def _scan_signal_a(
    responses: list[ReleasedResponse],
    fingerprint: DriftFingerprint,
    unlocked_rare_words: frozenset[str],
) -> tuple[int, int, int]:
    """Scan for deterministic anti-pattern hits.

    Returns: (hard_never_count, forbidden_pattern_count, soft_never_count)
    """
    hard_hits = 0
    forbidden_hits = 0
    soft_hits = 0

    for resp in responses:
        hard_hits += _scan_literals(
            resp.text,
            fingerprint.hard_never,
            exclude=unlocked_rare_words,
        )
        forbidden_hits += _scan_regexes(
            resp.text,
            fingerprint.forbidden_patterns,
        )
        soft_hits += _scan_literals(
            resp.text,
            fingerprint.soft_never,
        )

    return hard_hits, forbidden_hits, soft_hits


# ============================================================
# Signal B — Voice_DNA frequency check
# ============================================================

def _scan_signal_b(
    responses: list[ReleasedResponse],
    fingerprint: DriftFingerprint,
) -> bool:
    """Check voice_dna high-frequency marker presence.

    Returns True if observed_rate < 0.5 × expected_rate for any marker.
    """
    # Filter to mid+ length responses (≥20 chars) to avoid noise from
    # backchannel "嗯。" etc.
    valid_responses = [r for r in responses if len(r.text) >= 20]
    if not valid_responses:
        return False  # too few to signal

    for marker in fingerprint.voice_dna_markers:
        hits = 0
        for resp in valid_responses:
            if marker.is_regex:
                if isinstance(marker.pattern, re.Pattern) and marker.pattern.search(resp.text):
                    hits += 1
            else:
                if isinstance(marker.pattern, str) and marker.pattern in resp.text:
                    hits += 1

        observed_rate = hits / len(valid_responses)
        threshold = 0.5 * marker.expected_hit_rate

        if observed_rate < threshold:
            return True  # marker miss detected

    return False


# ============================================================
# Signal C — Sentence length distribution
# ============================================================

_BUCKET_THRESHOLDS = {
    "very_short": 15,
    "short": 30,
    "medium": 60,
    "long": float("inf"),
}


def _classify_sentence_length(avg_char_len: float) -> str:
    """Map average sentence char length to bucket."""
    if avg_char_len < _BUCKET_THRESHOLDS["very_short"]:
        return "very_short"
    if avg_char_len < _BUCKET_THRESHOLDS["short"]:
        return "short"
    if avg_char_len < _BUCKET_THRESHOLDS["medium"]:
        return "medium"
    return "long"


def _compute_avg_sentence_length(text: str) -> float:
    """Compute average sentence char length (Chinese-aware)."""
    # Split on Chinese/English sentence terminators
    sentences = re.split(r"[。！？!?]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 0.0

    total_chars = sum(len(s) for s in sentences)
    return total_chars / len(sentences)


def _scan_signal_c(
    responses: list[ReleasedResponse],
    fingerprint: DriftFingerprint,
) -> bool:
    """Check sentence length distribution vs bounds.

    Returns True if ≥3/5 responses fall outside [min_bucket, max_bucket].
    """
    if len(responses) < 3:
        return False  # too few to signal

    min_bucket = fingerprint.sentence_length_min_bucket
    max_bucket = fingerprint.sentence_length_max_bucket

    # Build bucket ordering
    bucket_order = ["very_short", "short", "medium", "long"]
    min_idx = bucket_order.index(min_bucket)
    max_idx = bucket_order.index(max_bucket)

    out_of_bounds = 0

    for resp in responses:
        avg_len = _compute_avg_sentence_length(resp.text)
        bucket = _classify_sentence_length(avg_len)
        bucket_idx = bucket_order.index(bucket)

        if bucket_idx < min_idx or bucket_idx > max_idx:
            out_of_bounds += 1

    # Trip if ≥3/5 out of bounds (design doc §4.1 Signal C)
    return out_of_bounds >= 3


# ============================================================
# Public API
# ============================================================

def scan_anti_patterns(
    responses: list[ReleasedResponse],
    soul: SoulSpec,
    fingerprint: DriftFingerprint,
    unlocked_facet_ids: tuple[str, ...],
) -> AntiPatternHits:
    """Run all three pre-filter signals.

    Args:
        responses: sampled assistant responses
        soul: Soul Spec (for reference; fingerprint already extracted)
        fingerprint: pre-compiled DriftFingerprint
        unlocked_facet_ids: currently unlocked facets (for rare-unlock-word filter)

    Returns:
        AntiPatternHits summarizing pre-filter results
    """
    # Determine which rare-unlock-words are active (conditions met)
    # For MVP: if a rare-unlock-word's associated facet is unlocked, allow it.
    # The full logic per §5.1 rare_unlock_words is condition-based; we simplify
    # to "facet unlocked → word allowed". Future: parse unlock_condition from spec.
    unlocked_rare = frozenset()  # MVP: no auto-unlock; orchestrator must signal

    # Signal A
    hard_hits, forbidden_hits, soft_hits = _scan_signal_a(
        responses,
        fingerprint,
        unlocked_rare,
    )

    # Signal B
    voice_dna_miss = _scan_signal_b(responses, fingerprint)

    # Signal C
    length_oob = _scan_signal_c(responses, fingerprint)

    return AntiPatternHits(
        hard_never_count=hard_hits,
        forbidden_pattern_count=forbidden_hits,
        soft_never_count=soft_hits,
        voice_dna_marker_miss=voice_dna_miss,
        sentence_length_out_of_bounds=length_oob,
    )
