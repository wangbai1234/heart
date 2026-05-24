"""
Concrete invariant predicates per the State Invariant Catalog (§5 of state_invariants.md).

Each function registers itself via InvariantRegistry and is available for:
- Layer 1 Hypothesis property tests via check_invariants(ctx)
- Layer 2 Runtime @invariant decorator on service methods

Author: Heart Platform
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from heart.infra.invariants import (
    InvariantContext,
    InvariantRegistry,
    Severity,
    invariant,
)


def _register_all() -> None:
    """Register all invariant predicates at module import time."""
    registry = InvariantRegistry.instance()

    # ── INV-M-* Memory invariants ────────────────────────────────

    registry.register(
        id="inv-m-3.l4-monotonic",
        name="L4 count monotonic",
        subsystem="memory",
        severity=Severity.FATAL,
        predicate=_inv_m_3_predicate,
        doc="L4 fact_count strictly non-decreasing across turns (sacred persistence). §02_memory_runtime.md:87",
    )

    registry.register(
        id="inv-m-5.multi-signal-promotion",
        name="Multi-signal L4 promotion gate",
        subsystem="memory",
        severity=Severity.FATAL,
        predicate=_inv_m_5_predicate,
        doc="Promotion to L4 requires ≥2 sacred_signals AND consolidation_round ≥ 1. §02_memory_runtime.md:99",
    )

    registry.register(
        id="inv-m-6.no-silent-loss",
        name="No silent memory loss",
        subsystem="memory",
        severity=Severity.WARN,
        predicate=_inv_m_6_predicate,
        doc="total_count across all layers ≥ total_count_{t-1} − decayed_at_t. §02_memory_runtime.md:139",
    )

    # ── INV-E-* Emotion invariants ────────────────────────────────

    registry.register(
        id="inv-e-1.inertia-cap",
        name="VAD inertia cap",
        subsystem="emotion",
        severity=Severity.FATAL,
        predicate=_inv_e_1_predicate,
        doc="Δvalence per turn ≤ inertia_cap. §03_emotion_state_machine.md:47",
    )

    registry.register(
        id="inv-e-2.stack-limit",
        name="Active emotion stack limit",
        subsystem="emotion",
        severity=Severity.FATAL,
        predicate=_inv_e_2_predicate,
        doc="|active_emotion_stack| ≤ MAX_CONCURRENT_EMOTIONS (5). §03_emotion_state_machine.md:50",
    )

    registry.register(
        id="inv-e-3.vad-range",
        name="VAD range check",
        subsystem="emotion",
        severity=Severity.FATAL,
        predicate=_inv_e_3_predicate,
        doc="VAD values in valid ranges: valence[-1,1], arousal[0,1], dominance[0,1]. §03_emotion_state_machine.md:51",
    )

    # ── INV-R-* Relationship invariants ────────────────────────────

    registry.register(
        id="inv-r-1.stage-monotonic",
        name="Relationship stage monotonic",
        subsystem="relationship",
        severity=Severity.FATAL,
        predicate=_inv_r_1_predicate,
        doc="Stage ordinal non-decreasing (regression only via gated regress paths). §04_relationship_phase_engine.md:55",
    )

    registry.register(
        id="inv-r-4.trust-asymmetry",
        name="Trust score asymmetry",
        subsystem="relationship",
        severity=Severity.WARN,
        predicate=_inv_r_4_predicate,
        doc="Trust builds slower than it falls: Δpositive ≤ 0.05, Δnegative ≥ −0.20. §04_relationship_phase_engine.md:120",
    )

    registry.register(
        id="inv-r-6.cold-war-no-progress",
        name="Cold war blocks progression",
        subsystem="relationship",
        severity=Severity.FATAL,
        predicate=_inv_r_6_predicate,
        doc="No stage progression while COLD_WAR special state is active. §04_relationship_phase_engine.md:145",
    )

    # ── INV-O-* Safety invariants ──────────────────────────────────

    registry.register(
        id="inv-o-2.message-severity-cap",
        name="Message severity not downgraded",
        subsystem="safety",
        severity=Severity.FATAL,
        predicate=_inv_o_2_predicate,
        doc="Message severity must not be downgraded after an upgrade. §07_agent_orchestration.md:120",
    )

    registry.register(
        id="inv-o-3.purple-blocked-from-soul",
        name="PURPLE blocked from Soul",
        subsystem="safety",
        severity=Severity.FATAL,
        predicate=_inv_o_3_predicate,
        doc="PURPLE-level user message never reaches Soul composition. §07_agent_orchestration.md:122",
    )


# ── Predicate implementations ────────────────────────────────────

def _inv_m_3_predicate(ctx: InvariantContext) -> bool:
    """L4 count must not decrease."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True  # Can't verify without both snapshots
    before_count = _get_l4_count(before)
    after_count = _get_l4_count(after)
    return after_count >= before_count


def _inv_m_5_predicate(ctx: InvariantContext) -> bool:
    """L4 promotion requires multi-signal gate."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_l4 = _get_l4_count(before)
    after_l4 = _get_l4_count(after)
    # If L4 didn't grow, gate is irrelevant
    if after_l4 <= before_l4:
        return True
    # Check that the promotion context had sufficient signals
    extra = ctx.extra or {}
    sacred_signals = extra.get("sacred_signals", [])
    consolidation_round = extra.get("consolidation_round", 0)
    return len(sacred_signals) >= 2 and consolidation_round >= 1


def _inv_m_6_predicate(ctx: InvariantContext) -> bool:
    """No silent memory loss across consolidation."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_total = _get_total_memory_count(before)
    after_total = _get_total_memory_count(after)
    decayed = _get_decayed_count(after) if hasattr(after, 'get') else 0
    return after_total >= before_total - decayed


