"""Tests for credits API routes.

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


class TestCreditsBalance:
    def test_balance_without_auth(self, client):
        response = client.get("/api/credits/balance")
        assert response.status_code == 401


class TestCreditsTransactions:
    def test_transactions_without_auth(self, client):
        response = client.get("/api/credits/transactions")
        assert response.status_code == 401


class TestCreditsRedeem:
    def test_redeem_without_auth(self, client):
        response = client.post(
            "/api/credits/redeem",
            json={"code": "ABCDEF123456"},
        )
        assert response.status_code == 401

    def test_redeem_missing_code(self, client, auth_headers):
        response = client.post(
            "/api/credits/redeem",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestCreditsPricing:
    """Pricing endpoint doesn't need auth or DB (no skip needed here)."""

    def test_pricing_returns_tiers(self, client):
        response = client.get("/api/credits/pricing")
        assert response.status_code == 200
        data = response.json()
        # models: deepseek + grok (claude removed 2026-08)
        assert {m["id"] for m in data["models"]} == {"deepseek", "grok"}
        # 3 membership tiers + 4 shop packs
        assert {t["tier"] for t in data["membership_tiers"]} == {
            "free", "plus", "immersive"
        }
        assert len(data["shop"]) == 4


class TestDailyCheckinAuth:
    """DB-gated: only the auth boundary lives here. Mocked check-in *logic*
    tests live in test_pricing_entitlements.py so they run without Postgres.
    """

    def test_checkin_without_auth(self, client):
        # No bearer token → 401 before handler runs.
        response = client.post("/api/credits/checkin")
        assert response.status_code == 401
