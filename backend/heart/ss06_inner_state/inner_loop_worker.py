"""
Inner Loop Worker — SS06 periodic heartbeat.

Periodically ticks InnerStateService for active user×character pairs,
generating proactive messages when conditions are met.

Controlled by HEART_INNER_LOOP_ENABLED=true (default: false).
Interval: HEART_INNER_LOOP_INTERVAL_S (default: 3600 = 1 hour).
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss06_inner_state.models import ProactiveMessage
from heart.ss06_inner_state.service import InnerStateService

logger = structlog.get_logger(__name__)

# In-memory store for proactive messages (will be replaced by DB in production)
_proactive_messages: List[ProactiveMessage] = []


def get_pending_proactive_messages(
    user_id: UUID,
    character_id: Optional[str] = None,
    since: Optional[timedelta] = None,
) -> List[ProactiveMessage]:
    """Get pending proactive messages for a user.

    Args:
        user_id: User UUID
        character_id: Optional character filter
        since: Optional time window (default: 7 days)

    Returns:
        List of pending ProactiveMessage
    """
    if since is None:
        since = timedelta(days=7)

    cutoff = datetime.now(timezone.utc) - since

    return [
        m
        for m in _proactive_messages
        if m.user_id == user_id
        and (character_id is None or m.character_id == character_id)
        and m.created_at >= cutoff
    ]


class InnerLoopWorker:
    """Periodic Inner Loop worker.

    Ticks InnerStateService for active user×character pairs,
    generating proactive messages when conditions are met.
    """

    def __init__(self, db_session_factory, inner_state_service: InnerStateService):
        """Initialize worker.

        Args:
            db_session_factory: Async session factory for database access
            inner_state_service: InnerStateService instance
        """
        self.db_session_factory = db_session_factory
        self.inner_state_service = inner_state_service
        self._should_stop = False

        self.interval_s = int(os.getenv("HEART_INNER_LOOP_INTERVAL_S", "3600"))

        logger.info(
            "inner_loop_worker_initialized",
            interval_seconds=self.interval_s,
        )

    async def start(self):
        """Start the inner loop worker."""
        logger.info("inner_loop_worker_started")

        while not self._should_stop:
            try:
                await self._tick_all_active_users()
            except Exception as e:
                logger.error("inner_loop_tick_failed", error=str(e))

            # Wait for next cycle
            try:
                await asyncio.sleep(self.interval_s)
            except asyncio.CancelledError:
                break

        logger.info("inner_loop_worker_stopped")

    async def stop(self):
        """Stop worker gracefully."""
        logger.info("inner_loop_worker_stopping")
        self._should_stop = True

    async def _tick_all_active_users(self):
        """Tick all active user×character pairs."""
        try:
            async with self.db_session_factory() as session:
                # Get active users (interacted in last 7 days)
                result = await session.execute(
                    text(
                        "SELECT DISTINCT user_id, character_id "
                        "FROM sessions "
                        "WHERE last_activity_at > NOW() - INTERVAL '7 days'"
                    )
                )
                rows = result.fetchall()

            logger.info("inner_loop_ticking", user_count=len(rows))

            # Process each user with a fresh session to avoid transaction errors
            for row in rows:
                user_id = row[0]
                character_id = row[1]

                try:
                    async with self.db_session_factory() as user_session:
                        # Get relationship info for better tick context
                        relationship_stage = "STRANGER"
                        intimacy = 0.0

                        # Get relationship state if available
                        rel_result = await user_session.execute(
                            text(
                                "SELECT current_stage, intimacy_level "
                                "FROM relationship_states "
                                "WHERE user_id = :user_id AND character_id = :character_id"
                            ),
                            {"user_id": str(user_id), "character_id": character_id},
                        )
                        rel_row = rel_result.fetchone()
                        if rel_row:
                            relationship_stage = rel_row[0] or "STRANGER"
                            intimacy = float(rel_row[1] or 0.0)

                        # Calculate days since last interaction
                        session_result = await user_session.execute(
                            text(
                                "SELECT last_activity_at "
                                "FROM sessions "
                                "WHERE user_id = :user_id AND character_id = :character_id"
                            ),
                            {"user_id": str(user_id), "character_id": character_id},
                        )
                        session_row = session_result.fetchone()
                        days_since_last = 0.0
                        if session_row and session_row[0]:
                            last_activity = session_row[0]
                            if hasattr(last_activity, "replace"):
                                last_activity = last_activity.replace(tzinfo=timezone.utc)
                            delta = datetime.now(timezone.utc) - last_activity
                            days_since_last = delta.total_seconds() / 86400

                        # Check for anniversary
                        is_anniversary = await self._check_anniversary(
                            user_id, character_id, user_session
                        )

                except Exception as e:
                    logger.error(
                        "inner_loop_user_query_failed",
                        user_id=str(user_id),
                        character_id=character_id,
                        error=str(e),
                    )
                    continue

                # Tick (outside session to avoid holding connection)
                try:
                    msg = self.inner_state_service.tick(
                        user_id=user_id,
                        character_id=character_id,
                        relationship_stage=relationship_stage,
                        intimacy=intimacy,
                        days_since_last_interaction=days_since_last,
                        is_anniversary=is_anniversary,
                    )

                    if msg is not None:
                        _proactive_messages.append(msg)
                        logger.info(
                            "proactive_message_generated",
                            user_id=str(user_id),
                            character_id=character_id,
                            trigger_type=msg.trigger_type,
                            content_preview=msg.content[:40],
                        )

                    # Check for ritual triggers (morning/night)
                    async with self.db_session_factory() as ritual_session:
                        ritual_msg = await self._check_ritual_triggers(
                            user_id, character_id, ritual_session
                        )
                    if ritual_msg is not None:
                        _proactive_messages.append(ritual_msg)

                except Exception as e:
                    logger.error(
                        "inner_loop_user_tick_failed",
                        user_id=str(user_id),
                        character_id=character_id,
                        error=str(e),
                    )

        except Exception as e:
            logger.error("inner_loop_fetch_users_failed", error=str(e))

    async def _check_anniversary(
        self,
        user_id: UUID,
        character_id: str,
        session: AsyncSession,
    ) -> bool:
        """Check if today is an anniversary for the user.

        Looks for L4 identity memories with anniversary patterns
        and checks if today matches.
        """
        try:
            result = await session.execute(
                text(
                    "SELECT id, key, value, next_anniversary_at "
                    "FROM identity_memories "
                    "WHERE user_id = :user_id AND character_id = :character_id "
                    "AND next_anniversary_at IS NOT NULL "
                    "AND next_anniversary_at::date = CURRENT_DATE"
                ),
                {"user_id": str(user_id), "character_id": character_id},
            )
            rows = result.fetchall()

            if rows:
                logger.info(
                    "anniversary_detected",
                    user_id=str(user_id),
                    character_id=character_id,
                    count=len(rows),
                )
                return True

        except Exception:
            logger.debug("anniversary_check_failed")

        return False

    async def _check_ritual_triggers(
        self,
        user_id: UUID,
        character_id: str,
        session: AsyncSession,
    ) -> Optional[ProactiveMessage]:
        """Check for ritual triggers (morning/night greetings).

        Returns a ProactiveMessage if a ritual should be triggered.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        hour = now.hour

        # Morning ritual: 6-10 AM
        if 6 <= hour <= 10:
            ritual_type = "morning"
            templates = {
                "rin": "早安。",
                "dorothy": "早安早安！新的一天开始啦！",
            }
        # Night ritual: 9 PM - 1 AM
        elif 21 <= hour or hour <= 1:
            ritual_type = "night"
            templates = {
                "rin": "晚安。明天见。",
                "dorothy": "晚安晚安！做个好梦哦！",
            }
        else:
            return None

        # Check if already sent today
        try:
            result = await session.execute(
                text(
                    "SELECT COUNT(*) FROM proactive_messages "
                    "WHERE user_id = :user_id AND character_id = :character_id "
                    "AND trigger_type = :trigger_type "
                    "AND created_at::date = CURRENT_DATE"
                ),
                {
                    "user_id": str(user_id),
                    "character_id": character_id,
                    "trigger_type": f"ritual_{ritual_type}",
                },
            )
            count = result.scalar()
            if count and count > 0:
                return None
        except Exception:
            # Table might not exist, proceed anyway
            pass

        # Generate ritual message
        content = templates.get(character_id, templates.get("rin", "早安。"))

        msg = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            content=content,
            trigger_type=f"ritual_{ritual_type}",
            created_at=now,
        )

        logger.info(
            "ritual_triggered",
            user_id=str(user_id),
            character_id=character_id,
            ritual_type=ritual_type,
        )

        return msg
