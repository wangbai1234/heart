"""Unit tests for P6: admin manual afdian order fulfillment."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# admin_fulfill_order (fulfillment.py)
# ---------------------------------------------------------------------------


class TestAdminFulfillOrder:
    @pytest.mark.asyncio
    async def test_raises_if_order_not_found(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = None
        db.execute = AsyncMock(return_value=fetch)

        with pytest.raises(ValueError, match="order not found"):
            await admin_fulfill_order(db, "nonexistent-order", uuid.uuid4())

    @pytest.mark.asyncio
    async def test_raises_if_already_fulfilled(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = (datetime(2026, 1, 1, tzinfo=timezone.utc), "plan-a", "")
        db.execute = AsyncMock(return_value=fetch)

        with pytest.raises(ValueError, match="already fulfilled"):
            await admin_fulfill_order(db, "order-001", uuid.uuid4())

    @pytest.mark.asyncio
    async def test_raises_for_unknown_plan(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = (None, "plan-unknown", "no code")
        db.execute = AsyncMock(return_value=fetch)

        with patch("heart.core.config.settings.afdian_sku_map", "{}"):
            with pytest.raises(ValueError, match="unknown plan_id"):
                await admin_fulfill_order(db, "order-002", uuid.uuid4())

    @pytest.mark.asyncio
    async def test_grants_coins_for_coins_plan(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = (None, "pack-220", "no code in remark")
        db.execute = AsyncMock(return_value=fetch)
        db.commit = AsyncMock()

        sku_map = '{"pack-220": {"type": "coins", "coins": 220}}'

        with (
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.grant_credits", new=AsyncMock(return_value=22000)) as mock_grant,
        ):
            detail = await admin_fulfill_order(db, "order-coins", user_id)

        assert detail == {"type": "coins", "coins": 220}
        mock_grant.assert_called_once()
        call_args = mock_grant.call_args[0]
        assert call_args[1] == user_id
        assert call_args[2] == 22000  # 220 × 100 fen

    @pytest.mark.asyncio
    async def test_activates_membership_for_membership_plan(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = (None, "plan-plus30", "no code in remark")
        db.execute = AsyncMock(return_value=fetch)
        db.commit = AsyncMock()

        sku_map = '{"plan-plus30": {"type": "membership", "tier": "plus", "days": 30}}'

        with (
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.activate_or_extend", new=AsyncMock()) as mock_activate,
        ):
            detail = await admin_fulfill_order(db, "order-plus", user_id)

        assert detail == {"type": "membership", "tier": "plus", "days": 30}
        mock_activate.assert_called_once()
        call_args = mock_activate.call_args[0]
        assert call_args[1] == user_id
        assert call_args[2] == "plus"
        assert call_args[3] == 30

    @pytest.mark.asyncio
    async def test_does_not_require_binding_code_in_remark(self):
        """Core guarantee: unmatched orders (empty remark) can still be fulfilled."""
        from heart.afdian.fulfillment import admin_fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        fetch = MagicMock()
        # remark is empty — this would fail the regular fulfill_order
        fetch.fetchone.return_value = (None, "plan-plus30", "")
        db.execute = AsyncMock(return_value=fetch)
        db.commit = AsyncMock()

        sku_map = '{"plan-plus30": {"type": "membership", "tier": "plus", "days": 30}}'

        with (
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.activate_or_extend", new=AsyncMock()),
        ):
            detail = await admin_fulfill_order(db, "order-empty-remark", user_id)

        assert detail["type"] == "membership"

    @pytest.mark.asyncio
    async def test_rollback_on_billing_error(self):
        from heart.afdian.fulfillment import admin_fulfill_order

        user_id = uuid.uuid4()
        db = AsyncMock()
        fetch = MagicMock()
        fetch.fetchone.return_value = (None, "pack-60", "")
        db.execute = AsyncMock(return_value=fetch)
        db.rollback = AsyncMock()

        sku_map = '{"pack-60": {"type": "coins", "coins": 60}}'

        with (
            patch("heart.core.config.settings.afdian_sku_map", sku_map),
            patch("heart.afdian.fulfillment.grant_credits", new=AsyncMock(side_effect=RuntimeError("ledger down"))),
        ):
            with pytest.raises(RuntimeError, match="ledger down"):
                await admin_fulfill_order(db, "order-err", user_id)

        db.rollback.assert_called_once()


# ---------------------------------------------------------------------------
# _apply_sku helper
# ---------------------------------------------------------------------------


class TestApplySku:
    @pytest.mark.asyncio
    async def test_raises_for_unknown_type(self):
        from heart.afdian.fulfillment import _apply_sku

        db = AsyncMock()
        with pytest.raises(ValueError, match="unknown fulfillment type"):
            await _apply_sku(db, uuid.uuid4(), "nft", {}, "order-x")

    @pytest.mark.asyncio
    async def test_coins_returns_detail(self):
        from heart.afdian.fulfillment import _apply_sku

        db = AsyncMock()
        with patch("heart.afdian.fulfillment.grant_credits", new=AsyncMock(return_value=6000)):
            detail = await _apply_sku(db, uuid.uuid4(), "coins", {"coins": 60}, "order-c")

        assert detail == {"type": "coins", "coins": 60}

    @pytest.mark.asyncio
    async def test_membership_returns_detail(self):
        from heart.afdian.fulfillment import _apply_sku

        db = AsyncMock()
        with patch("heart.afdian.fulfillment.activate_or_extend", new=AsyncMock()):
            detail = await _apply_sku(
                db, uuid.uuid4(), "membership", {"tier": "immersive", "days": 30}, "order-m"
            )

        assert detail == {"type": "membership", "tier": "immersive", "days": 30}
