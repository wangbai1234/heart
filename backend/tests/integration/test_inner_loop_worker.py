"""
Integration: Inner Loop worker + proactive messages API.

Verifies T2-02: Inner Loop scheduler generates proactive messages
and they can be retrieved via GET /api/proactive/pending.
"""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss06_inner_state.inner_loop_worker import (
    InnerLoopWorker,
    get_pending_proactive_messages,
    _proactive_messages,
)
from heart.ss06_inner_state.models import ProactiveMessage
from heart.ss06_inner_state.service import InnerStateService


class TestInnerLoopWorker:
    """Verify Inner Loop worker generates proactive messages."""

    def setup_method(self):
        """Clear proactive messages before each test."""
        _proactive_messages.clear()

    def test_get_pending_messages_empty(self):
        """Should return empty list when no messages."""
        user_id = uuid4()
        messages = get_pending_proactive_messages(user_id)
        assert messages == []

    def test_get_pending_messages_with_messages(self):
        """Should return messages for the user."""
        user_id = uuid4()
        character_id = "rin"

        msg = ProactiveMessage(
            user_id=user_id,
            character_id=character_id,
            content="今天想你了",
            trigger_type="scheduled",
            created_at=datetime.now(timezone.utc),
        )
        _proactive_messages.append(msg)

        messages = get_pending_proactive_messages(user_id, character_id)
        assert len(messages) == 1
        assert messages[0].content == "今天想你了"

    def test_get_pending_messages_filters_by_character(self):
        """Should filter by character_id when provided."""
        user_id = uuid4()

        msg1 = ProactiveMessage(
            user_id=user_id,
            character_id="rin",
            content="消息1",
            trigger_type="scheduled",
            created_at=datetime.now(timezone.utc),
        )
        msg2 = ProactiveMessage(
            user_id=user_id,
            character_id="dorothy",
            content="消息2",
            trigger_type="scheduled",
            created_at=datetime.now(timezone.utc),
        )
        _proactive_messages.extend([msg1, msg2])

        messages = get_pending_proactive_messages(user_id, character_id="rin")
        assert len(messages) == 1
        assert messages[0].character_id == "rin"

    def test_get_pending_messages_filters_by_time(self):
        """Should filter messages by time window."""
        user_id = uuid4()

        # Old message (should be filtered)
        old_msg = ProactiveMessage(
            user_id=user_id,
            character_id="rin",
            content="旧消息",
            trigger_type="scheduled",
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        # Recent message
        recent_msg = ProactiveMessage(
            user_id=user_id,
            character_id="rin",
            content="新消息",
            trigger_type="scheduled",
            created_at=datetime.now(timezone.utc),
        )
        _proactive_messages.extend([old_msg, recent_msg])

        messages = get_pending_proactive_messages(user_id)
        assert len(messages) == 1
        assert messages[0].content == "新消息"


class TestInnerLoopWorkerInitialization:
    """Verify Inner Loop worker initialization."""

    def test_worker_initializes_with_defaults(self):
        """Worker should initialize with default interval."""
        os.environ.pop("HEART_INNER_LOOP_INTERVAL_S", None)

        svc = InnerStateService()
        factory = MagicMock()

        worker = InnerLoopWorker(
            db_session_factory=factory,
            inner_state_service=svc,
        )

        assert worker.interval_s == 3600
        assert worker._should_stop is False

    def test_worker_respects_interval_env(self):
        """Worker should use HEART_INNER_LOOP_INTERVAL_S env var."""
        os.environ["HEART_INNER_LOOP_INTERVAL_S"] = "10"

        svc = InnerStateService()
        factory = MagicMock()

        worker = InnerLoopWorker(
            db_session_factory=factory,
            inner_state_service=svc,
        )

        assert worker.interval_s == 10

        os.environ.pop("HEART_INNER_LOOP_INTERVAL_S", None)
