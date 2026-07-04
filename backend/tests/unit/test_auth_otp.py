"""Tests for OTP authentication routes.

Tests that require PostgreSQL are skipped when DATABASE_URL is not set.
Run with DATABASE_URL set to execute all tests.
"""

from __future__ import annotations

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestOtpRequest:
    """Tests for POST /api/auth/otp/request."""

    def test_request_otp_invalid_email(self, client):
        response = client.post(
            "/api/auth/otp/request",
            json={"email": "not-an-email"},
        )
        assert response.status_code == 422

    def test_request_otp_missing_email(self, client):
        response = client.post(
            "/api/auth/otp/request",
            json={},
        )
        assert response.status_code == 422


class TestOtpVerify:
    """Tests for POST /api/auth/otp/verify."""

    def test_verify_missing_code(self, client):
        response = client.post(
            "/api/auth/otp/verify",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422


class TestRefreshToken:
    """Tests for POST /api/auth/refresh."""

    def test_refresh_missing_body(self, client):
        response = client.post("/api/auth/refresh")
        assert response.status_code == 422


class TestLogout:
    """Tests for POST /api/auth/logout."""

    def test_logout_without_auth(self, client):
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": "some-token"},
        )
        assert response.status_code == 401

    def test_logout_with_auth(self, client, auth_token):
        response = client.post(
            "/api/auth/logout",
            json={"refresh_token": "some-token"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert response.status_code == 200
        assert response.json()["ok"] is True


class TestGetMe:
    """Tests for GET /api/auth/me."""

    def test_me_without_auth(self, client):
        response = client.get("/api/auth/me")
        assert response.status_code == 401
