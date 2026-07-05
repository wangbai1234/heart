"""Unit tests for memory_extractor_worker skeleton."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from heart.workers.memory_extractor_worker import MemoryExtractorWorker


@pytest.fixture
def mock_session_factory():
    """Mock async session factory."""
    factory = MagicMock()
    session = AsyncMock()
    context_manager = AsyncMock()
    context_manager.__aenter__ = AsyncMock(return_value=session)
    context_manager.__aexit__ = AsyncMock(return_value=False)
    factory.return_value = context_manager
    return factory, session


@pytest.fixture
def worker(mock_session_factory):
    """Create a MemoryExtractorWorker with mock dependencies."""
    factory, _ = mock_session_factory
    return MemoryExtractorWorker(db_session_factory=factory)


class TestMemoryExtractorWorker:
    """Tests for MemoryExtractorWorker."""

    @pytest.mark.asyncio
    async def test_worker_can_be_created(self, mock_session_factory):
        """Worker should instantiate without error."""
        factory, _ = mock_session_factory
        worker = MemoryExtractorWorker(db_session_factory=factory)
        assert worker._should_stop is False

    @pytest.mark.asyncio
    async def test_stop_sets_flag(self, worker):
        """stop() should set _should_stop flag."""
        await worker.stop()
        assert worker._should_stop is True

    @pytest.mark.asyncio
    async def test_fetch_pending_empty(self, worker, mock_session_factory):
        """_fetch_pending should return empty list when no pending items."""
        _, session = mock_session_factory
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        items = await worker._fetch_pending(session)
        assert items == []
