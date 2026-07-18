"""Membership activation and extension service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant as grant_credits
from heart.membership import get_entitlements

logger = structlog.get_logger(__name__)


async def activate_or_extend(
    db: AsyncSession,
    user_id: uuid.UUID,
    tier: str,
    days: int,
    granted_by: str = "manual",
) -> datetime:
    """Grant or extend a membership tier for a user (upsert semantics).

    If the user already has an active membership of the same tier, the expiry
    is pushed forward from max(NOW(), current expires_at).  Otherwise a new
    row is inserted starting from NOW().

    Returns the new expires_at (UTC, timezone-aware).
    """
    now = datetime.now(tz=timezone.utc)

    result = await db.execute(
        text(
            """
            SELECT expires_at FROM user_memberships
            WHERE user_id = :uid AND tier = :tier AND expires_at > NOW()
            ORDER BY expires_at DESC
            LIMIT 1
            """
        ),
        {"uid": user_id, "tier": tier},
    )
    row = result.scalar_one_or_none()

    base_dt: datetime = row if row is not None else now
    new_expires = base_dt + timedelta(days=days)

    if row is not None:
        await db.execute(
            text(
                """
                UPDATE user_memberships
                SET expires_at = :expires_at, granted_by = :granted_by
                WHERE user_id = :uid AND tier = :tier AND expires_at > NOW()
                """
            ),
            {
                "uid": user_id,
                "tier": tier,
                "expires_at": new_expires,
                "granted_by": granted_by,
            },
        )
    else:
        await db.execute(
            text(
                """
                INSERT INTO user_memberships (id, user_id, tier, expires_at, granted_by, created_at)
                VALUES (:id, :uid, :tier, :expires_at, :granted_by, NOW())
                """
            ),
            {
                "id": uuid.uuid4(),
                "uid": user_id,
                "tier": tier,
                "expires_at": new_expires,
                "granted_by": granted_by,
            },
        )

    logger.info(
        "membership_activated",
        user_id=str(user_id),
        tier=tier,
        days=days,
        new_expires=new_expires.isoformat(),
        granted_by=granted_by,
    )

    ent = get_entitlements(tier)
    if ent.monthly_grant_fen > 0:
        await grant_credits(
            db,
            user_id,
            ent.monthly_grant_fen,
            idempotency_key=f"membership_grant:{granted_by}",
            type_str="membership_grant",
        )

    return new_expires
