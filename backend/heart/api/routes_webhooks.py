"""Webhook routes — /api/webhooks/*

Afdian (爱发电) webhook contract — see https://guide.afdian.com/creator/developer :
  - Afdian POSTs JSON: {"ec":200,"em":"ok","data":{"type":"order","order":{...}}}
    The order fields (out_trade_no / plan_id / sku_detail / remark /
    total_amount) live under ``data.order`` — NOT directly under ``data``.
  - The webhook body carries **no signature**. (The md5 ``sign`` scheme belongs
    to the query-order *API*, not the webhook.) Afdian's own guidance is to keep
    the webhook URL secret and make the handler idempotent. We therefore
    authenticate with a secret token carried in the URL query string
    (``?token=<AFDIAN_WEBHOOK_TOKEN>``) that only we and Afdian's config know.
  - The handler must respond ``{"ec":200}`` or Afdian treats it as failed and
    may re-push, so we always return 200 once the request is authenticated.
"""

from __future__ import annotations

import hmac
import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _authenticate(request: Request) -> bool:
    """Authenticate an Afdian webhook via the secret token in the URL.

    Afdian does not sign webhook bodies, so we rely on a shared secret embedded
    in the configured callback URL: ``.../api/webhooks/afdian?token=<secret>``.
    Uses a constant-time compare. When no token is configured we refuse (fail
    closed) rather than accept unauthenticated callbacks.
    """
    expected = (settings.afdian_webhook_token or "").strip()
    if not expected:
        logger.error("afdian_webhook_token_unset")
        return False
    provided = request.query_params.get("token", "")
    return hmac.compare_digest(provided, expected)


@router.post("/afdian")
async def afdian_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Handle Afdian order webhook: record for audit + auto-fulfill.

    Fulfillment (grant membership/coins) is driven by a binding code the user
    embeds in the Afdian order remark — see heart.afdian.fulfillment.
    """
    if not _authenticate(request):
        logger.warning("afdian_webhook_unauthorized")
        raise HTTPException(status_code=403, detail="Invalid token")

    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e

    data = body.get("data") if isinstance(body, dict) else None
    data = data if isinstance(data, dict) else {}

    # data.type is currently only "order"; ack anything else so Afdian stops.
    if data.get("type") not in (None, "", "order"):
        logger.info("afdian_webhook_ignored_type", type=data.get("type"))
        return {"ec": 200, "em": "ignored"}

    # Order fields live under data.order (NOT directly under data).
    order = data.get("order")
    order = order if isinstance(order, dict) else {}

    out_trade_no = str(order.get("out_trade_no") or "").strip()
    if not out_trade_no:
        logger.warning("afdian_webhook_missing_out_trade_no", body_preview=str(body)[:200])
        raise HTTPException(status_code=400, detail="Missing out_trade_no")

    plan_id = str(order.get("plan_id") or "")
    remark = str(order.get("remark") or "")

    # Idempotent insert for audit (duplicate pushes are expected — Afdian may
    # re-push; ON CONFLICT keeps the first row).
    try:
        await db.execute(
            text("""
                INSERT INTO afdian_orders
                    (out_trade_no, plan_id, sku_detail, total_amount, remark, raw_payload)
                VALUES (:otn, :plan, :sku, :amount, :remark, :raw)
                ON CONFLICT (out_trade_no) DO NOTHING
            """),
            {
                "otn": out_trade_no,
                "plan": plan_id,
                "sku": json.dumps(order.get("sku_detail")),
                "amount": _to_float(order.get("total_amount")),
                "remark": remark,
                "raw": json.dumps(body),
            },
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("afdian_webhook_db_error", error=str(e))
        # Still ack — Afdian only retries on non-200; a DB blip shouldn't cause
        # an unbounded retry storm. The row can be reconciled from raw_payload.

    logger.info("afdian_webhook_received", out_trade_no=out_trade_no, plan_id=plan_id)

    # Auto-fulfill: match remark binding code → grant membership/coins.
    try:
        from heart.afdian.fulfillment import fulfill_order

        await fulfill_order(db, out_trade_no, plan_id, remark)
    except Exception:
        logger.exception("afdian_auto_fulfill_error", out_trade_no=out_trade_no)
        # Ack anyway — admin can reconcile unmatched/failed orders manually.

    return {"ec": 200, "em": "success"}


def _to_float(value: object) -> float:
    """Best-effort parse of Afdian's amount (sent as a string like '5.00')."""
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
