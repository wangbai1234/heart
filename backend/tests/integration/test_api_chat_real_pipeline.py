"""
Integration: /api/auth/login + /api/chat full HTTP pipeline against real PG + Fake LLM.

This test closes two coverage gaps left by the rest of the suite:

1.  **HTTP layer is never exercised elsewhere.**
    `tests/live/test_real_turn_full_wiring.py` constructs `ComposerService(...)` by hand,
    completely bypassing FastAPI's router, middleware, dependency injection, and JWT auth.
    `tests/integration/test_orchestrator_session_flow.py` runs against `AsyncMock(db)` so the
    DB is never actually touched. No other test sends an HTTP request into the real ASGI app.
    Result: a regression in routing, auth, CORS, request validation, or response serialization
    is invisible to the suite.

2.  **Real PG + Real HTTP + Fake LLM is never combined.**
    Tier B mocks the LLM but never drives HTTP.
    Tier C (live) mocks the DB (`MemoryService(db_session=None)`) and constructs services by hand.
    Nothing in the middle ever proves that login → chat actually writes a `sessions` row.

This file plugs that gap. One test (`test_full_pipeline_login_chat_writes_session_row`)
covers ~80% of the practical "real path" risk:

    httpx.AsyncClient(ASGITransport(app))     ← real ASGI app, real middleware, real auth
        → /api/auth/login                     ← real JWT issuance
        → /api/chat (Bearer …)                ← real route + dep injection + JWT verify
            → Orchestrator.handle_turn        ← real safety + composer + cold-path tasks
                → SessionManager (real PG)    ← INSERT + UPDATE on `sessions`
                → ComposerService             ← real composition
                    → FakeModelRouter         ← deterministic, no API cost
    → psycopg2 SELECT on `sessions`           ← asserts side-effect

Markers
-------
- ``integration``: runs in Tier B (real PG, fake LLM).
- The module-level ``pytest.importorskip("testcontainers")`` skips cleanly on machines
  without Docker / testcontainers; in CI this is exactly the same gate the rest of
  Tier B uses (see `tests/integration/conftest.py`).

How to run
----------
    pip install testcontainers
    pytest backend/tests/integration/test_api_chat_real_pipeline.py -v

Or, against an externally-managed Postgres (e.g. the docker-compose ``heart-postgres``)::

    HEART_TEST_PG_URL=postgresql+asyncpg://heart:heartdev@localhost:5432/heart \
        pytest backend/tests/integration/test_api_chat_real_pipeline.py -v

The override DB is assumed to already have ``alembic upgrade head`` applied.

Notes
-----
- The fake LLM is an in-test stub (`_FakeModelRouter`) — not `FakeLLMProvider`,
  because the latter requires a pre-hashed prompt/response fixture that we don't
  control through the full Composer pipeline. The stub honors the
  ModelRouter.call_main contract and returns a deterministic response.
- `_cold_path_memory_encode` currently always uses `MemoryService(db_session=None)`
  (see `heart/ss07_orchestration/orchestrator.py:342`), so memory rows are NOT
  written in the present hot path. This test therefore asserts the `sessions`
  row write, which IS the DB side-effect that does happen end-to-end. When
  cold-path memory encoding gains real DB writes, extend the assertion block here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Iterator
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

# ─── Ensure backend on sys.path (mirrors live/conftest.py pattern) ───
_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

# ─── Make the JWT validator happy *before* heart imports ─────────────
# Settings.validate_jwt_secret() rejects keys shorter than 32 chars. The repo .env
# already ships a valid one, but we use setdefault so this file is also runnable
# in environments where .env is absent (e.g. CI without a mounted .env file).
os.environ.setdefault(
    "JWT_SECRET_KEY",
    "integration-test-jwt-secret-must-be-at-least-32-chars-do-not-use-in-prod",
)

# ─── Module-level skip if there's no way to reach a real Postgres ────
# Either testcontainers must be installed, *or* HEART_TEST_PG_URL must point
# at an externally-managed, already-migrated Postgres.
if not os.environ.get("HEART_TEST_PG_URL"):
    try:
        import testcontainers  # noqa: F401
    except ImportError:
        pytest.skip(
            "testcontainers not installed and HEART_TEST_PG_URL not set",
            allow_module_level=True,
        )
pytestmark = pytest.mark.integration


# ─── Fake LLM router ─────────────────────────────────────────────────


class _FakeModelRouter:
    """In-test stub that honors the `ModelRouter` interface ComposerService consumes.

    Why not `heart.infra.llm_providers.fake.FakeLLMProvider`?
        FakeLLMProvider does a SHA-256 hash on (system_prompt, user_msg) and raises
        ``KeyError`` on any miss. The system prompt that ComposerService assembles
        through the full pipeline (Soul + Memory + Emotion + Relationship + Inner
        State) does not match any pre-recorded fixture. The point of THIS test is to
        exercise the end-to-end pipeline, so we use a stub that returns a deterministic
        response regardless of the prompt.
    """

    config: Any = None  # ComposerService sometimes does `getattr(router, "config", None)`

    async def call_main(
        self,
        *,
        messages: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 2000,
        agent_name: str = "",
    ) -> str:
        last_user = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        return f"[fake-llm:{agent_name}] echo={last_user[:64]}"

    async def stream_main(self, **kwargs: Any) -> AsyncIterator[str]:
        text = await self.call_main(**kwargs)
        for word in text.split():
            yield word + " "


# ─── Postgres testcontainer + alembic migrations ─────────────────────


@pytest.fixture(scope="module")
def migrated_pg_url() -> Iterator[str]:
    """Yield an asyncpg URL pointing at a freshly-migrated Postgres.

    Default path: start a pgvector-enabled Postgres testcontainer, run
    ``alembic upgrade head`` against it. Module-scope so the container +
    migration cost is paid once for this file.

    Escape hatch: if ``HEART_TEST_PG_URL`` is set (e.g. ``postgresql+asyncpg://
    user:pw@host:5432/db``), use that instead. The DB is assumed to be already
    migrated. This is useful on dev hosts where testcontainers networking is
    broken (e.g. some Colima configurations that don't forward container ports).
    """
    override = os.environ.get("HEART_TEST_PG_URL")
    if override:
        yield override
        return

    from testcontainers.postgres import PostgresContainer

    container = PostgresContainer(
        image="pgvector/pgvector:pg15",
        username="heart",
        password="heart_test",
        dbname="heart_test",
    )
    container.start()
    try:
        # Different testcontainers versions return either ``postgresql://`` or
        # ``postgresql+psycopg2://`` here, so normalise both into the asyncpg URL
        # alembic/SQLAlchemy actually needs.
        sync_url = container.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
            "postgresql+pg8000://", "postgresql+asyncpg://"
        )
        if not async_url.startswith("postgresql+asyncpg://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # The alembic env.py reads DATABASE_URL from os.environ.
        prior_db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = async_url
        try:
            from alembic import command
            from alembic.config import Config

            cfg = Config(str(_BACKEND / "alembic.ini"))
            cfg.set_main_option("script_location", str(_BACKEND / "migrations"))
            command.upgrade(cfg, "head")
        finally:
            if prior_db_url is None:
                os.environ.pop("DATABASE_URL", None)
            else:
                os.environ["DATABASE_URL"] = prior_db_url

        yield async_url
    finally:
        container.stop()


@pytest.fixture
def pg_conn(migrated_pg_url: str) -> Iterator[Any]:
    """psycopg2 sync connection for SELECT assertions after a chat call."""
    import psycopg2

    # Strip any SQLAlchemy driver suffix — psycopg2 only understands the bare libpq URL.
    sync_url = migrated_pg_url.replace("postgresql+asyncpg://", "postgresql://").replace(
        "postgresql+psycopg2://", "postgresql://"
    )
    conn = psycopg2.connect(sync_url)
    try:
        yield conn
    finally:
        conn.close()


# ─── App with overrides (DB → testcontainer, LLM → fake) ─────────────


@pytest.fixture
def fake_model_router() -> _FakeModelRouter:
    return _FakeModelRouter()


@pytest.fixture
async def app_with_overrides(migrated_pg_url, fake_model_router, monkeypatch):
    """FastAPI app with:

    - ``get_db`` overridden via ``app.dependency_overrides`` → testcontainer Postgres.
    - ``wiring.get_model_router`` monkeypatched → ``_FakeModelRouter``.
    - All relevant ``@lru_cache``'d wiring helpers cleared so the orchestrator
      we get is freshly wired with the patched router for each test.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from heart.api import wiring
    from heart.api.main import create_app
    from heart.core.config import settings

    # Make any code that reads settings.database_url get the test URL too.
    monkeypatch.setattr(settings, "database_url", migrated_pg_url)

    test_engine = create_async_engine(migrated_pg_url, echo=False)
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with test_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    # Reset wiring's process-level caches so the orchestrator is built fresh and
    # picks up the patched get_model_router. SessionManager has an in-process
    # dict cache too; clearing it prevents stale (session_id → row) entries
    # from previous tests in the same process.
    wiring.get_model_router.cache_clear()
    wiring.get_orchestrator.cache_clear()
    wiring.get_session_manager.cache_clear()
    wiring.get_breaker_registry.cache_clear()
    wiring.get_safety_agent.cache_clear()
    wiring.get_emotion_service.cache_clear()
    wiring.get_relationship_service.cache_clear()
    wiring.get_inner_state_service.cache_clear()
    wiring.get_soul_registry.cache_clear()

    monkeypatch.setattr(wiring, "get_model_router", lambda: fake_model_router)

    app = create_app()
    app.dependency_overrides[wiring.get_db] = _override_get_db

    try:
        yield app
    finally:
        app.dependency_overrides.clear()
        await test_engine.dispose()
        # NOTE: don't call cache_clear() on wiring.get_model_router here —
        # monkeypatch has replaced it with a plain lambda for the duration of
        # this fixture, and lambdas don't have lru_cache attributes. Monkeypatch
        # restores the original after teardown automatically; the next test's
        # setup clears the (now-restored) lru_cache before patching again.


@pytest.fixture
async def http_client(app_with_overrides) -> AsyncIterator[Any]:
    """httpx.AsyncClient bound to the app via ASGITransport — no socket, no port,
    no race conditions, but a complete real ASGI request path.
    """
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app_with_overrides)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


