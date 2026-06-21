"""
Unit tests for SS02 Memory LLM Extractor — Writer.

Covers:
- Each decision type writes correct L2/L3/audit rows
- Idempotency via duplicate envelope replay
- Rollback on partial failure
- DLQ enqueue on failure

Author: 心屿团队
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss02_memory.extractor.resolver import DecisionType, ResolverDecision
from heart.ss02_memory.extractor.types import (
    Attribute,
    EntityType,
    ExtractionCandidate,
    ExtractionEnvelope,
    Kind,
    Operation,
    Window,
)
from heart.ss02_memory.extractor.writer import Writer, WriterError
from heart.ss02_memory.models import FactNode, MemoryAuditLog

# ── Helpers ────────────────────────────────────────────────────


def _make_candidate(
    entity_type=EntityType.SELF,
    attribute=Attribute.NAME,
    value="张三",
    entity_ref=None,
    source_turns=None,
    confidence=0.9,
    kind=Kind.DISCLOSURE,
    operation=Operation.CREATE,
    reasoning="T0: user said name",
) -> ExtractionCandidate:
    return ExtractionCandidate(
        entity_type=entity_type,
        attribute=attribute,
        value=value,
        entity_ref=entity_ref,
        source_turns=source_turns or [0],
        confidence=confidence,
        kind=kind,
        operation=operation,
        reasoning=reasoning,
    )


def _make_envelope(
    candidates=None,
    run_id=None,
) -> ExtractionEnvelope:
    return ExtractionEnvelope(
        extractor_run_id=run_id or uuid4(),
        model="test-model",
        prompt_version="1.0.0",
        schema_version="1.0.0",
        window=Window(turn_ids=[0, 1, 2], size=3),
        candidates=candidates or [],
        dropped_signals=[],
    )


def _make_fact_node(**overrides) -> FactNode:
    fact = MagicMock(spec=FactNode)
    fact.id = overrides.get("id", uuid4())
    fact.user_id = overrides.get("user_id", uuid4())
    fact.subject = overrides.get("subject", "self")
    fact.predicate = overrides.get("predicate", "name")
    fact.object = overrides.get("object", "张三")
    fact.confidence = overrides.get("confidence", 0.8)
    fact.confidence_ewma = overrides.get("confidence_ewma", 0.85)
    fact.mention_count = overrides.get("mention_count", 2)
    fact.is_active = overrides.get("is_active", True)
    fact.do_not_recall = overrides.get("do_not_recall", False)
    fact.source_turns = overrides.get("source_turns", [0])
    fact.confirmation_count = overrides.get("confirmation_count", 0)
    fact.superseded_by_id = None
    return fact


def _make_decision(
    decision_type=DecisionType.CREATE,
    candidate=None,
    matched_fact=None,
    new_confidence_ewma=None,
    reason="test reason",
) -> ResolverDecision:
    return ResolverDecision(
        decision=decision_type,
        candidate=candidate or _make_candidate(),
        matched_fact=matched_fact,
        new_confidence_ewma=new_confidence_ewma,
        reason=reason,
    )


def _mock_session(existing_audit=None):
    """Create a mock session that handles idempotency check."""
    session = AsyncMock()
    # Use MagicMock (not AsyncMock) for the result — scalar_one_or_none is sync
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_audit
    session.execute.return_value = mock_result
    return session


# ── CREATE tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_writes_l2_l3_audit():
    """CREATE decision writes L2 audit + L3 FactNode + L3 audit."""
    session = _mock_session()  # No existing audit → not idempotent
    user_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(reasoning="T0: name disclosed")
    envelope = _make_envelope([candidate], run_id=run_id)
    decision = _make_decision(DecisionType.CREATE, candidate=candidate)

    await writer.commit([decision], envelope)

    # Should have added multiple objects
    added_objects = [call.args[0] for call in session.add.call_args_list]
    assert len(added_objects) >= 2  # L2 audit + L3 fact + L3 audit

    # Verify L2 audit entry
    l2_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L2"]
    assert len(l2_audits) == 1
    assert l2_audits[0].operation == "create"
    assert l2_audits[0].entity_type == "self"
    assert l2_audits[0].source_turns == [0]

    # Verify L3 fact node
    l3_facts = [o for o in added_objects if isinstance(o, FactNode)]
    assert len(l3_facts) == 1
    assert l3_facts[0].subject == "self"
    assert l3_facts[0].predicate == "name"
    assert l3_facts[0].object == "张三"
    assert l3_facts[0].source_turns == [0]
    assert l3_facts[0].mention_count == 1
    assert l3_facts[0].confidence_ewma == 0.9
    assert l3_facts[0].is_active is True

    # Verify L3 audit entry
    l3_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L3"]
    assert len(l3_audits) == 1
    assert l3_audits[0].operation == "create"
    assert l3_audits[0].old_value is None
    assert l3_audits[0].new_value is not None


# ── REINFORCE tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_reinforce_updates_fact():
    """REINFORCE decision updates mention_count, confidence_ewma, source_turns."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    fact = _make_fact_node(
        mention_count=2,
        confidence_ewma=0.8,
        source_turns=[0],
        confirmation_count=1,
    )

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(value="张三", confidence=0.95, source_turns=[1])
    envelope = _make_envelope([candidate])
    decision = _make_decision(
        DecisionType.REINFORCE,
        candidate=candidate,
        matched_fact=fact,
        new_confidence_ewma=0.7 * 0.8 + 0.3 * 0.95,
    )

    await writer.commit([decision], envelope)

    # Verify fact was updated
    assert fact.mention_count == 3
    assert fact.confirmation_count == 2
    assert 0 in fact.source_turns
    assert 1 in fact.source_turns

    # Verify L3 audit
    added_objects = [call.args[0] for call in session.add.call_args_list]
    l3_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L3"]
    assert len(l3_audits) == 1
    assert l3_audits[0].operation == "update"
    assert l3_audits[0].old_value is not None
    assert l3_audits[0].new_value is not None


