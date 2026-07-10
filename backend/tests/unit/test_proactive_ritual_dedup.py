"""Unit tests for ritual trigger logic: idle-time gate + dedup + daily quota.

The new logic (replacing the UTC hour-window approach):
- Primary gate: user idle < 8 h → never fire.
- 8–12 h → dice (50 %).
- > 12 h → always fire.
- Dedup: at most one ritual_idle per (user, character) per day.
- Daily quota: counted toward DAILY_PROACTIVE_QUOTA.
- Content: from LLM via _resolve_proactive_content.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss06_inner_state import inner_loop_worker
from heart.ss06_inner_state.inner_loop_worker import (
    DAILY_PROACTIVE_QUOTA,
    InnerLoopWorker,
)

# Anchor "now" in UTC
NOW = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # 14:00 UTC (22:00 Beijing)

# Idle durations
VERY_IDLE = NOW - timedelta(hours=15)   # > 12 h → always fires
MEDIUM_IDLE = NOW - timedelta(hours=10) # 8-12 h → dice zone (50 %)
RECENT = NOW - timedelta(hours=2)       # < 8 h → never fires


def _worker(resolve_return: str = "test message") -> InnerLoopWorker:
    svc = MagicMock()
    svc._resolve_proactive_content = AsyncMock(return_value=resolve_return)
    return InnerLoopWorker(
        db_session_factory=MagicMock(),
        inner_state_service=svc,
    )


@pytest.mark.unit
class TestRitualDedupAndQuota:
    async def test_morning_ritual_generated_when_none_today(self, monkeypatch):
        """User idle > 12 h and no dedup → message generated with ritual_idle type."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        w = _worker("早上好！")
        msg = await w._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )

        assert msg is not None
        assert msg.trigger_type == "ritual_idle"
        assert msg.content == "早上好！"

    async def test_ritual_deduped_when_already_sent_today(self, monkeypatch):
        """One ritual_idle already recorded today → suppress."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=1))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=1))

        msg = await _worker()._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )

        assert msg is None

    async def test_ritual_respects_daily_quota(self, monkeypatch):
        """No ritual_idle yet today, but daily budget spent → suppress."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "count_all_today",
            AsyncMock(return_value=DAILY_PROACTIVE_QUOTA),
        )

        msg = await _worker()._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )

        assert msg is None

    async def test_no_ritual_when_chatted_recently(self, monkeypatch):
        """User chatted 2 h ago (< 8 h threshold) → skip before touching the DB."""
        count_today = AsyncMock(return_value=0)
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", count_today)
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        msg = await _worker()._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=RECENT,
        )

        assert msg is None
        count_today.assert_not_awaited()

    async def test_ritual_generated_for_dorothy_very_idle(self, monkeypatch):
        """User idle > 12 h with dorothy character → generates ritual_idle message."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        w = _worker("想你了~")
        msg = await w._check_ritual_triggers(
            uuid4(), "dorothy", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )

        assert msg is not None
        assert msg.trigger_type == "ritual_idle"
        assert msg.content == "想你了~"

    async def test_dedup_error_is_not_swallowed(self, monkeypatch):
        """A DB error on count_today must propagate (not be silently ignored)."""
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "count_today",
            AsyncMock(side_effect=RuntimeError("relation \"proactive_messages\" does not exist")),
        )
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        with pytest.raises(RuntimeError):
            await _worker()._check_ritual_triggers(
                uuid4(), "rin", MagicMock(),
                now=NOW, last_user_message_at=VERY_IDLE,
            )

    async def test_no_ritual_when_no_last_message_fires(self, monkeypatch):
        """last_user_message_at=None (new user, no history) → treated as very idle → fires."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        w = _worker("欢迎！")
        msg = await w._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=None,
        )

        assert msg is not None
