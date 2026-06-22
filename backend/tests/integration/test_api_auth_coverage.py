"""Integration tests for API auth coverage (PR-1, H5).

Tests that user-data routes reject:
- No token → 401
- Token user_id ≠ query user_id → 403
- Match → 200
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from heart.core.auth import auth_manager


@pytest.fixture
def token_user_a():
    return auth_manager.create_access_token(user_id="00000000-0000-0000-0000-000000000001")


@pytest.fixture
def token_user_b():
    return auth_manager.create_access_token(user_id="00000000-0000-0000-0000-000000000002")


@pytest.fixture
def headers_a(token_user_a):
    return {"Authorization": f"Bearer {token_user_a.access_token}"}


@pytest.fixture
def headers_b(token_user_b):
    return {"Authorization": f"Bearer {token_user_b.access_token}"}


USER_A = "00000000-0000-0000-0000-000000000001"
USER_B = "00000000-0000-0000-0000-000000000002"


@pytest.fixture
def client():
    from heart.api.main import app
    return TestClient(app)


@pytest.mark.integration
class TestAuthCoverage:

    @pytest.mark.parametrize(
        "method,path_template",
        [
            ("GET", "/api/state/emotion?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/relationship?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/inner?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/recent?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/l4?user_id={uid}&character_id=rin"),
            ("GET", "/api/proactive/pending?user_id={uid}"),
        ],
    )
    def test_no_token_returns_401(self, client, method, path_template):
        url = path_template.format(uid=USER_A)
        resp = client.request(method, url)
        assert resp.status_code == 401, f"{method} {url} returned {resp.status_code}"

    @pytest.mark.parametrize(
        "method,path_template",
        [
            ("GET", "/api/state/emotion?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/relationship?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/inner?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/recent?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/l4?user_id={uid}&character_id=rin"),
            ("GET", "/api/proactive/pending?user_id={uid}"),
        ],
    )
    def test_wrong_uid_returns_403(self, client, headers_a, method, path_template):
        url = path_template.format(uid=USER_B)
        resp = client.request(method, url, headers=headers_a)
        assert resp.status_code == 403, f"{method} {url} returned {resp.status_code}"

    @pytest.mark.parametrize(
        "method,path_template",
        [
            ("GET", "/api/state/emotion?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/relationship?user_id={uid}&character_id=rin"),
            ("GET", "/api/state/inner?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/recent?user_id={uid}&character_id=rin"),
            ("GET", "/api/memory/l4?user_id={uid}&character_id=rin"),
            ("GET", "/api/proactive/pending?user_id={uid}"),
        ],
    )
    def test_matching_uid_returns_200(self, client, headers_a, method, path_template):
        url = path_template.format(uid=USER_A)
        resp = client.request(method, url, headers=headers_a)
        assert resp.status_code == 200, f"{method} {url} returned {resp.status_code}"

    def test_voice_synthesize_no_token_401(self, client):
        resp = client.post(
            "/api/voice/synthesize",
            json={"text": "hello", "character_id": "rin"},
        )
        assert resp.status_code == 401

    def test_voice_synthesize_with_token(self, client, headers_a):
        resp = client.post(
            "/api/voice/synthesize",
            json={"text": "hello", "character_id": "rin"},
            headers=headers_a,
        )
        assert resp.status_code in (200, 503)

    def test_forget_no_token_401(self, client):
        resp = client.post(
            "/api/memory/forget?user_id=00000000-0000-0000-0000-000000000001&memory_id=test",
        )
        assert resp.status_code == 401

    def test_forget_wrong_uid_403(self, client, headers_a):
        resp = client.post(
            f"/api/memory/forget?user_id={USER_B}&memory_id=test",
            headers=headers_a,
        )
        assert resp.status_code == 403
