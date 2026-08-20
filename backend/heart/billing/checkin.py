"""Permanent daily coin grants, including same-day membership top-ups."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import get_balance, grant
from heart.core.config import settings


def daily_target_for_tier(tier: str) -> int:
    return {
        "free": settings.daily_checkin_coins,
        "plus": settings.plus_daily_checkin_coins,
        "immersive": settings.immersive_daily_checkin_coins,
    }.get(tier, settings.daily_checkin_coins)


async def claim_daily_grant(
    db: AsyncSession, user_id: uuid.UUID, tier: str, *, day: str | None = None
) -> dict:
    today = day or (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d")
    daily_total = daily_target_for_tier(tier)
    key_prefix = f"checkin:{user_id}:{today}:"
    legacy_key = f"checkin:{user_id}:{today}"
    awarded_fen = int(
        (
            await db.execute(
                text(
                    "SELECT COALESCE(SUM(delta), 0) FROM credit_transactions "
                    "WHERE user_id = :uid AND ref_type = 'checkin' "
                    "AND (idempotency_key LIKE :prefix OR idempotency_key = :legacy)"
                ),
                {"uid": user_id, "prefix": f"{key_prefix}%", "legacy": legacy_key},
            )
        ).scalar_one()
    )
    coins = max(0, daily_total - awarded_fen // 100)
    if coins:
        balance = await grant(
            db,
            user_id,
            coins * 100,
            idempotency_key=f"{key_prefix}{daily_total}",
            type_str="grant",
            ref_type="checkin",
        )
    else:
        balance = await get_balance(db, user_id)
    return {
        "granted": coins > 0,
        "already": coins == 0,
        "coins": coins,
        "daily_total": daily_total,
        "tier": tier,
        "balance": balance / 100,
    }
