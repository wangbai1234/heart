"""Unit tests for BUG-4: ritual dedup + daily quota + no silent swallow.

Before the fix, ``proactive_messages`` did not exist, the dedup query's
exception was swallowed (``except Exception: pass``), and rituals bypassed the
daily quota — so ``ritual_morning`` was emitted on every tick. These tests lock
in the corrected behaviour.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from heart.ss06_inner_state import inner_loop_worker
from heart.ss06_inner_state.inner_loop_worker import (
    DAILY_PROACTIVE_QUOTA,
    InnerLoopWorker,
)

MORNING = datetime(2026, 7, 8, 7, 0, tzinfo=timezone.utc)  # inside 6-10 window
NIGHT = datetime(2026, 7, 8, 22, 0, tzinfo=timezone.utc)  # inside 21-01 window
MIDDAY = datetime(2026, 7, 8, 14, 0, tzinfo=timezone.utc)  # outside any window


def _worker() -> InnerLoopWorker:
    return InnerLoopWorker(
        db_session_factory=MagicMock(),
        inner_state_service=MagicMock(),
    )


@pytest.mark.unit
class TestRitualDedupAndQuota:
    async def test_morning_ritual_generated_when_none_today(self, monkeypatch):
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        msg = await _worker()._check_ritual_triggers(uuid4(), "rin", MagicMock(), now=MORNING)

        assert msg is not None
        assert msg.trigger_type == "ritual_morning"
        assert msg.content == "早安。"

    async def test_ritual_deduped_when_already_sent_today(self, monkeypatch):
        # One ritual_morning already recorded today -> suppress the second.
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=1))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=1))

        msg = await _worker()._check_ritual_triggers(uuid4(), "rin", MagicMock(), now=MORNING)

        assert msg is None

    async def test_ritual_respects_daily_quota(self, monkeypatch):
        # No ritual_morning yet today, but the daily proactive budget is spent.
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "count_all_today",
            AsyncMock(return_value=DAILY_PROACTIVE_QUOTA),
        )

        msg = await _worker()._check_ritual_triggers(uuid4(), "rin", MagicMock(), now=MORNING)

        assert msg is None

    async def test_no_ritual_outside_window(self, monkeypatch):
        count_today = AsyncMock(return_value=0)
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", count_today)
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        msg = await _worker()._check_ritual_triggers(uuid4(), "rin", MagicMock(), now=MIDDAY)

        assert msg is None
        # Short-circuits before touching the DB at all.
        count_today.assert_not_awaited()

    async def test_night_ritual_for_dorothy(self, monkeypatch):
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        msg = await _worker()._check_ritual_triggers(uuid4(), "dorothy", MagicMock(), now=NIGHT)

        assert msg is not None
        assert msg.trigger_type == "ritual_night"
        assert msg.content == "晚安晚安！做个好梦哦！"

    async def test_dedup_error_is_not_swallowed(self, monkeypatch):
        # A missing table (or any DB error) must surface, not be silently
        # ignored the way the old `except Exception: pass` did.
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "count_today",
            AsyncMock(side_effect=RuntimeError("relation \"proactive_messages\" does not exist")),
        )
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))

        with pytest.raises(RuntimeError):
            await _worker()._check_ritual_triggers(uuid4(), "rin", MagicMock(), now=MORNING)
