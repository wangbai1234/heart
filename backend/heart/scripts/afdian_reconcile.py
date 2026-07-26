"""Reconcile Afdian orders from the CLI.

Two modes:

  # Backfill + fulfill one order (missed webhook / placed before SKU map config)
  python -m heart.scripts.afdian_reconcile 202607260235315198102911757

  # List recent orders — prints the real sku_id / plan_id you must put in
  # AFDIAN_SKU_MAP (webhook payloads key on these, NOT the friendly pack_6 names)
  python -m heart.scripts.afdian_reconcile --list

Requires AFDIAN_USER_ID + AFDIAN_API_TOKEN in the environment / .env.
"""

from __future__ import annotations

import argparse
import asyncio
import json

from heart.afdian.api_client import list_orders, query_order
from heart.afdian.fulfillment import reconcile_order
from heart.api.wiring import _get_session_factory


async def _reconcile(out_trade_no: str) -> int:
    factory = _get_session_factory()
    async with factory() as db:
        success, message = await reconcile_order(db, out_trade_no)
    print(f"{'OK ' if success else 'FAIL'} {out_trade_no}: {message}")
    return 0 if success else 1


async def _inspect(out_trade_no: str) -> int:
    order = await query_order(out_trade_no)
    if order is None:
        print(f"order not found in afdian: {out_trade_no}")
        return 1
    print(json.dumps(order, ensure_ascii=False, indent=2))
    return 0


async def _list(pages: int) -> int:
    print("=== recent afdian orders (use these ids in AFDIAN_SKU_MAP) ===")
    for page in range(1, pages + 1):
        orders, total_page = await list_orders(page)
        for o in orders:
            skus = [
                {"sku_id": s.get("sku_id"), "name": s.get("name"), "price": s.get("price")}
                for s in (o.get("sku_detail") or [])
            ]
            print(
                json.dumps(
                    {
                        "out_trade_no": o.get("out_trade_no"),
                        "title": o.get("plan_title"),
                        "amount": o.get("total_amount"),
                        "product_type": o.get("product_type"),
                        "plan_id": o.get("plan_id"),
                        "sku_detail": skus,
                        "remark": o.get("remark"),
                        "status": o.get("status"),
                    },
                    ensure_ascii=False,
                )
            )
        if page >= total_page:
            break
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile Afdian orders")
    parser.add_argument("out_trade_no", nargs="?", help="订单号（履约该订单）")
    parser.add_argument("--list", action="store_true", help="列出近期订单（获取 sku_id/plan_id）")
    parser.add_argument("--pages", type=int, default=3, help="--list 时翻页数（默认 3）")
    parser.add_argument(
        "--inspect", action="store_true", help="只打印订单详情，不履约（配合 out_trade_no）"
    )
    args = parser.parse_args()

    if args.list:
        return asyncio.run(_list(args.pages))
    if not args.out_trade_no:
        parser.error("需要 out_trade_no，或使用 --list")
    if args.inspect:
        return asyncio.run(_inspect(args.out_trade_no))
    return asyncio.run(_reconcile(args.out_trade_no))


if __name__ == "__main__":
    raise SystemExit(main())
