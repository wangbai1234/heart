"""Regression tests for background cleanup workers."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.workers.runner import _run_replay_cleanup_loop


@pytest.mark.asyncio
async def test_replay_cleanup_binds_explicit_naive_utc_cutoff(monkeypatch):
    """PostgreSQL cannot bind parameters inside an INTERVAL literal."""
    monkeypatch.setenv("HEART_REPLAY_RETENTION_DAYS", "7")

    stop_event = asyncio.Event()
    captured: dict[str, object] = {}
    result = MagicMock(rowcount=0)
    session = MagicMock()

    async def execute(statement, params):
        captured["statement"] = str(statement)
        captured["params"] = params
        stop_event.set()
        return result

    session.execute = AsyncMock(side_effect=execute)
    session.commit = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=session)

    before = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    with patch("heart.api.wiring._get_session_factory", return_value=factory):
        await _run_replay_cleanup_loop(stop_event)
    after = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)

    assert captured["statement"] == "DELETE FROM replay_snapshots WHERE created_at < :cutoff"
    params = captured["params"]
    assert isinstance(params, dict)
    cutoff = params["cutoff"]
    assert isinstance(cutoff, datetime)
    assert cutoff.tzinfo is None
    assert before <= cutoff <= after
    session.commit.assert_awaited_once()
