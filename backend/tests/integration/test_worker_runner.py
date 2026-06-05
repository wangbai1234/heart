"""
Integration: Worker runner startup/shutdown.

Verifies T1-05: Memory Encoder Worker + Consolidator Worker
start and stop correctly with HEART_WORKERS_ENABLED env switch.
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWorkerRunner:
    """Verify worker runner starts and stops workers."""

    @pytest.mark.asyncio
    async def test_workers_disabled_by_default(self):
        """Workers should not start when HEART_WORKERS_ENABLED is not set."""
        os.environ.pop("HEART_WORKERS_ENABLED", None)

        from heart.workers.runner import start_workers, stop_workers, _worker_tasks

        _worker_tasks.clear()

        await start_workers()

        assert len(_worker_tasks) == 0

    @pytest.mark.asyncio
    async def test_workers_start_when_enabled(self):
        """Workers should start when HEART_WORKERS_ENABLED=true."""
        os.environ["HEART_WORKERS_ENABLED"] = "true"

        from heart.workers.runner import start_workers, stop_workers, _worker_tasks

        _worker_tasks.clear()

        with patch("heart.api.wiring._get_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = MagicMock(return_value=mock_ctx)

            await start_workers()

            # Should have started 2 workers
            assert len(_worker_tasks) == 2

            # Stop workers
            await stop_workers()

        os.environ.pop("HEART_WORKERS_ENABLED", None)

    @pytest.mark.asyncio
    async def test_workers_stop_gracefully(self):
        """Workers should stop gracefully on shutdown."""
        os.environ["HEART_WORKERS_ENABLED"] = "true"

        from heart.workers.runner import start_workers, stop_workers, _worker_tasks

        _worker_tasks.clear()

        with patch("heart.api.wiring._get_session_factory") as mock_factory:
            mock_session = AsyncMock()
            mock_ctx = MagicMock()
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_factory.return_value = MagicMock(return_value=mock_ctx)

            await start_workers()
            assert len(_worker_tasks) == 2

            await stop_workers()
            assert len(_worker_tasks) == 0

        os.environ.pop("HEART_WORKERS_ENABLED", None)
