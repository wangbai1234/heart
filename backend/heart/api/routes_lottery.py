"""Invite lottery and membership coupon APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.lottery.service import LotteryError, draw
from heart.membership.coupons import CouponError, activate_coupon

from .wiring import get_db

router = APIRouter(prefix="/api", tags=["rewards"])


class DrawRequest(BaseModel):
    chance_id: int = Field(gt=0)


@router.get("/lottery/status")
async def lottery_status(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    chance = (
        (
            await db.execute(
                text(
                    """
                SELECT COUNT(*) AS available, MIN(expires_at) AS next_expiry
                FROM invite_draw_chances
                WHERE user_id = :uid AND consumed_at IS NULL AND expires_at > NOW()
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .one()
    )
    chances = (
        (
            await db.execute(
                text(
                    """
                SELECT id, expires_at FROM invite_draw_chances
                WHERE user_id = :uid AND consumed_at IS NULL AND expires_at > NOW()
                ORDER BY expires_at, id
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .all()
    )
    prizes = (
        (
            await db.execute(
                text(
                    """
                SELECT code, kind, payload, weight
                FROM lottery_prizes
                WHERE pool_id = (SELECT id FROM lottery_pool_versions WHERE status = 'active')
                  AND enabled = TRUE
                ORDER BY id
                """
                )
            )
        )
        .mappings()
        .all()
    )
    return {
        "available_chances": int(chance["available"]),
        "next_expiry_at": chance["next_expiry"],
        "chances": [dict(row) for row in chances],
        "pool_prizes": [dict(row) for row in prizes],
    }


@router.post("/lottery/draw")
async def draw_lottery(
    body: DrawRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await draw(db, uuid.UUID(current_user.user_id), body.chance_id)
    except LotteryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/rewards/coupons")
async def list_coupons(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    await db.execute(
        text(
            """
            UPDATE membership_reward_coupons SET status = 'expired'
            WHERE user_id = :uid AND status = 'active' AND activate_by <= NOW()
            """
        ),
        {"uid": uid},
    )
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT id, tier, days, granted_at, activate_by, activated_at,
                       starts_at, expires_at, status
                FROM membership_reward_coupons
                WHERE user_id = :uid ORDER BY granted_at DESC
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .all()
    )
    return {"coupons": [dict(row) for row in rows]}


@router.post("/rewards/coupons/{coupon_id}/activate")
async def activate_membership_coupon(
    coupon_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await activate_coupon(db, uuid.UUID(current_user.user_id), coupon_id)
    except CouponError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
