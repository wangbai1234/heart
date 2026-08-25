"""Periodic settlement of frozen referral commissions."""

from __future__ import annotations

import asyncio
import os

import structlog

from heart.commission.service import settle_due_commissions

logger = structlog.get_logger(__name__)


async def run_commission_settle_loop(stop_event: asyncio.Event) -> None:
    from heart.api.wiring import _get_session_factory

    interval_s = int(os.getenv("HEART_COMMISSION_SETTLE_INTERVAL_S", "3600"))
    factory = _get_session_factory()
    while not stop_event.is_set():
        try:
            async with factory() as session:
                settled = await settle_due_commissions(session)
                await session.commit()
                if settled:
                    logger.info("commissions_settled", count=settled)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("commission_settlement_failed")
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
            break
        except asyncio.TimeoutError:
            continue
