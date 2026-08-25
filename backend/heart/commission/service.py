"""Referral commission attribution, settlement, reversal, and store-credit spending."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.membership.service import activate_or_extend

logger = structlog.get_logger(__name__)

COMMISSION_RATE_PERCENT = 10
ATTRIBUTION_DAYS = 30
SETTLEMENT_DAYS = 15
RISK_SETTLEMENT_DAYS = 30

COMMISSION_PRODUCTS: dict[str, dict[str, Any]] = {
    "plan_plus": {"target": "membership", "price_fen": 2900, "tier": "plus", "days": 30},
    "plan_immersive": {
        "target": "membership",
        "price_fen": 6900,
        "tier": "immersive",
        "days": 30,
    },
    "pack_6": {"target": "coins", "price_fen": 600, "coins": 60},
    "pack_18": {"target": "coins", "price_fen": 1800, "coins": 220},
    "pack_48": {"target": "coins", "price_fen": 4800, "coins": 650},
    "pack_128": {"target": "coins", "price_fen": 12800, "coins": 2000},
}


class CommissionError(ValueError):
    pass


async def load_commission_rules(db: AsyncSession) -> dict[str, int]:
    defaults = {
        "rate_percent": COMMISSION_RATE_PERCENT,
        "attribution_days": ATTRIBUTION_DAYS,
        "settlement_days": SETTLEMENT_DAYS,
        "risk_settlement_days": RISK_SETTLEMENT_DAYS,
    }
    configured = (
        await db.execute(
            text("SELECT config FROM growth_rule_settings WHERE namespace = 'commission'")
        )
    ).scalar_one_or_none() or {}
    return {key: int(configured.get(key, value)) for key, value in defaults.items()}


async def create_commission_for_order(
    db: AsyncSession,
    invitee_id: uuid.UUID,
    order_id: str,
    paid_fen: int,
    paid_at: Any,
) -> bool:
    if paid_fen <= 0:
        return False
    rules = await load_commission_rules(db)
    invite = (
        (
            await db.execute(
                text(
                    """
                SELECT iu.inviter_id, iu.risk_level, u.created_at AS registered_at
                FROM user_invite_uses iu
                JOIN users u ON u.id = iu.invitee_id
                WHERE iu.invitee_id = :invitee_id AND iu.status = 'qualified'
                  AND iu.qualified_at IS NOT NULL
                """
                ),
                {"invitee_id": invitee_id},
            )
        )
        .mappings()
        .first()
    )
    if not invite:
        return False
    if paid_at > invite["registered_at"] + __import__("datetime").timedelta(
        days=rules["attribution_days"]
    ):
        return False

    commission_fen = paid_fen * rules["rate_percent"] // 100
    if commission_fen <= 0:
        return False
    freeze_days = (
        rules["risk_settlement_days"]
        if invite["risk_level"] in {"mid", "high"}
        else rules["settlement_days"]
    )
    inserted = (
        await db.execute(
            text(
                """
                INSERT INTO commission_entries
                  (inviter_id, invitee_id, order_id, paid_fen, commission_fen,
                   settle_at, idem_key)
                VALUES (:inviter_id, :invitee_id, :order_id, :paid_fen, :commission_fen,
                        NOW() + make_interval(days => :freeze_days), :idem_key)
                ON CONFLICT (idem_key) DO NOTHING
                RETURNING id
                """
            ),
            {
                "inviter_id": invite["inviter_id"],
                "invitee_id": invitee_id,
                "order_id": order_id,
                "paid_fen": paid_fen,
                "commission_fen": commission_fen,
                "freeze_days": freeze_days,
                "idem_key": f"commission:{order_id}",
            },
        )
    ).fetchone()
    return bool(inserted)


async def create_commission_from_fulfilled_order(db: AsyncSession, order_id: str) -> bool:
    order = (
        (
            await db.execute(
                text(
                    """
                SELECT resolved_user_id,
                       FLOOR(total_amount * 100)::INT AS paid_fen,
                       received_at
                FROM afdian_orders
                WHERE out_trade_no = :order_id AND fulfilled_at IS NOT NULL
                """
                ),
                {"order_id": order_id},
            )
        )
        .mappings()
        .first()
    )
    if not order or not order["resolved_user_id"] or not order["paid_fen"]:
        return False
    return await create_commission_for_order(
        db,
        uuid.UUID(str(order["resolved_user_id"])),
        order_id,
        int(order["paid_fen"]),
        order["received_at"],
    )


async def backfill_commissions_for_invitee(db: AsyncSession, invitee_id: uuid.UUID) -> int:
    orders = (
        (
            await db.execute(
                text(
                    """
                SELECT out_trade_no, FLOOR(total_amount * 100)::INT AS paid_fen, received_at
                FROM afdian_orders
                WHERE resolved_user_id = :uid AND fulfilled_at IS NOT NULL
                ORDER BY received_at
                """
                ),
                {"uid": invitee_id},
            )
        )
        .mappings()
        .all()
    )
    created = 0
    for order in orders:
        if order["paid_fen"] and await create_commission_for_order(
            db,
            invitee_id,
            str(order["out_trade_no"]),
            int(order["paid_fen"]),
            order["received_at"],
        ):
            created += 1
    return created


async def apply_ledger_delta(
    db: AsyncSession,
    user_id: uuid.UUID,
    delta_fen: int,
    reason: str,
    ref_id: str,
    idem_key: str,
    *,
    allow_negative: bool,
) -> tuple[int, bool]:
    await db.execute(text("SELECT id FROM users WHERE id = :uid FOR UPDATE"), {"uid": user_id})
    existing = (
        await db.execute(
            text("SELECT balance_fen FROM commission_ledger WHERE idem_key = :idem_key"),
            {"idem_key": idem_key},
        )
    ).scalar_one_or_none()
    if existing is not None:
        return int(existing), False

    condition = "" if allow_negative else "AND commission_balance_fen + :delta >= 0"
    balance = (
        await db.execute(
            text(
                f"""
                UPDATE users
                SET commission_balance_fen = commission_balance_fen + :delta
                WHERE id = :uid {condition}
                RETURNING commission_balance_fen
                """  # noqa: S608 - condition is selected from fixed internal constants
            ),
            {"uid": user_id, "delta": delta_fen},
        )
    ).scalar_one_or_none()
    if balance is None:
        raise CommissionError("insufficient_commission_balance")
    await db.execute(
        text(
            """
            INSERT INTO commission_ledger
              (user_id, delta_fen, balance_fen, reason, ref_id, idem_key)
            VALUES (:uid, :delta, :balance, :reason, :ref_id, :idem_key)
            """
        ),
        {
            "uid": user_id,
            "delta": delta_fen,
            "balance": balance,
            "reason": reason,
            "ref_id": ref_id,
            "idem_key": idem_key,
        },
    )
    return int(balance), True


async def settle_due_commissions(db: AsyncSession, limit: int = 100) -> int:
    entries = (
        (
            await db.execute(
                text(
                    """
                SELECT id, inviter_id, commission_fen FROM commission_entries
                WHERE status = 'pending' AND settle_at <= NOW()
                ORDER BY settle_at, id
                FOR UPDATE SKIP LOCKED LIMIT :limit
                """
                ),
                {"limit": limit},
            )
        )
        .mappings()
        .all()
    )
    for entry in entries:
        await apply_ledger_delta(
            db,
            uuid.UUID(str(entry["inviter_id"])),
            int(entry["commission_fen"]),
            "settle",
            str(entry["id"]),
            f"settle:{entry['id']}",
            allow_negative=True,
        )
        await db.execute(
            text(
                """
                UPDATE commission_entries SET status = 'settled', settled_at = NOW()
                WHERE id = :id AND status = 'pending'
                """
            ),
            {"id": entry["id"]},
        )
    return len(entries)


async def reverse_commission_by_order(db: AsyncSession, order_id: str) -> bool:
    entry = (
        (
            await db.execute(
                text("SELECT * FROM commission_entries WHERE order_id = :order_id FOR UPDATE"),
                {"order_id": order_id},
            )
        )
        .mappings()
        .first()
    )
    if not entry or entry["status"] == "cancelled":
        return False
    if entry["status"] == "settled":
        await apply_ledger_delta(
            db,
            uuid.UUID(str(entry["inviter_id"])),
            -int(entry["commission_fen"]),
            "reverse",
            str(entry["id"]),
            f"reverse:{entry['id']}",
            allow_negative=True,
        )
    await db.execute(
        text(
            """
            UPDATE commission_entries SET status = 'cancelled', cancelled_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": entry["id"]},
    )
    return True


