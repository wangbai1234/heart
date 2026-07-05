"""Integration tests for rate limiting (PR-3).

Tests that routes return 429 when rate limit is exceeded.
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from heart.core.auth import auth_manager


@pytest.fixture
def client():
    from heart.api.main import app

    return TestClient(app)


@pytest.fixture
def auth_headers():
    token = auth_manager.create_access_token(user_id="00000000-0000-0000-0000-000000000001")
    return {"Authorization": f"Bearer {token.access_token}"}


@pytest.mark.integration
class TestRateLimit:
    def test_login_rate_limit(self, client):
        """Login should enforce 10/minute rate limit."""
        # Send 11 requests rapidly
        responses = []
        for i in range(11):
            resp = client.post(
                "/api/auth/login",
                json={"user_id": f"user-{i}", "email": f"u{i}@test.com"},
            )
            responses.append(resp.status_code)

        # At least one should be 429
        assert 429 in responses, f"Expected 429 in responses: {responses}"

    def test_chat_rate_limit(self, client, auth_headers):
        """Chat should enforce 30/minute rate limit."""
        # Send 31 requests rapidly
        responses = []
        for i in range(31):
            resp = client.post(
                "/api/chat",
                json={
                    "messages": [{"role": "user", "content": f"test {i}"}],
                    "character_id": "rin",
                },
                headers=auth_headers,
            )
            responses.append(resp.status_code)

        assert 429 in responses, f"Expected 429 in responses: {responses}"

    def test_state_routes_rate_limit(self, client, auth_headers):
        """State routes should enforce 60/minute rate limit."""
        # Send 61 requests rapidly
        responses = []
        for i in range(61):
            resp = client.get(
                "/api/state/emotion?user_id=00000000-0000-0000-0000-000000000001&character_id=rin",
                headers=auth_headers,
            )
            responses.append(resp.status_code)

        assert 429 in responses, f"Expected 429 in responses: {responses}"
