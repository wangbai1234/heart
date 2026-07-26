"""Afdian (爱发电) open-API client — query orders server-side.

The webhook (heart.api.routes_webhooks) is the primary fulfillment path, but it
is fire-and-forget: Afdian pushes once, and if the push is missed (endpoint
down, order placed before the SKU map was configured, network blip) the order
never auto-fulfills. This client lets us pull an order (or list recent orders)
straight from Afdian and reconcile it — see heart.afdian.fulfillment.reconcile_order.

API contract (https://afdian.com/api/open):
  POST https://afdian.com/api/open/query-order
  body: {"user_id": <uid>, "params": <json-string>, "ts": <unix-s>, "sign": <md5>}
  sign = md5(f"{token}params{params}ts{ts}user_id{user_id}")
  Response: {"ec":200,"em":"...","data":{"list":[...],"total_count":N,"total_page":M}}
  ec != 200 signals an API-level error (bad sign, unknown user, etc.).
"""

from __future__ import annotations

import hashlib
import json

import httpx
import structlog

from heart.core.config import settings

logger = structlog.get_logger(__name__)

_BASE_URL = "https://afdian.com/api/open"
_TIMEOUT = 15.0


class AfdianAPIError(RuntimeError):
    """Raised when Afdian's open API returns a non-200 ``ec`` or is unreachable."""


def _sign(token: str, params: str, ts: int, user_id: str) -> str:
    raw = f"{token}params{params}ts{ts}user_id{user_id}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _require_creds() -> tuple[str, str]:
    user_id = (settings.afdian_user_id or "").strip()
    token = (settings.afdian_api_token or "").strip()
    if not user_id or not token:
        raise AfdianAPIError(
            "afdian_user_id / afdian_api_token not configured "
            "(set AFDIAN_USER_ID and AFDIAN_API_TOKEN)"
        )
    return user_id, token


async def _post(endpoint: str, params_obj: dict, *, ts: int) -> dict:
    """Sign + POST one open-API call. ``ts`` is injected for deterministic tests."""
    user_id, token = _require_creds()
    params = json.dumps(params_obj, separators=(",", ":"), ensure_ascii=False)
    sign = _sign(token, params, ts, user_id)
    body = {"user_id": user_id, "params": params, "ts": ts, "sign": sign}

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{_BASE_URL}/{endpoint}", json=body)
    except httpx.HTTPError as e:
        raise AfdianAPIError(f"afdian request failed: {e}") from e

    try:
        payload = resp.json()
    except ValueError as e:
        raise AfdianAPIError(f"afdian returned non-JSON (status {resp.status_code})") from e

    ec = payload.get("ec")
    if ec != 200:
        raise AfdianAPIError(f"afdian ec={ec} em={payload.get('em')!r}")
    return payload.get("data") or {}


def _now_ts() -> int:
    # Wrapped so tests can monkeypatch without importing time at call sites.
    import time

    return int(time.time())


async def query_order(out_trade_no: str, *, ts: int | None = None) -> dict | None:
    """Fetch a single order by out_trade_no. Returns the order dict or None.

    The order dict mirrors the webhook ``data.order`` shape: out_trade_no,
    plan_id, sku_detail (list), remark, total_amount, status, etc.
    """
    out_trade_no = (out_trade_no or "").strip()
    if not out_trade_no:
        return None
    data = await _post(
        "query-order", {"out_trade_no": out_trade_no}, ts=ts if ts is not None else _now_ts()
    )
    orders = data.get("list") or []
    for order in orders:
        if str(order.get("out_trade_no") or "") == out_trade_no:
            return order
    return orders[0] if orders else None


async def list_orders(page: int = 1, *, ts: int | None = None) -> tuple[list[dict], int]:
    """List orders (newest first). Returns ``(orders, total_page)``.

    Handy for harvesting the real Afdian sku_id/plan_id values needed to fill
    AFDIAN_SKU_MAP — see heart/scripts/afdian_reconcile.py --list.
    """
    data = await _post(
        "query-order", {"page": max(1, int(page))}, ts=ts if ts is not None else _now_ts()
    )
    orders = data.get("list") or []
    total_page = int(data.get("total_page") or 1)
    return orders, total_page
