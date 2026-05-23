"""
Drift Detector - SS01 Soul Spec §6.5 机制 B

Detects persona drift (voice_dna loss, anti_pattern violations, style drift)
asynchronously (post-response-release) using a cheap LLM (Haiku) with 70%
pre-filter skip rate.

Design doc: docs/design/drift_detector.md
Spec authority: runtime_specs/01_identity_anchor_soul_spec.md §6.5, §10.1

Author: 心屿团队
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from uuid import UUID

from .anchor_injector import DriftEvidence
from .anti_pattern_scanner import AntiPatternHits, scan_anti_patterns
from .drift_fingerprint import DriftFingerprint, build_fingerprints
from .drift_llm_client import DriftLLMClient, LLMDriftResult
from .drift_score_fuser import compute_final_score, should_emit_reinforce
from .registry import get_soul_registry


# ============================================================
# Types (per design doc §2)
# ============================================================


@dataclass(frozen=True)
class ReleasedResponse:
    """Single assistant response that was released to the user."""

    turn_index: int
    text: str
    was_rerolled: bool = False  # True if Mechanism C rerolled this
    was_fallback: bool = False  # True if DP-3 system fallback


@dataclass(frozen=True)
class SASSnapshotForDrift:
    """Snapshot of Soul Activation State fields needed for drift check."""

    current_drift_score: float  # [0, 1], the previous EMA
    last_drift_check_at: Optional[str] = None  # ISO8601
    unlocked_facet_ids: tuple[str, ...] = ()  # for rare-unlock-word filter


@dataclass(frozen=True)
class DriftCheckRequest:
    """Request to evaluate drift for a (user, character) pair."""

    user_id: UUID
    character_id: str
    soul_spec_version: str
    turn_index: int
    recent_assistant_responses: list[ReleasedResponse]
    sas_snapshot: SASSnapshotForDrift
    daily_llm_call_count: int = 0


class DriftDecision(str, Enum):
    """Outcome of drift check."""

    SKIPPED_PREFILTER = "skipped_prefilter"
    SKIPPED_COSTCAP = "skipped_costcap"
    LLM_EVALUATED = "llm_evaluated"
    LLM_TIMEOUT = "llm_timeout"


@dataclass(frozen=True)
class DriftEvent:
    """Drift event to be written to SAS (matches §5.2 schema)."""

    drift_type: str  # "voice_dna_loss" | "anti_pattern_match" etc
    drift_score: float
    turns_analyzed: list[int]
    sample_messages: list[str]
    detected_patterns: list[str]
    correction_applied: str = "reinforce_anchor"


@dataclass(frozen=True)
class DriftDebugInfo:
    """Observability — what signals fired, raw LLM response."""

    prefilter_hits: AntiPatternHits
    sampled_turn_indices: list[int]
    llm_raw_score: Optional[float] = None
    llm_timeout_occurred: bool = False
    cold_session: bool = False


@dataclass(frozen=True)
class DriftCheckResult:
    """Result of drift evaluation."""

    drift_score: float  # [0, 1], to write to SAS.current_drift_score
    decision: DriftDecision
    evidence: Optional[DriftEvidence] = None  # populated iff REINFORCE should fire
    drift_event: Optional[DriftEvent] = None  # populated iff drift detected
    llm_used: bool = False
    latency_ms: int = 0
    debug: Optional[DriftDebugInfo] = None


# ============================================================
# Sampler (per design doc §4.5)
# ============================================================


def sample_responses(history: list[ReleasedResponse]) -> list[ReleasedResponse]:
    """Sample last 5 valid responses from history.

    Filters out:
    - was_fallback (DP-3 system fallbacks)
    - len(text) < 10 (too thin to signal)

    Returns chronological order (oldest first).
    """
    sampled = []
    for r in reversed(history):
        if r.was_fallback:
            continue
        if len(r.text) < 10:
            continue
        sampled.append(r)
        if len(sampled) == 5:
            break

    sampled.reverse()  # chronological
    return sampled


def should_invoke_llm_for_sample(sampled: list[ReleasedResponse]) -> bool:
    """Cold-session protection: require ≥3 valid responses."""
    return len(sampled) >= 3


# ============================================================
# DriftDetector
# ============================================================


class DriftDetector:
    """Asynchronous drift detector using pre-filter + cheap LLM.

    Thread-safe — no shared mutable state across (user, character).
    Pre-compiles per-soul fingerprints at __init__ and stores in
    MappingProxyType for lock-free concurrent reads.
    """

    _COST_CAP_PER_USER_PER_DAY = 20
    _LLM_TIMEOUT_SECONDS = 3.0

    def __init__(
        self,
        registry=None,
        llm_client: Optional[DriftLLMClient] = None,
    ):
        """Initialize drift detector.

        Args:
            registry: SoulRegistry (defaults to singleton).
            llm_client: DriftLLMClient (for testing; defaults to real Haiku).
        """
        self._registry = registry or get_soul_registry()
        self._llm_client = llm_client or DriftLLMClient()

        # Pre-compile per-soul fingerprints at startup (§4.2 pre-compilation)
        self._fingerprints = build_fingerprints(self._registry)

    async def evaluate(self, request: DriftCheckRequest) -> DriftCheckResult:
        """Evaluate drift for a (user, character) pair.

        Per design doc §3 flow:
        1. Sample responses (§4.5)
        2. Pre-filter scan (§4.1)
        3. Decide: skip or LLM?
        4. If LLM: call + fuse score (§4.3)
        5. Build evidence if REINFORCE threshold crossed (§4.4)
        6. Return result
        """
        start_time_ms = int(time.time() * 1000)

        # 1. Sample
        sampled = sample_responses(request.recent_assistant_responses)

        # Cold-session guard
        if not should_invoke_llm_for_sample(sampled):
            return DriftCheckResult(
                drift_score=request.sas_snapshot.current_drift_score,
                decision=DriftDecision.SKIPPED_PREFILTER,
                latency_ms=int(time.time() * 1000) - start_time_ms,
                debug=DriftDebugInfo(
                    prefilter_hits=AntiPatternHits(),
                    sampled_turn_indices=[],
                    cold_session=True,
                ),
            )

        # 2. Pre-filter scan
        soul = self._registry.get_soul(
            request.character_id,
            request.soul_spec_version,
        )
        fingerprint = self._fingerprints.get((request.character_id, request.soul_spec_version))
        if fingerprint is None:
            # Fallback for souls without fingerprint (shouldn't happen)
            fingerprint = DriftFingerprint.empty()

        prefilter_hits = scan_anti_patterns(
            responses=sampled,
            soul=soul,
            fingerprint=fingerprint,
            unlocked_facet_ids=request.sas_snapshot.unlocked_facet_ids,
        )

        prev_ema = request.sas_snapshot.current_drift_score

        # 3. Decide: skip or LLM?
        needs_llm = prefilter_hits.any_signal_tripped()

        # Cost cap check
        if needs_llm and request.daily_llm_call_count >= self._COST_CAP_PER_USER_PER_DAY:
            # Cost cap hit — pre-filter only, apply floors
            final_score = compute_final_score(
                llm_score=None,
                prefilter_hits=prefilter_hits,
                prev_ema=prev_ema,
            )
            return DriftCheckResult(
                drift_score=final_score,
                decision=DriftDecision.SKIPPED_COSTCAP,
                latency_ms=int(time.time() * 1000) - start_time_ms,
                debug=DriftDebugInfo(
                    prefilter_hits=prefilter_hits,
                    sampled_turn_indices=[r.turn_index for r in sampled],
                ),
            )

        llm_result: Optional[LLMDriftResult] = None

        if needs_llm:
            # 4. LLM call
            llm_result = await self._llm_client.evaluate_drift(
                soul=soul,
                responses=sampled,
                timeout_seconds=self._LLM_TIMEOUT_SECONDS,
            )

        # 5. Fuse score
        llm_score = llm_result.drift_score if llm_result else None
        final_score = compute_final_score(
            llm_score=llm_score,
            prefilter_hits=prefilter_hits,
            prev_ema=prev_ema,
        )

        # 6. Build evidence + drift_event if threshold crossed
        evidence: Optional[DriftEvidence] = None
        drift_event: Optional[DriftEvent] = None

        if should_emit_reinforce(
            final_score=final_score,
            prev_ema=prev_ema,
            prefilter_hits=prefilter_hits,
            llm_violations_count=len(llm_result.violations) if llm_result else 0,
        ):
            # Build DriftEvidence (reuse existing type from anchor_injector)
            if llm_result and llm_result.violations:
                sample_messages = tuple(v["sample_excerpt"] for v in llm_result.violations[:3])
                detected_patterns = tuple(v["detected_pattern"] for v in llm_result.violations[:3])
                required_patterns = tuple(llm_result.required_patterns[:2])

                evidence = DriftEvidence(
                    sample_messages=sample_messages,
                    detected_patterns=detected_patterns,
                    required_patterns=required_patterns,
                    drift_type=llm_result.drift_type,
                )

                drift_event = DriftEvent(
                    drift_type=llm_result.drift_type,
                    drift_score=final_score,
                    turns_analyzed=[r.turn_index for r in sampled],
                    sample_messages=list(sample_messages),
                    detected_patterns=list(detected_patterns),
                )

        # Determine decision
        if llm_result is None:
            decision = DriftDecision.SKIPPED_PREFILTER
        elif llm_result.timeout_occurred:
            decision = DriftDecision.LLM_TIMEOUT
        else:
            decision = DriftDecision.LLM_EVALUATED

        return DriftCheckResult(
            drift_score=final_score,
            decision=decision,
            evidence=evidence,
            drift_event=drift_event,
            llm_used=(llm_result is not None and not llm_result.timeout_occurred),
            latency_ms=int(time.time() * 1000) - start_time_ms,
            debug=DriftDebugInfo(
                prefilter_hits=prefilter_hits,
                sampled_turn_indices=[r.turn_index for r in sampled],
                llm_raw_score=llm_score,
                llm_timeout_occurred=(llm_result.timeout_occurred if llm_result else False),
            ),
        )


# ============================================================
# Singleton pattern (for production; tests use DriftDetector() directly)
# ============================================================

_drift_detector: Optional[DriftDetector] = None


def get_drift_detector() -> DriftDetector:
    """Get singleton DriftDetector instance."""
    global _drift_detector
    if _drift_detector is None:
        _drift_detector = DriftDetector()
    return _drift_detector


def reset_drift_detector() -> None:
    """Reset singleton (for tests)."""
    global _drift_detector
    _drift_detector = None