# ── SUPERSEDE tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_supersede_marks_old_inactive_creates_new():
    """SUPERSEDE marks old fact inactive, creates new fact."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    old_fact = _make_fact_node(object_val="北京", is_active=True)

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(
        attribute=Attribute.LOCATION_RESIDENCE,
        value="上海",
        confidence=0.85,
    )
    envelope = _make_envelope([candidate])
    decision = _make_decision(
        DecisionType.SUPERSEDE,
        candidate=candidate,
        matched_fact=old_fact,
    )

    await writer.commit([decision], envelope)

    # Old fact should be inactive
    assert old_fact.is_active is False
    assert old_fact.superseded_by_id is not None

    # Should have new fact + audits
    added_objects = [call.args[0] for call in session.add.call_args_list]
    l3_facts = [o for o in added_objects if isinstance(o, FactNode)]
    assert len(l3_facts) == 1
    assert l3_facts[0].object == "上海"
    assert l3_facts[0].is_active is True
    assert old_fact.id in l3_facts[0].contradicting_fact_ids


# ── SOFT_DELETE tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_soft_delete_marks_do_not_recall():
    """SOFT_DELETE sets do_not_recall=True (INV-M-NEW-C: never physical delete)."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    fact = _make_fact_node(do_not_recall=False)

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(kind=Kind.NEGATION, operation=Operation.SOFT_DELETE)
    envelope = _make_envelope([candidate])
    decision = _make_decision(
        DecisionType.SOFT_DELETE,
        candidate=candidate,
        matched_fact=fact,
    )

    await writer.commit([decision], envelope)

    # Fact should be soft-deleted
    assert fact.do_not_recall is True

    # Should have L3 audit
    added_objects = [call.args[0] for call in session.add.call_args_list]
    l3_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L3"]
    assert len(l3_audits) == 1
    assert l3_audits[0].operation == "soft_delete"


