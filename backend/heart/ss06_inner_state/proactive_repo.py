"""Persistence for SS06 proactive messages.

The Inner Loop worker generates proactive messages (scheduled/anniversary/
ritual …). These are persisted to the ``proactive_messages`` table (migration
018) so that:

- ritual dedup (``count_today``) and the daily quota can actually be enforced —
  previously the dedup query hit a non-existent table, the error was swallowed,
  and ``ritual_morning`` greetings piled up once per tick;
- ``/api/proactive/pending`` survives process restarts and can mark messages
  delivered instead of re-serving them forever.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List, Sequence
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss06_inner_state.models import ProactiveMessage


async def insert_message(session: AsyncSession, msg: ProactiveMessage) -> None:
    """Persist one proactive message. Caller owns the transaction (commit)."""
    await session.execute(
        text(
            "INSERT INTO proactive_messages "
            "(id, user_id, character_id, content, trigger_type, created_at, delivered) "
            "VALUES (:id, :user_id, :character_id, :content, :trigger_type, "
            ":created_at, :delivered)"
        ),
        {
            "id": str(msg.id),
            "user_id": str(msg.user_id),
            "character_id": msg.character_id,
            "content": msg.content,
            "trigger_type": msg.trigger_type,
            "created_at": msg.created_at,
            "delivered": msg.delivered,
        },
    )
    await session.commit()


async def count_today(
    session: AsyncSession,
    user_id: UUID,
    character_id: str,
    trigger_type: str,
) -> int:
    """Count messages of ``trigger_type`` already created today (UTC date).

    Used for ritual dedup — one ``ritual_morning`` / ``ritual_night`` per day.
    """
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
            "trigger_type": trigger_type,
        },
    )
    return int(result.scalar() or 0)


async def count_all_today(
    session: AsyncSession,
    user_id: UUID,
    character_id: str,
) -> int:
    """Count all proactive messages created today for this user×character.

    Used to enforce the daily quota across every trigger type (rituals
    included), mirroring InnerStateService's ``proactives_today >= 3`` gate.
    """
    result = await session.execute(
        text(
            "SELECT COUNT(*) FROM proactive_messages "
            "WHERE user_id = :user_id AND character_id = :character_id "
            "AND created_at::date = CURRENT_DATE"
        ),
        {"user_id": str(user_id), "character_id": character_id},
    )
    return int(result.scalar() or 0)


async def any_recent_across_characters(
    session: AsyncSession,
    user_id: UUID,
    within_minutes: int,
) -> bool:
    """Did any character send this user a proactive within ``within_minutes``?

    Cross-character rate-limit: prevents the "8 characters in the same second"
    burst reported in TEST_REPORT_20260712 BUG-6. Ticks fan out per character
    within a single scheduler pass, so without a user-scoped gate a chatty
    user with many characters gets a wall of concurrent proactives.
    """
    result = await session.execute(
        text(
            "SELECT 1 FROM proactive_messages "
            "WHERE user_id = :user_id "
            "AND created_at >= NOW() - make_interval(mins => :mins) "
            "LIMIT 1"
        ),
        {"user_id": str(user_id), "mins": int(within_minutes)},
    )
    return result.first() is not None


async def content_seen_recently(
    session: AsyncSession,
    user_id: UUID,
    character_id: str,
    content: str,
    within_days: int,
) -> bool:
    """Has this exact content been sent recently for this user×character?

    Blocks the "月月想着你，今天过得怎么样？" x9 spam (TEST_REPORT_20260712
    BUG-1). Compares on the trimmed content, so trailing whitespace does not
    let a near-duplicate slip past.
    """
    stripped = (content or "").strip()
    if not stripped:
        return False
    result = await session.execute(
        text(
            "SELECT 1 FROM proactive_messages "
            "WHERE user_id = :user_id AND character_id = :character_id "
            "AND TRIM(content) = :content "
            "AND created_at >= NOW() - make_interval(days => :days) "
            "LIMIT 1"
        ),
        {
            "user_id": str(user_id),
            "character_id": character_id,
            "content": stripped,
            "days": int(within_days),
        },
    )
    return result.first() is not None


async def fetch_pending(
    session: AsyncSession,
    user_id: UUID,
    character_id: str | None = None,
    since: timedelta | None = None,
) -> List[ProactiveMessage]:
    """Return undelivered proactive messages within the ``since`` window."""
    if since is None:
        since = timedelta(days=7)
    cutoff = datetime.now(timezone.utc) - since

    params: dict[str, object] = {"user_id": str(user_id), "cutoff": cutoff}
    sql = (
        "SELECT id, user_id, character_id, content, trigger_type, "
        "created_at, delivered, delivered_at FROM proactive_messages "
        "WHERE user_id = :user_id AND delivered = false AND created_at >= :cutoff"
    )
    if character_id is not None:
        sql += " AND character_id = :character_id"
        params["character_id"] = character_id
    sql += " ORDER BY created_at DESC"

    result = await session.execute(text(sql), params)
    rows = result.fetchall()
    return [
        ProactiveMessage(
            id=r.id,
            user_id=r.user_id,
            character_id=r.character_id,
            content=r.content,
            trigger_type=r.trigger_type,
            created_at=r.created_at,
            delivered=r.delivered,
            delivered_at=r.delivered_at,
        )
        for r in rows
    ]


async def mark_delivered(
    session: AsyncSession,
    user_id: UUID,
    message_ids: Sequence[UUID],
) -> int:
    """Mark messages delivered. Scoped to ``user_id`` to prevent cross-user acks.

    Returns the number of rows updated.
    """
    if not message_ids:
        return 0
    result = await session.execute(
        text(
            "UPDATE proactive_messages SET delivered = true, delivered_at = NOW() "
            "WHERE user_id = :user_id AND id = ANY(:ids) AND delivered = false"
        ),
        {"user_id": str(user_id), "ids": [str(m) for m in message_ids]},
    )
    await session.commit()
    # rowcount lives on CursorResult (DML); getattr keeps mypy happy across the
    # Result union and tolerates drivers that report -1.
    rowcount = getattr(result, "rowcount", 0)
    return int(rowcount) if rowcount and rowcount > 0 else 0
