"""Tests for EmotionEvent persistence (P1-2).

Guards that the process-singleton EmotionService (no request-bound db_session)
still durably records each turn's EmotionEvent through an injected
session_factory. Previously it was built with no DB at all, so the
`emotion_events` table stayed empty forever.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss03_emotion.models import EmotionEvent
from heart.ss03_emotion.service import EmotionService


def _make_cold_session_factory():
    """Return (factory, cold_session) where `async with factory() as s` yields the session."""
    cold = AsyncMock()  # execute/flush/commit are awaitable
    cold.add = MagicMock()  # SQLAlchemy Session.add is synchronous
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=cold)
    cm.__aexit__ = AsyncMock(return_value=False)
    factory = MagicMock(return_value=cm)
    return factory, cold


@pytest.mark.asyncio
async def test_process_turn_persists_event_via_cold_session():
    factory, cold = _make_cold_session_factory()
    svc = EmotionService(session_factory=factory)

    await svc.process_turn(
        user_id=uuid4(),
        character_id="rin",
        user_message="我今天特别开心！",
        turn_id=uuid4(),
        context={
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "established",
            "user_emotion_vad": {"valence": 0.6, "arousal": 0.5, "dominance": 0.5},
        },
        soul_config={},
    )

    # Cold session opened, an EmotionEvent added, and committed.
    factory.assert_called_once()
    assert cold.add.call_count == 1
    added = cold.add.call_args.args[0]
    assert isinstance(added, EmotionEvent)
    assert added.event_type == "turn_processed"
    cold.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_memory_only_service_does_not_persist():
    """No db_session and no session_factory → compute state but never touch a DB."""
    svc = EmotionService()  # memory-only
    # Should not raise even though there is nowhere to persist.
    state = await svc.process_turn(
        user_id=uuid4(),
        character_id="rin",
        user_message="随便说点什么",
        turn_id=uuid4(),
        context={"days_since_last": 0, "hours_since_last": 0.1, "relationship_phase": "stranger"},
        soul_config={},
    )
    assert state is not None
