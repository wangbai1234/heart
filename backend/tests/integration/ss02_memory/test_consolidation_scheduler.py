"""Integration test — consolidation scheduler against a real PostgreSQL.

Proves the fix for the "decay/promotion never runs" bug: without an enqueued
pending job the ConsolidationWorker had nothing to process. The scheduler must
create exactly one pending ``consolidation_jobs`` row per active (user,
character) per UTC day, and be idempotent across re-runs.

Tier B integration test — needs real PostgreSQL.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import select

from heart.ss02_memory.models import ConsolidationJob, MemoryEncodingEvent
from heart.workers.consolidation_scheduler import enqueue_due_consolidation_jobs

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_postgres,
]


def _event(user_id, character_id: str, *, age_hours: float) -> MemoryEncodingEvent:
    created = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=age_hours)
    return MemoryEncodingEvent(
        event_id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        source_turn_id=uuid4(),
        source_user_text="hi",
        status="llm_done",
        created_at=created,
    )


async def _count_pending(session, user_id, character_id: str) -> int:
    result = await session.execute(
        select(ConsolidationJob).where(
            ConsolidationJob.user_id == user_id,
            ConsolidationJob.character_id == character_id,
            ConsolidationJob.status == "pending",
        )
    )
    return len(result.scalars().all())


@pytest.mark.asyncio
async def test_enqueues_one_job_per_active_pair(db_session):
    user_a, user_b = uuid4(), uuid4()
    db_session.add_all(
        [
            _event(user_a, "luna", age_hours=1),
            _event(user_a, "luna", age_hours=5),  # same pair, still one job
            _event(user_a, "sol", age_hours=2),  # different character → own job
            _event(user_b, "luna", age_hours=3),  # different user → own job
        ]
    )
    await db_session.flush()

    inserted = await enqueue_due_consolidation_jobs(db_session, lookback_hours=48)

    assert inserted == 3
    assert await _count_pending(db_session, user_a, "luna") == 1
    assert await _count_pending(db_session, user_a, "sol") == 1
    assert await _count_pending(db_session, user_b, "luna") == 1


@pytest.mark.asyncio
async def test_idempotent_within_the_same_day(db_session):
    user_id = uuid4()
    db_session.add(_event(user_id, "luna", age_hours=1))
    await db_session.flush()

    first = await enqueue_due_consolidation_jobs(db_session, lookback_hours=48)
    second = await enqueue_due_consolidation_jobs(db_session, lookback_hours=48)

    assert first == 1
    assert second == 0  # ON CONFLICT DO NOTHING on the day bucket
    assert await _count_pending(db_session, user_id, "luna") == 1


@pytest.mark.asyncio
async def test_ignores_users_outside_lookback_window(db_session):
    stale_user = uuid4()
    db_session.add(_event(stale_user, "luna", age_hours=100))  # older than 48h
    await db_session.flush()

    inserted = await enqueue_due_consolidation_jobs(db_session, lookback_hours=48)

    assert inserted == 0
    assert await _count_pending(db_session, stale_user, "luna") == 0
