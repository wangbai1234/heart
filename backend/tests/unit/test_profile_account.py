"""Tests for profile and account API routes.

Tests that require PostgreSQL are skipped when DATABASE_URL is not set.
"""

from __future__ import annotations

import io
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


class TestProfileGet:
    def test_profile_without_auth(self, client):
        response = client.get("/api/profile")
        assert response.status_code == 401


class TestProfileUpdate:
    def test_update_without_auth(self, client):
        response = client.patch(
            "/api/profile",
            json={"display_name": "New Name"},
        )
        assert response.status_code == 401

    def test_update_empty_body(self, client, auth_headers):
        response = client.patch(
            "/api/profile",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "No fields" in response.json()["detail"]

    def test_update_invalid_gender(self, client, auth_headers):
        response = client.patch(
            "/api/profile",
            json={"gender": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestProfileAvatar:
    def test_avatar_without_auth(self, client):
        response = client.post("/api/profile/avatar")
        assert response.status_code == 401

    def test_avatar_invalid_type(self, client, auth_headers):
        files = {"file": ("test.txt", io.BytesIO(b"test"), "text/plain")}
        response = client.post(
            "/api/profile/avatar",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "jpg/png/webp" in response.json()["detail"]

    def test_avatar_too_large(self, client, auth_headers):
        large_data = b"x" * (6 * 1024 * 1024)
        files = {"file": ("test.jpg", io.BytesIO(large_data), "image/jpeg")}
        response = client.post(
            "/api/profile/avatar",
            files=files,
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestAccountDelete:
    def test_delete_without_auth(self, client):
        response = client.post(
            "/api/account/delete",
            json={"confirm": "test@example.com"},
        )
        assert response.status_code == 401


class TestAccountExport:
    def test_export_without_auth(self, client):
        response = client.post("/api/account/export")
        assert response.status_code == 401


class TestAccountClearConversations:
    def test_clear_without_auth(self, client):
        response = client.post("/api/account/clear-conversations")
        assert response.status_code == 401
