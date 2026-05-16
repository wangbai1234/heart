"""Tests for Echo Chat endpoint."""

import pytest
from fastapi.testclient import TestClient
from heart.api.main import create_app
from heart.core.auth import auth_manager


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create a valid auth token for testing."""
    token = auth_manager.create_access_token(
        user_id="test-user",
        email="test@example.com",
    )
    return token.access_token


class TestAuthEndpoints:
    """Tests for authentication endpoints."""

    def test_login(self, client):
        """Test user login endpoint."""
        response = client.post(
            "/api/auth/login",
            json={
                "user_id": "new-user-123",
                "email": "newuser@example.com",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_without_email(self, client):
        """Test login without email."""
        response = client.post(
            "/api/auth/login",
            json={"user_id": "user-no-email"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_verify_valid_token(self, client, auth_token):
        """Test token verification with valid token."""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "test-user"
        assert data["email"] == "test@example.com"
        assert data["valid"] is True

    def test_verify_invalid_token(self, client):
        """Test token verification with invalid token."""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401  # HTTPException from auth verification

    def test_verify_missing_token(self, client):
        """Test token verification without token."""
        response = client.get("/api/auth/verify")

        assert response.status_code == 403

    def test_refresh_token(self, client, auth_token):
        """Test token refresh endpoint."""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        # Refreshed token is valid
        verify_response = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {data['access_token']}"},
        )
        assert verify_response.status_code == 200


class TestEchoChatEndpoint:
    """Tests for echo chat endpoint."""

    def test_echo_chat_success(self, client, auth_token):
        """Test successful echo chat request."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "user", "content": "Hello, how are you?"},
                    {"role": "assistant", "content": "I'm doing well!"},
                    {"role": "user", "content": "That's great!"},
                ],
                "character_id": "rin",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "That's great!" in data["response"]
        assert data["character_id"] == "rin"
        assert "message_id" in data

    def test_echo_chat_different_character(self, client, auth_token):
        """Test echo chat with different character."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "user", "content": "Hello Dorothy"},
                ],
                "character_id": "dorothy",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "dorothy" in data["response"].lower()
        assert data["character_id"] == "dorothy"

    def test_echo_chat_no_user_message(self, client, auth_token):
        """Test echo chat with no user message."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "assistant", "content": "Hello there!"},
                ],
                "character_id": "default",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert "user message" in data["detail"].lower()

    def test_echo_chat_empty_messages(self, client, auth_token):
        """Test echo chat with empty messages list."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [],
                "character_id": "default",
            },
        )

        assert response.status_code == 400

    def test_echo_chat_without_auth(self, client):
        """Test echo chat without authentication."""
        response = client.post(
            "/api/chat/echo",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"},
                ],
                "character_id": "default",
            },
        )

        assert response.status_code == 403

    def test_echo_chat_multiple_user_messages(self, client, auth_token):
        """Test echo chat returns last user message."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "user", "content": "First message"},
                    {"role": "assistant", "content": "Response"},
                    {"role": "user", "content": "Second message"},
                    {"role": "assistant", "content": "Another response"},
                    {"role": "user", "content": "Final message"},
                ],
                "character_id": "test",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "Final message" in data["response"]
        # Should not contain earlier messages
        assert "First message" not in data["response"]

    def test_echo_chat_returns_unique_message_id(self, client, auth_token):
        """Test echo chat returns unique message IDs."""
        message_ids = set()

        for i in range(5):
            response = client.post(
                "/api/chat/echo",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "messages": [
                        {"role": "user", "content": f"Message {i}"},
                    ],
                    "character_id": "default",
                },
            )

            assert response.status_code == 200
            data = response.json()
            message_ids.add(data["message_id"])

        # All message IDs should be unique
        assert len(message_ids) == 5

    def test_echo_chat_default_character(self, client, auth_token):
        """Test echo chat with default character."""
        response = client.post(
            "/api/chat/echo",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "messages": [
                    {"role": "user", "content": "Testing default"},
                ],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["character_id"] == "default"
