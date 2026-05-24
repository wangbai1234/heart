"""
Property-based tests for SS04 Relationship invariants (INV-R-*).

Tests:
- INV-R-1: Stage ordinal non-decreasing
- INV-R-4: Trust score asymmetry
- INV-R-6: Cold war blocks progression

Author: Heart Platform
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from heart.infra.invariants import InvariantContext, InvariantRegistry
import heart.infra.invariant_predicates  # noqa: F401

from tests.properties.strategies import relationship_state_strategy


# ── INV-R-1: Stage monotonic ────────────────────────────────────

@given(
    before=relationship_state_strategy(),
    after=relationship_state_strategy(),
)
@settings(max_examples=200, deadline=2000)
def test_inv_r_1_stage_monotonic(before, after):
    """Stage ordinal must be non-decreasing."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-r-1.stage-monotonic")
    assert record is not None, "inv-r-1.stage-monotonic not registered"

    ctx = InvariantContext(
        before_state=before,
        after_state=after,
        trace_id="test-r-1",
    )
    result = record.predicate(ctx)

    stages = {
        "STRANGER": 0, "ACQUAINTANCE": 1, "FRIEND": 2,
        "CONFIDANT": 3, "ROMANTIC_INTEREST": 4, "LOVER": 5, "BONDED": 6,
    }
    before_ord = stages.get(before["current_stage"].upper(), -1)
    after_ord = stages.get(after["current_stage"].upper(), -1)

    if after_ord < before_ord:
        assert not result, (
            f"INV-R-1: stage regressed from {before['current_stage']} "
            f"to {after['current_stage']}"
        )
    else:
        assert result, f"INV-R-1: false positive for {before['current_stage']} → {after['current_stage']}"


# ── INV-R-4: Trust asymmetry ────────────────────────────────────

@given(
    before=relationship_state_strategy(),
    delta=st.floats(min_value=-0.5, max_value=0.5),
)
@settings(max_examples=200, deadline=2000)
def test_inv_r_4_trust_asymmetry(before, delta):
    """Trust builds slower than falls: Δpos ≤ 0.05, Δneg ≥ -0.20."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-r-4.trust-asymmetry")
    assert record is not None, "inv-r-4.trust-asymmetry not registered"

    after = dict(before)
    after["trust_score"] = max(0.0, min(1.0, before["trust_score"] + delta))

    ctx = InvariantContext(
        before_state=before,
        after_state=after,
        trace_id="test-r-4",
    )
    result = record.predicate(ctx)

    actual_delta = after["trust_score"] - before["trust_score"]

    if actual_delta > 0.05:
        assert not result, (
            f"INV-R-4: trust increased by {actual_delta:.3f} (> 0.05)"
        )
    elif actual_delta < -0.20:
        assert not result, (
            f"INV-R-4: trust dropped by {actual_delta:.3f} (< -0.20)"
        )
    else:
        # actual_delta in [-0.20, 0.05] — should pass
        assert result, (
            f"INV-R-4: false positive for trust delta {actual_delta:.3f}"
        )


# ── INV-R-6: Cold war blocks progression ────────────────────────

@given(state=relationship_state_strategy())
@settings(max_examples=200, deadline=2000)
def test_inv_r_6_cold_war_no_progress(state):
    """No stage progression while COLD_WAR is active."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-r-6.cold-war-no-progress")
    assert record is not None, "inv-r-6.cold-war-no-progress not registered"

    # Create an after state with a higher stage
    after = dict(state)
    stages = [
        "STRANGER", "ACQUAINTANCE", "FRIEND", "CONFIDANT",
        "ROMANTIC_INTEREST", "LOVER", "BONDED",
    ]
    current_idx = stages.index(state["current_stage"])
    if current_idx + 1 < len(stages):
        after["current_stage"] = stages[current_idx + 1]

    ctx = InvariantContext(
        before_state=state,
        after_state=after,
        trace_id="test-r-6",
    )
    result = record.predicate(ctx)

    has_cold_war = any(
        s.get("state_type") == "COLD_WAR"
        for s in state.get("active_special_states", [])
    )

    if has_cold_war and after["current_stage"] != state["current_stage"]:
        assert not result, (
            f"INV-R-6: progression during COLD_WAR from "
            f"{state['current_stage']} to {after['current_stage']}"
        )
    elif not has_cold_war or after["current_stage"] == state["current_stage"]:
        # No cold war or no actual progression — should pass
        assert result, (
            f"INV-R-6: false positive — cold_war={has_cold_war}, "
            f"progressing={after['current_stage'] != state['current_stage']}"
        )
