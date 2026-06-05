"""
Integration: State-inspect API endpoints.

Verifies T3-01: All state-inspect endpoints return correct structure.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from heart.api.main import create_app


@pytest.fixture
def client():
    """Create test client."""
    app = create_app()
    return TestClient(app)


class TestStateInspectAPI:
    """Verify state-inspect API endpoints."""

    def test_emotion_endpoint_structure(self, client):
        """GET /api/state/emotion should return emotion state."""
        user_id = str(uuid4())
        response = client.get(f"/api/state/emotion?user_id={user_id}&character_id=rin")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "character_id" in data
        assert "vad" in data

    def test_relationship_endpoint_structure(self, client):
        """GET /api/state/relationship should return relationship state."""
        user_id = str(uuid4())
        response = client.get(f"/api/state/relationship?user_id={user_id}&character_id=rin")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "character_id" in data

    def test_inner_endpoint_structure(self, client):
        """GET /api/state/inner should return inner state."""
        user_id = str(uuid4())
        response = client.get(f"/api/state/inner?user_id={user_id}&character_id=rin")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "character_id" in data
        assert "mood" in data
        assert "energy" in data

    def test_proactive_endpoint_structure(self, client):
        """GET /api/proactive/pending should return messages."""
        user_id = str(uuid4())
        response = client.get(f"/api/proactive/pending?user_id={user_id}")
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert "count" in data
        assert "messages" in data

    def test_dev_endpoints_require_dev_mode(self, client):
        """Dev endpoints should require HEART_DEV_MODE=true."""
        user_id = str(uuid4())
        response = client.post(f"/api/dev/jump_phase?user_id={user_id}&character_id=rin&phase=4")
        assert response.status_code == 200
        data = response.json()
        assert "error" in data  # Should error without dev mode
