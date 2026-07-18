"""Webhook routes — /api/webhooks/*"""

from __future__ import annotations

import hashlib
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


class AfdianWebhookPayload(BaseModel):
    """Afdian webhook payload (simplified)."""

    out_trade_no: str = ""
    plan_id: str = ""
    sku_detail: dict | list | None = None
    total_amount: float | str = 0
    remark: str = ""
    # Afdian sends many more fields; we capture in raw_payload


def _verify_afdian_sign(params: dict, token: str) -> bool:
    """Verify Afdian webhook signature.

    Afdian sign = md5(user_id + params_json_sorted + token)
    """
    sign = params.pop("sign", None)
    if not sign:
        return False

    # Sort params, concatenate
    sorted_keys = sorted(params.keys())
    params_str = "".join(f"{k}{params[k]}" for k in sorted_keys)
    raw = f"{params.get('user_id', '')}{params_str}{token}"
    expected = hashlib.md5(raw.encode()).hexdigest()
    return sign == expected


@router.post("/afdian")
async def afdian_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Afdian webhook for order reconciliation.

    Does NOT directly add credits — only records order for audit.
    Credits are added via redemption codes.
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    # Verify sign
    params = dict(body)
    if not _verify_afdian_sign(params, settings.afdian_webhook_token):
        logger.warning("afdian_webhook_invalid_sign")
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = body.get("data", {})
    out_trade_no = data.get("out_trade_no", "")

    if not out_trade_no:
        raise HTTPException(status_code=400, detail="Missing out_trade_no")

    # Idempotent insert
    try:
        await db.execute(
            text("""
                INSERT INTO afdian_orders (out_trade_no, plan_id, sku_detail, total_amount, remark, raw_payload)
                VALUES (:otn, :plan, :sku, :amount, :remark, :raw)
                ON CONFLICT (out_trade_no) DO NOTHING
            """),
            {
                "otn": out_trade_no,
                "plan": data.get("plan_id", ""),
                "sku": json.dumps(data.get("sku_detail")),
                "amount": float(data.get("total_amount", 0)),
                "remark": data.get("remark", ""),
                "raw": json.dumps(body),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("afdian_webhook_db_error", error=str(e))
        # Still return 200 to avoid Afdian retry

    logger.info("afdian_webhook_received", out_trade_no=out_trade_no)

    # Auto-fulfill: match remark binding code → grant membership/coins
    try:
        from heart.afdian.fulfillment import fulfill_order

        plan_id = data.get("plan_id", "")
        remark = data.get("remark", "")
        await fulfill_order(db, out_trade_no, plan_id, remark)
    except Exception:
        logger.exception("afdian_auto_fulfill_error", out_trade_no=out_trade_no)
        # Return 200 anyway — Afdian will not retry on 200

    return {"ec": 200, "em": "success"}
