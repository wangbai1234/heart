"""Focused V1 tests for lottery selection and commission accounting."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _mapping_first(value):
    mappings = MagicMock()
    mappings.first.return_value = value
    result = MagicMock()
    result.mappings.return_value = mappings
    return result


def _fetchone(value):
    result = MagicMock()
    result.fetchone.return_value = value
    return result


def _scalar(value):
    result = MagicMock()
    result.scalar_one.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def test_choose_weighted_honours_interval_boundaries():
    from heart.lottery.service import choose_weighted

    prizes = [{"code": "a", "weight": 5}, {"code": "b", "weight": 3}]
    with patch("heart.lottery.service.secrets.randbelow", return_value=4):
        assert choose_weighted(prizes)["code"] == "a"
    with patch("heart.lottery.service.secrets.randbelow", return_value=5):
        assert choose_weighted(prizes)["code"] == "b"


@pytest.mark.asyncio
async def test_admin_can_add_prize_to_draft_pool():
    from heart.api.routes_admin import LotteryPrizeCreateRequest, admin_create_lottery_prize

    prize = {
        "code": "coin_20",
        "kind": "coins",
        "payload": {"coins": 20},
        "weight": 5000,
        "face_value_fen": 200,
        "total_stock": 5000,
        "daily_stock": None,
        "per_user_limit_json": None,
        "fallback_prize_code": None,
        "enabled": True,
    }
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_scalar("draft"), _mapping_first(prize), MagicMock()])

    result = await admin_create_lottery_prize(
        pool_id=7,
        body=LotteryPrizeCreateRequest(**prize),
        _=None,
        db=db,
    )

    assert result == prize
    insert_params = db.execute.await_args_list[1].args[1]
    assert insert_params["payload"] == '{"coins": 20}'
    assert insert_params["per_user_limit"] is None
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_admin_cannot_add_prize_to_active_pool():
    from heart.api.routes_admin import LotteryPrizeCreateRequest, admin_create_lottery_prize

    db = AsyncMock()
    db.execute = AsyncMock(return_value=_scalar("active"))
    body = LotteryPrizeCreateRequest(
        code="coin_20",
        kind="coins",
        payload={"coins": 20},
        weight=5000,
        face_value_fen=200,
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_create_lottery_prize(pool_id=7, body=body, _=None, db=db)

    assert exc_info.value.status_code == 400
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_admin_rejects_invalid_membership_prize_payload():
    from heart.api.routes_admin import LotteryPrizeCreateRequest, admin_create_lottery_prize

    db = AsyncMock()
    body = LotteryPrizeCreateRequest(
        code="vip_bad",
        kind="membership",
        payload={"tier": "plus", "days": 0},
        weight=10,
        face_value_fen=2900,
    )

    with pytest.raises(HTTPException) as exc_info:
        await admin_create_lottery_prize(pool_id=7, body=body, _=None, db=db)

    assert exc_info.value.status_code == 422
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_commission_is_ten_percent_floored():
    from heart.commission.service import create_commission_for_order

    now = datetime.now(tz=timezone.utc)
    inviter_id = uuid.uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar({}),
            _mapping_first({"inviter_id": inviter_id, "risk_level": "low", "registered_at": now}),
            _fetchone((77,)),
        ]
    )
    created = await create_commission_for_order(
        db, uuid.uuid4(), "order-1", 2901, now + timedelta(days=1)
    )
    assert created is True
    params = db.execute.await_args_list[2].args[1]
    assert params["commission_fen"] == 290
    assert params["freeze_days"] == 15


@pytest.mark.asyncio
async def test_commission_rejects_order_outside_attribution_window():
    from heart.commission.service import create_commission_for_order

    now = datetime.now(tz=timezone.utc)
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _scalar({}),
            _mapping_first({"inviter_id": uuid.uuid4(), "risk_level": "low", "registered_at": now}),
        ]
    )
    created = await create_commission_for_order(
        db, uuid.uuid4(), "late-order", 6900, now + timedelta(days=30, seconds=1)
    )
    assert created is False
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_commission_ledger_duplicate_is_idempotent():
    from heart.commission.service import apply_ledger_delta

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), _scalar(350)])
    balance, applied = await apply_ledger_delta(
        db,
        uuid.uuid4(),
        100,
        "settle",
        "1",
        "settle:1",
        allow_negative=True,
    )
    assert (balance, applied) == (350, False)
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_commission_spend_cannot_make_balance_negative():
    from heart.commission.service import CommissionError, apply_ledger_delta

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[MagicMock(), _scalar(None), _scalar(None)])
    with pytest.raises(CommissionError, match="insufficient_commission_balance"):
        await apply_ledger_delta(
            db,
            uuid.uuid4(),
            -2900,
            "spend_membership",
            "plan_plus",
            "spend:token",
            allow_negative=False,
        )
