"""
Drift Fingerprint - per-soul compiled patterns for fast pre-filter.

Builds at DriftDetector startup and stores in MappingProxyType for
lock-free concurrent access.

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .registry import SoulRegistry
    from .schema_validator import SoulSpec


@dataclass(frozen=True)
class VoiceDNAMarker:
    """Expected marker for a high-frequency voice_dna pattern."""

    vd_id: str
    pattern: str | re.Pattern  # literal or regex to search for
    expected_hit_rate: float  # e.g. 0.4 = expect in ≥40% of responses
    is_regex: bool = False


@dataclass(frozen=True)
class DriftFingerprint:
    """Compiled per-soul drift detection fingerprint.

    Built once at startup from Soul Spec, then frozen for lock-free reads.
    """

    character_id: str
    soul_spec_version: str

    # Signal A - anti-pattern literals
    hard_never: frozenset[str]
    soft_never: frozenset[str]
    forbidden_patterns: tuple[re.Pattern, ...]  # pre-compiled regex
    rare_unlock_words: frozenset[str]

    # Signal B - voice_dna markers
    voice_dna_markers: tuple[VoiceDNAMarker, ...]

    # Signal C - sentence length bounds
    sentence_length_min_bucket: str  # "very_short" | "short" | "medium" | "long"
    sentence_length_max_bucket: str

    @staticmethod
    def empty() -> DriftFingerprint:
        """Empty fingerprint for fallback."""
        return DriftFingerprint(
            character_id="",
            soul_spec_version="",
            hard_never=frozenset(),
            soft_never=frozenset(),
            forbidden_patterns=(),
            rare_unlock_words=frozenset(),
            voice_dna_markers=(),
            sentence_length_min_bucket="very_short",
            sentence_length_max_bucket="long",
        )


def _build_fingerprint(soul: SoulSpec) -> DriftFingerprint:
    """Build fingerprint from a single Soul Spec."""
    # Signal A — anti-patterns
    hard_never = frozenset(soul.identity_anchor.anti_patterns.hard_never)
    soft_never = frozenset(soul.identity_anchor.anti_patterns.soft_never or [])
    rare_unlock = frozenset(
        w.word for w in (soul.identity_anchor.anti_patterns.rare_unlock_words or [])
    )

    forbidden_patterns = tuple(
        re.compile(fp.regex) for fp in (soul.identity_anchor.anti_patterns.forbidden_patterns or [])
    )

    # Signal B — voice_dna high-frequency markers
    markers: list[VoiceDNAMarker] = []
    for vd in soul.identity_anchor.voice_dna:
        if vd.frequency != "high":
            continue

        # Extract markers from examples
        # For MVP: look for literal repeating patterns in examples
        # Rin vd-001: "……" appears in all examples → marker
        # Rin vd-NEW-A: digit patterns → regex marker
        marker_pattern = _extract_marker_from_voice_dna(vd)
        if marker_pattern:
            markers.append(marker_pattern)

    # Signal C — sentence length bounds
    sent_bounds = soul.cognitive_style.expression.sentence_length.evolution_bound
    min_bucket = sent_bounds[0]
    max_bucket = sent_bounds[1]

    return DriftFingerprint(
        character_id=soul.character_id,
        soul_spec_version=soul.spec_version,
        hard_never=hard_never,
        soft_never=soft_never,
        forbidden_patterns=forbidden_patterns,
        rare_unlock_words=rare_unlock,
        voice_dna_markers=tuple(markers),
        sentence_length_min_bucket=min_bucket,
        sentence_length_max_bucket=max_bucket,
    )


def _extract_marker_from_voice_dna(vd) -> VoiceDNAMarker | None:
    """Extract searchable marker from voice_dna entry.

    Heuristics (MVP):
    - If examples contain "……" → literal marker
    - If examples contain digit patterns → regex marker for time precision
    - Otherwise None (can't auto-extract — skip signal B for this vd)
    """
    if not vd.examples:
        return None

    # Filter to string examples only (examples can be str or dict per schema)
    string_examples = [ex for ex in vd.examples if isinstance(ex, str)]
    if not string_examples:
        return None

    # Check for ellipsis marker (Rin vd-001)
    if any("……" in ex for ex in string_examples):
        return VoiceDNAMarker(
            vd_id=vd.id,
            pattern="……",
            expected_hit_rate=0.4,  # expect in ≥40% of mid+ length responses
            is_regex=False,
        )

    # Check for time precision marker (Rin vd-NEW-A)
    # Pattern: digit + time unit (天|月|日|号|条|分钟 etc)
    time_pattern = r"\d+\s*(?:天|月|日|号|条|分钟|小时|年)"
    if any(re.search(time_pattern, ex) for ex in string_examples):
        return VoiceDNAMarker(
            vd_id=vd.id,
            pattern=re.compile(time_pattern),
            expected_hit_rate=0.3,  # slightly lower — not every response mentions time
            is_regex=True,
        )

    # Future: extract more patterns (凛式反问 etc.) via regex/heuristic
    return None


def build_fingerprints(
    registry: SoulRegistry,
) -> MappingProxyType[tuple[str, str], DriftFingerprint]:
    """Build all fingerprints at startup.

    Returns immutable mapping: (character_id, version) → DriftFingerprint.
    """
    fingerprints = {}

    for character_id in registry.list_characters():
        for version in registry.list_versions(character_id):
            soul = registry.get_soul(character_id, version)
            fp = _build_fingerprint(soul)
            fingerprints[(character_id, version)] = fp

    return MappingProxyType(fingerprints)
