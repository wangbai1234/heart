"""Membership API routes — /api/membership/*"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.membership import get_effective_tier, get_entitlements

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/membership", tags=["membership"])


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
