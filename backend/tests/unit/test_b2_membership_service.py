"""Unit tests for B2: user_memberships service + GET /api/membership."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, call

import pytest


# ---------------------------------------------------------------------------
# activate_or_extend
# ---------------------------------------------------------------------------


class TestActivateOrExtend:
    @pytest.mark.asyncio
    async def test_new_membership_inserts_from_now(self):
        from heart.membership.service import activate_or_extend

        db = AsyncMock()
        # First execute (SELECT) returns None → no existing membership
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        insert_result = MagicMock()
        db.execute = AsyncMock(side_effect=[select_result, insert_result])

        user_id = uuid.uuid4()
        before = datetime.now(tz=timezone.utc)
        expires = await activate_or_extend(db, user_id, "plus", 30)
        after = datetime.now(tz=timezone.utc)

        assert expires >= before + timedelta(days=30)
        assert expires <= after + timedelta(days=30)
        assert db.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_extends_existing_membership(self):
        from heart.membership.service import activate_or_extend

        db = AsyncMock()
        existing_expires = datetime.now(tz=timezone.utc) + timedelta(days=15)
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = existing_expires
        insert_result = MagicMock()
        db.execute = AsyncMock(side_effect=[select_result, insert_result])

        user_id = uuid.uuid4()
        expires = await activate_or_extend(db, user_id, "plus", 30)

        expected = existing_expires + timedelta(days=30)
        assert abs((expires - expected).total_seconds()) < 1

    @pytest.mark.asyncio
    async def test_granted_by_is_passed_to_insert(self):
        from heart.membership.service import activate_or_extend

        captured_params = {}

        async def fake_execute(stmt, params=None):
            if params and "granted_by" in params:
                captured_params.update(params)
            return MagicMock()

        db = AsyncMock()
        # SELECT returns None
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[select_result, AsyncMock()])

        # Patch the second call to capture params
        calls = []
        original_execute = db.execute

        async def tracking_execute(stmt, params=None):
            calls.append(params)
            r = MagicMock()
            r.scalar_one_or_none.return_value = None
            return r

        db.execute = tracking_execute

        await activate_or_extend(db, uuid.uuid4(), "immersive", 30, granted_by="afdian:order123")

        # Second call is the INSERT with granted_by
        insert_params = calls[1]
        assert insert_params["granted_by"] == "afdian:order123"
        assert insert_params["tier"] == "immersive"

    @pytest.mark.asyncio
    async def test_returns_timezone_aware_datetime(self):
        from heart.membership.service import activate_or_extend

        db = AsyncMock()
        select_result = MagicMock()
        select_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(side_effect=[select_result, MagicMock()])

        expires = await activate_or_extend(db, uuid.uuid4(), "plus", 7)
        assert expires.tzinfo is not None


# ---------------------------------------------------------------------------
# GET /api/membership — response shape
# ---------------------------------------------------------------------------


def _make_db_for_membership(expires_at=None, binding_code="TESTCODE1"):
    """Build an AsyncMock db that handles GET /membership queries."""
    db = AsyncMock()

    expires_mock = MagicMock()
    expires_mock.scalar_one_or_none.return_value = expires_at

    binding_mock = MagicMock()
    binding_mock.scalar_one_or_none.return_value = binding_code

    db.execute = AsyncMock(side_effect=[expires_mock, binding_mock])
    db.commit = AsyncMock()
    return db


class TestGetMembershipEndpoint:
    @pytest.mark.asyncio
    async def test_returns_tier_and_entitlements(self):
        from unittest.mock import patch

        from heart.api.routes_membership import get_membership

        current_user = MagicMock()
        current_user.user_id = str(uuid.uuid4())
        db = _make_db_for_membership()

        with patch(
            "heart.api.routes_membership.get_effective_tier", new=AsyncMock(return_value="plus")
        ):
            result = await get_membership(current_user=current_user, db=db)

        assert result["tier"] == "plus"
        assert "grok" in result["entitlements"]["models"]
        assert "claude" not in result["entitlements"]["models"]
        assert "fish" in result["entitlements"]["tts"]
        assert result["monthly_grant"] == 400
        assert "binding_code" in result
        assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_free_tier_has_no_fish(self):
        from unittest.mock import patch

        from heart.api.routes_membership import get_membership

        current_user = MagicMock()
        current_user.user_id = str(uuid.uuid4())
        db = _make_db_for_membership()

        with patch(
            "heart.api.routes_membership.get_effective_tier", new=AsyncMock(return_value="free")
        ):
            result = await get_membership(current_user=current_user, db=db)

        assert result["tier"] == "free"
        assert "grok" not in result["entitlements"]["models"]
        assert "fish" not in result["entitlements"]["tts"]
        assert result["monthly_grant"] == 0

    @pytest.mark.asyncio
    async def test_immersive_tier_has_claude(self):
        from unittest.mock import patch

        from heart.api.routes_membership import get_membership

        current_user = MagicMock()
        current_user.user_id = str(uuid.uuid4())
        db = _make_db_for_membership()

        with patch(
            "heart.api.routes_membership.get_effective_tier",
            new=AsyncMock(return_value="immersive"),
        ):
            result = await get_membership(current_user=current_user, db=db)

        assert "claude" in result["entitlements"]["models"]
        assert result["monthly_grant"] == 800

    @pytest.mark.asyncio
    async def test_free_user_has_null_expires_at(self):
        from unittest.mock import patch

        from heart.api.routes_membership import get_membership

        current_user = MagicMock()
        current_user.user_id = str(uuid.uuid4())
        db = _make_db_for_membership(expires_at=None)

        with patch(
            "heart.api.routes_membership.get_effective_tier", new=AsyncMock(return_value="free")
        ):
            result = await get_membership(current_user=current_user, db=db)

        assert result["expires_at"] is None
