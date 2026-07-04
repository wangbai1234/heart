"""
Integration test for SS02 Memory slow path full pipeline.

Tests the complete flow:
  Resolver → Writer

with real PostgreSQL + canned candidates.
Asserts L2/L3/audit_log rows match expectations.

Tier B integration test — needs real PostgreSQL.

Author: 心屿团队
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from heart.ss02_memory.extractor.resolver import DecisionType, Resolver
from heart.ss02_memory.extractor.types import (
    Attribute,
    EntityType,
    ExtractionCandidate,
    ExtractionEnvelope,
    Kind,
    Operation,
    Window,
)
from heart.ss02_memory.extractor.writer import Writer
from heart.ss02_memory.models import FactNode, MemoryAuditLog

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_postgres,
]


# ── Helpers ────────────────────────────────────────────────────


def _cand(
    entity_type=EntityType.SELF,
    attribute=Attribute.NAME,
    value="张三",
    entity_ref=None,
    confidence=0.9,
    kind=Kind.DISCLOSURE,
    operation=Operation.CREATE,
    source_turns=None,
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


def _envelope(candidates, run_id=None) -> ExtractionEnvelope:
    return ExtractionEnvelope(
        extractor_run_id=run_id or uuid4(),
        model="test-model",
        prompt_version="1.0.0",
        schema_version="1.0.0",
        window=Window(turn_ids=[0, 1, 2], size=3),
        candidates=candidates,
        dropped_signals=[],
    )


# ── Test: full pipeline CREATE ────────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_create(db_session):
    """CREATE: no prior fact → new L3 row + L2/L3 audits."""
    user_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()

    envelope = _envelope(
        [_cand(reasoning="T0: user said their name is 张三")],
        run_id=run_id,
    )

    resolver = Resolver(db_session, user_id)
    decisions = await resolver.resolve(envelope)
    assert len(decisions) == 1
    assert decisions[0].decision == DecisionType.CREATE

    writer = Writer(db_session, user_id, session_id)
    await writer.commit(decisions, envelope)

    # Verify L3 fact
    result = await db_session.execute(select(FactNode).where(FactNode.user_id == user_id))
    facts = result.scalars().all()
    assert len(facts) == 1
    assert facts[0].subject == "self"
    assert facts[0].predicate == "name"
    assert facts[0].object == "张三"
    assert facts[0].source_turns == [0]
    assert facts[0].mention_count == 1
    assert facts[0].is_active is True
    assert facts[0].do_not_recall is False

    # Verify audit log
    result = await db_session.execute(
        select(MemoryAuditLog).where(MemoryAuditLog.extractor_run_id == run_id)
    )
    audits = result.scalars().all()
    l2 = [a for a in audits if a.tier == "L2"]
    l3 = [a for a in audits if a.tier == "L3"]
    assert len(l2) == 1
    assert len(l3) == 1
    assert l2[0].operation == "create"
    assert l3[0].operation == "create"
    assert l3[0].source_turns == [0]  # INV-M-NEW-A


# ── Test: REINFORCE ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_reinforce(db_session):
    """REINFORCE: prior fact with same value → mention_count++, ewma update."""
    user_id = uuid4()
    session_id = uuid4()

    fact = FactNode(
        id=uuid4(),
        user_id=user_id,
        character_id="default",
        predicate="name",
        subject="self",
        object="张三",
        literal_text="self: name = 张三",
        raw_evidence="prior",
        source_episode_ids=[],
        source_turn_ids=[],
        source_turns=[0],
        confidence=0.8,
        emotional_charge=0.0,
        importance=0.5,
        confirmation_count=0,
        contradiction_count=0,
        contradicting_fact_ids=[],
        is_corrected=False,
        do_not_recall=False,
        state="vivid",
        mention_count=1,
        confidence_ewma=0.8,
        is_active=True,
    )
    db_session.add(fact)
    await db_session.flush()

    envelope = _envelope(
        [_cand(value="张三", confidence=0.95, reasoning="T1: confirmed name again")]
    )

    resolver = Resolver(db_session, user_id)
    decisions = await resolver.resolve(envelope)
    assert decisions[0].decision == DecisionType.REINFORCE

    writer = Writer(db_session, user_id, session_id)
    await writer.commit(decisions, envelope)

    result = await db_session.execute(select(FactNode).where(FactNode.user_id == user_id))
    facts = result.scalars().all()
    assert len(facts) == 1
    assert facts[0].mention_count == 2
    assert facts[0].confirmation_count == 1
    expected_ewma = 0.7 * 0.8 + 0.3 * 0.95
    assert abs(facts[0].confidence_ewma - expected_ewma) < 1e-6


# ── Test: SUPERSEDE ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_supersede(db_session):
    """SUPERSEDE: different value + high confidence → old inactive, new active."""
    user_id = uuid4()
    session_id = uuid4()

    old_fact_id = uuid4()
    fact = FactNode(
        id=old_fact_id,
        user_id=user_id,
        character_id="default",
        predicate="location_residence",
        subject="self",
        object="北京",
        literal_text="self: location_residence = 北京",
        raw_evidence="prior",
        source_episode_ids=[],
        source_turn_ids=[],
        source_turns=[0],
        confidence=0.8,
        emotional_charge=0.0,
        importance=0.5,
        confirmation_count=0,
        contradiction_count=0,
        contradicting_fact_ids=[],
        is_corrected=False,
        do_not_recall=False,
        state="vivid",
        mention_count=1,
        confidence_ewma=0.8,
        is_active=True,
    )
    db_session.add(fact)
    await db_session.flush()

    envelope = _envelope(
        [
            _cand(
                attribute=Attribute.LOCATION_RESIDENCE,
                value="上海",
                confidence=0.85,
                reasoning="T2: user moved to Shanghai",
            )
        ]
    )

    resolver = Resolver(db_session, user_id)
    decisions = await resolver.resolve(envelope)
    assert decisions[0].decision == DecisionType.SUPERSEDE

    writer = Writer(db_session, user_id, session_id)
    await writer.commit(decisions, envelope)

    result = await db_session.execute(select(FactNode).where(FactNode.user_id == user_id))
    facts = result.scalars().all()
    assert len(facts) == 2

    old = [f for f in facts if f.id == old_fact_id][0]
    new = [f for f in facts if f.id != old_fact_id][0]

    assert old.is_active is False
    assert old.superseded_by_id == new.id
    assert new.is_active is True
    assert new.object == "上海"
    assert old_fact_id in new.contradicting_fact_ids


# ── Test: SOFT_DELETE (INV-M-NEW-C) ───────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_soft_delete(db_session):
    """SOFT_DELETE: negation → do_not_recall=True, never physical delete."""
    user_id = uuid4()
    session_id = uuid4()

    fact_id = uuid4()
    fact = FactNode(
        id=fact_id,
        user_id=user_id,
        character_id="default",
        predicate="other",
        subject="pet",
        object="猫",
        literal_text="pet: other = 猫",
        raw_evidence="prior",
        source_episode_ids=[],
        source_turn_ids=[],
        source_turns=[0],
        confidence=0.8,
        emotional_charge=0.0,
        importance=0.5,
        confirmation_count=0,
        contradiction_count=0,
        contradicting_fact_ids=[],
        is_corrected=False,
        do_not_recall=False,
        state="vivid",
        mention_count=1,
        confidence_ewma=0.8,
        is_active=True,
    )
    db_session.add(fact)
    await db_session.flush()

    envelope = _envelope(
        [
            _cand(
                entity_type=EntityType.PET,
                attribute=Attribute.OTHER,
                value="猫",
                kind=Kind.NEGATION,
                operation=Operation.SOFT_DELETE,
                reasoning="T5: user said no pets",
            )
        ]
    )

    resolver = Resolver(db_session, user_id)
    decisions = await resolver.resolve(envelope)
    assert decisions[0].decision == DecisionType.SOFT_DELETE

    writer = Writer(db_session, user_id, session_id)
    await writer.commit(decisions, envelope)

    result = await db_session.execute(select(FactNode).where(FactNode.id == fact_id))
    fact = result.scalar_one()
    assert fact is not None, "Fact must NOT be physically deleted (INV-M-NEW-C)"
    assert fact.do_not_recall is True


# ── Test: REJECT → L2 audit only ──────────────────────────────


@pytest.mark.asyncio
async def test_full_pipeline_reject(db_session):
    """REJECT: rhetoric → L2 audit only, no L3 changes."""
    user_id = uuid4()
    session_id = uuid4()
    run_id = uuid4()

    envelope = _envelope(
        [_cand(kind=Kind.RHETORIC, reasoning="T0: joke, not real")],
        run_id=run_id,
    )

    resolver = Resolver(db_session, user_id)
    decisions = await resolver.resolve(envelope)
    assert decisions[0].decision == DecisionType.REJECT

    writer = Writer(db_session, user_id, session_id)
    await writer.commit(decisions, envelope)

    result = await db_session.execute(
        select(MemoryAuditLog).where(MemoryAuditLog.extractor_run_id == run_id)
    )
    audits = result.scalars().all()
    l2 = [a for a in audits if a.tier == "L2"]
    l3 = [a for a in audits if a.tier == "L3"]
    assert len(l2) == 1
    assert l2[0].operation == "reject"
    assert len(l3) == 0

    result = await db_session.execute(select(FactNode).where(FactNode.user_id == user_id))
    assert len(result.scalars().all()) == 0


# ── Test: INV-M-NEW-B (≤1 active row per key) ────────────────


@pytest.mark.asyncio
async def test_inv_m_new_b_single_active_per_key(db_session):
    """INV-M-NEW-B: after SUPERSEDE, ≤1 active row per (user, entity, attr)."""
    user_id = uuid4()
    session_id = uuid4()

    envelope1 = _envelope([_cand(value="北京", reasoning="T0: lives in Beijing")])
    resolver = Resolver(db_session, user_id)
    d1 = await resolver.resolve(envelope1)
    writer = Writer(db_session, user_id, session_id)
    await writer.commit(d1, envelope1)

    envelope2 = _envelope([_cand(value="上海", confidence=0.9, reasoning="T1: moved to Shanghai")])
    resolver2 = Resolver(db_session, user_id)
    d2 = await resolver2.resolve(envelope2)
    writer2 = Writer(db_session, user_id, session_id)
    await writer2.commit(d2, envelope2)

    result = await db_session.execute(
        select(FactNode).where(
            FactNode.user_id == user_id,
            FactNode.subject == "self",
            FactNode.predicate == "name",
            FactNode.is_active.is_(True),
        )
    )
    active = result.scalars().all()
    assert len(active) <= 1, f"INV-M-NEW-B: {len(active)} active rows, expected ≤1"
