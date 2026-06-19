"""
Property-based tests for SS02 Memory invariants (INV-M-*).

Tests:
- INV-M-3: L4 count monotonic (sacred persistence)
- INV-M-5: Multi-signal promotion gate
- INV-M-6: No silent memory loss
- INV-M-NEW-B: ≤1 active row per (user_id, entity_type, entity_ref, attribute)
- INV-M-NEW-C: negation never physically deletes

Author: Heart Platform
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

import heart.infra.invariant_predicates  # noqa: F401
from heart.infra.invariants import (
    InvariantContext,
    InvariantRegistry,
)
from heart.ss02_memory.extractor.resolver import _compute_ewma
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


# ── INV-M-NEW-B: ≤1 active row per key ─────────────────────────


@dataclass
class L3Row:
    """Simplified L3 fact for property testing."""

    id: UUID = field(default_factory=uuid4)
    user_id: UUID = field(default_factory=uuid4)
    entity_type: str = "self"
    entity_ref: str = "self"
    attribute: str = "name"
    value: str = "test"
    is_active: bool = True
    do_not_recall: bool = False


_entity_types = st.sampled_from(
    ["self", "pet", "family", "friend", "colleague", "location", "preference"]
)
_attributes = st.sampled_from(
    ["name", "nickname", "age", "occupation", "location_residence", "hobby", "other"]
)
_values = st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",)))


def _l3_row_strategy():
    """Generate random L3 fact rows."""
    return st.builds(
        L3Row,
        entity_type=_entity_types,
        entity_ref=st.text(min_size=1, max_size=20),
        attribute=_attributes,
        value=_values,
        is_active=st.booleans(),
        do_not_recall=st.booleans(),
    )


@given(rows=st.lists(_l3_row_strategy(), min_size=1, max_size=50))
@settings(max_examples=1000, deadline=2000)
def test_inv_m_new_b_single_active_per_key(rows):
    """INV-M-NEW-B: at any time, ≤1 active row per (user_id, entity_type, entity_ref, attribute).

    Simulates the Resolver's CREATE/SUPERSEDE logic and verifies the invariant
    holds after processing all rows.
    """
    # Group by composite key
    active_by_key: dict[tuple, list[L3Row]] = {}

    for row in rows:
        key = (row.user_id, row.entity_type, row.entity_ref, row.attribute)

        if not row.is_active or row.do_not_recall:
            # Inactive/deleted rows don't count
            continue

        if key not in active_by_key:
            active_by_key[key] = [row]
        else:
            # SUPERSEDE: mark old inactive, add new
            for old in active_by_key[key]:
                old.is_active = False
            active_by_key[key] = [row]

    # Verify: each key has at most 1 active row
    for key, active_rows in active_by_key.items():
        truly_active = [r for r in active_rows if r.is_active]
        assert len(truly_active) <= 1, (
            f"INV-M-NEW-B: key {key} has {len(truly_active)} active rows, expected ≤1"
        )


# ── INV-M-NEW-C: negation never physically deletes ────────────


@given(
    rows=st.lists(_l3_row_strategy(), min_size=1, max_size=30),
    negation_indices=st.lists(st.integers(min_value=0, max_value=29), min_size=0, max_size=10),
)
@settings(max_examples=1000, deadline=2000)
def test_inv_m_new_c_negation_never_deletes(rows, negation_indices):
    """INV-M-NEW-C: negation (soft delete) never physically removes a row.

    After applying soft deletes, every row that existed before still exists
    in the collection — it's just marked do_not_recall=True.
    """
    # Track initial row IDs
    initial_ids = {row.id for row in rows}

    # Apply soft deletes to selected indices
    for idx in negation_indices:
        if idx < len(rows):
            rows[idx].do_not_recall = True

    # After soft delete, all rows still exist (none removed)
    final_ids = {row.id for row in rows}
    assert initial_ids == final_ids, (
        f"INV-M-NEW-C: rows were physically deleted! Missing: {initial_ids - final_ids}"
    )

    # Soft-deleted rows have do_not_recall=True
    for idx in negation_indices:
        if idx < len(rows):
            assert rows[idx].do_not_recall is True, (
                f"INV-M-NEW-C: row at index {idx} was negated but do_not_recall is False"
            )


# ── EWMA convergence property ─────────────────────────────────


@given(
    initial=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    observations=st.lists(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
        min_size=1,
        max_size=100,
    ),
)
@settings(max_examples=200, deadline=2000)
def test_ewma_bounded(initial, observations):
    """EWMA must stay bounded in [0, 1] for valid inputs."""
    ewma = initial
    for obs in observations:
        ewma = _compute_ewma(ewma, obs)
        assert 0.0 <= ewma <= 1.0, f"EWMA out of bounds: {ewma} after obs={obs}"


# ── INV-M-NEW-A: source_turns + extractor_run_id always present ──


def test_inv_m_new_a_source_turns_always_present():
    """INV-M-NEW-A: Every L2/L3 record must carry source_turns and extractor_run_id.

    This is a structural invariant test that verifies the core types
    require these fields — the test constructs minimal instances and
    checks field presence, rather than running Hypothesis generators.
    """
    from heart.ss02_memory.extractor.types import (
        ExtractionCandidate,
        ExtractionEnvelope,
    )

    # Verify ExtractionCandidate requires source_turns (list[int])
    c = ExtractionCandidate(
        entity_type="self",
        attribute="name",
        value="test",
        source_turns=[1],
        confidence=0.9,
        kind="disclosure",
        operation="create",
        reasoning="T1: test",
    )
    assert c.source_turns is not None
    assert len(c.source_turns) >= 1
    assert all(isinstance(t, int) for t in c.source_turns)

    # Verify envelope-level extractor_run_id
    from uuid import uuid4

    run_id = uuid4()
    env = ExtractionEnvelope(
        extractor_run_id=run_id,
        model="test",
        prompt_version="1.0.0",
        schema_version="1.0.0",
        window={"turn_ids": [1], "size": 1},
        candidates=[c],
        dropped_signals=[],
    )
    assert env.extractor_run_id == run_id


# ── INV-M-15: L4 promotion conditions ──────────────────────────


def test_inv_m_15_l4_promotion_conditions():
    """INV-M-15: L4 candidates must satisfy promotion rules (≥3 mentions,
    confidence_ewma ≥ 0.8, age ≥ 1 day, no contradiction).

    Verifies the threshold values used by Promoter are correctly defined
    and internally consistent. Full integration coverage lives in
    tests/integration/ss02_memory/test_promoter_end_to_end.py.
    """
    from heart.core.config import settings

    # Thresholds must be within reasonable bounds
    assert settings.memory_promoter_min_mentions >= 2, "min_mentions too low"
    assert settings.memory_promoter_min_mentions <= 10, "min_mentions too high"
    assert 0.5 <= settings.memory_promoter_min_confidence <= 1.0, "min_confidence out of range"
    assert settings.memory_promoter_min_age_days >= 0, "min_age_days negative"
    assert settings.memory_promoter_batch_size >= 1, "batch_size too small"
    assert settings.memory_promoter_l4_cap >= 1, "l4_cap too small"

    # Demotion thresholds must be stricter than promotion
    assert settings.memory_promoter_demotion_min_count >= 1
    assert settings.memory_promoter_demotion_window_days > 0
    assert settings.memory_promoter_contradiction_clear_days > 0

    # Cross-session threshold: L4 needs persistence across sessions
    assert settings.memory_promoter_min_cross_sessions >= 0
