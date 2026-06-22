"""Unit tests for SS06 proactive queue bound + N+1 fix (PR-4, H8+H9)."""

from __future__ import annotations

import collections
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from heart.ss06_inner_state.inner_loop_worker import (
    _proactive_messages,
    get_pending_proactive_messages,
)
from heart.ss06_inner_state.models import ProactiveMessage


def _make_message(user_id=None, character_id="rin", hours_ago=0, seq=0):
    """Create a ProactiveMessage for testing."""
    return ProactiveMessage(
        user_id=user_id or uuid4(),
        character_id=character_id,
        content=f"test message {seq}",
        trigger_type="test",
        created_at=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
    )


@pytest.mark.unit
class TestProactiveQueueBound:

    def setup_method(self):
        """Clear queue before each test."""
        _proactive_messages.clear()

    def test_queue_maxlen_1000(self):
        """Queue should be bounded at 1000 items."""
        assert isinstance(_proactive_messages, collections.deque)
        assert _proactive_messages.maxlen == 1000

    def test_queue_evicts_oldest_on_overflow(self):
        """When queue is full, adding new items should evict oldest."""
        uid = uuid4()
        # Fill queue to capacity
        for i in range(1000):
            _proactive_messages.append(_make_message(user_id=uid, hours_ago=i, seq=i))

        assert len(_proactive_messages) == 1000
        oldest_seq = _proactive_messages[0].content

        # Add one more — oldest should be evicted
        new_msg = _make_message(user_id=uid, hours_ago=0, seq=9999)
        _proactive_messages.append(new_msg)

        assert len(_proactive_messages) == 1000
        assert _proactive_messages[0].content != oldest_seq

    def test_get_pending_filters_by_user(self):
        """get_pending_proactive_messages should filter by user_id."""
        uid = uuid4()
        other_uid = uuid4()

        _proactive_messages.append(_make_message(user_id=uid))
        _proactive_messages.append(_make_message(user_id=other_uid))

        result = get_pending_proactive_messages(user_id=uid)
        assert len(result) == 1
        assert result[0].user_id == uid

    def test_get_pending_filters_by_time(self):
        """get_pending_proactive_messages should filter by time window."""
        uid = uuid4()
        _proactive_messages.append(_make_message(user_id=uid, hours_ago=1))
        _proactive_messages.append(_make_message(user_id=uid, hours_ago=200))  # >7 days

        result = get_pending_proactive_messages(user_id=uid)
        assert len(result) == 1  # Only the 1-hour-old one


@pytest.mark.unit
class TestSingleSessionQuery:

    def test_single_query_returns_joined_data(self):
        """The tick query should be a single JOIN, not N separate queries."""
        # Read the source to verify single query pattern
        import inspect
        from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker

        source = inspect.getsource(InnerLoopWorker._tick_all_active_users)
        # Should have exactly one SELECT...FROM sessions query
        assert source.count("SELECT s.user_id, s.character_id") == 1
        # Should NOT have per-user SELECT queries
        assert "WHERE user_id = :user_id AND character_id = :character_id" not in source
