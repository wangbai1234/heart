"""
Integration tests for UGC character creation/management (C5a endpoints).

Coverage:
  - POST /api/characters    → create, quota limit
  - PATCH /api/characters/{id}  → edit + version bump
  - PATCH /api/characters/{id}/visibility
  - POST /api/characters/{id}/disable
  - GET /api/characters → is_owner flag
  - is_known_character guard after creation

Requires testcontainers (pip install testcontainers).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from uuid import uuid4

import pytest

try:
    import testcontainers  # noqa: F401
    HAS_TESTCONTAINERS = True
except ImportError:
    HAS_TESTCONTAINERS = False

pytestmark = pytest.mark.asyncio

# ── Minimal draft payload ───────────────────────────────────────────


def _make_draft(name: str = "小雪") -> dict:
    return {
        "display_name": {"zh": name},
        "persona": "小雪是一个温柔善良的女孩，喜欢在深夜和朋友聊星星。她的声音轻柔，说话不紧不慢。",
        "greeting_style": "warm",
        "speech_samples": ["……今天也要加油哦。"],
        "sliders": {
            "warmth": 0.75,
            "talkativeness": 0.5,
            "directness": 0.4,
            "humor": 0.3,
            "playfulness": 0.5,
            "steadiness": 0.6,
        },
        "locale": "zh",
    }


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def postgres_container():
    if not HAS_TESTCONTAINERS:
        pytest.skip("testcontainers not installed")
    from testcontainers.postgres import PostgresContainer

    c = PostgresContainer(
        image="pgvector/pgvector:pg15",
        username="heart",
        password="heart_test",
        dbname="heart_test",
    )
    c.start()
    db_url = c.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
    os.environ["TEST_DATABASE_URL"] = c.get_connection_url()
    os.environ["TEST_ASYNC_DATABASE_URL"] = db_url
    yield c
    c.stop()


@pytest.fixture(scope="module")
def redis_container():
    if not HAS_TESTCONTAINERS:
        pytest.skip("testcontainers not installed")
    from testcontainers.redis import RedisContainer

    c = RedisContainer(image="redis:7-alpine")
    c.start()
    os.environ["TEST_REDIS_URL"] = (
        f"redis://{c.get_container_host_ip()}:{c.get_exposed_port(6379)}"
    )
    yield c
    c.stop()


@pytest.fixture(scope="module")
def setup_db(postgres_container):
    result = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
        env={**os.environ, "DATABASE_URL": os.environ["TEST_ASYNC_DATABASE_URL"]},
    )
    if result.returncode != 0:
        pytest.skip(f"Alembic migration failed: {result.stderr}")

    from sqlalchemy import create_engine
    engine = create_engine(
        os.environ["TEST_DATABASE_URL"].replace("postgresql://", "postgresql+psycopg2://")
    )
    yield engine
    engine.dispose()


@pytest.fixture
def app(setup_db, redis_container):
    os.environ["DATABASE_URL"] = os.environ["TEST_ASYNC_DATABASE_URL"]
    os.environ["REDIS_URL"] = os.environ["TEST_REDIS_URL"]
    os.environ["JWT_ALGORITHM"] = "HS256"
    os.environ["JWT_SECRET_KEY"] = "test-ugc-secret-key-for-integration-123456"
    os.environ["OTP_PEPPER"] = "test-ugc-pepper-integration-123456"
    os.environ["ANTHROPIC_API_KEY"] = "test-fake-key"
    os.environ["SAFETY_ENABLED"] = "false"  # skip LLM safety screen in tests

    from heart.api.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    from fastapi.testclient import TestClient

    return TestClient(app)


def _auth_headers(user_id: str | None = None, email: str = "ugc@test.com") -> dict:
    from heart.core.auth import auth_manager

    uid = user_id or str(uuid4())
    token = auth_manager.create_access_token(user_id=uid, email=email)
    return {"Authorization": f"Bearer {token.access_token}"}, uid


# ── Tests ────────────────────────────────────────────────────────────


class TestUGCCharacterCreate:
    def test_create_character_returns_id_and_name(self, client):
        headers, _ = _auth_headers()
        resp = client.post("/api/characters", json=_make_draft("小雪"), headers=headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "id" in data
        assert data["display_name"] == "小雪"
        assert data["visibility"] == "private"
        assert data["spec_version"]

    def test_created_character_appears_in_catalog(self, client):
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("明月"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        catalog_resp = client.get("/api/characters", headers=headers)
        assert catalog_resp.status_code == 200, catalog_resp.text
        ids = [c["id"] for c in catalog_resp.json()["characters"]]
        assert char_id in ids

    def test_created_character_is_owner_true(self, client):
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("夏树"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        catalog_resp = client.get("/api/characters", headers=headers)
        chars = catalog_resp.json()["characters"]
        char_entry = next((c for c in chars if c["id"] == char_id), None)
        assert char_entry is not None
        assert char_entry["is_owner"] is True

    def test_builtin_characters_is_owner_false(self, client):
        headers, _ = _auth_headers()
        catalog_resp = client.get("/api/characters", headers=headers)
        chars = catalog_resp.json()["characters"]
        for c in chars:
            if c.get("is_builtin"):
                assert c["is_owner"] is False

    def test_quota_limit_enforced(self, client):
        """Creating more than 5 UGC characters per user should fail."""
        headers, _ = _auth_headers()
        for i in range(5):
            resp = client.post("/api/characters", json=_make_draft(f"测试角色{i}"), headers=headers)
            assert resp.status_code == 200, f"Failed to create char {i}: {resp.text}"
        over_limit = client.post("/api/characters", json=_make_draft("超额角色"), headers=headers)
        assert over_limit.status_code == 422
        assert "最多创建" in over_limit.json()["detail"]

    def test_create_without_auth_returns_401(self, client):
        resp = client.post("/api/characters", json=_make_draft())
        assert resp.status_code == 401

    def test_persona_too_short_returns_422(self, client):
        headers, _ = _auth_headers()
        short_draft = _make_draft()
        short_draft["persona"] = "太短"  # < 20 chars
        resp = client.post("/api/characters", json=short_draft, headers=headers)
        assert resp.status_code == 422


class TestUGCCharacterEdit:
    def test_edit_bumps_spec_version(self, client):
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("初版角色"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]
        v1 = create_resp.json()["spec_version"]

        edit_resp = client.patch(
            f"/api/characters/{char_id}",
            json=_make_draft("修改版角色"),
            headers=headers,
        )
        assert edit_resp.status_code == 200, edit_resp.text
        v2 = edit_resp.json()["spec_version"]
        assert v2 != v1  # version must bump

    def test_non_owner_edit_returns_403(self, client):
        owner_headers, _ = _auth_headers()
        other_headers, _ = _auth_headers()

        create_resp = client.post("/api/characters", json=_make_draft("私有角色"), headers=owner_headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/characters/{char_id}", json=_make_draft("入侵修改"), headers=other_headers
        )
        assert resp.status_code == 403

    def test_builtin_character_edit_returns_403(self, client):
        headers, _ = _auth_headers()
        resp = client.patch("/api/characters/rin", json=_make_draft(), headers=headers)
        assert resp.status_code == 403


class TestUGCCharacterVisibility:
    def test_set_visibility_to_unlisted(self, client):
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("可见角色"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/characters/{char_id}/visibility",
            json={"visibility": "unlisted"},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["visibility"] == "unlisted"

    def test_non_owner_visibility_change_returns_403(self, client):
        owner_headers, _ = _auth_headers()
        other_headers, _ = _auth_headers()

        create_resp = client.post("/api/characters", json=_make_draft("私有角色B"), headers=owner_headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        resp = client.patch(
            f"/api/characters/{char_id}/visibility",
            json={"visibility": "public"},
            headers=other_headers,
        )
        assert resp.status_code == 403


class TestUGCCharacterDisable:
    def test_disable_hides_from_catalog(self, client):
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("待停用角色"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        disable_resp = client.post(f"/api/characters/{char_id}/disable", headers=headers)
        assert disable_resp.status_code == 200, disable_resp.text
        assert disable_resp.json()["status"] in ("disabled", "inactive", "hidden")

        # Should not appear in catalog (or appear with disabled status)
        catalog_resp = client.get("/api/characters", headers=headers)
        active_ids = [
            c["id"]
            for c in catalog_resp.json()["characters"]
            if c.get("status") != "disabled"
        ]
        assert char_id not in active_ids

    def test_non_owner_disable_returns_403(self, client):
        owner_headers, _ = _auth_headers()
        other_headers, _ = _auth_headers()

        create_resp = client.post("/api/characters", json=_make_draft("被保护角色"), headers=owner_headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        resp = client.post(f"/api/characters/{char_id}/disable", headers=other_headers)
        assert resp.status_code == 403


class TestUGCCharacterRegistry:
    def test_new_character_is_known_after_creation(self, client):
        """After creation, is_known_character must return True (registry hot-loaded)."""
        headers, _ = _auth_headers()
        create_resp = client.post("/api/characters", json=_make_draft("注册测试"), headers=headers)
        assert create_resp.status_code == 200, create_resp.text
        char_id = create_resp.json()["id"]

        from heart.ss01_soul.character_catalog import is_known_character

        assert is_known_character(char_id), (
            f"Character {char_id} not found in registry after creation"
        )
