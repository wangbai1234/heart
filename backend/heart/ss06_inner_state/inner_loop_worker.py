"""
Inner Loop Worker — SS06 periodic heartbeat.

Periodically ticks InnerStateService for active user×character pairs,
generating proactive messages when conditions are met.

Controlled by HEART_INNER_LOOP_ENABLED=true (default: false).
Interval: HEART_INNER_LOOP_INTERVAL_S (default: 3600 = 1 hour).
"""

from __future__ import annotations

import asyncio
import collections
import os
import random
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss06_inner_state import proactive_repo
from heart.ss06_inner_state.models import ProactiveMessage
from heart.ss06_inner_state.service import InnerStateService

logger = structlog.get_logger(__name__)

# Daily proactive quota per (user, character), mirrors InnerStateService Gate I-5.
DAILY_PROACTIVE_QUOTA = 3

# Idle-time thresholds for ritual trigger gate (hours).
MIN_IDLE_HOURS = 8.0
DICE_IDLE_HOURS = 12.0

# Cross-character cooldown. Mirrors CROSS_CHARACTER_COOLDOWN_MINUTES on
# InnerStateService so both entry points enforce the same user-scoped rule.
_CROSS_CHARACTER_COOLDOWN_MINUTES = 30

# Content-dedup window (days). Mirrors CONTENT_DEDUP_DAYS on
# InnerStateService.
_CONTENT_DEDUP_DAYS = 3

# Bounded in-memory mirror of recently generated messages. Retained for one
# release as a fallback/diagnostic; the source of truth is the
# proactive_messages table. TODO(sunset 2026-09): remove once the DB-backed
# /pending path has soaked in production.
_proactive_messages: collections.deque[ProactiveMessage] = collections.deque(maxlen=1000)


