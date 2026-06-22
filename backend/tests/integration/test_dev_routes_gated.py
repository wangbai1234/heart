"""Integration tests for debug route gating (PR-2, H5 debug sub-item).

Tests that /api/profile/* returns 404 when HEART_DEV_MODE=false,
and 200 when HEART_DEV_MODE=true.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client():
    from heart.api.main import app
    return TestClient(app)


@pytest.mark.integration
class TestDevRoutesGated:

    def test_profile_records_default_404(self, client):
        """Without HEART_DEV_MODE=true, /api/profile/records should 404."""
        resp = client.get("/api/profile/records")
        assert resp.status_code == 404

    def test_profile_reset_default_404(self, client):
        """Without HEART_DEV_MODE=true, /api/profile/reset should 404."""
        resp = client.post("/api/profile/reset")
        assert resp.status_code == 404

    @patch.dict(os.environ, {"HEART_DEV_MODE": "true"}, clear=False)
    def test_profile_records_enabled_200(self):
        """With HEART_DEV_MODE=true, /api/profile/records should 200."""
        from heart.api.routes import dev_router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(dev_router, prefix="/api/profile")
        with TestClient(app) as c:
            resp = c.get("/api/profile/records")
            assert resp.status_code == 200
