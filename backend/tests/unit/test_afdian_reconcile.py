"""Unit tests for the Afdian open-API client + order reconciliation."""

from __future__ import annotations

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# api_client._sign — guard the exact signature formula against drift
# ---------------------------------------------------------------------------


def test_sign_matches_afdian_formula():
    from heart.afdian.api_client import _sign

    token, params, ts, user_id = "tok", '{"page":1}', 1785042131, "uid-1"
    expected = hashlib.md5(
        f"{token}params{params}ts{ts}user_id{user_id}".encode()
    ).hexdigest()
    assert _sign(token, params, ts, user_id) == expected


# ---------------------------------------------------------------------------
# api_client._require_creds
# ---------------------------------------------------------------------------


def test_require_creds_raises_when_unset():
    from heart.afdian.api_client import AfdianAPIError, _require_creds

    with (
        patch("heart.core.config.settings.afdian_user_id", ""),
        patch("heart.core.config.settings.afdian_api_token", ""),
    ):
        with pytest.raises(AfdianAPIError):
            _require_creds()


# ---------------------------------------------------------------------------
# api_client.query_order / list_orders (via mocked _post)
# ---------------------------------------------------------------------------


class TestQueryOrder:
    @pytest.mark.asyncio
    async def test_returns_matching_order(self):
        from heart.afdian import api_client

        order = {"out_trade_no": "otn-1", "plan_id": "p", "sku_detail": []}
        with patch.object(
            api_client, "_post", new=AsyncMock(return_value={"list": [order]})
        ):
            result = await api_client.query_order("otn-1")
        assert result == order

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_out_trade_no(self):
        from heart.afdian import api_client

        with patch.object(api_client, "_post", new=AsyncMock()) as mock_post:
            result = await api_client.query_order("")
        assert result is None
        mock_post.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_in_list(self):
        from heart.afdian import api_client

        with patch.object(api_client, "_post", new=AsyncMock(return_value={"list": []})):
            result = await api_client.query_order("otn-missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_orders_returns_orders_and_total_page(self):
        from heart.afdian import api_client

        with patch.object(
            api_client,
            "_post",
            new=AsyncMock(return_value={"list": [{"out_trade_no": "a"}], "total_page": 4}),
        ):
            orders, total_page = await api_client.list_orders(2)
        assert orders == [{"out_trade_no": "a"}]
        assert total_page == 4


class TestPostErrorHandling:
    @pytest.mark.asyncio
    async def test_raises_on_non_200_ec(self):
        from heart.afdian import api_client

        resp = MagicMock()
        resp.json.return_value = {"ec": 400, "em": "bad sign"}
        client = MagicMock()
        client.post = AsyncMock(return_value=resp)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("heart.core.config.settings.afdian_user_id", "uid"),
            patch("heart.core.config.settings.afdian_api_token", "tok"),
            patch("heart.afdian.api_client.httpx.AsyncClient", return_value=ctx),
        ):
            with pytest.raises(api_client.AfdianAPIError):
                await api_client._post("query-order", {"page": 1}, ts=123)


# ---------------------------------------------------------------------------
# fulfillment.reconcile_order
# ---------------------------------------------------------------------------


class TestReconcileOrder:
    @pytest.mark.asyncio
    async def test_returns_false_when_order_not_in_afdian(self):
        from heart.afdian.fulfillment import reconcile_order

        db = AsyncMock()
        with patch("heart.afdian.api_client.query_order", new=AsyncMock(return_value=None)):
            ok, msg = await reconcile_order(db, "otn-missing")
        assert ok is False
        assert msg == "order_not_found_in_afdian"

    @pytest.mark.asyncio
    async def test_records_then_fulfills(self):
        from heart.afdian import fulfillment

        db = AsyncMock()
        order = {
            "out_trade_no": "otn-9",
            "plan_id": "plan-x",
            "remark": "code: ABCD1234",
            "sku_detail": [{"sku_id": "sku_6", "count": 1}],
        }

        with (
            patch("heart.afdian.api_client.query_order", new=AsyncMock(return_value=order)),
            patch.object(
                fulfillment, "record_order", new=AsyncMock(return_value="otn-9")
            ) as mock_record,
            patch.object(
                fulfillment, "fulfill_order", new=AsyncMock(return_value=(True, "ok"))
            ) as mock_fulfill,
        ):
            ok, msg = await fulfillment.reconcile_order(db, "otn-9")

        assert ok is True
        assert msg == "ok"
        mock_record.assert_awaited_once()
        # fulfill_order called with (db, out_trade_no, plan_id, remark, sku_detail)
        args = mock_fulfill.call_args[0]
        assert args[1] == "otn-9"
        assert args[2] == "plan-x"
        assert args[3] == "code: ABCD1234"
        assert args[4] == order["sku_detail"]

    @pytest.mark.asyncio
    async def test_returns_false_on_api_error(self):
        from heart.afdian import fulfillment
        from heart.afdian.api_client import AfdianAPIError

        db = AsyncMock()
        with patch(
            "heart.afdian.api_client.query_order",
            new=AsyncMock(side_effect=AfdianAPIError("boom")),
        ):
            ok, msg = await fulfillment.reconcile_order(db, "otn-err")
        assert ok is False
        assert msg.startswith("afdian_api_error")


# ---------------------------------------------------------------------------
# fulfillment.record_order
# ---------------------------------------------------------------------------


class TestRecordOrder:
    @pytest.mark.asyncio
    async def test_raises_without_out_trade_no(self):
        from heart.afdian.fulfillment import record_order

        db = AsyncMock()
        with pytest.raises(ValueError):
            await record_order(db, {"plan_id": "p"}, {})

    @pytest.mark.asyncio
    async def test_inserts_and_commits(self):
        from heart.afdian.fulfillment import record_order

        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()
        order = {"out_trade_no": "otn-3", "plan_id": "p", "total_amount": "6.00"}

        otn = await record_order(db, order, {"raw": True})

        assert otn == "otn-3"
        db.execute.assert_awaited_once()
        db.commit.assert_awaited_once()
        params = db.execute.call_args[0][1]
        assert params["otn"] == "otn-3"
        assert params["amount"] == 6.0
