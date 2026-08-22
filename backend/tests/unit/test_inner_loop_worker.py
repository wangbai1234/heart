"""Unit tests for SS06 proactive queue bound + N+1 fix (PR-4, H8+H9)."""

from __future__ import annotations

import collections
import inspect
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
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
        from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker

        source = inspect.getsource(InnerLoopWorker._tick_all_active_users)
        # Should have exactly one SELECT...FROM sessions query
        assert source.count("SELECT s.user_id, s.character_id") == 1
        # Should NOT have per-user SELECT queries
        assert "WHERE user_id = :user_id AND character_id = :character_id" not in source
        assert "user_character_model_preferences" in source

    @pytest.mark.asyncio
    async def test_v2_receives_selected_user_character_model(self):
        from heart.core.config import settings
        from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker

        user_id = uuid4()
        now = datetime.now(timezone.utc)
        result = MagicMock()
        result.fetchall.return_value = [
            (
                user_id,
                "rin",
                now - timedelta(days=2),
                "FRIEND",
                0.6,
                "Asia/Shanghai",
                now - timedelta(hours=25),
                "grok-4.6",
            )
        ]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)

        class _SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        worker = InnerLoopWorker(
            db_session_factory=lambda: _SessionContext(),
            inner_state_service=MagicMock(),
        )
        worker._generate_v2_proactive_message = AsyncMock()

        with (
            patch.object(settings, "proactive_v2_enabled", True),
            patch("heart.ss06_inner_state.inner_loop_worker.random.random", return_value=0.0),
        ):
            await worker._tick_all_active_users()

        assert worker._generate_v2_proactive_message.await_args.kwargs["model"] == "grok-4.6"
        assert session.execute.await_args.args[1] == {"default_model": "gemini-3.1"}

    @pytest.mark.asyncio
    async def test_v2_composition_context_keeps_selected_model(self, monkeypatch):
        from heart.ss06_inner_state import proactive_repo
        from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker

        session = MagicMock()

        class _SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        composer = MagicMock()
        composer.compose = AsyncMock(return_value=None)
        monkeypatch.setattr(
            "heart.api.wiring._get_session_factory",
            lambda: lambda: _SessionContext(),
        )
        monkeypatch.setattr(
            "heart.api.wiring.build_composer_service",
            AsyncMock(return_value=composer),
        )
        monkeypatch.setattr(
            proactive_repo,
            "count_today_per_user",
            AsyncMock(return_value=0),
        )
        monkeypatch.setattr(
            proactive_repo,
            "any_recent_across_characters",
            AsyncMock(return_value=False),
        )

        worker = InnerLoopWorker(
            db_session_factory=MagicMock(),
            inner_state_service=MagicMock(),
        )
        await worker._generate_v2_proactive_message(
            user_id=uuid4(),
            character_id="rin",
            hours_since=12,
            user_timezone="Asia/Shanghai",
            model="gpt-5.5",
        )

        ctx = composer.compose.await_args.kwargs["ctx"]
        assert ctx.model == "gpt-5.5"

    @pytest.mark.asyncio
    async def test_v2_persists_action_and_dialogue_as_separate_bubbles(self, monkeypatch):
        """Inline v2 delivery must preserve the regular chat bubble contract."""
        from heart.ss06_inner_state import proactive_repo
        from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker

        session = MagicMock()
        session.execute = AsyncMock()
        session.commit = AsyncMock()

        class _SessionContext:
            async def __aenter__(self):
                return session

            async def __aexit__(self, exc_type, exc, tb):
                return False

        composer = MagicMock()
        composer.compose = AsyncMock(
            return_value=SimpleNamespace(response="（轻笑）你还没睡吗？")
        )
        monkeypatch.setattr(
            "heart.api.wiring._get_session_factory",
            lambda: lambda: _SessionContext(),
        )
        monkeypatch.setattr(
            "heart.api.wiring.build_composer_service",
            AsyncMock(return_value=composer),
        )
        monkeypatch.setattr(proactive_repo, "count_today_per_user", AsyncMock(return_value=0))
        monkeypatch.setattr(
            proactive_repo, "any_recent_across_characters", AsyncMock(return_value=False)
        )
        monkeypatch.setattr(proactive_repo, "insert_message_audit", AsyncMock())

        worker = InnerLoopWorker(
            db_session_factory=MagicMock(),
            inner_state_service=MagicMock(),
        )
        await worker._generate_v2_proactive_message(
            user_id=uuid4(),
            character_id="rin",
            hours_since=12,
            user_timezone="Asia/Shanghai",
            model="gpt-5.5",
        )

        inserts = [call for call in session.execute.await_args_list if "INSERT INTO chat_messages" in str(call.args[0])]
        assert len(inserts) == 2
        first_params = inserts[0].args[1]
        second_params = inserts[1].args[1]
        assert [first_params["kind"], second_params["kind"]] == ["action", "text"]
        assert [first_params["sequence_id"], second_params["sequence_id"]] == [0, 1]
        assert first_params["turn_id"] == second_params["turn_id"]
        assert first_params["content"] == "轻笑"
        assert second_params["content"] == "你还没睡吗？"
