"""Versioned, server-authoritative invite lottery engine."""

from __future__ import annotations

import json
import secrets
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.membership.coupons import grant_coupon


class LotteryError(ValueError):
    pass


def choose_weighted(prizes: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(int(prize["weight"]) for prize in prizes)
    if total <= 0:
        raise LotteryError("lottery_pool_empty")
    point = secrets.randbelow(total)
    cursor = 0
    for prize in prizes:
        cursor += int(prize["weight"])
        if point < cursor:
            return prize
    raise LotteryError("lottery_pool_invalid")


async def _limit_reached(
    db: AsyncSession, user_id: uuid.UUID, pool_id: int, prize: dict[str, Any]
) -> bool:
    limit = prize.get("per_user_limit_json")
    if not limit:
        return False
    group = str(limit.get("group") or prize["code"])
    count = int(
        (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*)
                    FROM lottery_draws d
                    JOIN lottery_prizes p ON p.pool_id = d.pool_id AND p.code = d.prize_code
                    WHERE d.user_id = :uid AND d.pool_id = :pool_id
                      AND COALESCE(p.per_user_limit_json->>'group', p.code) = :group
                      AND d.created_at >= NOW() - make_interval(days => :days)
                    """
                ),
                {
                    "uid": user_id,
                    "pool_id": pool_id,
                    "group": group,
                    "days": int(limit["days"]),
                },
            )
        ).scalar_one()
    )
    return count >= int(limit["max"])


async def _stock_exhausted(db: AsyncSession, pool_id: int, prize: dict[str, Any]) -> bool:
    if prize.get("total_stock") is not None:
        total = int(
            (
                await db.execute(
                    text(
                        "SELECT COUNT(*) FROM lottery_draws "
                        "WHERE pool_id = :pool_id AND prize_code = :code"
                    ),
                    {"pool_id": pool_id, "code": prize["code"]},
                )
            ).scalar_one()
        )
        if total >= int(prize["total_stock"]):
            return True
    if prize.get("daily_stock") is not None:
        daily = int(
            (
                await db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM lottery_draws
                        WHERE pool_id = :pool_id AND prize_code = :code
                          AND DATE(created_at AT TIME ZONE 'Asia/Shanghai') =
                              DATE(NOW() AT TIME ZONE 'Asia/Shanghai')
                        """
                    ),
                    {"pool_id": pool_id, "code": prize["code"]},
                )
            ).scalar_one()
        )
        if daily >= int(prize["daily_stock"]):
            return True
    return False


async def draw(db: AsyncSession, user_id: uuid.UUID, chance_id: int) -> dict[str, Any]:
    chance = (
        (
            await db.execute(
                text(
                    """
                SELECT id, user_id, pool_id, expires_at, consumed_at, draw_id
                FROM invite_draw_chances WHERE id = :chance_id FOR UPDATE
                """
                ),
                {"chance_id": chance_id},
            )
        )
        .mappings()
        .first()
    )
    if not chance or uuid.UUID(str(chance["user_id"])) != user_id:
        raise LotteryError("chance_not_found")
    if chance["consumed_at"] is not None:
        existing = (
            (
                await db.execute(
                    text("SELECT * FROM lottery_draws WHERE chance_id = :chance_id"),
                    {"chance_id": chance_id},
                )
            )
            .mappings()
            .one()
        )
        return dict(existing)
    expired = (
        await db.execute(text("SELECT :expires_at <= NOW()"), {"expires_at": chance["expires_at"]})
    ).scalar_one()
    if expired:
        raise LotteryError("chance_expired")
    if chance["pool_id"] is None:
        raise LotteryError("chance_has_no_pool")

    pool_id = int(chance["pool_id"])
    pool = (
        (
            await db.execute(
                text(
                    "SELECT id, status, total_chances FROM lottery_pool_versions WHERE id = :id FOR UPDATE"
                ),
                {"id": pool_id},
            )
        )
        .mappings()
        .one()
    )
    if pool["status"] not in {"active", "closed"}:
        raise LotteryError("lottery_pool_unavailable")

    prizes = [
        dict(row)
        for row in (
            await db.execute(
                text(
                    """
                    SELECT code, kind, payload, weight, face_value_fen, total_stock,
                           daily_stock, per_user_limit_json, fallback_prize_code
                    FROM lottery_prizes
                    WHERE pool_id = :pool_id AND enabled = TRUE
                    ORDER BY id
                    """
                ),
                {"pool_id": pool_id},
            )
        )
        .mappings()
        .all()
    ]
    selected = choose_weighted(prizes)
    if await _stock_exhausted(db, pool_id, selected) or await _limit_reached(
        db, user_id, pool_id, selected
    ):
        fallback_code = selected.get("fallback_prize_code") or "coin_20"
        selected = next((prize for prize in prizes if prize["code"] == fallback_code), None)
        if selected is None:
            raise LotteryError("fallback_prize_missing")

    draw_id = int(
        (
            await db.execute(
                text(
                    """
                    INSERT INTO lottery_draws
                      (user_id, pool_id, chance_id, prize_code, prize_kind, payload,
                       face_value_fen, idem_key)
                    VALUES (:uid, :pool_id, :chance_id, :code, :kind, CAST(:payload AS jsonb),
                            :face_value_fen, :idem_key)
                    RETURNING id
                    """
                ),
                {
                    "uid": user_id,
                    "pool_id": pool_id,
                    "chance_id": chance_id,
                    "code": selected["code"],
                    "kind": selected["kind"],
                    "payload": json.dumps(selected["payload"]),
                    "face_value_fen": selected["face_value_fen"],
                    "idem_key": f"draw:{chance_id}",
                },
            )
        ).scalar_one()
    )
    await db.execute(
        text(
            """
            UPDATE invite_draw_chances
            SET consumed_at = NOW(), draw_id = :draw_id
            WHERE id = :chance_id AND consumed_at IS NULL
            """
        ),
        {"draw_id": draw_id, "chance_id": chance_id},
    )

    balance = None
    payload = selected["payload"]
    if selected["kind"] == "coins":
        balance = await grant(
            db,
            user_id,
            int(payload["coins"]) * 100,
            idempotency_key=f"draw_reward:{draw_id}",
            type_str="grant",
            ref_type="lottery",
            ref_id=str(draw_id),
            auto_commit=False,
        )
    else:
        await grant_coupon(
            db,
            user_id,
            str(payload["tier"]),
            int(payload["days"]),
            source=f"lottery:{draw_id}",
            idem_key=f"coupon:lottery:{draw_id}",
        )
    return {
        "id": draw_id,
        "chance_id": chance_id,
        "pool_id": pool_id,
        "prize_code": selected["code"],
        "prize_kind": selected["kind"],
        "payload": payload,
        "face_value_fen": int(selected["face_value_fen"]),
        "balance": balance / 100 if balance is not None else None,
    }
