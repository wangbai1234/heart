"""
Property-based tests for SS03 Emotion invariants (INV-E-*).

Tests:
- INV-E-2: Active emotion stack ≤ MAX_CONCURRENT_EMOTIONS (5)
- INV-E-3: VAD values in valid ranges

Author: Heart Platform
"""

from __future__ import annotations

from hypothesis import given, settings

import heart.infra.invariant_predicates  # noqa: F401
from heart.infra.invariants import InvariantContext, InvariantRegistry
from tests.properties.strategies import emotion_state_dict_strategy

# ── INV-E-2: Stack limit ────────────────────────────────────────


@given(state=emotion_state_dict_strategy())
@settings(max_examples=200, deadline=2000)
def test_inv_e_2_stack_limit(state):
    """Active emotion stack must not exceed 5 concurrent emotions."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-e-2.stack-limit")
    assert record is not None, "inv-e-2.stack-limit not registered"

    ctx = InvariantContext(
        before_state=None,
        after_state=state,
        trace_id="test-e-2",
    )
    result = record.predicate(ctx)

    stack_size = len(state.get("active_stack", []))

    if stack_size > 5:
        assert not result, f"INV-E-2: stack size {stack_size} exceeds limit"
        # Check mutation in after state shouldn't silently pass
        for entry in state["active_stack"]:
            assert entry["intensity"] >= 0.05, (
                f"INV-E-2: stack entry below eviction threshold ({entry['intensity']})"
            )
    else:
        assert result, f"INV-E-2: false positive for stack size {stack_size}"


# ── INV-E-3: VAD range ──────────────────────────────────────────


@given(state=emotion_state_dict_strategy())
@settings(max_examples=200, deadline=2000)
def test_inv_e_3_vad_range(state):
    """VAD values must be within valid ranges."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-e-3.vad-range")
    assert record is not None, "inv-e-3.vad-range not registered"

    ctx = InvariantContext(
        before_state=None,
        after_state=state,
        trace_id="test-e-3",
    )
    result = record.predicate(ctx)

    v = state.get("vad_valence", 0)
    a = state.get("vad_arousal", 0)
    d = state.get("vad_dominance", 0)

    in_range = (-1.0 <= v <= 1.0) and (0.0 <= a <= 1.0) and (0.0 <= d <= 1.0)

    if in_range:
        assert result, f"INV-E-3: false positive for valid VAD ({v:.2f}, {a:.2f}, {d:.2f})"
    else:
        assert not result, f"INV-E-3: out-of-range VAD ({v:.2f}, {a:.2f}, {d:.2f}) but check passed"
