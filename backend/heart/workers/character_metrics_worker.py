"""Daily character recommendation metrics and low-heat creator support."""

from __future__ import annotations

import asyncio
import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text

logger = structlog.get_logger(__name__)

_SHANGHAI = ZoneInfo("Asia/Shanghai")


async def refresh_character_metrics(session) -> int:
    """Refresh 30-day real-behaviour metrics in one set-based SQL statement.

    The recommendation page only reads the persisted result. It never performs
    COUNT(DISTINCT) or cross-day aggregation on a user request.
    """
    result = await session.execute(
        text(
            """
            WITH active_days AS (
              SELECT character_id,
                     user_id,
                     COUNT(DISTINCT (created_at AT TIME ZONE 'Asia/Shanghai')::date) AS days
                FROM chat_messages
               WHERE role = 'user'
                 AND rewound_at IS NULL
                 AND created_at >= NOW() - INTERVAL '30 days'
               GROUP BY character_id, user_id
            ), aggregates AS (
              SELECT character_id,
                     COUNT(*)::integer AS play_uv,
                     COUNT(*) FILTER (WHERE days >= 2)::integer AS return_uv
                FROM active_days
               GROUP BY character_id
            ), scored AS (
              SELECT c.id,
                     COALESCE(a.play_uv, 0) AS play_uv,
                     COALESCE(a.return_uv, 0) AS return_uv,
                     (COALESCE(a.return_uv, 0) + 2.0)
                       / (COALESCE(a.play_uv, 0) + 10.0) AS return_rate,
                     CASE WHEN MAX(LN(1 + COALESCE(a.play_uv, 0))) OVER () > 0
                          THEN LN(1 + COALESCE(a.play_uv, 0))
                               / MAX(LN(1 + COALESCE(a.play_uv, 0))) OVER ()
                          ELSE 0 END AS play_score,
                     CASE WHEN MAX(LN(1 + COALESCE(a.return_uv, 0))) OVER () > 0
                          THEN LN(1 + COALESCE(a.return_uv, 0))
                               / MAX(LN(1 + COALESCE(a.return_uv, 0))) OVER ()
                          ELSE 0 END AS return_score
               FROM characters c
                LEFT JOIN aggregates a ON a.character_id = c.id
               WHERE c.status = 'active'
                 AND (
                      c.owner_user_id IS NULL
                      OR (c.visibility = 'public' AND c.review_status = 'approved')
                 )
            )
            UPDATE characters c
               SET real_play_uv = s.play_uv,
                   return_user_uv = s.return_uv,
                   smoothed_return_rate = s.return_rate,
                   recommendation_score = 0.55 * s.play_score
                                        + 0.30 * s.return_score
                                        + 0.15 * s.return_rate,
                   metrics_calculated_at = NOW()
              FROM scored s
             WHERE c.id = s.id
            """
        )
    )
    return max(0, result.rowcount or 0)


async def support_low_heat_characters(
    session,
    *,
    support_day: date,
    limit: int = 5,
) -> list[tuple[str, int]]:
    """Give the lowest-heat eligible UGC one daily +50..100 support increment."""
    result = await session.execute(
        text(
            """
            WITH targets AS (
              SELECT id
                FROM characters
               WHERE owner_user_id IS NOT NULL
                 AND status = 'active'
                 AND visibility = 'public'
                 AND review_status = 'approved'
                 AND (last_heat_support_date IS NULL OR last_heat_support_date < :support_day)
               ORDER BY display_heat ASC, random()
               LIMIT :limit
               FOR UPDATE SKIP LOCKED
            ), increments AS (
              SELECT id, 50 + FLOOR(random() * 51)::integer AS amount
                FROM targets
            )
            UPDATE characters c
               SET display_heat = c.display_heat + i.amount,
                   last_heat_support_date = :support_day
              FROM increments i
             WHERE c.id = i.id
            RETURNING c.id, i.amount
            """
        ),
        {"support_day": support_day, "limit": limit},
    )
    return [(row.id, int(row.amount)) for row in result]


async def run_character_metrics_loop(stop_event: asyncio.Event) -> None:
    """Run metrics/support immediately on boot and then at a daily interval."""
    from heart.api.wiring import _get_session_factory

    interval_s = int(os.getenv("HEART_CHARACTER_METRICS_INTERVAL_S", "86400"))
    support_limit = int(os.getenv("HEART_LOW_HEAT_SUPPORT_COUNT", "5"))
    factory = _get_session_factory()
    logger.info(
        "character_metrics_worker_started",
        interval_s=interval_s,
        support_limit=support_limit,
    )

    while not stop_event.is_set():
        next_interval = interval_s
        try:
            async with factory() as session:
                updated = await refresh_character_metrics(session)
                supported = await support_low_heat_characters(
                    session,
                    support_day=datetime.now(_SHANGHAI).date(),
                    limit=support_limit,
                )
                await session.commit()
                logger.info(
                    "character_metrics_refreshed",
                    updated=updated,
                    supported=supported,
                )
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("character_metrics_refresh_failed", error=str(exc))
            # Deploy replaces the worker container before Alembic runs. If the
            # new columns are not present during that brief window, retry soon
            # after migration instead of sleeping for a full day.
            next_interval = min(interval_s, 60)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=next_interval)
            break
        except asyncio.TimeoutError:
            continue
