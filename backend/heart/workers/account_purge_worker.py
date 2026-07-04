"""
Account Purge Worker — deletes data for accounts past their 30-day grace period.

Scans account_deletion_requests where purge_after < now() and status='pending'.
Purges: memory (L2/L3/L4), emotion/relationship state, chat_messages, avatar files.
Marks status='purged'.
"""

from __future__ import annotations

import asyncio
import os

import structlog
from sqlalchemy import text

from heart.api.wiring import _get_session_factory

logger = structlog.get_logger(__name__)

PURGE_INTERVAL_S = int(os.getenv("HEART_ACCOUNT_PURGE_INTERVAL_S", "3600"))  # 1 hour


async def run_account_purge_loop(stop_event: asyncio.Event) -> None:
    """Periodically purge accounts past their deletion grace period."""
    factory = _get_session_factory()
    logger.info("account_purge_worker_started", interval_s=PURGE_INTERVAL_S)

    while not stop_event.is_set():
        try:
            await _purge_expired_accounts(factory)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("account_purge_failed", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=PURGE_INTERVAL_S)
            break
        except asyncio.TimeoutError:
            continue


async def _purge_expired_accounts(factory) -> None:
    """Find and purge accounts past grace period."""
    async with factory() as session:
        # Find pending deletions past purge_after
        result = await session.execute(
            text("""
                SELECT id, user_id FROM account_deletion_requests
                WHERE status = 'pending' AND purge_after < NOW()
                LIMIT 50
            """)
        )
        requests = result.fetchall()

        if not requests:
            return

        purged_count = 0
        for req_id, user_id in requests:
            try:
                await _purge_single_user(session, user_id)
                await session.execute(
                    text("""
                        UPDATE account_deletion_requests
                        SET status = 'purged', completed_at = NOW()
                        WHERE id = :id
                    """),
                    {"id": req_id},
                )
                purged_count += 1
            except Exception as e:
                logger.error("user_purge_failed", user_id=str(user_id), error=str(e))

        await session.commit()
        if purged_count > 0:
            logger.info("accounts_purged", count=purged_count)


async def _purge_single_user(session, user_id) -> None:
    """Purge all data for a single user."""
    uid = str(user_id)

    # Delete chat messages
    await session.execute(
        text("DELETE FROM chat_messages WHERE user_id = :uid"),
        {"uid": user_id},
    )

    # Delete emotion events and state
    await session.execute(
        text("DELETE FROM emotion_events WHERE user_id = :uid"),
        {"uid": uid},
    )
    await session.execute(
        text("DELETE FROM emotion_states WHERE user_id = :uid"),
        {"uid": uid},
    )

    # Delete relationship events and state
    await session.execute(
        text("DELETE FROM relationship_events WHERE user_id = :uid"),
        {"uid": uid},
    )
    await session.execute(
        text("DELETE FROM relationship_states WHERE user_id = :uid"),
        {"uid": uid},
    )

    # Delete memory data
    await session.execute(
        text("DELETE FROM episodic_memories WHERE user_id = :uid"),
        {"uid": uid},
    )
    await session.execute(
        text("DELETE FROM fact_nodes WHERE user_id = :uid"),
        {"uid": uid},
    )
    await session.execute(
        text("DELETE FROM identity_memories WHERE user_id = :uid"),
        {"uid": uid},
    )

    # Clear L1 Redis cache
    try:
        import redis.asyncio as aioredis

        from heart.core.config import settings

        r = aioredis.from_url(settings.redis_url)
        pattern = f"memory:l1:{uid}:*"
        async for key in r.scan_iter(match=pattern, count=100):
            await r.delete(key)
        await r.close()
    except Exception as e:
        logger.warning("redis_purge_failed", user_id=uid, error=str(e))

    # Delete S3 avatar if present
    try:
        avatar_result = await session.execute(
            text("SELECT avatar_url FROM users WHERE id = :uid"),
            {"uid": user_id},
        )
        avatar_row = avatar_result.scalar_one_or_none()
        if avatar_row and "chat_audio" not in avatar_row:
            from heart.infra.storage import is_s3_configured

            if is_s3_configured():
                import boto3

                from heart.core.config import settings

                # Extract key from URL
                url_parts = avatar_row.split("/")
                bucket_idx = (
                    url_parts.index(settings.s3_bucket_name)
                    if settings.s3_bucket_name in url_parts
                    else -1
                )
                if bucket_idx >= 0:
                    key = "/".join(url_parts[bucket_idx + 1 :])
                    client = boto3.client(
                        "s3",
                        endpoint_url=settings.s3_endpoint_url,
                        aws_access_key_id=settings.s3_access_key_id,
                        aws_secret_access_key=settings.s3_secret_access_key,
                    )
                    client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
                    logger.info("s3_avatar_deleted", user_id=uid, key=key)
    except Exception as e:
        logger.warning("s3_avatar_delete_failed", user_id=uid, error=str(e))

    # Clear avatar_url
    await session.execute(
        text("UPDATE users SET avatar_url = NULL WHERE id = :uid"),
        {"uid": user_id},
    )

    logger.info("user_data_purged", user_id=uid)
