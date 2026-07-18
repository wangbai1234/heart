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
    """Return current pricing per api_contract.md §1.1."""
    from heart.billing.pricing import action_cost_fen, llm_cost_fen, tts_cost_fen
    from heart.membership import get_entitlements

    free_ent = get_entitlements("free")
    plus_ent = get_entitlements("plus")
    immersive_ent = get_entitlements("immersive")

    return {
        "signup_grant": settings.signup_grant_credits // 100,
        "afdian_url": settings.afdian_sponsor_url,
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
        # One-shot actions — includes TTS and clone (cost in display coins)
        "actions": [
            {
                "id": "tts_mimo",
                "label": "MiMo 语音合成",
                "cost": tts_cost_fen("mimo") // 100,
            },
            {
                "id": "tts_fish",
                "label": "Fish Audio 语音合成",
                "cost": tts_cost_fen("fish") // 100,
            },
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
        # Membership subscription tiers — per api_contract.md §1.1
        "membership_tiers": [
            {
                "tier": "free",
                "label": "体验版",
                "price": 0,
                "sku": None,
                "benefits": ["DeepSeek 免费对话", "MiMo 语音"],
                "models": free_ent.models,
                "tts": free_ent.tts,
                "clone": free_ent.clone,
                "monthly_grant": free_ent.monthly_grant_fen // 100,
            },
            {
                "tier": "plus",
                "label": "进阶版",
                "price": settings.membership_plus_price_monthly,
                "sku": "plan_plus",
                "benefits": [
                    "DeepSeek + Grok 对话",
                    "MiMo + Fish 语音",
                    "声音克隆",
                    f"每月赠 {plus_ent.monthly_grant_fen // 100} 币",
                ],
                "models": plus_ent.models,
                "tts": plus_ent.tts,
                "clone": plus_ent.clone,
                "monthly_grant": plus_ent.monthly_grant_fen // 100,
            },
            {
                "tier": "immersive",
                "label": "沉浸版",
                "price": settings.membership_immersive_price_monthly,
                "sku": "plan_immersive",
                "benefits": [
                    "全模型（含 Claude）",
                    "MiMo + Fish 语音",
                    "声音克隆",
                    f"每月赠 {immersive_ent.monthly_grant_fen // 100} 币",
                ],
                "models": immersive_ent.models,
                "tts": immersive_ent.tts,
                "clone": immersive_ent.clone,
                "monthly_grant": immersive_ent.monthly_grant_fen // 100,
            },
        ],
        # Coin shop packages — SKU names and credits match api_contract.md §1.1
        "shop": [
            {"sku": "pack_6", "label": "☕ 小份补给", "price": 6, "credits": 60, "bonus": 0},
            {"sku": "pack_18", "label": "🌙 陪伴补给", "price": 18, "credits": 220, "bonus": 20},
            {"sku": "pack_48", "label": "⭐ 深度补给", "price": 48, "credits": 650, "bonus": 170},
            {
                "sku": "pack_128",
                "label": "🌌 长期陪伴",
                "price": 128,
                "credits": 2000,
                "bonus": 720,
            },
        ],
    }
