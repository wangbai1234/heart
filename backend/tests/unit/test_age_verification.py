"""Tests for server-side age verification gate (Phase 2).

Verifies that the require_age_verified dependency correctly rejects
unverified users and passes verified ones.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from heart.api.deps import require_age_verified
from heart.core.auth import TokenData, auth_manager

pytestmark = pytest.mark.asyncio


def _make_token(user_id: str = None) -> str:
    """Create a valid JWT for testing."""
    uid = user_id or str(uuid.uuid4())
    token = auth_manager.create_access_token(user_id=uid, email="test@example.com")
    return token.access_token


class TestRequireAgeVerified:
    """Test the require_age_verified dependency directly."""

    async def test_verified_user_passes(self):
        """User with age_verified_at set → returns TokenData."""
        uid = uuid.uuid4()
        user = TokenData(user_id=str(uid), email="test@test.com")
        mock_age = datetime(2000, 1, 1, tzinfo=timezone.utc)

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_age
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("heart.api.deps._get_engine", return_value=MagicMock()):
            with patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_ctx):
                result = await require_age_verified(current_user=user)
                assert result.user_id == str(uid)

    async def test_unverified_user_rejected(self):
        """User with age_verified_at = NULL → raises 403."""
        uid = uuid.uuid4()
        user = TokenData(user_id=str(uid), email="test@test.com")

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_db)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)

        with patch("heart.api.deps._get_engine", return_value=MagicMock()):
            with patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_ctx):
                from fastapi import HTTPException

                with pytest.raises(HTTPException) as exc_info:
                    await require_age_verified(current_user=user)
                assert exc_info.value.status_code == 403
                assert exc_info.value.detail == "age_verification_required"


class TestAgeGateEndpointRegistration:
    """Test that age gate is wired to the correct endpoints via app routes."""

    def test_app_routes_have_age_gate(self):
        """Inspect the full app to verify require_age_verified is in the dependency chain."""
        from heart.api.main import create_app

        app = create_app()

        # Collect routes that use require_age_verified
        gated_paths = set()
        for route in app.routes:
            if hasattr(route, "dependant"):
                for dep in route.dependant.dependencies:
                    if hasattr(dep, "call") and getattr(dep.call, "__name__", "") == "require_age_verified":
                        gated_paths.add(route.path)

        # These should be gated
        assert "/api/chat" in gated_paths, f"REST /api/chat not gated. Gated: {gated_paths}"
        assert "/api/voice/synthesize" in gated_paths, f"Voice synthesize not gated. Gated: {gated_paths}"
        assert "/api/credits/redeem" in gated_paths, f"Redeem not gated. Gated: {gated_paths}"

        # These should NOT be gated
        assert "/api/credits/balance" not in gated_paths
        assert "/api/credits/pricing" not in gated_paths
        assert "/api/credits/transactions" not in gated_paths
