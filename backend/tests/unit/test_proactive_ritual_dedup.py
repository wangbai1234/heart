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


def _patch_default_gates(monkeypatch):
    """Neutralize the new user-scoped and content-dedup gates (default: allow)."""
    monkeypatch.setattr(
        inner_loop_worker.proactive_repo,
        "any_recent_across_characters",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        inner_loop_worker.proactive_repo,
        "content_seen_recently",
        AsyncMock(return_value=False),
    )


@pytest.mark.unit
class TestRitualDedupAndQuota:
    async def test_morning_ritual_generated_when_none_today(self, monkeypatch):
        """User idle > 12 h and no dedup → message generated with ritual_idle type."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))
        _patch_default_gates(monkeypatch)

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
        _patch_default_gates(monkeypatch)

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
        _patch_default_gates(monkeypatch)

        w = _worker("欢迎！")
        msg = await w._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=None,
        )

        assert msg is not None

    async def test_ritual_suppressed_by_cross_character_cooldown(self, monkeypatch):
        """Another character just pinged this user → suppress this one (BUG-6)."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "any_recent_across_characters",
            AsyncMock(return_value=True),
        )
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "content_seen_recently",
            AsyncMock(return_value=False),
        )

        msg = await _worker()._check_ritual_triggers(
            uuid4(), "rin", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )
        assert msg is None

    async def test_ritual_suppressed_when_content_seen_recently(self, monkeypatch):
        """Same content already sent recently for this character → suppress (BUG-1)."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "any_recent_across_characters",
            AsyncMock(return_value=False),
        )
        # First and second attempt both come back as duplicate → suppress.
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "content_seen_recently",
            AsyncMock(return_value=True),
        )

        msg = await _worker("月月想着你，今天过得怎么样？")._check_ritual_triggers(
            uuid4(), "yueyue", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )
        assert msg is None

    async def test_ritual_dedup_retry_succeeds_when_second_attempt_is_fresh(self, monkeypatch):
        """First LLM sample is a repeat, second one is fresh → fire with the fresh one."""
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_today", AsyncMock(return_value=0))
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "count_all_today", AsyncMock(return_value=0))
        monkeypatch.setattr(
            inner_loop_worker.proactive_repo,
            "any_recent_across_characters",
            AsyncMock(return_value=False),
        )
        seen = AsyncMock(side_effect=[True, False])
        monkeypatch.setattr(inner_loop_worker.proactive_repo, "content_seen_recently", seen)

        # svc._resolve_proactive_content returns 2 different strings across the retry.
        svc = MagicMock()
        svc._resolve_proactive_content = AsyncMock(side_effect=["月月想着你", "今晚外面月亮很圆"])
        w = InnerLoopWorker(db_session_factory=MagicMock(), inner_state_service=svc)

        msg = await w._check_ritual_triggers(
            uuid4(), "yueyue", MagicMock(),
            now=NOW, last_user_message_at=VERY_IDLE,
        )
        assert msg is not None
        assert msg.content == "今晚外面月亮很圆"
        assert seen.await_count == 2


class TestRepoQuotaGate:
    """proactive_repo.insert_message enforces DAILY_PROACTIVE_QUOTA as last defense."""

    @pytest.mark.asyncio
    async def test_repo_insert_refuses_over_quota(self, monkeypatch):
        """insert_message returns False and skips INSERT when sent_today >= quota."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4
        from datetime import datetime, timezone

        from heart.ss06_inner_state import proactive_repo
        from heart.ss06_inner_state.models import ProactiveMessage

        msg = ProactiveMessage(
            id=uuid4(),
            user_id=uuid4(),
            character_id="test_char",
            content="今晚外面月亮很圆",
            trigger_type="ritual_idle",
            created_at=datetime.now(tz=timezone.utc),
        )

        mock_session = MagicMock()

        # Simulate quota already exhausted
        with patch.object(
            proactive_repo,
            "count_all_today",
            new=AsyncMock(return_value=3),
        ):
            result = await proactive_repo.insert_message(mock_session, msg)

        assert result is False
        mock_session.execute.assert_not_called()
        mock_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_repo_insert_succeeds_under_quota(self, monkeypatch):
        """insert_message returns True and executes INSERT when sent_today < quota."""
        from unittest.mock import AsyncMock, MagicMock, patch
        from uuid import uuid4
        from datetime import datetime, timezone

        from heart.ss06_inner_state import proactive_repo
        from heart.ss06_inner_state.models import ProactiveMessage

        msg = ProactiveMessage(
            id=uuid4(),
            user_id=uuid4(),
            character_id="test_char",
            content="今晚外面月亮很圆",
            trigger_type="ritual_idle",
            created_at=datetime.now(tz=timezone.utc),
        )

        mock_session = MagicMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        with patch.object(
            proactive_repo,
            "count_all_today",
            new=AsyncMock(return_value=2),
        ):
            result = await proactive_repo.insert_message(mock_session, msg)

        assert result is True
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
