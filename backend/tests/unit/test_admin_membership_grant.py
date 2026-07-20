"""Unit tests for admin manual membership upgrade — POST /api/admin/membership/grant."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


def _db_returning_user(user_id: uuid.UUID, email: str = "u@example.com"):
    """AsyncMock db whose first execute resolves a live user row."""
    db = AsyncMock()
    row = MagicMock()
    row.mappings.return_value.first.return_value = {"id": user_id, "email": email}
    db.execute = AsyncMock(return_value=row)
    return db


def _db_no_user():
    db = AsyncMock()
    row = MagicMock()
    row.mappings.return_value.first.return_value = None
    db.execute = AsyncMock(return_value=row)
    return db


class TestAdminGrantMembership:
    @pytest.mark.asyncio
    async def test_grants_plus_by_user_id(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        uid = uuid.uuid4()
        db = _db_returning_user(uid, "plus@example.com")
        new_expires = datetime.now(tz=timezone.utc) + timedelta(days=30)

        body = GrantMembershipRequest(user_id=str(uid), tier="plus", days=30)
        with patch(
            "heart.api.routes_admin.activate_or_extend",
            new=AsyncMock(return_value=new_expires),
        ) as mock_activate:
            result = await admin_grant_membership(body=body, _=None, db=db)

        assert result.ok is True
        assert result.tier == "plus"
        assert result.user_id == str(uid)
        assert result.email == "plus@example.com"
        assert result.expires_at == new_expires.isoformat()
        # tier + days threaded through to the service
        call_args = mock_activate.call_args
        assert call_args.args[1] == uid
        assert call_args.args[2] == "plus"
        assert call_args.args[3] == 30

    @pytest.mark.asyncio
    async def test_grants_immersive_by_email(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        uid = uuid.uuid4()
        db = _db_returning_user(uid)
        new_expires = datetime.now(tz=timezone.utc) + timedelta(days=90)

        body = GrantMembershipRequest(email="Immersive@Example.com", tier="immersive", days=90)
        with patch(
            "heart.api.routes_admin.activate_or_extend",
            new=AsyncMock(return_value=new_expires),
        ) as mock_activate:
            result = await admin_grant_membership(body=body, _=None, db=db)

        assert result.tier == "immersive"
        assert mock_activate.call_args.args[2] == "immersive"
        assert mock_activate.call_args.args[3] == 90

    @pytest.mark.asyncio
    async def test_default_days_is_30(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        uid = uuid.uuid4()
        db = _db_returning_user(uid)
        with patch(
            "heart.api.routes_admin.activate_or_extend",
            new=AsyncMock(return_value=datetime.now(tz=timezone.utc)),
        ) as mock_activate:
            body = GrantMembershipRequest(user_id=str(uid), tier="plus")
            await admin_grant_membership(body=body, _=None, db=db)

        assert mock_activate.call_args.args[3] == 30

    @pytest.mark.asyncio
    async def test_rejects_free_tier(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        db = _db_returning_user(uuid.uuid4())
        body = GrantMembershipRequest(user_id=str(uuid.uuid4()), tier="free")
        with pytest.raises(HTTPException) as exc:
            await admin_grant_membership(body=body, _=None, db=db)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_rejects_unknown_tier(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        db = _db_returning_user(uuid.uuid4())
        body = GrantMembershipRequest(user_id=str(uuid.uuid4()), tier="platinum")
        with pytest.raises(HTTPException) as exc:
            await admin_grant_membership(body=body, _=None, db=db)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_tier_is_case_insensitive(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        uid = uuid.uuid4()
        db = _db_returning_user(uid)
        with patch(
            "heart.api.routes_admin.activate_or_extend",
            new=AsyncMock(return_value=datetime.now(tz=timezone.utc)),
        ) as mock_activate:
            body = GrantMembershipRequest(user_id=str(uid), tier="PLUS")
            result = await admin_grant_membership(body=body, _=None, db=db)

        assert result.tier == "plus"
        assert mock_activate.call_args.args[2] == "plus"

    @pytest.mark.asyncio
    async def test_missing_user_returns_404(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        db = _db_no_user()
        body = GrantMembershipRequest(email="ghost@example.com", tier="plus")
        with pytest.raises(HTTPException) as exc:
            await admin_grant_membership(body=body, _=None, db=db)
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_requires_user_id_or_email(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        db = AsyncMock()
        body = GrantMembershipRequest(tier="plus")
        with pytest.raises(HTTPException) as exc:
            await admin_grant_membership(body=body, _=None, db=db)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_bad_user_id_format_returns_422(self):
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        db = AsyncMock()
        body = GrantMembershipRequest(user_id="not-a-uuid", tier="immersive")
        with pytest.raises(HTTPException) as exc:
            await admin_grant_membership(body=body, _=None, db=db)
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_granted_by_is_unique_per_call(self):
        """activate_or_extend derives its coin-grant idempotency key from
        granted_by; two admin grants must not collide (else renewal coins vanish)."""
        from heart.api.routes_admin import GrantMembershipRequest, admin_grant_membership

        uid = uuid.uuid4()
        seen: list[str] = []

        async def capture(db, user_id, tier, days, granted_by="manual"):
            seen.append(granted_by)
            return datetime.now(tz=timezone.utc)

        with patch("heart.api.routes_admin.activate_or_extend", new=capture):
            for _ in range(2):
                db = _db_returning_user(uid)
                body = GrantMembershipRequest(user_id=str(uid), tier="plus")
                await admin_grant_membership(body=body, _=None, db=db)

        assert len(seen) == 2
        assert seen[0] != seen[1]
        assert all(g.startswith("admin:") for g in seen)
