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
    """Return current pricing info including model costs and membership tiers."""
    from heart.billing.pricing import action_cost_fen, llm_cost_fen, tts_cost_fen
    from heart.membership import get_entitlements

    free_ent = get_entitlements("free")
    plus_ent = get_entitlements("plus")
    immersive_ent = get_entitlements("immersive")

    return {
        # Legacy fields (kept for backwards compat)
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
        # Model pricing (cost in display coins per LLM turn)
        "models": [
            {
                "id": "deepseek",
                "label": "DeepSeek",
                "cost": llm_cost_fen("deepseek") // 100,
                "tiers_allowed": ["free", "plus", "immersive"],
            },
            {
                "id": "grok",
                "label": "Grok",
                "cost": settings.grok_cost_credits,
                "tiers_allowed": ["plus", "immersive"],
            },
            {
                "id": "claude",
                "label": "Claude",
                "cost": settings.claude_cost_credits,
                "tiers_allowed": ["immersive"],
            },
        ],
        # TTS pricing (cost in display coins per voice bubble)
        "tts_providers": [
            {
                "id": "mimo",
                "label": "MiMo",
                "cost": settings.mimo_tts_cost_credits,
                "tiers_allowed": ["free", "plus", "immersive"],
            },
            {
                "id": "fish",
                "label": "Fish Audio",
                "cost": settings.fish_tts_cost_credits,
                "tiers_allowed": ["plus", "immersive"],
            },
        ],
        # One-shot actions (cost in display coins)
        "actions": [
            {
                "id": "clone_mimo",
                "label": "MiMo 声音克隆",
                "cost": action_cost_fen("clone_mimo") // 100,
            },
            {
                "id": "clone_fish",
                "label": "Fish 声音克隆",
                "cost": action_cost_fen("clone_fish") // 100,
            },
        ],
        # Membership subscription tiers
        "membership_tiers": [
            {
                "id": "free",
                "label": "体验版",
                "price_monthly": 0,
                "models": free_ent.models,
                "tts": free_ent.tts,
                "clone": free_ent.clone,
                "monthly_grant": free_ent.monthly_grant_fen // 100,
            },
            {
                "id": "plus",
                "label": "进阶版",
                "price_monthly": settings.membership_plus_price_monthly,
                "models": plus_ent.models,
                "tts": plus_ent.tts,
                "clone": plus_ent.clone,
                "monthly_grant": plus_ent.monthly_grant_fen // 100,
            },
            {
                "id": "immersive",
                "label": "沉浸版",
                "price_monthly": settings.membership_immersive_price_monthly,
                "models": immersive_ent.models,
                "tts": immersive_ent.tts,
                "clone": immersive_ent.clone,
                "monthly_grant": immersive_ent.monthly_grant_fen // 100,
            },
        ],
        # Coin shop packages
        "shop": [
            {"sku": "coins_60", "label": "☕ 小份补给", "price": 6, "credits": 60, "bonus": 0},
            {"sku": "coins_220", "label": "🌙 陪伴补给", "price": 18, "credits": 200, "bonus": 20},
            {"sku": "coins_650", "label": "⭐ 深度补给", "price": 48, "credits": 480, "bonus": 170},
            {
                "sku": "coins_2000",
                "label": "🌌 长期陪伴",
                "price": 128,
                "credits": 1280,
                "bonus": 720,
            },
        ],
    }
