"""Unit tests for heart.billing.voice_call — per-minute voice-call billing.

Free-minute allowance is tier-scoped (free:0, plus:10, immersive:60) and resets
each Asia/Shanghai calendar month. Minutes beyond the allowance cost
voice_call_minute_cost_fen() (2000 fen). Billing is idempotent per
(call_id, minute).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest


def _db_returning(used_value):
    """A mock AsyncSession whose first SELECT returns *used_value* used_minutes."""
    db = AsyncMock()
    sel = MagicMock()
    sel.scalar_one_or_none.return_value = used_value
    db.execute = AsyncMock(return_value=sel)
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestCurrentMonthKey:
    def test_format_is_year_month(self):
        from datetime import datetime, timezone

        from heart.billing.voice_call import current_month_key

        key = current_month_key(datetime(2026, 8, 6, 12, 0, tzinfo=timezone.utc))
        assert key == "2026-08"

    def test_shanghai_rolls_over_at_local_midnight(self):
        from datetime import datetime, timezone

        from heart.billing.voice_call import current_month_key

        # 2026-07-31 20:00 UTC == 2026-08-01 04:00 Asia/Shanghai → August bucket.
        key = current_month_key(datetime(2026, 7, 31, 20, 0, tzinfo=timezone.utc))
        assert key == "2026-08"


class TestChargeCallMinute:
    @pytest.mark.asyncio
    async def test_free_minute_within_allowance(self, monkeypatch):
        from heart.billing import voice_call

        monkeypatch.setattr(voice_call, "get_effective_tier", AsyncMock(return_value="plus"))
        monkeypatch.setattr(voice_call, "voice_call_free_minutes", lambda tier: 10)
        monkeypatch.setattr(voice_call, "_bump_used_minute", AsyncMock(return_value=True))

        db = _db_returning(3)  # 3 of 10 free minutes used
        # get_balance is imported lazily inside the function
        monkeypatch.setattr("heart.billing.get_balance", AsyncMock(return_value=5000))

        status, balance = await voice_call.charge_call_minute(db, uuid.uuid4(), "call-1", 3)
        assert status == "free"
        assert balance == 5000
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_charged_when_allowance_spent(self, monkeypatch):
        from heart.billing import voice_call

        monkeypatch.setattr(voice_call, "get_effective_tier", AsyncMock(return_value="plus"))
        monkeypatch.setattr(voice_call, "voice_call_free_minutes", lambda tier: 10)
        monkeypatch.setattr(voice_call, "voice_call_minute_cost_fen", lambda: 2000)
        deduct = AsyncMock(return_value=8000)
        monkeypatch.setattr(voice_call, "deduct_credits", deduct)

        db = _db_returning(10)  # allowance fully spent
        status, balance = await voice_call.charge_call_minute(db, uuid.uuid4(), "call-1", 10)
        assert status == "charged"
        assert balance == 8000
        # idempotency key must be voice_call:{call_id}:{minute}
        args, _ = deduct.call_args
        assert args[3] == "voice_call:call-1:10"
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, monkeypatch):
        from heart.billing import InsufficientCreditsError, voice_call

        monkeypatch.setattr(voice_call, "get_effective_tier", AsyncMock(return_value="free"))
        monkeypatch.setattr(voice_call, "voice_call_free_minutes", lambda tier: 0)
        monkeypatch.setattr(voice_call, "voice_call_minute_cost_fen", lambda: 2000)
        monkeypatch.setattr(
            voice_call,
            "deduct_credits",
            AsyncMock(side_effect=InsufficientCreditsError(needed=2000, balance=500)),
        )

        db = _db_returning(0)
        status, balance = await voice_call.charge_call_minute(db, uuid.uuid4(), "call-1", 0)
        assert status == "insufficient"
        assert balance == 500
        db.rollback.assert_awaited()

    @pytest.mark.asyncio
    async def test_free_tier_charges_from_minute_zero(self, monkeypatch):
        from heart.billing import voice_call

        monkeypatch.setattr(voice_call, "get_effective_tier", AsyncMock(return_value="free"))
        monkeypatch.setattr(voice_call, "voice_call_free_minutes", lambda tier: 0)
        monkeypatch.setattr(voice_call, "voice_call_minute_cost_fen", lambda: 2000)
        deduct = AsyncMock(return_value=3000)
        monkeypatch.setattr(voice_call, "deduct_credits", deduct)

        db = _db_returning(0)
        status, _ = await voice_call.charge_call_minute(db, uuid.uuid4(), "c", 0)
        assert status == "charged"
