"""Unit tests for B6: afdian webhook auto-fulfillment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# resolve_user_by_binding_code
# ---------------------------------------------------------------------------


class TestResolveUserByBindingCode:
    @pytest.mark.asyncio
    async def test_returns_none_for_empty_remark(self):
        from heart.afdian.fulfillment import resolve_user_by_binding_code

        db = AsyncMock()
        result = await resolve_user_by_binding_code(db, "")
        assert result is None
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_matching_code(self):
        from heart.afdian.fulfillment import resolve_user_by_binding_code

        db = AsyncMock()
        fetch_result = MagicMock()
        fetch_result.fetchone.return_value = None
        db.execute = AsyncMock(return_value=fetch_result)

        result = await resolve_user_by_binding_code(db, "order_ref: ABCD1234")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_user_id_when_code_matches(self):
        from heart.afdian.fulfillment import resolve_user_by_binding_code

        user_id = uuid.uuid4()
        db = AsyncMock()
        fetch_result = MagicMock()
        fetch_result.fetchone.return_value = (str(user_id),)
        db.execute = AsyncMock(return_value=fetch_result)

        result = await resolve_user_by_binding_code(db, "备注 XYZA9876")
        assert result == user_id


# ---------------------------------------------------------------------------
# fulfill_order
# ---------------------------------------------------------------------------


class TestFulfillOrder:
    @pytest.mark.asyncio
    async def test_skips_already_fulfilled_order(self):
        from heart.afdian.fulfillment import fulfill_order

        db = AsyncMock()
        # SELECT returns row with fulfilled_at set
        fulfilled_row = MagicMock()
        fulfilled_row.fetchone.return_value = (
            datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        db.execute = AsyncMock(return_value=fulfilled_row)

        ok, msg = await fulfill_order(db, "order-001", "plan-a", "binding: XYZ")
        assert ok is True
        assert msg == "already_fulfilled"

    @pytest.mark.asyncio
    async def test_returns_false_when_no_binding_code(self):
        from heart.afdian.fulfillment import fulfill_order

        db = AsyncMock()
        # Not yet fulfilled
        not_fulfilled = MagicMock()
        not_fulfilled.fetchone.return_value = (None,)
        db.execute = AsyncMock(return_value=not_fulfilled)
        db.commit = AsyncMock()

        with patch(
            "heart.afdian.fulfillment.resolve_user_by_binding_code",
            new=AsyncMock(return_value=None),
        ):
            ok, msg = await fulfill_order(db, "order-002", "plan-a", "no code here")

        assert ok is False
        assert msg == "no_binding_code_match"

    @pytest.mark.asyncio
    async def test_grants_coins_for_coins_sku(self):
        from heart.afdian.fulfillment import fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        not_fulfilled = MagicMock()
        not_fulfilled.fetchone.return_value = (None,)
        db.execute = AsyncMock(return_value=not_fulfilled)
        db.commit = AsyncMock()

        sku_map = '{"plan-coins": {"type": "coins", "coins": 220}}'

        with (
            patch("heart.afdian.fulfillment.resolve_user_by_binding_code", new=AsyncMock(return_value=user_id)),
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.grant_credits", new=AsyncMock(return_value=22000)) as mock_grant,
        ):
            ok, msg = await fulfill_order(db, "order-003", "plan-coins", "code: ABCD1234")

        assert ok is True
        assert msg == "ok"
        mock_grant.assert_called_once()
        call_args = mock_grant.call_args
        assert call_args[0][2] == 22000  # 220 coins × 100 fen

    @pytest.mark.asyncio
    async def test_grants_membership_for_membership_sku(self):
        from heart.afdian.fulfillment import fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        not_fulfilled = MagicMock()
        not_fulfilled.fetchone.return_value = (None,)
        db.execute = AsyncMock(return_value=not_fulfilled)
        db.commit = AsyncMock()

        sku_map = '{"plan-plus30": {"type": "membership", "tier": "plus", "days": 30}}'

        with (
            patch("heart.afdian.fulfillment.resolve_user_by_binding_code", new=AsyncMock(return_value=user_id)),
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.activate_or_extend", new=AsyncMock()) as mock_activate,
        ):
            ok, msg = await fulfill_order(db, "order-004", "plan-plus30", "code: ABCD1234")

        assert ok is True
        assert msg == "ok"
        mock_activate.assert_called_once()
        _, call_kwargs = mock_activate.call_args
        # positional: (db, user_id, tier, days, granted_by=...)
        assert mock_activate.call_args[0][2] == "plus"
        assert mock_activate.call_args[0][3] == 30

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_plan(self):
        from heart.afdian.fulfillment import fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        not_fulfilled = MagicMock()
        not_fulfilled.fetchone.return_value = (None,)
        db.execute = AsyncMock(return_value=not_fulfilled)
        db.commit = AsyncMock()

        with (
            patch("heart.afdian.fulfillment.resolve_user_by_binding_code", new=AsyncMock(return_value=user_id)),
            patch("heart.core.config.settings.afdian_sku_map", "{}"),
        ):
            ok, msg = await fulfill_order(db, "order-005", "plan-unknown", "code: ABCD")

        assert ok is False
        assert msg == "unknown_plan_id"
