"""Yuan-denominated referral commission balance and spending API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.commission.service import COMMISSION_PRODUCTS, CommissionError, spend_commission
from heart.core.auth import TokenData, get_current_user

from .wiring import get_db

router = APIRouter(prefix="/api/commission", tags=["commission"])


class SpendCommissionRequest(BaseModel):
    target: str
    sku: str
    client_token: str = Field(min_length=8, max_length=64)


@router.get("/balance")
async def commission_balance(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    balance = int(
        (
            await db.execute(
                text("SELECT commission_balance_fen FROM users WHERE id = :uid"),
                {"uid": uid},
            )
        ).scalar_one()
    )
    entries = (
        (
            await db.execute(
                text(
                    """
                SELECT order_id, paid_fen, commission_fen, status, settle_at,
                       created_at, settled_at
                FROM commission_entries
                WHERE inviter_id = :uid ORDER BY created_at DESC LIMIT 50
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .all()
    )
    return {
        "balance_fen": balance,
        "balance_yuan": balance / 100,
        "entries": [dict(row) for row in entries],
        "products": COMMISSION_PRODUCTS,
    }


@router.post("/spend")
async def spend_commission_balance(
    body: SpendCommissionRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await spend_commission(
            db,
            uuid.UUID(current_user.user_id),
            body.target,
            body.sku,
            body.client_token,
        )
    except CommissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
