"""Invite system API routes."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.invite.service import get_or_create_code, record_invite_signup

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/invite", tags=["invite"])

_APP_BASE_URL = "https://yuoyuo.app"


@router.get("")
async def get_invite_info(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the current user's invite code and deep-link URL."""
    user_id = uuid.UUID(current_user.user_id)
    code = await get_or_create_code(db, user_id)
    return {
        "code": code,
        "url": f"{_APP_BASE_URL}/join?ref={code}",
    }


class UseInviteRequest(BaseModel):
    code: str


@router.post("/use")
async def use_invite_code(
    body: UseInviteRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Record that the current user registered with an invite code.

    Must be called once right after signup.  Idempotent — later calls
    with the same invitee are silently ignored.
    """
    if not body.code or len(body.code) > 16:
        raise HTTPException(status_code=400, detail="无效的邀请码")

    user_id = uuid.UUID(current_user.user_id)
    ok = await record_invite_signup(db, user_id, body.code)
    return {"accepted": ok}
