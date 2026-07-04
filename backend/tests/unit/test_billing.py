"""Tests for billing service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Mock DB session helper ──

def _mock_db_session(scalar_result=None, rowcount=1, fetchone_result=None):
    """Create a mock AsyncSession that returns expected results."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_result
    result.scalar_one.return_value = scalar_result
    result.fetchone.return_value = fetchone_result
    result.rowcount = rowcount
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


# ── Tests ──

class TestGetBalance:
    """Tests for billing.get_balance."""

    @pytest.mark.asyncio
    async def test_get_balance_returns_value(self):
        from heart.billing import get_balance

        db = _mock_db_session(scalar_result=500)
        balance = await get_balance(db, uuid.uuid4())
        assert balance == 500

    @pytest.mark.asyncio
    async def test_get_balance_user_not_found(self):
        from heart.billing import get_balance

        db = _mock_db_session(scalar_result=None)
        with pytest.raises(ValueError, match="not found"):
            await get_balance(db, uuid.uuid4())


class TestChargeTurn:
    """Tests for billing.charge_turn."""

    @pytest.mark.asyncio
    async def test_charge_text_turn_deducts_1(self):
        from heart.billing import charge_turn

        db = _mock_db_session(scalar_result=99)  # new balance after charge
        balance = await charge_turn(db, uuid.uuid4(), "turn-001", "text")
        assert balance == 99
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_charge_voice_turn_deducts_5(self):
        from heart.billing import charge_turn

        db = _mock_db_session(scalar_result=95)
        balance = await charge_turn(db, uuid.uuid4(), "turn-002", "voice")
        assert balance == 95

    @pytest.mark.asyncio
    async def test_charge_turn_insufficient_balance(self):
        from heart.billing import InsufficientCreditsError, charge_turn

        # CTE returns None (insufficient), idempotency check returns None, get_balance returns 0
        session = AsyncMock()
        result_cte = MagicMock()
        result_cte.scalar_one_or_none.return_value = None
        result_idem = MagicMock()
        result_idem.scalar_one_or_none.return_value = None
        result_balance = MagicMock()
        result_balance.scalar_one_or_none.return_value = 0
        session.execute = AsyncMock(side_effect=[result_cte, result_idem, result_balance])
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        with pytest.raises(InsufficientCreditsError):
            await charge_turn(session, uuid.uuid4(), "turn-003", "text")

    @pytest.mark.asyncio
    async def test_charge_turn_idempotent(self):
        from heart.billing import charge_turn

        # CTE returns None (already charged), idempotency check returns existing balance
        session = AsyncMock()
        result_cte = MagicMock()
        result_cte.scalar_one_or_none.return_value = None
        result_idem = MagicMock()
        result_idem.scalar_one_or_none.return_value = 100  # existing balance_after
        session.execute = AsyncMock(side_effect=[result_cte, result_idem])
        session.commit = AsyncMock()
        session.rollback = AsyncMock()

        balance = await charge_turn(session, uuid.uuid4(), "turn-004", "text")
        assert balance == 100


class TestRedeem:
    """Tests for billing.redeem."""

    @pytest.mark.asyncio
    async def test_redeem_invalid_code(self):
        from heart.billing import redeem

        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = None
        session.execute = AsyncMock(return_value=result)
        session.rollback = AsyncMock()

        with pytest.raises(ValueError, match="无效"):
            await redeem(session, uuid.uuid4(), "INVALIDCODE")

    @pytest.mark.asyncio
    async def test_redeem_already_used(self):
        from heart.billing import redeem

        session = AsyncMock()
        result = MagicMock()
        result.mappings.return_value.first.return_value = {
            "id": uuid.uuid4(),
            "credits_value": 300,
            "status": "redeemed",
            "expires_at": None,
        }
        session.execute = AsyncMock(return_value=result)
        session.rollback = AsyncMock()

        with pytest.raises(ValueError, match="已被使用"):
            await redeem(session, uuid.uuid4(), "ABCDEF123456")


class TestRefund:
    """Tests for billing.refund."""

    @pytest.mark.asyncio
    async def test_refund_adds_credits(self):
        from heart.billing import refund

        db = _mock_db_session(scalar_result=105)
        balance = await refund(db, uuid.uuid4(), "turn-005", 5, "safety_blocked")
        assert balance == 105
        db.commit.assert_called_once()


class TestGrant:
    """Tests for billing.grant."""

    @pytest.mark.asyncio
    async def test_grant_signup_bonus(self):
        from heart.billing import grant

        db = _mock_db_session(scalar_result=100)
        balance = await grant(
            db, uuid.uuid4(), 100, "signup_grant:test-user", "grant", "signup"
        )
        assert balance == 100
        db.commit.assert_called_once()
