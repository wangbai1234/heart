"""Credits API routes — /api/credits/*"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import InsufficientCreditsError, get_balance, redeem
from heart.core.auth import TokenData, get_current_user
from heart.core.config import settings

from .deps import require_age_verified
from .rate_limit import limiter
from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/credits", tags=["credits"])


@router.get("/balance")
async def balance(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return current credits balance."""
    uid = uuid.UUID(current_user.user_id)
    bal = await get_balance(db, uid)
    return {"balance": bal / 100}


@router.get("/transactions")
async def transactions(
    cursor: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return paginated credit transactions (newest first)."""
    uid = uuid.UUID(current_user.user_id)

    if cursor:
        result = await db.execute(
            text("""
                SELECT delta, type, ref_type, balance_after, created_at
                FROM credit_transactions
                WHERE user_id = :uid AND created_at < :cursor
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": uid, "cursor": cursor, "limit": limit + 1},
        )
    else:
        result = await db.execute(
            text("""
                SELECT delta, type, ref_type, balance_after, created_at
                FROM credit_transactions
                WHERE user_id = :uid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": uid, "limit": limit + 1},
        )

    rows = result.mappings().all()
    has_next = len(rows) > limit
    items = rows[:limit]

    return {
        "items": [
            {
                "delta": r["delta"] / 100,
                "type": r["type"],
                "ref_type": r["ref_type"],
                "balance_after": r["balance_after"] / 100,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            }
            for r in items
        ],
        "next_cursor": items[-1]["created_at"].isoformat() if has_next and items else None,
    }


class RedeemRequest(BaseModel):
    code: str


@router.post("/redeem")
@limiter.limit("10/minute")
async def redeem_code(
    request: Request,
    body: RedeemRequest,
    current_user: TokenData = Depends(require_age_verified),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Redeem a code for credits."""
    uid = uuid.UUID(current_user.user_id)
    try:
        new_balance = await redeem(db, uid, body.code)
        return {"ok": True, "credited": True, "balance": new_balance / 100}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except InsufficientCreditsError:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Insufficient credits"
        ) from None


@router.get("/pricing")
async def pricing() -> dict:
    """Return current pricing info."""
    return {
        "signup_grant": settings.signup_grant_credits / 100,
        "per_text": settings.credits_cost_text_message / 100,
        "per_voice": settings.credits_cost_voice_message / 100,
        "afdian_url": settings.afdian_sponsor_url,
        "tiers": [
            {"label": "尝鲜", "price": 6, "credits": 300},
            {"label": "常用", "price": 30, "credits": 1800},
            {"label": "超值", "price": 68, "credits": 4500},
            {"label": "豪华", "price": 128, "credits": 9000},
        ],
    }
