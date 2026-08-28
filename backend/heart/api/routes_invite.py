"""Invite system API routes."""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.invite.service import (
    daily_chance_limit,
    get_or_create_code,
    load_invite_rules,
    record_invite_signup,
)
from heart.membership import get_effective_tier

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
                "WHERE inviter_id = :uid AND qualified_at IS NOT NULL"
            ),
            {"uid": user_id},
        )
    ).scalar_one()

    pending_count = (
        await db.execute(
            text(
                "SELECT COUNT(*) FROM user_invite_uses "
                "WHERE inviter_id = :uid AND qualified_at IS NULL"
            ),
            {"uid": user_id},
        )
    ).scalar_one()

    # Keep the deprecated total_reward field for old clients during rollout.
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
    tier = await get_effective_tier(db, user_id)
    daily_limit = daily_chance_limit(tier, await load_invite_rules(db))
    today_granted = int(
        (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM invite_draw_chances
                    WHERE user_id = :uid
                      AND grant_day = DATE(NOW() AT TIME ZONE 'Asia/Shanghai')
                    """
                ),
                {"uid": user_id},
            )
        ).scalar_one()
    )
    chance_row = (
        (
            await db.execute(
                text(
                    """
                SELECT COUNT(*) AS available, MIN(expires_at) AS next_expiry
                FROM invite_draw_chances
                WHERE user_id = :uid AND consumed_at IS NULL AND expires_at > NOW()
                """
                ),
                {"uid": user_id},
            )
        )
        .mappings()
        .one()
    )
    invitees = (
        (
            await db.execute(
                text(
                    """
                SELECT id,
                       CASE WHEN status IN ('review', 'rejected')
                            THEN '疑似刷账号行为'
                            ELSE status
                       END AS status,
                       msg_count, ai_reply_count, qualified_at, created_at
                FROM user_invite_uses
                WHERE inviter_id = :uid
                ORDER BY created_at DESC LIMIT 50
                """
                ),
                {"uid": user_id},
            )
        )
        .mappings()
        .all()
    )

    return {
        "invite_code": code,
        "invite_url": f"{_APP_BASE_URL}/login?invite={code}",
        "invited_count": invited_count,
        "pending_count": pending_count,
        "total_reward": int(total_reward_fen) // 100,
        "stages": [],
        "available_chances": int(chance_row["available"]),
        "next_expiry_at": chance_row["next_expiry"],
        "today_granted": today_granted,
        "daily_limit": daily_limit,
        "today_remaining": max(0, daily_limit - today_granted),
        "invitees": [dict(row) for row in invitees],
    }


class BindInviteRequest(BaseModel):
    code: str


@router.post("/bind")
async def bind_invite_code(
    body: BindInviteRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bind an invite code to the current user. Per api_contract.md §1.4."""
    if not body.code or len(body.code) > 16:
        raise HTTPException(status_code=400, detail="invalid_code")

    user_id = uuid.UUID(current_user.user_id)
    result = await record_invite_signup(
        db,
        user_id,
        body.code,
        device_id=request.headers.get("x-device-id"),
        ip=request.client.host if request.client else None,
    )

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
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Deprecated: use POST /bind instead."""
    if not body.code or len(body.code) > 16:
        raise HTTPException(status_code=400, detail="无效的邀请码")

    user_id = uuid.UUID(current_user.user_id)
    result = await record_invite_signup(
        db,
        user_id,
        body.code,
        device_id=request.headers.get("x-device-id"),
        ip=request.client.host if request.client else None,
    )
    if result == "ok":
        await db.commit()
    return {"accepted": result == "ok"}
