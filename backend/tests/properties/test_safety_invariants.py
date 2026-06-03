"""
Property-based tests for SS07 Safety invariants (INV-O-*).

Tests:
- INV-O-2: Message severity must not be downgraded
- INV-O-3: PURPLE blocked from Soul

Author: Heart Platform
"""

from __future__ import annotations

from hypothesis import given, settings

import heart.infra.invariant_predicates  # noqa: F401
from heart.infra.invariants import InvariantContext, InvariantRegistry
from tests.properties.strategies import classification_result_strategy

# ── INV-O-2: Severity not downgraded ────────────────────────────


@given(
    before=classification_result_strategy(),
)
@settings(max_examples=200, deadline=2000)
def test_inv_o_2_severity_not_downgraded(before):
    """Message severity must not be downgraded after an upgrade."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-o-2.message-severity-cap")
    assert record is not None, "inv-o-2.message-severity-cap not registered"

    severity_order = {"GREEN": 0, "YELLOW": 1, "PURPLE": 2}

    # Generate after with potentially lower severity
    for after_sev in ("GREEN", "YELLOW", "PURPLE"):
        after = dict(before)
        after["severity"] = after_sev

        ctx = InvariantContext(
            before_state=before,
            after_state=after,
            trace_id="test-o-2",
        )
        result = record.predicate(ctx)

        before_ord = severity_order.get(before["severity"], -1)
        after_ord = severity_order.get(after_sev, -1)

        if after_ord < before_ord:
            assert not result, (
                f"INV-O-2: severity downgraded from {before['severity']} to {after_sev}"
            )
        else:
            assert result, f"INV-O-2: false positive for {before['severity']} → {after_sev}"


# ── INV-O-3: PURPLE blocked from Soul ───────────────────────────


@given(result=classification_result_strategy())
@settings(max_examples=200, deadline=2000)
def test_inv_o_3_purple_blocked_from_soul(result):
    """PURPLE-level message must be blocked from Soul composition."""
    registry = InvariantRegistry.instance()
    record = registry.get("inv-o-3.purple-blocked-from-soul")
    assert record is not None, "inv-o-3.purple-blocked-from-soul not registered"

    # Test blocked case (PURPLE + blocked=True → should pass)
    ctx_blocked = InvariantContext(
        before_state=None,
        after_state=result,
        trace_id="test-o-3-blocked",
        extra={"blocked_from_soul": True},
    )
    result_blocked = record.predicate(ctx_blocked)

    # Test unblocked case (PURPLE + blocked=False → should fail)
    ctx_unblocked = InvariantContext(
        before_state=None,
        after_state=result,
        trace_id="test-o-3-unblocked",
        extra={"blocked_from_soul": False},
    )
    result_unblocked = record.predicate(ctx_unblocked)

    if result.get("severity") == "PURPLE":
        # Must block PURPLE messages
        assert result_blocked, "INV-O-3: PURPLE message not blocked"
        assert not result_unblocked, "INV-O-3: PURPLE message passed through unblocked"
    else:
        # Non-PURPLE: should pass regardless
        assert result_blocked, f"INV-O-3: false positive for {result.get('severity')} (blocked)"
        assert result_unblocked, f"INV-O-3: false positive for {result.get('severity')} (unblocked)"
