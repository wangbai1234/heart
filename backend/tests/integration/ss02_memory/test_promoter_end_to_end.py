"""Integration test for SS02 Memory L3→L4 Promoter.

Seeds L3 facts with controlled data → runs promoter → asserts L4 + audit_log.
Requires real PostgreSQL (Tier B integration test).

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import (
    FactNode,
    IdentityMemory,
    MemoryAuditLog,
)
from heart.ss02_memory.promoter import Promoter, PromoterConfig

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_postgres,
]


# ── Helpers ────────────────────────────────────────────────────


def _seed_fact(
    session: AsyncSession,
    *,
    user_id=None,
    predicate="has_pet",
    subject="user",
    object_val="老铁的猫",
    mention_count=4,
    confidence_ewma=0.88,
    age_days=2,
    is_corrected=False,
    do_not_recall=False,
    is_active=True,
    last_contradicted_at=None,
    source_turns=None,
) -> FactNode:
    """Insert a controlled L3 FactNode for testing."""
    now = datetime.now(timezone.utc)
    fact = FactNode(
        id=uuid4(),
        user_id=user_id or uuid4(),
        character_id="default",
        predicate=predicate,
        subject=subject,
        object=object_val,
        literal_text=f"{subject}: {predicate} = {object_val}",
        raw_evidence=f"User said: {object_val}",
        source_episode_ids=[],
        source_turn_ids=[],
        source_turns=source_turns or [0, 1, 2],
        confidence=confidence_ewma,
        emotional_charge=0.0,
        importance=0.5,
        is_identity_level=False,
        confirmation_count=mention_count,
        contradiction_count=0,
        contradicting_fact_ids=[],
        is_corrected=is_corrected,
        do_not_recall=do_not_recall,
        last_confirmed_at=now,
        last_contradicted_at=last_contradicted_at,
        state="vivid",
        mention_count=mention_count,
        confidence_ewma=confidence_ewma,
        last_extractor_run_id=None,
        is_active=is_active,
        superseded_by_id=None,
        was_l4=False,
        created_at=now - timedelta(days=age_days),
        updated_at=now,
    )
    session.add(fact)
    return fact


def _seed_audit_log(
    session: AsyncSession,
    *,
    user_id,
    fact_id,
    session_id=None,
    tier="L3",
    operation="create",
    created_at=None,
):
    """Insert a MemoryAuditLog entry for cross-session counting."""
    audit = MemoryAuditLog(
        id=uuid4(),
        user_id=user_id,
        session_id=session_id or uuid4(),
        tier=tier,
        operation=operation,
        entity_type="fact",
        entity_ref=str(fact_id),
        attribute="has_pet",
        old_value=None,
        new_value={"predicate": "has_pet", "subject": "user", "object": "老铁的猫"},
        source_turns=[0],
        actor="resolver",
        reasoning="test",
        created_at=created_at or datetime.now(timezone.utc),
    )
    session.add(audit)
    return audit


def _make_config(**overrides) -> PromoterConfig:
    defaults = dict(
        K1_min_mentions=3,
        K2_min_confidence_ewma=0.80,
        K3_min_age_days=1,
        K4_min_cross_sessions=2,
        K5_contradiction_clear_days=7,
        batch_size=200,
        per_user_l4_cap=50,
        blocklist_exact=("current_mood", "current_emotion", "currently_doing"),
        blocklist_glob=("current_*", "feeling_*", "recent_*"),
        demotion_window_days=14,
        demotion_min_count=2,
    )
    defaults.update(overrides)
    return PromoterConfig(**defaults)


# ── End-to-end: Happy path ─────────────────────────────────────


@pytest.mark.asyncio
async def test_promoter_e2e_happy_path(db_session: AsyncSession):
    """Seed L3 → run promoter → assert L4 + audit + L3 metadata."""
    user_id = uuid4()

    # Seed L3 fact
    fact = _seed_fact(
        db_session,
        user_id=user_id,
        mention_count=4,
        confidence_ewma=0.88,
        age_days=2,
    )
    await db_session.flush()

    # Seed audit logs from 3 distinct sessions (K4=2 requires ≥2)
    for i in range(3):
        _seed_audit_log(
            db_session,
            user_id=user_id,
            fact_id=fact.id,
            session_id=uuid4(),
            created_at=datetime.now(timezone.utc) - timedelta(hours=i * 8),
        )
    await db_session.flush()

    # Run promoter
    cfg = _make_config()
    promoter = Promoter(db_session, cfg)
    result = await promoter.run_batch(user_ids=[user_id])

    await db_session.commit()

    # Assert: fact was promoted
    assert len(result.promoted) == 1

    # Assert: L4 row exists
    l4_stmt = select(IdentityMemory).where(
        IdentityMemory.user_id == user_id,
        IdentityMemory.demoted_at.is_(None),
    )
    l4_result = await db_session.execute(l4_stmt)
    l4_rows = l4_result.scalars().all()
    assert len(l4_rows) == 1
    assert l4_rows[0].key == "has_pet"
    assert l4_rows[0].value == "老铁的猫"
    assert l4_rows[0].promoted_from_fact_id == fact.id

    # Assert: L3 metadata updated
    fact_stmt = select(FactNode).where(FactNode.id == fact.id)
    fact_result = await db_session.execute(fact_stmt)
    updated_fact = fact_result.scalar_one()
    assert updated_fact.is_identity_level is True
    assert updated_fact.promoted_to_l4_at is not None
    assert updated_fact.promotion_reason is not None

    # Assert: audit log written
    audit_stmt = select(MemoryAuditLog).where(
        MemoryAuditLog.user_id == user_id,
        MemoryAuditLog.tier == "L4",
        MemoryAuditLog.operation == "promote",
    )
    audit_result = await db_session.execute(audit_stmt)
    audit_rows = audit_result.scalars().all()
    assert len(audit_rows) == 1
    assert audit_rows[0].actor == "promoter"


# ── End-to-end: Blocklist ──────────────────────────────────────


@pytest.mark.asyncio
async def test_promoter_e2e_blocklist(db_session: AsyncSession):
    """Fact with blocklisted predicate → never promoted."""
    user_id = uuid4()

    fact = _seed_fact(
        db_session,
        user_id=user_id,
        predicate="current_mood",
        object_val="开心",
        mention_count=20,
        confidence_ewma=1.0,
        age_days=30,
    )

    # Seed audit logs from many sessions
    for i in range(15):
        _seed_audit_log(
            db_session,
            user_id=user_id,
            fact_id=fact.id,
            session_id=uuid4(),
        )
    await db_session.flush()

    cfg = _make_config()
    promoter = Promoter(db_session, cfg)
    result = await promoter.run_batch(user_ids=[user_id])

    await db_session.commit()

    # No promotion
    assert len(result.promoted) == 0

    # No L4 rows
    l4_stmt = select(IdentityMemory).where(IdentityMemory.user_id == user_id)
    l4_result = await db_session.execute(l4_stmt)
    assert len(l4_result.scalars().all()) == 0


# ── End-to-end: Glob blocklist ─────────────────────────────────


@pytest.mark.asyncio
async def test_promoter_e2e_glob_blocklist(db_session: AsyncSession):
    """Fact matching glob pattern (current_*) → never promoted."""
    user_id = uuid4()

    fact = _seed_fact(
        db_session,
        user_id=user_id,
        predicate="current_location_in_city",
        object_val="杭州",
        mention_count=10,
        confidence_ewma=0.95,
        age_days=30,
    )

    for i in range(5):
        _seed_audit_log(db_session, user_id=user_id, fact_id=fact.id, session_id=uuid4())
    await db_session.flush()

    cfg = _make_config()
    promoter = Promoter(db_session, cfg)
    result = await promoter.run_batch(user_ids=[user_id])

    await db_session.commit()

    assert len(result.promoted) == 0


# ── End-to-end: Idempotency ────────────────────────────────────


@pytest.mark.asyncio
async def test_promoter_e2e_idempotent(db_session: AsyncSession):
    """Running promoter twice on same data → only one L4 row."""
    user_id = uuid4()

    fact = _seed_fact(db_session, user_id=user_id)
    for i in range(3):
        _seed_audit_log(db_session, user_id=user_id, fact_id=fact.id, session_id=uuid4())
    await db_session.flush()

    cfg = _make_config()
    promoter = Promoter(db_session, cfg)

    # First run
    result1 = await promoter.run_batch(user_ids=[user_id])
    await db_session.commit()

    # Second run
    result2 = await promoter.run_batch(user_ids=[user_id])
    await db_session.commit()

    assert len(result1.promoted) == 1
    assert len(result2.promoted) == 0  # Already promoted, no duplicate

    # Only one L4 row
    l4_stmt = select(IdentityMemory).where(
        IdentityMemory.user_id == user_id,
        IdentityMemory.demoted_at.is_(None),
    )
    l4_result = await db_session.execute(l4_stmt)
    assert len(l4_result.scalars().all()) == 1


# ── End-to-end: L4 cap ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_promoter_e2e_l4_cap(db_session: AsyncSession):
    """User at L4 cap → eligible fact not promoted."""
    user_id = uuid4()

    # Create 50 active L4 rows
    for i in range(50):
        l4 = IdentityMemory(
            id=uuid4(),
            user_id=user_id,
            character_id="default",
            category="test",
            key=f"test_key_{i}",
            value=f"val_{i}",
            disclosed_at=datetime.now(timezone.utc),
            sacred_reason="test",
            significance_score=0.90,
            promotion_trigger="test",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(l4)

    # Create eligible L3 fact
    fact = _seed_fact(db_session, user_id=user_id)
    for i in range(3):
        _seed_audit_log(db_session, user_id=user_id, fact_id=fact.id, session_id=uuid4())
    await db_session.flush()

    cfg = _make_config(per_user_l4_cap=50)
    promoter = Promoter(db_session, cfg)
    result = await promoter.run_batch(user_ids=[user_id])

    await db_session.commit()

    # Not promoted due to cap
    assert len(result.promoted) == 0

    # L3 unchanged
    fact_stmt = select(FactNode).where(FactNode.id == fact.id)
    fact_result = await db_session.execute(fact_stmt)
    updated = fact_result.scalar_one()
    assert updated.promoted_to_l4_at is None
