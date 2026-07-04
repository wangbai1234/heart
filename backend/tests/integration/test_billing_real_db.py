"""
Integration tests for billing against real PostgreSQL.

These tests exercise grant/redeem/charge_turn/refund directly,
catching SQL bugs (like wrong column names in CTEs) that mock tests miss.

Requires: running PostgreSQL (make docker-up) + alembic upgrade head.
Run: DATABASE_URL=postgresql+asyncpg://heart:heartdev@localhost:5432/heart \
     pytest tests/integration/test_billing_real_db.py -v
"""

import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]

DATABASE_URL = os.environ.get(
    "TEST_ASYNC_DATABASE_URL",
    os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://heart:heartdev@localhost:5432/heart",
    ),
)


@pytest_asyncio.fixture(scope="module")
async def engine():
    """Create engine against real PostgreSQL."""
    eng = create_async_engine(DATABASE_URL, echo=False)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    """Per-test session with rollback."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def user_id(engine):
    """Create a test user and return its ID."""
    uid = uuid.uuid4()
    email = f"billing-test-{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO users (id, email, credits_balance) VALUES (:id, :email, 0)"
            ),
            {"id": uid, "email": email},
        )
    return uid


@pytest_asyncio.fixture
async def user_with_balance(engine):
    """Create a test user with 100 credits."""
    uid = uuid.uuid4()
    email = f"balance-test-{uid.hex[:8]}@test.com"
    async with engine.begin() as conn:
        await conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO users (id, email, credits_balance) VALUES (:id, :email, 100)"
            ),
            {"id": uid, "email": email},
        )
    return uid


class TestGrant:
    """Test billing.grant against real PostgreSQL."""

    async def test_grant_increases_balance(self, db, user_id):
        from heart.billing import get_balance, grant

        new_balance = await grant(db, user_id, 50, idempotency_key=f"grant:{uuid.uuid4()}")
        assert new_balance == 50

        balance = await get_balance(db, user_id)
        assert balance == 50

    async def test_grant_idempotent(self, db, user_id):
        from heart.billing import grant

        key = f"grant-idem:{uuid.uuid4()}"
        b1 = await grant(db, user_id, 100, idempotency_key=key)
        b2 = await grant(db, user_id, 100, idempotency_key=key)
        assert b1 == b2 == 100

    async def test_grant_creates_ledger_entry(self, db, user_id, engine):
        from heart.billing import grant

        key = f"grant-ledger:{uuid.uuid4()}"
        await grant(db, user_id, 75, idempotency_key=key, ref_type="test", ref_id="abc")

        async with engine.begin() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text(
                    "SELECT delta, balance_after, type FROM credit_transactions WHERE idempotency_key = :key"
                ),
                {"key": key},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == 75  # delta
            assert row[1] == 75  # balance_after
            assert row[2] == "grant"


class TestRedeem:
    """Test billing.redeem against real PostgreSQL."""

    async def test_redeem_increases_balance(self, db, user_id, engine):
        from heart.billing import redeem

        code = f"TEST{uuid.uuid4().hex[:8].upper()}"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO redemption_codes (code, credits_value, status) VALUES (:code, 300, 'active')"
                ),
                {"code": code},
            )

        new_balance = await redeem(db, user_id, code)
        assert new_balance == 300

    async def test_redeem_code_marked_redeemed(self, db, user_id, engine):
        from heart.billing import redeem

        code = f"USED{uuid.uuid4().hex[:8].upper()}"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO redemption_codes (code, credits_value, status) VALUES (:code, 100, 'active')"
                ),
                {"code": code},
            )

        await redeem(db, user_id, code)

        async with engine.begin() as conn:
            result = await conn.execute(
                __import__("sqlalchemy").text(
                    "SELECT status, redeemed_by FROM redemption_codes WHERE code = :code"
                ),
                {"code": code},
            )
            row = result.fetchone()
            assert row[0] == "redeemed"
            assert row[1] == user_id

    async def test_redeem_already_used_raises(self, db, user_id, engine):
        from heart.billing import redeem

        code = f"ALREADY{uuid.uuid4().hex[:8].upper()}"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO redemption_codes (code, credits_value, status, redeemed_by, redeemed_at) "
                    "VALUES (:code, 100, 'redeemed', :uid, NOW())"
                ),
                {"code": code, "uid": user_id},
            )

        with pytest.raises(ValueError, match="已被使用"):
            await redeem(db, user_id, code)

    async def test_redeem_disabled_code_raises(self, db, user_id, engine):
        from heart.billing import redeem

        code = f"DISABLED{uuid.uuid4().hex[:8].upper()}"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO redemption_codes (code, credits_value, status) VALUES (:code, 100, 'disabled')"
                ),
                {"code": code},
            )

        with pytest.raises(ValueError, match="已失效"):
            await redeem(db, user_id, code)


class TestChargeTurn:
    """Test billing.charge_turn against real PostgreSQL."""

    async def test_charge_text_turn(self, db, user_with_balance):
        from heart.billing import charge_turn, get_balance

        turn_id = str(uuid.uuid4())
        new_balance = await charge_turn(db, user_with_balance, turn_id, "text")
        assert new_balance == 99  # 100 - 1

    async def test_charge_voice_turn(self, db, user_with_balance):
        from heart.billing import charge_turn

        turn_id = str(uuid.uuid4())
        new_balance = await charge_turn(db, user_with_balance, turn_id, "voice")
        assert new_balance == 95  # 100 - 5

    async def test_charge_idempotent(self, db, user_with_balance):
        from heart.billing import charge_turn

        turn_id = str(uuid.uuid4())
        b1 = await charge_turn(db, user_with_balance, turn_id, "text")
        b2 = await charge_turn(db, user_with_balance, turn_id, "text")
        assert b1 == b2 == 99

    async def test_charge_insufficient_balance(self, db, engine):
        from heart.billing import InsufficientCreditsError, charge_turn

        uid = uuid.uuid4()
        email = f"poor-{uid.hex[:8]}@test.com"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO users (id, email, credits_balance) VALUES (:id, :email, 0)"
                ),
                {"id": uid, "email": email},
            )

        with pytest.raises(InsufficientCreditsError):
            await charge_turn(db, uid, str(uuid.uuid4()), "text")

    async def test_charge_voice_insufficient(self, db, engine):
        """User with 2 credits can't afford voice (5)."""
        from heart.billing import InsufficientCreditsError, charge_turn

        uid = uuid.uuid4()
        email = f"poor-voice-{uid.hex[:8]}@test.com"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO users (id, email, credits_balance) VALUES (:id, :email, 2)"
                ),
                {"id": uid, "email": email},
            )

        with pytest.raises(InsufficientCreditsError):
            await charge_turn(db, uid, str(uuid.uuid4()), "voice")


class TestRefund:
    """Test billing.refund against real PostgreSQL."""

    async def test_refund_increases_balance(self, db, user_with_balance):
        from heart.billing import charge_turn, refund

        turn_id = str(uuid.uuid4())
        await charge_turn(db, user_with_balance, turn_id, "voice")
        new_balance = await refund(db, user_with_balance, turn_id, 5, reason="safety_blocked")
        assert new_balance == 100  # back to original


class TestBalanceNeverNegative:
    """Verify credits_balance CHECK constraint works."""

    async def test_balance_check_constraint(self, db, engine):
        """DB CHECK(credits_balance >= 0) prevents negative balance."""
        from heart.billing import InsufficientCreditsError, charge_turn

        uid = uuid.uuid4()
        email = f"check-{uid.hex[:8]}@test.com"
        async with engine.begin() as conn:
            await conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO users (id, email, credits_balance) VALUES (:id, :email, 1)"
                ),
                {"id": uid, "email": email},
            )

        # First turn costs 1 → balance 0, OK
        await charge_turn(db, uid, str(uuid.uuid4()), "text")

        # Second turn costs 1 → would go negative, should fail
        with pytest.raises(InsufficientCreditsError):
            await charge_turn(db, uid, str(uuid.uuid4()), "text")
