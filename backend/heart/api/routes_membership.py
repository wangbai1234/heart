"""Membership API routes — /api/membership/*"""

from __future__ import annotations

import random
import string
import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.membership import get_effective_tier, get_entitlements

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/membership", tags=["membership"])


def _gen_binding_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


@router.get("")
async def get_membership(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the current user's effective membership tier and entitlements."""
    tier = await get_effective_tier(db, uuid.UUID(current_user.user_id))
    ent = get_entitlements(tier)
    return {
        "tier": tier,
        "models": ent.models,
        "tts": ent.tts,
        "clone": ent.clone,
        "monthly_grant_coins": ent.monthly_grant_fen // 100,
    }


@router.post("/binding_code")
async def create_binding_code(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a binding code to embed in an afdian order remark.

    Code is unique, 8-char uppercase alphanumeric, valid for 7 days.
    """
    code = _gen_binding_code()
    await db.execute(
        text(
            """
            INSERT INTO user_binding_codes (id, user_id, code, created_at, expires_at)
            VALUES (:id, :uid, :code, NOW(), NOW() + INTERVAL '7 days')
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {"id": uuid.uuid4(), "uid": uuid.UUID(current_user.user_id), "code": code},
    )
    await db.commit()
    return {"code": code, "instructions": "在爱发电备注中填入此代码，系统将自动匹配并发放权益"}
