"""Tests for Echo Chat endpoint."""

from unittest import mock

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
        user_id="550e8400-e29b-41d4-a716-446655440000",
        email="test@example.com",
    )
    return token.access_token


class TestAuthEndpoints:
    """Tests for authentication endpoints.

    Note: /api/auth/login, /api/auth/verify, /api/auth/refresh are now
    dev-only stubs (gated behind HEART_DEV_MODE=true). The real auth
    endpoints are /api/auth/otp/request, /api/auth/otp/verify, etc.
    """

    def test_login_dev_only(self, client):
        """Test that login stub is not available in production mode."""
        response = client.post(
            "/api/auth/login",
            json={
                "user_id": "new-user-123",
                "email": "newuser@example.com",
            },
        )
        # Dev stub not registered without HEART_DEV_MODE
        assert response.status_code == 404

    def test_verify_endpoint_removed(self, client, auth_token):
        """Test that /auth/verify endpoint is removed (replaced by /auth/me)."""
        response = client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 404

    def test_verify_missing_token(self, client):
        """Test auth endpoint without token returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_refresh_requires_body(self, client, auth_token):
        """Test that refresh endpoint requires refresh_token in body."""
        response = client.post(
            "/api/auth/refresh",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        # 422 = missing required body field
        assert response.status_code == 422


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

        assert response.status_code == 401

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
        with mock.patch("heart.api.routes.get_current_user", return_value=auth_token):
            response = client.post(
                "/api/chat/echo",
                json={
                    "messages": [{"role": "user", "content": "Testing default"}],
                },
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["character_id"] == "rin"
