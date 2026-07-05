"""
Credit Reconciliation Worker — verifies ledger consistency.

Periodically checks that SUM(delta) from credit_transactions
equals users.credits_balance for each user. Logs drift as warning.
"""

from __future__ import annotations

import asyncio
import os

import structlog
from sqlalchemy import text

from heart.api.wiring import _get_session_factory

logger = structlog.get_logger(__name__)

RECONCILIATION_INTERVAL_S = int(
    os.getenv("HEART_CREDIT_RECONCILIATION_INTERVAL_S", "3600")
)  # 1 hour


async def run_credit_reconciliation_loop(stop_event: asyncio.Event) -> None:
    """Periodically verify credit ledger consistency."""
    factory = _get_session_factory()
    logger.info("credit_reconciliation_started", interval_s=RECONCILIATION_INTERVAL_S)

    while not stop_event.is_set():
        try:
            drift_count = await _check_balance_drift(factory)
            if drift_count > 0:
                logger.warning("credit_balance_drift_detected", drift_count=drift_count)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("credit_reconciliation_failed", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=RECONCILIATION_INTERVAL_S)
            break
        except asyncio.TimeoutError:
            continue


async def _check_balance_drift(factory) -> int:
    """Check for balance drift between ledger and cached balance.

    Returns number of users with drifted balances.
    """
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT u.id, u.credits_balance, COALESCE(SUM(ct.delta), 0) AS ledger_sum
                FROM users u
                LEFT JOIN credit_transactions ct ON ct.user_id = u.id
                WHERE u.status = 'active'
                GROUP BY u.id, u.credits_balance
                HAVING u.credits_balance != COALESCE(SUM(ct.delta), 0)
                LIMIT 100
            """)
        )
        drifts = result.fetchall()

        for user_id, cached_balance, ledger_sum in drifts:
            logger.warning(
                "credit_balance_mismatch",
                user_id=str(user_id),
                cached_balance=cached_balance,
                ledger_sum=ledger_sum,
                drift=cached_balance - ledger_sum,
            )

        return len(drifts)