# ─── Demo user identity (matches routes._coerce_uuid) ────────────────

_DEMO_USER_ID = "integration_demo_alice"
_DEMO_CHARACTER_ID = "rin"


def _demo_user_uuid() -> UUID:
    return uuid5(NAMESPACE_DNS, _DEMO_USER_ID)


@pytest.fixture
def clean_sessions(pg_conn) -> None:
    """Delete prior session rows for the demo user so each test is deterministic."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM sessions WHERE user_id = %s AND character_id = %s",
            (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
        )
    pg_conn.commit()


# ─── Tests ───────────────────────────────────────────────────────────


async def test_login_returns_bearer_token(http_client):
    """POST /api/auth/login → 200 + JWT-shaped Token response."""
    r = await http_client.post(
        "/api/auth/login",
        json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["token_type"] == "bearer"
    assert isinstance(body["access_token"], str) and body["access_token"]
    assert body["expires_in"] > 0


async def test_chat_without_token_is_403(http_client):
    """Auth dep is wired — missing Authorization header → 403 (not 200, not 500)."""
    r = await http_client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "hi"}], "character_id": "rin"},
    )
    assert r.status_code == 403


async def test_chat_with_bogus_token_is_401(http_client):
    """JWT verification path runs — malformed token → 401 from auth_manager.verify_token."""
    r = await http_client.post(
        "/api/chat",
        headers={"Authorization": "Bearer not-a-real-jwt"},
        json={"messages": [{"role": "user", "content": "hi"}], "character_id": "rin"},
    )
    assert r.status_code == 401


async def test_chat_rejects_empty_messages(http_client):
    """Route-level validation: no user message → 400 (proves the route body parses)."""
    login = await http_client.post(
        "/api/auth/login",
        json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
    )
    token = login.json()["access_token"]
    r = await http_client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messages": [{"role": "assistant", "content": "only assistant"}],
            "character_id": "rin",
        },
    )
    assert r.status_code == 400


async def test_full_pipeline_login_chat_writes_session_row(http_client, pg_conn, clean_sessions):
    """The real path, end-to-end.

    Asserts:
      1. ``/api/auth/login`` issues a usable JWT.
      2. ``/api/chat`` returns 200 with the documented schema.
      3. Response was produced by the FakeModelRouter (proves composer reached the LLM phase).
      4. A row was written to ``sessions`` with ``turn_count >= 1`` and the right character.
      5. PURPLE safety flag was *not* tripped on a GREEN message.
    """
    # 1. login → bearer
    login = await http_client.post(
        "/api/auth/login",
        json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    # 2. chat → drives the full pipeline
    chat = await http_client.post(
        "/api/chat",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "messages": [{"role": "user", "content": "こんにちは、今日はいい天気だね"}],
            "character_id": _DEMO_CHARACTER_ID,
        },
    )
    assert chat.status_code == 200, chat.text

    # 3. response schema
    body = chat.json()
    assert set(body.keys()) >= {"response", "character_id", "message_id"}
    assert body["character_id"] == _DEMO_CHARACTER_ID
    assert isinstance(body["response"], str) and body["response"]
    UUID(body["message_id"])  # raises if not a UUID

    # 4. response was produced by the FakeModelRouter — i.e. composer didn't
    #    silently fall back to the `model_router is None` branch.
    assert "[fake-llm:" in body["response"], (
        f"Response did not come from FakeModelRouter — composer fell back? "
        f"Got: {body['response']!r}"
    )

    # 5. DB side-effect: sessions row was INSERTed (load_or_create) and UPDATEd (record_turn)
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT turn_count, suicide_protocol_active, character_id
            FROM sessions
            WHERE user_id = %s AND character_id = %s
            """,
            (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
        )
        row = cur.fetchone()
    assert row is not None, "no sessions row was written — orchestrator never reached the DB"
    turn_count, suicide_active, character_id = row
    assert turn_count >= 1, f"expected turn_count >= 1, got {turn_count}"
    assert suicide_active is False, "GREEN message must not flip suicide_protocol_active"
    assert character_id == _DEMO_CHARACTER_ID


async def test_repeated_chat_increments_turn_count(http_client, pg_conn, clean_sessions):
    """Two ``/api/chat`` calls → single session row, ``turn_count == 2``."""
    login = await http_client.post(
        "/api/auth/login",
        json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "messages": [{"role": "user", "content": "hello"}],
        "character_id": _DEMO_CHARACTER_ID,
    }

    r1 = await http_client.post("/api/chat", headers=headers, json=payload)
    assert r1.status_code == 200, r1.text
    r2 = await http_client.post("/api/chat", headers=headers, json=payload)
    assert r2.status_code == 200, r2.text

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*), MAX(turn_count) FROM sessions "
            "WHERE user_id = %s AND character_id = %s",
            (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
        )
        count, max_turn = cur.fetchone()
    assert count == 1, f"expected exactly 1 session row, got {count}"
    assert max_turn == 2, f"expected turn_count=2 after two chats, got {max_turn}"
