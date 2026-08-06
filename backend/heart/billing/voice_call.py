"""Voice-call (语音通话) per-minute billing with monthly free allowance.

A voice call is ephemeral — unlike a story run there is no persistent row to
anchor billing to, so the client drives billing with a heartbeat carrying a
client-generated ``call_id`` (unique per call) and a monotonic ``minute`` index
(0, 1, 2, …). Idempotency keys are ``voice_call:{call_id}:{minute}`` so a
duplicated/retried heartbeat never bills the same minute twice.

Free-minute allowance is tier-scoped and resets every calendar month
(Asia/Shanghai). The first ``voice_call_free_minutes(tier)`` minutes of a
month consume the allowance (charged 0 fen); every minute beyond it costs
``voice_call_minute_cost_fen()``.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import InsufficientCreditsError, deduct_credits
from heart.billing.pricing import voice_call_minute_cost_fen
from heart.membership import get_effective_tier, voice_call_free_minutes

logger = structlog.get_logger(__name__)

_SHANGHAI = ZoneInfo("Asia/Shanghai")


def current_month_key(now: datetime | None = None) -> str:
    """Return the Asia/Shanghai month bucket as ``YYYY-MM``."""
    now = now or datetime.now(tz=timezone.utc)
    return now.astimezone(_SHANGHAI).strftime("%Y-%m")


async def get_quota(db: AsyncSession, user_id: uuid.UUID) -> dict:
    """Return this month's voice-call quota snapshot for *user_id*.

    Shape: ``{"tier", "free_minutes", "used_minutes", "remaining_minutes",
    "minute_cost_coins", "month_key"}``. All minute counts are whole minutes;
    coins are display coins (1 coin = 100 fen).
    """
    tier = await get_effective_tier(db, user_id)
    free_minutes = voice_call_free_minutes(tier)
    month_key = current_month_key()

    used = (
        await db.execute(
            text(
                "SELECT used_minutes FROM user_voice_call_quotas "
                "WHERE user_id = :uid AND month_key = :mk"
            ),
            {"uid": user_id, "mk": month_key},
        )
    ).scalar_one_or_none() or 0

    from heart.core.config import settings

    return {
        "tier": tier,
        "free_minutes": free_minutes,
        "used_minutes": int(used),
        "remaining_minutes": max(0, free_minutes - int(used)),
        "minute_cost_coins": settings.voice_call_minute_cost_coins,
        "month_key": month_key,
    }


async def _bump_used_minute(
    db: AsyncSession, user_id: uuid.UUID, month_key: str, expected_used: int
) -> bool:
    """Advance ``used_minutes`` from *expected_used* to +1, idempotently.

    Uses an upsert guarded on ``used_minutes = expected_used`` so two concurrent
    heartbeats for the same minute index only advance the counter once (the
    second is a guarded no-op). Returns True when this call performed the bump.
    """
    result = await db.execute(
        text(
            """
            INSERT INTO user_voice_call_quotas (id, user_id, month_key, used_minutes, updated_at)
            VALUES (:id, :uid, :mk, 1, NOW())
            ON CONFLICT (user_id, month_key) DO UPDATE
                SET used_minutes = user_voice_call_quotas.used_minutes + 1,
                    updated_at = NOW()
                WHERE user_voice_call_quotas.used_minutes = :expected
            RETURNING used_minutes
            """
        ),
        {
            "id": uuid.uuid4(),
            "uid": user_id,
            "mk": month_key,
            "expected": expected_used,
        },
    )
    return result.scalar_one_or_none() is not None


async def charge_call_minute(
    db: AsyncSession,
    user_id: uuid.UUID,
    call_id: str,
    minute: int,
) -> tuple[str, int]:
    """Bill one minute of voice call (driven by the client heartbeat).

    Returns ``(status, balance)`` where status is one of:

    - ``"free"`` — inside the monthly free allowance; nothing charged.
      ``balance`` is the current balance (unchanged).
    - ``"charged"`` — one paid minute billed; ``balance`` is the new balance.
    - ``"insufficient"`` — balance can't cover a paid minute; the caller should
      end the call and prompt a recharge. ``balance`` is the (unchanged) balance.

    Idempotent per (call_id, minute) via the key ``voice_call:{call_id}:{minute}``.
    Free-minute consumption is tracked in ``user_voice_call_quotas`` keyed by the
    Asia/Shanghai month, so the allowance resets each calendar month.
    """
    from heart.billing import get_balance

    tier = await get_effective_tier(db, user_id)
    free_minutes = voice_call_free_minutes(tier)
    month_key = current_month_key()

    used = (
        await db.execute(
            text(
                "SELECT used_minutes FROM user_voice_call_quotas "
                "WHERE user_id = :uid AND month_key = :mk FOR UPDATE"
            ),
            {"uid": user_id, "mk": month_key},
        )
    ).scalar_one_or_none() or 0
    used = int(used)

    if used < free_minutes:
        # Still inside the free allowance — consume one free minute, charge 0.
        bumped = await _bump_used_minute(db, user_id, month_key, used)
        await db.commit()
        if not bumped:
            logger.debug(
                "voice_call_free_minute_race",
                user_id=str(user_id),
                call_id=call_id,
                minute=minute,
            )
        return ("free", await get_balance(db, user_id))

    # Free allowance spent → charge per-minute rate, idempotent per minute.
    cost = voice_call_minute_cost_fen()
    try:
        balance = await deduct_credits(
            db,
            user_id,
            cost,
            f"voice_call:{call_id}:{minute}",
            "consume_voice_call",
        )
        await db.commit()
    except InsufficientCreditsError as e:
        await db.rollback()
        return ("insufficient", e.balance)

    logger.info(
        "voice_call_minute_charged",
        user_id=str(user_id),
        call_id=call_id,
        minute=minute,
        cost=cost,
        balance=balance,
    )
    return ("charged", balance)
