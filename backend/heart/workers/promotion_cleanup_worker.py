"""Delete approved promotion evidence and review records after three days."""

from __future__ import annotations

import asyncio
import os

import structlog
from sqlalchemy import text

from heart.api.wiring import _get_session_factory
from heart.infra.storage import delete_s3_object, is_s3_configured, object_key_from_storage_url

logger = structlog.get_logger(__name__)

RETENTION_DAYS = 3
CLEANUP_INTERVAL_S = int(os.getenv("HEART_PROMOTION_CLEANUP_INTERVAL_S", "3600"))


async def run_promotion_cleanup_loop(stop_event: asyncio.Event) -> None:
    """Run immediately on startup and then once per configured interval."""
    factory = _get_session_factory()
    logger.info(
        "promotion_cleanup_worker_started",
        retention_days=RETENTION_DAYS,
        interval_s=CLEANUP_INTERVAL_S,
    )

    while not stop_event.is_set():
        try:
            await _purge_expired_promotions(factory)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("promotion_cleanup_failed", error=str(exc))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=CLEANUP_INTERVAL_S)
            break
        except asyncio.TimeoutError:
            continue


async def _purge_expired_promotions(factory) -> None:
    async with factory() as session:
        rows = (
            (
                await session.execute(
                    text(
                        """
                    SELECT id, screenshot_url
                    FROM promotion_submissions
                    WHERE status='approved'
                      AND reviewed_at < NOW() - INTERVAL '3 days'
                    ORDER BY reviewed_at ASC
                    LIMIT 100
                    """
                    )
                )
            )
            .mappings()
            .all()
        )

        deleted = 0
        for row in rows:
            screenshot_url = row["screenshot_url"]
            key = object_key_from_storage_url(screenshot_url) if screenshot_url else None
            if key:
                if not is_s3_configured():
                    logger.warning(
                        "promotion_image_delete_deferred",
                        submission_id=str(row["id"]),
                        reason="storage_not_configured",
                    )
                    continue
                try:
                    await delete_s3_object(key)
                except Exception as exc:
                    logger.warning(
                        "promotion_image_delete_failed",
                        submission_id=str(row["id"]),
                        key=key,
                        error=str(exc),
                    )
                    continue

            await session.execute(
                text("DELETE FROM promotion_submissions WHERE id=:id AND status='approved'"),
                {"id": row["id"]},
            )
            deleted += 1

        await session.commit()
        if deleted:
            logger.info("expired_promotions_deleted", count=deleted)