async def spend_commission(
    db: AsyncSession,
    user_id: uuid.UUID,
    target: str,
    sku: str,
    client_token: str,
) -> dict[str, Any]:
    product = COMMISSION_PRODUCTS.get(sku)
    if not product or product["target"] != target:
        raise CommissionError("invalid_commission_product")
    amount = int(product["price_fen"])
    reason = "spend_membership" if target == "membership" else "spend_coins"
    balance, applied = await apply_ledger_delta(
        db,
        user_id,
        -amount,
        reason,
        sku,
        f"spend:{client_token}",
        allow_negative=False,
    )
    if not applied:
        return {"ok": True, "applied": False, "balance_fen": balance, "sku": sku}

    if target == "membership":
        await activate_or_extend(
            db,
            user_id,
            str(product["tier"]),
            int(product["days"]),
            granted_by=f"commission:{client_token}",
            auto_commit=False,
        )
    else:
        await grant(
            db,
            user_id,
            int(product["coins"]) * 100,
            idempotency_key=f"commission_spend:{client_token}",
            type_str="grant",
            ref_type="commission_exchange",
            ref_id=sku,
            auto_commit=False,
        )
    return {
        "ok": True,
        "applied": True,
        "balance_fen": balance,
        "sku": sku,
        "target": target,
    }
