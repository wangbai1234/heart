"""Membership API routes — /api/membership/*"""

from __future__ import annotations

import secrets
import string
import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.membership import get_effective_tier, get_entitlements, get_paid_checkin_tier

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/membership", tags=["membership"])

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _gen_binding_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))


async def _get_or_create_binding_code(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return the most recent valid binding code, creating one if none exists."""
    row = (
        await db.execute(
            text(
                "SELECT code FROM user_binding_codes "
                "WHERE user_id = :uid AND expires_at > NOW() "
                "ORDER BY expires_at DESC LIMIT 1"
            ),
            {"uid": user_id},
        )
    ).scalar_one_or_none()
    if row:
        return str(row)

    code = _gen_binding_code()
    await db.execute(
        text(
            "INSERT INTO user_binding_codes (id, user_id, code, created_at, expires_at) "
            "VALUES (:id, :uid, :code, NOW(), NOW() + INTERVAL '7 days') "
            "ON CONFLICT (code) DO NOTHING"
        ),
        {"id": uuid.uuid4(), "uid": user_id, "code": code},
    )
    await db.commit()
    return code


@router.get("")
async def get_membership(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return effective membership per api_contract.md §1.2."""
    uid = uuid.UUID(current_user.user_id)
    tier = await get_effective_tier(db, uid)
    checkin_tier = await get_paid_checkin_tier(db, uid)
    ent = get_entitlements(tier)

    expires_row = (
        await db.execute(
            text(
                """
                SELECT expires_at FROM (
                  SELECT tier, expires_at FROM user_memberships
                  WHERE user_id = :uid AND expires_at > NOW()
                  UNION ALL
                  SELECT tier, expires_at FROM membership_reward_coupons
                  WHERE user_id = :uid AND status = 'activated'
                    AND starts_at <= NOW() AND expires_at > NOW()
                ) entitlements
                ORDER BY CASE tier WHEN 'immersive' THEN 2 WHEN 'plus' THEN 1 ELSE 0 END DESC,
                         expires_at DESC LIMIT 1
                """
            ),
            {"uid": uid},
        )
    ).scalar_one_or_none()
    expires_at = expires_row.isoformat() if expires_row else None

    binding_code = await _get_or_create_binding_code(db, uid)

    # Voice-call monthly free-minute allowance + this month's usage.
    from heart.billing.checkin import daily_target_for_tier
    from heart.billing.voice_call import get_quota

    voice_call = await get_quota(db, uid)

    return {
        "tier": tier,
        "expires_at": expires_at,
        "monthly_grant": ent.monthly_grant_fen // 100,
        "daily_checkin_coins": daily_target_for_tier(checkin_tier),
        "daily_coins_permanent": True,
        "entitlements": {
            "models": ent.models,
            "tts": ent.tts,
            "clone": ent.clone,
            "free": ent.free,
        },
        "voice_call": {
            "free_minutes": voice_call["free_minutes"],
            "used_minutes": voice_call["used_minutes"],
            "remaining_minutes": voice_call["remaining_minutes"],
            "minute_cost_coins": voice_call["minute_cost_coins"],
        },
        "binding_code": binding_code,
    }


@router.post("/binding_code")
async def create_binding_code(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a fresh binding code to embed in an afdian order remark."""
    code = _gen_binding_code()
    await db.execute(
        text(
            "INSERT INTO user_binding_codes (id, user_id, code, created_at, expires_at) "
            "VALUES (:id, :uid, :code, NOW(), NOW() + INTERVAL '7 days') "
            "ON CONFLICT (code) DO NOTHING"
        ),
        {"id": uuid.uuid4(), "uid": uuid.UUID(current_user.user_id), "code": code},
    )
    await db.commit()
    return {"code": code, "instructions": "在爱发电备注中填入此代码，系统将自动匹配并发放权益"}
