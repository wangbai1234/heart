"""Consolidation Scheduler — enqueues pending ``consolidation_jobs`` rows.

Why this exists
---------------
``ConsolidationWorker`` polls ``consolidation_jobs WHERE status='pending' AND
scheduled_for <= now`` (memory_consolidator.py) but **nothing in the codebase
ever inserted a pending job** — the only ``ConsolidationJob(...)`` construction
(``ss02_memory/service.py``) returns a ``status='triggered'`` result object and
is never persisted to that queue. As a result the worker's whole 8-step pipeline
never ran in production:

  - Step 5 (L3 → L4 promotion via ``L4Promoter.check_promotions``) produced nothing
  - Step 7 (batch decay via ``DecayEngine``) never fired → every L2/L3 memory
    stayed ``state='active'`` forever, no forgetting curve ever applied.

This scheduler closes that gap: once per tick it inserts **one pending job per
active (user, character) per UTC day**. The existing ``ConsolidationWorker``
picks it up within a minute and runs decay + promotion (steps 5/7/8/9 run
unconditionally by user×character; the LLM episode-summarization steps 1–3 only
do work when there are recent turns to cluster, so cost tracks real activity).

Idempotency
-----------
``consolidation_jobs`` has ``UNIQUE(user_id, character_id, scheduled_for)``. We
bucket ``scheduled_for`` to UTC midnight and ``INSERT ... ON CONFLICT DO NOTHING``,
so re-running the scheduler within the same day — or running it on multiple API
replicas concurrently — never creates duplicate jobs.

The enqueue function deliberately does **not** commit; the loop runner owns the
transaction. This keeps it usable inside the integration test's rollback-scoped
session and mirrors the repo's "caller owns commit" convention.
"""

from __future__ import annotations

import asyncio
import os

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = structlog.get_logger(__name__)

# Re-check hourly. The per-day dedup key means this still yields at most one job
# per user×character per day regardless of how often the loop ticks.
DEFAULT_INTERVAL_S = 3600
# Only schedule consolidation for users who actually talked recently. 48h gives a
# margin so a user active late one day still gets consolidated the next.
DEFAULT_LOOKBACK_HOURS = 48

_ENQUEUE_SQL = text(
    """
    INSERT INTO consolidation_jobs
        (job_id, user_id, character_id, scheduled_for, status, created_at)
    SELECT
        gen_random_uuid(),
        active.user_id,
        active.character_id,
        date_trunc('day', now() AT TIME ZONE 'UTC') AT TIME ZONE 'UTC',
        'pending',
        now()
    FROM (
        SELECT DISTINCT user_id, character_id
        FROM memory_encoding_events
        -- memory_encoding_events.created_at is naive UTC (timezone=False), so
        -- compare against naive-UTC wall clock to stay independent of the DB
        -- session's TimeZone setting.
        WHERE created_at >= (now() AT TIME ZONE 'UTC') - make_interval(hours => :lookback_hours)
    ) AS active
    ON CONFLICT (user_id, character_id, scheduled_for) DO NOTHING
    """
)


async def enqueue_due_consolidation_jobs(
    session: AsyncSession,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
) -> int:
    """Insert one pending consolidation job per active (user, character) for the
    current UTC day. Idempotent via ON CONFLICT DO NOTHING.

    Does NOT commit — the caller owns the transaction.

    Returns the number of jobs newly inserted (0 when everything was already
    scheduled for today or no user was active in the lookback window).
    """
    result = await session.execute(_ENQUEUE_SQL, {"lookback_hours": int(lookback_hours)})
    # rowcount lives on the DML CursorResult; getattr tolerates drivers that
    # report -1 and keeps mypy happy across the Result union.
    rowcount = getattr(result, "rowcount", 0)
    inserted = int(rowcount) if rowcount and rowcount > 0 else 0
    if inserted:
        logger.info(
            "consolidation_jobs_enqueued",
            count=inserted,
            lookback_hours=int(lookback_hours),
        )
    return inserted


async def run_consolidation_scheduler_loop(
    db_session_factory: async_sessionmaker[AsyncSession],
    stop_event: asyncio.Event,
) -> None:
    """Periodically enqueue due consolidation jobs until ``stop_event`` is set."""
    interval_s = int(os.getenv("HEART_CONSOLIDATION_SCHEDULER_INTERVAL_S", str(DEFAULT_INTERVAL_S)))
    lookback_hours = int(
        os.getenv("HEART_CONSOLIDATION_LOOKBACK_HOURS", str(DEFAULT_LOOKBACK_HOURS))
    )
    logger.info(
        "consolidation_scheduler_started",
        interval_s=interval_s,
        lookback_hours=lookback_hours,
    )

    while not stop_event.is_set():
        try:
            async with db_session_factory() as session:
                await enqueue_due_consolidation_jobs(session, lookback_hours)
                await session.commit()
        except asyncio.CancelledError:
            break
        except Exception as e:
            # Do not swallow silently — log with context and keep the loop alive
            # so one bad tick doesn't kill scheduling for everyone.
            logger.error("consolidation_scheduler_failed", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
            break  # stop_event was set
        except asyncio.TimeoutError:
            continue  # interval elapsed, schedule again

    logger.info("consolidation_scheduler_stopped")
