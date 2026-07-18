"""Afdian order fulfillment: resolve user from binding code + grant membership/coins."""

from __future__ import annotations

import json
import uuid
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant as grant_credits
from heart.core.config import settings
from heart.membership.service import activate_or_extend

logger = structlog.get_logger(__name__)


def _parse_sku_map() -> dict:
    try:
        return json.loads(settings.afdian_sku_map)
    except Exception:
        logger.exception("afdian_sku_map_parse_failed")
        return {}


async def resolve_user_by_binding_code(db: AsyncSession, remark: str) -> Optional[uuid.UUID]:
    """Extract binding code from remark and look up the user.

    Binding code may appear anywhere in the remark (case-insensitive prefix match
    on the code field). Returns user_id if found + not expired, else None.
    """
    if not remark:
        return None

    # Look for any active, unexpired code that appears as a word in the remark
    result = await db.execute(
        text(
            """
            SELECT user_id FROM user_binding_codes
            WHERE :remark ILIKE '%' || code || '%'
              AND (expires_at IS NULL OR expires_at > NOW())
              AND used_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"remark": remark},
    )
    row = result.fetchone()
    if row is None:
        return None
    return uuid.UUID(str(row[0]))


async def fulfill_order(
    db: AsyncSession,
    out_trade_no: str,
    plan_id: str,
    remark: str,
) -> tuple[bool, str]:
    """Fulfill one afdian order idempotently.

    Returns (success, message).
    Already-fulfilled orders are silently skipped (idempotent).
    """
    # Check already fulfilled
    row = await db.execute(
        text("SELECT fulfilled_at FROM afdian_orders WHERE out_trade_no = :otn"),
        {"otn": out_trade_no},
    )
    existing = row.fetchone()
    if existing and existing[0] is not None:
        return True, "already_fulfilled"

    user_id = await resolve_user_by_binding_code(db, remark)
    if user_id is None:
        await db.execute(
            text(
                """
                UPDATE afdian_orders
                SET fulfillment_error = 'no_binding_code_match'
                WHERE out_trade_no = :otn
                """
            ),
            {"otn": out_trade_no},
        )
        await db.commit()
        logger.warning("afdian_fulfill_no_user", out_trade_no=out_trade_no, remark=remark)
        return False, "no_binding_code_match"

    sku_map = _parse_sku_map()
    fulfillment = sku_map.get(plan_id)
    if fulfillment is None:
        await db.execute(
            text(
                """
                UPDATE afdian_orders
                SET fulfillment_error = 'unknown_plan_id',
                    resolved_user_id = :uid
                WHERE out_trade_no = :otn
                """
            ),
            {"otn": out_trade_no, "uid": user_id},
        )
        await db.commit()
        logger.warning("afdian_fulfill_unknown_plan", out_trade_no=out_trade_no, plan_id=plan_id)
        return False, "unknown_plan_id"

    ftype = fulfillment.get("type")
    try:
        if ftype == "membership":
            tier = fulfillment["tier"]
            days = int(fulfillment["days"])
            await activate_or_extend(db, user_id, tier, days, granted_by=f"afdian:{out_trade_no}")
        elif ftype == "coins":
            coins = int(fulfillment["coins"])
            fen = coins * 100
            await grant_credits(
                db, user_id, fen, f"afdian:{out_trade_no}", ref_type="afdian_purchase"
            )
        else:
            raise ValueError(f"unknown fulfillment type: {ftype!r}")

        await db.execute(
            text(
                """
                UPDATE afdian_orders
                SET fulfilled_at = NOW(),
                    resolved_user_id = :uid
                WHERE out_trade_no = :otn
                """
            ),
            {"otn": out_trade_no, "uid": user_id},
        )
        # Mark binding code as used
        await db.execute(
            text(
                """
                UPDATE user_binding_codes
                SET used_at = NOW()
                WHERE :remark ILIKE '%' || code || '%'
                  AND used_at IS NULL
                """
            ),
            {"remark": remark},
        )
        await db.commit()
        logger.info(
            "afdian_fulfilled",
            out_trade_no=out_trade_no,
            user_id=str(user_id),
            ftype=ftype,
        )
        return True, "ok"
    except Exception:
        await db.rollback()
        logger.exception("afdian_fulfill_error", out_trade_no=out_trade_no)
        raise
