"""Invite system API routes."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.core.config import settings
from heart.invite.service import get_or_create_code, record_invite_signup

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/invite", tags=["invite"])

_APP_BASE_URL = "https://yuoyuo.app"


@router.get("/status")
async def get_invite_status(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return invite status per api_contract.md §1.3."""
    user_id = uuid.UUID(current_user.user_id)
    code = await get_or_create_code(db, user_id)

    invited_count = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM user_invite_uses "
                "WHERE inviter_id = :uid AND first_chat_at IS NOT NULL"
            ),
            {"uid": user_id},
        )
    ).scalar_one()

    pending_count = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM user_invite_uses "
                "WHERE inviter_id = :uid AND first_chat_at IS NULL"
            ),
            {"uid": user_id},
        )
    ).scalar_one()

    # Sum all invite-type grants (set via type_str="invite" in handle_first_chat)
    total_reward_fen = (
        await db.execute(
            text(
                "SELECT COALESCE(SUM(delta), 0) FROM credit_transactions "
                "WHERE user_id = :uid AND ref_type = 'invite'"
            ),
            {"uid": user_id},
        )
    ).scalar_one()

    invited_count = int(invited_count)
    pending_count = int(pending_count)

    return {
        "invite_code": code,
        "invite_url": f"{_APP_BASE_URL}/login?invite={code}",
        "invited_count": invited_count,
        "pending_count": pending_count,
        "total_reward": int(total_reward_fen) // 100,
        "stages": [
            {
                "threshold": 5,
                "bonus": settings.invite_milestone_5_coins,
                "reached": invited_count >= 5,
            },
            {
                "threshold": 10,
                "bonus": settings.invite_milestone_10_coins,
                "reached": invited_count >= 10,
            },
        ],
    }


class BindInviteRequest(BaseModel):
    code: str


@router.post("/bind")
async def bind_invite_code(
    body: BindInviteRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bind an invite code to the current user. Per api_contract.md §1.4."""
    if not body.code or len(body.code) > 16:
        raise HTTPException(status_code=400, detail="invalid_code")

    user_id = uuid.UUID(current_user.user_id)
    result = await record_invite_signup(db, user_id, body.code)

    if result == "ok":
        await db.commit()
        return {"ok": True}
    raise HTTPException(status_code=400, detail=result)


# ── Legacy endpoints (deprecated aliases, kept for forward-compatibility) ──


@router.get("")
async def get_invite_info(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deprecated: use GET /status instead."""
    user_id = uuid.UUID(current_user.user_id)
    code = await get_or_create_code(db, user_id)
    return {
        "code": code,
        "url": f"{_APP_BASE_URL}/login?invite={code}",
    }


class UseInviteRequest(BaseModel):
    code: str


@router.post("/use")
async def use_invite_code(
    body: UseInviteRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deprecated: use POST /bind instead."""
    if not body.code or len(body.code) > 16:
        raise HTTPException(status_code=400, detail="无效的邀请码")

    user_id = uuid.UUID(current_user.user_id)
    result = await record_invite_signup(db, user_id, body.code)
    if result == "ok":
        await db.commit()
    return {"accepted": result == "ok"}