def get_pending_proactive_messages(
    user_id: UUID,
    character_id: Optional[str] = None,
    since: Optional[timedelta] = None,
) -> List[ProactiveMessage]:
    """Read the in-memory mirror of generated proactive messages.

    NOTE: the authoritative source is now the ``proactive_messages`` table,
    which the ``/api/proactive/pending`` route reads directly (survives restart
    and supports delivered/ack). This helper remains for the in-memory
    diagnostic mirror and existing tests.

    Args:
        user_id: User UUID
        character_id: Optional character filter
        since: Optional time window (default: 7 days)
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


def _build_local_time_context(
    utc_now: datetime,
    user_timezone: str,
    hours_since_last_message: float,
) -> dict:
    """Return a time-context dict for the proactive content LLM prompt."""
    try:
        tz = ZoneInfo(user_timezone)
    except Exception:
        tz = ZoneInfo("Asia/Shanghai")

    local_now = utc_now.astimezone(tz)
    local_hour = local_now.hour
    weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday_cn = weekday_names[local_now.weekday()]

    if 5 <= local_hour < 12:
        time_of_day = "早上"
    elif 12 <= local_hour < 18:
        time_of_day = "下午"
    elif 18 <= local_hour < 22:
        time_of_day = "傍晚"
    else:
        time_of_day = "深夜"

    return {
        "hour": local_hour,
        "time_of_day": time_of_day,
        "weekday": weekday_cn,
        "hours_since_last_message": round(hours_since_last_message, 1),
    }


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
        """Tick all active user×character pairs with a single DB session."""
        try:
            async with self.db_session_factory() as session:
                # Single JOIN query: active users + relationship + user timezone +
                # last message from the user in this conversation
                result = await session.execute(
                    text(
                        "SELECT s.user_id, s.character_id, s.last_activity_at, "
                        "r.current_stage, r.intimacy_level, "
                        "COALESCE(u.timezone, 'Asia/Shanghai') AS user_timezone, "
                        "(SELECT MAX(cm.created_at) FROM chat_messages cm "
                        " WHERE cm.user_id = s.user_id "
                        "   AND cm.character_id = s.character_id "
                        "   AND cm.role = 'user') AS last_user_message_at "
                        "FROM sessions s "
                        "LEFT JOIN relationship_states r "
                        "  ON r.user_id = s.user_id AND r.character_id = s.character_id "
                        "LEFT JOIN users u ON u.id = s.user_id "
                        "WHERE s.last_activity_at > NOW() - INTERVAL '7 days'"
                    )
                )
                rows = result.fetchall()

            logger.info("inner_loop_ticking", user_count=len(rows))

            for row in rows:
                user_id = row[0]
                character_id = row[1]
                last_activity = row[2]
                relationship_stage = row[3] or "STRANGER"
                intimacy = float(row[4] or 0.0)
                user_timezone: str = row[5] or "Asia/Shanghai"
                last_user_msg_at = row[6]

                # Calculate days since last interaction
                days_since_last = 0.0
                if last_activity:
                    if hasattr(last_activity, "replace"):
                        last_activity = last_activity.replace(tzinfo=timezone.utc)
                    delta = datetime.now(timezone.utc) - last_activity
                    days_since_last = delta.total_seconds() / 86400

                # Normalise last_user_message_at to UTC-aware datetime
                if last_user_msg_at and hasattr(last_user_msg_at, "replace"):
                    last_user_msg_at = last_user_msg_at.replace(tzinfo=timezone.utc)

                # Check for anniversary
                try:
                    async with self.db_session_factory() as anniv_session:
                        is_anniversary = await self._check_anniversary(
                            user_id, character_id, anniv_session
                        )
                except Exception:
                    is_anniversary = False

                # Load lightweight context for LLM-generated proactive content
                # (best-effort; empty strings just yield a less-personalized message).
                recent_context, user_facts = await self._load_proactive_context(
                    user_id, character_id
                )

                # Tick — pass a DB session so the daily quota / cross-character
                # cooldown / content-dedup gates hit the proactive_messages
                # table. Without a session tick() falls back to an in-memory
                # counter that resets on process restart, which is how BUG-6
                # in TEST_REPORT_20260712 got 4 messages per (user, character)
                # per day past the 3-cap.
                try:
                    async with self.db_session_factory() as tick_session:
                        msg = await self.inner_state_service.tick(
                            user_id=user_id,
                            character_id=character_id,
                            relationship_stage=relationship_stage,
                            intimacy=intimacy,
                            days_since_last_interaction=days_since_last,
                            is_anniversary=is_anniversary,
                            recent_context=recent_context,
                            user_facts=user_facts,
                            db=tick_session,
                        )

                    if msg is not None:
                        await self._persist(msg)
                        _proactive_messages.append(msg)
                        logger.info(
                            "proactive_message_generated",
                            user_id=str(user_id),
                            character_id=character_id,
                            trigger_type=msg.trigger_type,
                            content_preview=msg.content[:40],
                        )

                    # Check for ritual triggers (idle-based, local-time-aware)
                    async with self.db_session_factory() as ritual_session:
                        ritual_msg = await self._check_ritual_triggers(
                            user_id,
                            character_id,
                            ritual_session,
                            user_timezone=user_timezone,
                            last_user_message_at=last_user_msg_at,
                        )
                    if ritual_msg is not None:
                        await self._persist(ritual_msg)
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

    async def _persist(self, msg: ProactiveMessage) -> None:
        """Persist a generated proactive message to the proactive_messages table.

        Best-effort: a persistence failure is logged but does not abort the tick
        (the message still reaches the in-memory mirror). It is NOT swallowed
        silently — unlike the previous dedup path, the error is surfaced.
        """
        try:
            async with self.db_session_factory() as session:
                await proactive_repo.insert_message(session, msg)
        except Exception as e:
            logger.error(
                "proactive_message_persist_failed",
                user_id=str(msg.user_id),
                character_id=msg.character_id,
                trigger_type=msg.trigger_type,
                error=str(e),
            )

    async def _load_proactive_context(
        self,
        user_id: UUID,
        character_id: str,
    ) -> tuple[str, str]:
        """Load recent episodes + top facts to personalize proactive content.

        Best-effort: returns ("", "") on any failure so a proactive message can
        still be generated (or fall back to a template) without the context.
        """
        recent_context = ""
        user_facts = ""
        try:
            async with self.db_session_factory() as session:
                episodes = await session.execute(
                    text(
                        "SELECT episode_summary FROM episodic_memories "
                        "WHERE user_id = :user_id AND character_id = :character_id "
                        "AND do_not_recall = false "
                        "ORDER BY episode_end_at DESC LIMIT 5"
                    ),
                    {"user_id": str(user_id), "character_id": character_id},
                )
                summaries = [r[0] for r in episodes.fetchall() if r[0]]
                recent_context = "\n".join(f"- {s}" for s in reversed(summaries))

                facts = await session.execute(
                    text(
                        "SELECT literal_text FROM fact_nodes "
                        "WHERE user_id = :user_id AND character_id = :character_id "
                        "AND do_not_recall = false AND is_active = true "
                        "ORDER BY importance DESC, confidence DESC LIMIT 5"
                    ),
                    {"user_id": str(user_id), "character_id": character_id},
                )
                fact_lines = [r[0] for r in facts.fetchall() if r[0]]
                user_facts = "\n".join(f"- {f}" for f in fact_lines)
        except Exception as e:
            logger.debug("proactive_context_load_failed", error=str(e))
        return recent_context, user_facts

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

    async def _dedup_or_none(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        character_id: str,
        content: str,
        trigger_type: str,
        hours_since: float,
        ltc: dict,
    ) -> Optional[str]:
        """Retry the content once if it duplicates a recent send; else suppress.

        Mirrors ``InnerStateService`` Gate I-8 for the ritual path.
        """
        for _attempt in range(2):
            if not await proactive_repo.content_seen_recently(
                session, user_id, character_id, content, _CONTENT_DEDUP_DAYS
            ):
                return content
            logger.info(
                "ritual_content_duplicate_retry",
                user_id=str(user_id),
                character_id=character_id,
            )
            content = await self.inner_state_service._resolve_proactive_content(
                character_id=character_id,
                trigger_type=trigger_type,
                relationship_stage="FRIEND",
                intimacy=0.5,
                days_since_last_interaction=hours_since / 24,
                recent_context="",
                user_facts="",
                local_time_context=ltc,
            )
        logger.info(
            "ritual_suppressed_content_dedup",
            user_id=str(user_id),
            character_id=character_id,
            content_preview=(content or "")[:40],
        )
        return None

    async def _check_ritual_triggers(
        self,
        user_id: UUID,
        character_id: str,
        session: AsyncSession,
        now: Optional[datetime] = None,
        user_timezone: str = "Asia/Shanghai",
        last_user_message_at: Optional[datetime] = None,
    ) -> Optional[ProactiveMessage]:
        """Check for proactive triggers using idle-time gate + local-time context.

        New logic (replaces UTC hour-window):
        - Primary gate: user must be idle >= 8 hours since their last message.
          < 8 h → never fire (user is actively chatting, don't interrupt).
          8-12 h → roll dice (50 % chance to fire).
          > 12 h → always fire (AI should reach out proactively).
        - Dedup gate: at most one proactive per (user, character) per day.
        - Daily quota: counted toward DAILY_PROACTIVE_QUOTA.
        - Content: generated by LLM with local-time context injected into the
          prompt; falls back to legacy template only on LLM failure.
        """
        if now is None:
            now = datetime.now(timezone.utc)

        # ── Idle gate ──────────────────────────────────────────────────────────
        if last_user_message_at is None:
            hours_since = float("inf")
        else:
            hours_since = (now - last_user_message_at).total_seconds() / 3600

        if hours_since < MIN_IDLE_HOURS:
            return None

        if MIN_IDLE_HOURS <= hours_since < DICE_IDLE_HOURS:
            if random.random() > 0.5:
                return None

        trigger_type = "ritual_idle"

        # ── Dedup & quota ──────────────────────────────────────────────────────
        already_sent = await proactive_repo.count_today(
            session, user_id, character_id, trigger_type
        )
        if already_sent > 0:
            return None

        sent_today = await proactive_repo.count_all_today(session, user_id, character_id)
        if sent_today >= DAILY_PROACTIVE_QUOTA:
            logger.info(
                "ritual_suppressed_daily_quota",
                user_id=str(user_id),
                character_id=character_id,
                sent_today=sent_today,
            )
            return None

        # Cross-character cooldown — same rule as InnerStateService Gate I-7.
        # Prevents the fan-out burst where every character pings the user in
        # the same tick (TEST_REPORT_20260712 BUG-6).
        if await proactive_repo.any_recent_across_characters(
            session, user_id, _CROSS_CHARACTER_COOLDOWN_MINUTES
        ):
            logger.info(
                "ritual_suppressed_cross_character_cooldown",
                user_id=str(user_id),
                character_id=character_id,
                window_minutes=_CROSS_CHARACTER_COOLDOWN_MINUTES,
            )
            return None

        # ── Build local-time context + generate content ───────────────────────
        ltc = _build_local_time_context(now, user_timezone, hours_since)
        content = await self.inner_state_service._resolve_proactive_content(
            character_id=character_id,
            trigger_type=trigger_type,
            relationship_stage="FRIEND",
            intimacy=0.5,
            days_since_last_interaction=hours_since / 24,
            recent_context="",
            user_facts="",
            local_time_context=ltc,
        )

        content = await self._dedup_or_none(
            session=session,
            user_id=user_id,
            character_id=character_id,
            content=content,
            trigger_type=trigger_type,
            hours_since=hours_since,
            ltc=ltc,
        )
        if content is None:
            return None

        msg = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            content=content,
            trigger_type=trigger_type,
            created_at=now,
        )

        logger.info(
            "ritual_triggered",
            user_id=str(user_id),
            character_id=character_id,
            hours_since=round(hours_since, 1),
            local_time_of_day=ltc.get("time_of_day"),
        )

        return msg
