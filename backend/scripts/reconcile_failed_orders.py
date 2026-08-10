#!/usr/bin/env python3
"""Reconcile failed afdian orders after the binding code reuse fix."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from heart.afdian.fulfillment import fulfill_order


async def main():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Find all failed orders with no_binding_code_match error
        result = await session.execute(
            text(
                """
                SELECT out_trade_no, plan_id, remark, sku_detail, custom_order_id,
                       total_amount, received_at
                FROM afdian_orders
                WHERE fulfillment_error = 'no_binding_code_match'
                  AND fulfilled_at IS NULL
                  AND received_at >= '2026-08-09'
                ORDER BY received_at DESC
                """
            )
        )

        failed_orders = result.fetchall()

        if not failed_orders:
            print("✅ No failed orders found.")
            return

        print(f"Found {len(failed_orders)} failed orders:")
        for order in failed_orders:
            print(
                f"  - {order[0]} | ¥{order[5]} | "
                f"{order[6].strftime('%Y-%m-%d %H:%M:%S')} | "
                f"custom_id={order[4] or 'N/A'} remark={order[2][:20] if order[2] else 'N/A'}"
            )

        print("\nRetrying fulfillment with the fix (binding codes can now be reused)...")

        success_count = 0
        for order in failed_orders:
            out_trade_no, plan_id, remark, sku_detail, custom_order_id = order[:5]

            print(f"\n📦 Processing {out_trade_no}...")
            try:
                ok, msg = await fulfill_order(
                    session, out_trade_no, plan_id, remark, sku_detail, custom_order_id
                )

                if ok:
                    print(f"   ✅ SUCCESS: {msg}")
                    success_count += 1
                else:
                    print(f"   ❌ FAILED: {msg}")
            except Exception as e:
                print(f"   ❌ ERROR: {e}")

        print(f"\n{'='*60}")
        print(f"✅ Successfully fulfilled {success_count}/{len(failed_orders)} orders")
        print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
