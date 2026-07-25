"""Unit tests for the consolidation scheduler enqueue plumbing.

Behavioural (real-DB idempotency) coverage lives in
``tests/integration/ss02_memory/test_consolidation_scheduler.py``. These unit
tests pin the SQL shape and rowcount handling without a database, so they run in
the default CI ``unit-tests`` stage.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.workers.consolidation_scheduler import enqueue_due_consolidation_jobs


def _mock_session(rowcount: int) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.rowcount = rowcount
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_enqueue_issues_insert_on_conflict_with_lookback():
    session = _mock_session(rowcount=3)

    inserted = await enqueue_due_consolidation_jobs(session, lookback_hours=48)

    assert inserted == 3
    session.execute.assert_awaited_once()
    stmt, params = session.execute.await_args.args
    sql = str(stmt)
    assert "INSERT INTO consolidation_jobs" in sql
    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    # Dedup key must be the day bucket so re-runs collapse to one job/day.
    assert "date_trunc('day'" in sql
    assert params == {"lookback_hours": 48}
    # Enqueue must not own the transaction — the loop runner commits.
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_enqueue_returns_zero_when_nothing_inserted():
    session = _mock_session(rowcount=0)

    inserted = await enqueue_due_consolidation_jobs(session)

    assert inserted == 0


@pytest.mark.asyncio
async def test_enqueue_treats_negative_rowcount_as_zero():
    # Some drivers report rowcount == -1 when unknown; must not leak downstream.
    session = _mock_session(rowcount=-1)

    inserted = await enqueue_due_consolidation_jobs(session)

    assert inserted == 0


@pytest.mark.asyncio
async def test_enqueue_coerces_lookback_to_int():
    session = _mock_session(rowcount=1)

    await enqueue_due_consolidation_jobs(session, lookback_hours="24")  # type: ignore[arg-type]

    _stmt, params = session.execute.await_args.args
    assert params == {"lookback_hours": 24}
