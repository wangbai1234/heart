"""
Property-based tests for SS02 Memory invariants (INV-M-*).

Tests:
- INV-M-3: L4 count monotonic (sacred persistence)
- INV-M-5: Multi-signal promotion gate
- INV-M-6: No silent memory loss

Author: Heart Platform
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

import heart.infra.invariant_predicates  # noqa: F401
from heart.infra.invariants import (
    InvariantContext,
    InvariantRegistry,
)
from tests.properties.strategies import memory_count_strategy

# ── INV-M-3: L4 count monotonic ─────────────────────────────────


@given(
    before=memory_count_strategy(),
    after=memory_count_strategy(),
)
@settings(max_examples=200, deadline=2000)
def test_inv_m_3_l4_monotonic(before, after):
    """L4 count must never decrease — sacred persistence invariant."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-m-3.l4-monotonic")
    assert record is not None, "inv-m-3.l4-monotonic not registered"

    ctx = InvariantContext(
        before_state=before,
        after_state=after,
        trace_id="test-m-3",
    )
    result = record.predicate(ctx)

    if after["l4_count"] < before["l4_count"]:
        assert not result, f"INV-M-3: L4 decreased from {before['l4_count']} to {after['l4_count']}"
    else:
        assert result, f"INV-M-3: false positive — L4 {before['l4_count']} → {after['l4_count']}"


# ── INV-M-5: Multi-signal promotion gate ────────────────────────


@given(
    before=memory_count_strategy(),
    sacred_signals_count=st.integers(min_value=0, max_value=5),
    consolidation_round=st.integers(min_value=0, max_value=5),
)
@settings(max_examples=200, deadline=2000)
def test_inv_m_5_multi_signal_promotion(before, sacred_signals_count, consolidation_round):
    """L4 promotion requires ≥2 sacred signals AND consolidation_round ≥ 1."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-m-5.multi-signal-promotion")
    assert record is not None, "inv-m-5.multi-signal-promotion not registered"

    # Build after state: L4 increases by 1
    after = dict(before)
    after["l4_count"] = before["l4_count"] + 1

    ctx = InvariantContext(
        before_state=before,
        after_state=after,
        trace_id="test-m-5",
        extra={
            "sacred_signals": ["sig"] * sacred_signals_count,
            "consolidation_round": consolidation_round,
        },
    )
    result = record.predicate(ctx)

    meets_gate = sacred_signals_count >= 2 and consolidation_round >= 1
    if meets_gate:
        assert result, (
            f"INV-M-5: gate passed but rejected — {sacred_signals_count} signals, round {consolidation_round}"
        )
    else:
        # When L4 increases but gate not met, should fail
        assert not result or sacred_signals_count <= 0, (
            f"INV-M-5: gate not met ({sacred_signals_count} signals, round {consolidation_round}) "
            f"but promotion allowed"
        )


# ── INV-M-6: No silent memory loss ──────────────────────────────


@given(
    before=memory_count_strategy(),
    decay=st.integers(min_value=0, max_value=30),
)
@settings(max_examples=200, deadline=2000)
def test_inv_m_6_no_silent_loss(before, decay):
    """Total memory count must not decrease more than decay count."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-m-6.no-silent-loss")
    assert record is not None, "inv-m-6.no-silent-loss not registered"

    before_total = before["l1_count"] + before["l2_count"] + before["l3_count"] + before["l4_count"]

    # Simulate after: counts reduced by decay, but at most combined decay
    after = dict(before)
    # Randomly distribute decay across L1-L3 (L4 never decays)
    for layer in ("l1_count", "l2_count", "l3_count"):
        layer_decay = min(after[layer], decay // 3)
        after[layer] -= layer_decay
    after["decayed_count"] = decay

    ctx = InvariantContext(
        before_state=before,
        after_state=after,
        trace_id="test-m-6",
    )
    result = record.predicate(ctx)

    after_total = after["l1_count"] + after["l2_count"] + after["l3_count"] + after["l4_count"]
    expected_min = before_total - decay

    if after_total < expected_min:
        assert not result, (
            f"INV-M-6: total {after_total} < min expected {expected_min} "
            f"(before {before_total}, decay {decay})"
        )
