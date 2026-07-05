"""Tests for characters and webhooks API routes.

Tests that require PostgreSQL are skipped when DATABASE_URL is not set.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from heart.api.main import create_app
from heart.core.auth import auth_manager

_has_db = bool(os.environ.get("DATABASE_URL"))

pytestmark = pytest.mark.skipif(not _has_db, reason="requires DATABASE_URL")


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def auth_token():
    token = auth_manager.create_access_token(
        user_id="550e8400-e29b-41d4-a716-446655440000",
        email="test@example.com",
    )
    return token.access_token


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


class TestCharacterSettings:
    def test_get_settings_without_auth(self, client):
        response = client.get("/api/characters/rin/settings")
        assert response.status_code == 401

    def test_patch_settings_without_auth(self, client):
        response = client.patch(
            "/api/characters/rin/settings",
            json={"voice_enabled": True},
        )
        assert response.status_code == 401

    def test_patch_settings_invalid_body(self, client, auth_headers):
        response = client.patch(
            "/api/characters/rin/settings",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestChatHistory:
    def test_history_without_auth(self, client):
        response = client.get("/api/chat/history?character_id=rin")
        assert response.status_code == 401

    def test_history_missing_character_id(self, client, auth_headers):
        response = client.get(
            "/api/chat/history",
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestAfdianWebhook:
    def test_webhook_invalid_json(self, client):
        response = client.post(
            "/api/webhooks/afdian",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in (400, 422)

    def test_webhook_missing_sign(self, client):
        response = client.post(
            "/api/webhooks/afdian",
            json={"data": {"out_trade_no": "test-001"}},
        )
        assert response.status_code in (400, 403)
