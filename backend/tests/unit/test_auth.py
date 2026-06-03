"""Tests for JWT authentication module."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException, status

from heart.core.auth import AuthManager, Token, TokenData


@pytest.fixture
def auth_manager_instance():
    """Create auth manager instance for testing."""
    return AuthManager(
        secret_key="test-secret-key",
        algorithm="HS256",
        expire_minutes=60,
    )


class TestAuthManager:
    """Tests for AuthManager class."""

    def test_create_access_token(self, auth_manager_instance):
        """Test token creation."""
        token = auth_manager_instance.create_access_token(
            user_id="test-user-123",
            email="test@example.com",
        )

        assert isinstance(token, Token)
        assert token.token_type == "bearer"
        assert token.access_token is not None
        assert token.expires_in == 60 * 60  # 60 minutes in seconds

    def test_verify_valid_token(self, auth_manager_instance):
        """Test token verification with valid token."""
        # Create token
        token = auth_manager_instance.create_access_token(
            user_id="test-user-456",
            email="user@example.com",
        )

        # Verify token
        token_data = auth_manager_instance.verify_token(token.access_token)

        assert isinstance(token_data, TokenData)
        assert token_data.user_id == "test-user-456"
        assert token_data.email == "user@example.com"

    def test_verify_invalid_token(self, auth_manager_instance):
        """Test token verification with invalid token."""
        with pytest.raises(HTTPException) as exc_info:
            auth_manager_instance.verify_token("invalid-token-string")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_expired_token(self):
        """Test token verification with expired token."""
        auth_manager = AuthManager(
            secret_key="test-secret",
            algorithm="HS256",
            expire_minutes=-1,  # Already expired
        )

        token = auth_manager.create_access_token(
            user_id="test-user",
            email="test@example.com",
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_manager.verify_token(token.access_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in exc_info.value.detail.lower()

    def test_verify_token_missing_user_id(self, auth_manager_instance):
        """Test token verification when user_id is missing."""
        # Create malformed token without user_id
        payload = {
            "email": "test@example.com",
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=60)).timestamp()),
        }
        invalid_token = jwt.encode(
            payload,
            auth_manager_instance.secret_key,
            algorithm=auth_manager_instance.algorithm,
        )

        with pytest.raises(HTTPException) as exc_info:
            auth_manager_instance.verify_token(invalid_token)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, auth_manager_instance):
        """Test token refresh."""
        import time

        # Create token
        original_token = auth_manager_instance.create_access_token(
            user_id="test-user-789",
            email="refresh@example.com",
        )

        # Wait to ensure different iat
        time.sleep(0.01)

        # Refresh token
        refreshed_token = auth_manager_instance.refresh_token(original_token.access_token)

        assert isinstance(refreshed_token, Token)
        assert refreshed_token.token_type == "bearer"

        # Verify refreshed token is valid and has same user_id
        token_data = auth_manager_instance.verify_token(refreshed_token.access_token)
        assert token_data.user_id == "test-user-789"
        assert token_data.email == "refresh@example.com"

    def test_token_payload_structure(self, auth_manager_instance):
        """Test token payload contains expected fields."""
        token = auth_manager_instance.create_access_token(
            user_id="payload-test",
            email="payload@test.com",
        )

        # Decode without verification to inspect payload
        payload = jwt.decode(
            token.access_token,
            auth_manager_instance.secret_key,
            algorithms=[auth_manager_instance.algorithm],
        )

        assert "sub" in payload
        assert "email" in payload
        assert "exp" in payload
        assert "iat" in payload
        assert payload["sub"] == "payload-test"
        assert payload["email"] == "payload@test.com"

    def test_multiple_tokens_are_different(self, auth_manager_instance):
        """Test that multiple token creations produce valid tokens."""
        import time

        token1 = auth_manager_instance.create_access_token(user_id="user1")
        # Wait to ensure different iat timestamp
        time.sleep(1.01)
        token2 = auth_manager_instance.create_access_token(user_id="user1")

        # Both tokens should be valid
        data1 = auth_manager_instance.verify_token(token1.access_token)
        data2 = auth_manager_instance.verify_token(token2.access_token)

        assert data1.user_id == "user1"
        assert data2.user_id == "user1"
        # Tokens may have different iat if created > 1 second apart
        assert token1.access_token != token2.access_token

    def test_different_users_different_tokens(self, auth_manager_instance):
        """Test that different users produce different tokens."""
        token1 = auth_manager_instance.create_access_token(user_id="user1")
        token2 = auth_manager_instance.create_access_token(user_id="user2")

        assert token1.access_token != token2.access_token

        # Verify they decode to different user IDs
        data1 = auth_manager_instance.verify_token(token1.access_token)
        data2 = auth_manager_instance.verify_token(token2.access_token)

        assert data1.user_id == "user1"
        assert data2.user_id == "user2"