def _inv_e_1_predicate(ctx: InvariantContext) -> bool:
    """VAD inertia cap per turn."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_v = _safe_vad_val(before, "valence")
    after_v = _safe_vad_val(after, "valence")
    delta = abs(after_v - before_v)
    max_change = _safe_vad_val(ctx.extra or {}, "max_valence_change", 0.15)
    return delta <= max_change


def _inv_e_2_predicate(ctx: InvariantContext) -> bool:
    """Active emotion stack must not exceed limit."""
    after = ctx.after_state
    if after is None:
        return True
    stack = after.get("active_stack") if isinstance(after, dict) else getattr(after, "active_stack", [])
    return len(stack) <= 5


def _inv_e_3_predicate(ctx: InvariantContext) -> bool:
    """VAD values in valid ranges."""
    after = ctx.after_state
    if after is None:
        return True
    v = _safe_vad_val(after, "valence", 0.0)
    a = _safe_vad_val(after, "arousal", 0.0)
    d = _safe_vad_val(after, "dominance", 0.0)
    return (-1.0 <= v <= 1.0) and (0.0 <= a <= 1.0) and (0.0 <= d <= 1.0)


def _inv_r_1_predicate(ctx: InvariantContext) -> bool:
    """Stage ordinal must be non-decreasing."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_stage = _get_stage_ordinal(before)
    after_stage = _get_stage_ordinal(after)
    # Regression is gated but possible — the check is that
    # evaluate() alone never regresses unless _check_regression is the code path.
    # For this predicate, we only flag if before > after without explicit regress.
    # Simplified: accept if stage didn't change or advanced; regress paths
    # are handled by the explicit regression check method.
    return after_stage >= before_stage


def _inv_r_4_predicate(ctx: InvariantContext) -> bool:
    """Trust asymmetry: builds slower than falls."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_trust = _safe_float_val(before, "trust_score", 0.5)
    after_trust = _safe_float_val(after, "trust_score", 0.5)
    delta = after_trust - before_trust
    if delta > 0:
        return delta <= 0.05
    return delta >= -0.20


def _inv_r_6_predicate(ctx: InvariantContext) -> bool:
    """No progress while COLD_WAR is active."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_stage = _get_stage_ordinal(before)
    after_stage = _get_stage_ordinal(after)
    if after_stage <= before_stage:
        return True  # No progression
    # Check for cold war in before state
    active_states = _get_active_special_states(before)
    if any(s.get("state_type") == "COLD_WAR" for s in active_states):
        return False  # Progression during cold war
    return True


def _inv_o_2_predicate(ctx: InvariantContext) -> bool:
    """Message severity must not be downgraded."""
    before = ctx.before_state
    after = ctx.after_state
    if before is None or after is None:
        return True
    before_sev = _severity_ordinal(before)
    after_sev = _severity_ordinal(after)
    return after_sev >= before_sev


def _inv_o_3_predicate(ctx: InvariantContext) -> bool:
    """PURPLE message must be blocked from Soul composition."""
    after = ctx.after_state
    if after is None:
        return True
    severity = _get_severity(after)
    blocked = ctx.extra.get("blocked_from_soul", False) if ctx.extra else False
    if severity == "PURPLE":
        return blocked
    return True


# ── Helpers ──────────────────────────────────────────────────────

def _get_l4_count(state: Any) -> int:
    if isinstance(state, dict):
        return state.get("l4_count", 0)
    return getattr(state, "l4_count", 0)


def _get_total_memory_count(state: Any) -> int:
    if isinstance(state, dict):
        return sum(state.get(layer, 0) for layer in ("l1_count", "l2_count", "l3_count", "l4_count"))
    return (
        getattr(state, "l1_count", 0)
        + getattr(state, "l2_count", 0)
        + getattr(state, "l3_count", 0)
        + getattr(state, "l4_count", 0)
    )


def _get_decayed_count(state: Any) -> int:
    if isinstance(state, dict):
        return state.get("decayed_count", 0)
    return getattr(state, "decayed_count", 0)


def _safe_vad_val(state: Any, dim: str, default: float = 0.0) -> float:
    if isinstance(state, dict):
        key = f"vad_{dim}" if not dim.startswith("vad_") else dim
        val = state.get(key, None)
        if val is None:
            val = state.get(dim, default)
        return float(val) if val is not None else default
    val = getattr(state, f"vad_{dim}", None)
    if val is None:
        val = getattr(state, dim, default)
    return float(val) if val is not None else default


def _get_stage_ordinal(state: Any) -> int:
    stages = {
        "STRANGER": 0, "ACQUAINTANCE": 1, "FRIEND": 2,
        "CONFIDANT": 3, "ROMANTIC_INTEREST": 4, "LOVER": 5, "BONDED": 6,
    }
    if isinstance(state, dict):
        return stages.get(state.get("current_stage", "").upper(), -1)
    return stages.get(getattr(state, "current_stage", "").upper(), -1)


def _get_active_special_states(state: Any) -> List[Dict]:
    if isinstance(state, dict):
        return state.get("active_special_states", [])
    return getattr(state, "active_special_states", [])


def _safe_float_val(state: Any, key: str, default: float = 0.0) -> float:
    if isinstance(state, dict):
        return float(state.get(key, default))
    return float(getattr(state, key, default))


_SEVERITY_ORDER = {"GREEN": 0, "YELLOW": 1, "PURPLE": 2}


def _severity_ordinal(result: Any) -> int:
    sev = _get_severity(result)
    return _SEVERITY_ORDER.get(sev, -1)


def _get_severity(result: Any) -> str:
    if isinstance(result, dict):
        return result.get("severity", "GREEN")
    return getattr(result, "severity", "GREEN")


# ── Auto-register at import ──────────────────────────────────────
_register_all()