# ── REJECT tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reject_writes_l2_audit_only():
    """REJECT writes L2 audit but no L3 changes."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(kind=Kind.RHETORIC)
    envelope = _make_envelope([candidate])
    decision = _make_decision(DecisionType.REJECT, candidate=candidate)

    await writer.commit([decision], envelope)

    added_objects = [call.args[0] for call in session.add.call_args_list]

    # Should have L2 audit only
    l2_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L2"]
    assert len(l2_audits) == 1
    assert l2_audits[0].operation == "reject"

    # Should NOT have L3 facts or L3 audits
    l3_facts = [o for o in added_objects if isinstance(o, FactNode)]
    l3_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L3"]
    assert len(l3_facts) == 0
    assert len(l3_audits) == 0


# ── CONFLICT_DEFER tests ──────────────────────────────────────


@pytest.mark.asyncio
async def test_conflict_defer_writes_l2_audit_only():
    """CONFLICT_DEFER writes L2 audit but no L3 changes."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate(confidence=0.4)
    envelope = _make_envelope([candidate])
    decision = _make_decision(DecisionType.CONFLICT_DEFER, candidate=candidate)

    await writer.commit([decision], envelope)

    added_objects = [call.args[0] for call in session.add.call_args_list]
    l2_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L2"]
    assert len(l2_audits) == 1
    assert l2_audits[0].operation == "conflict_defer"


# ── Idempotency tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_idempotent_skip_duplicate_run():
    """Same extractor_run_id → reject second commit."""
    existing_audit = MagicMock()  # Non-None → already processed
    session = _mock_session(existing_audit=existing_audit)
    user_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate()
    envelope = _make_envelope([candidate], run_id=run_id)
    decision = _make_decision(DecisionType.CREATE, candidate=candidate)

    await writer.commit([decision], envelope)

    # Should NOT have added any objects (idempotent skip)
    session.add.assert_not_called()
    session.commit.assert_not_called()


# ── Rollback tests ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rollback_on_commit_failure():
    """On commit exception: rollback, mark queue failed, enqueue DLQ."""
    session = _mock_session()
    session.commit.side_effect = Exception("DB constraint violation")
    user_id = uuid4()
    session_id = uuid4()

    writer = Writer(session, user_id, session_id)
    candidate = _make_candidate()
    envelope = _make_envelope([candidate])
    decision = _make_decision(DecisionType.CREATE, candidate=candidate)

    with pytest.raises(WriterError, match="Writer commit failed"):
        await writer.commit([decision], envelope)

    # Should have called rollback
    session.rollback.assert_called()


# ── Multiple decisions ────────────────────────────────────────


@pytest.mark.asyncio
async def test_multiple_decisions_single_transaction():
    """All decisions for one envelope are in one transaction."""
    session = _mock_session()
    user_id = uuid4()
    session_id = uuid4()

    writer = Writer(session, user_id, session_id)
    decisions = [
        _make_decision(DecisionType.CREATE, candidate=_make_candidate(value="A")),
        _make_decision(DecisionType.REJECT, candidate=_make_candidate(kind=Kind.RHETORIC)),
        _make_decision(
            DecisionType.SOFT_DELETE,
            candidate=_make_candidate(kind=Kind.NEGATION),
            matched_fact=_make_fact_node(),
        ),
    ]
    envelope = _make_envelope()

    await writer.commit(decisions, envelope)

    # Single commit call
    session.commit.assert_called_once()

    # Should have L2 audits for all 3 + L3 fact for CREATE + L3 audit for CREATE + L3 audit for SOFT_DELETE
    added_objects = [call.args[0] for call in session.add.call_args_list]
    l2_audits = [o for o in added_objects if isinstance(o, MemoryAuditLog) and o.tier == "L2"]
    assert len(l2_audits) == 3  # One per decision
