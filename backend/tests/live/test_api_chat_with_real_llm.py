"""
Live: /api/auth/login + /api/chat full HTTP pipeline against real PG + real DeepSeek.

Closes the coverage gap between Tier B (real PG + fake LLM) and Tier C (real LLM
+ fake DB): this test exercises the FULL stack — real ASGI app (FastAPI + JWT +
middleware) → real Postgres → real DeepSeek API call. No mocks anywhere in the
hot path.

Cost-capped at $0.20 per test class. Skipped without ``--live`` flag and
``DEEPSEEK_API_KEY`` env var.

Fixtures mirror the integration test (``test_api_chat_real_pipeline.py``) but:
- ``get_model_router`` is NOT monkeypatched — wiring builds a real ModelRouter
  backed by DeepSeek.
- ``settings.deepseek_api_key`` is monkeypatched from ``DEEPSEEK_API_KEY`` env.
- Cost is estimated via ``real_deepseek_provider.estimate_cost()`` and recorded
  through the session-scoped ``cost_tracker``.

How to run::

    DEEPSEEK_API_KEY=sk-...   \\
    HEART_TEST_PG_URL=postgresql+asyncpg://... \\
    pytest backend/tests/live/test_api_chat_with_real_llm.py -v --live
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, AsyncIterator, Iterator
from uuid import NAMESPACE_DNS, UUID, uuid5

import pytest

# ── Path + JWT bootstrap ────────────────────────────────────────────

_BACKEND = Path(__file__).resolve().parents[2]
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

os.environ.setdefault(
    "JWT_SECRET_KEY",
    "live-test-jwt-secret-must-be-at-least-32-chars-do-not-use",
)

# ── Demo user identity ──────────────────────────────────────────────

_DEMO_USER_ID = "live_demo_alice"
_DEMO_CHARACTER_ID = "rin"


def _demo_user_uuid() -> UUID:
    return uuid5(NAMESPACE_DNS, _DEMO_USER_ID)


# ── PG fixtures (mirror integration test) ───────────────────────────


@pytest.fixture(scope="module")
def migrated_pg_url() -> Iterator[str]:
    """Yield an asyncpg URL pointing at a freshly-migrated Postgres.

    Default path: start a pgvector-enabled Postgres testcontainer, run
    ``alembic upgrade head`` against it. Module-scope so the start cost
    is amortised across the file.

    Escape hatch: ``HEART_TEST_PG_URL`` env var (same pattern as the
    integration test) — point it at the docker-compose ``heart-postgres``.
    """
    override = os.environ.get("HEART_TEST_PG_URL")
    if override:
        yield override
        return

    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip(
            "testcontainers not installed and HEART_TEST_PG_URL not set",
            allow_module_level=True,
        )

    container = PostgresContainer(
        image="pgvector/pgvector:pg15",
        username="heart",
        password="heart_test",
        dbname="heart_test",
    )
    container.start()
    try:
        sync_url = container.get_connection_url()
        async_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://").replace(
            "postgresql+pg8000://", "postgresql+asyncpg://"
        )
        if not async_url.startswith("postgresql+asyncpg://"):
            async_url = async_url.replace("postgresql://", "postgresql+asyncpg://", 1)

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
    """psycopg2 sync connection for SELECT assertions."""
    import psycopg2

    sync_url = migrated_pg_url.replace("postgresql+asyncpg://", "postgresql://")
    conn = psycopg2.connect(sync_url)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture
def clean_sessions(pg_conn) -> None:
    """Delete prior session rows for the demo user."""
    with pg_conn.cursor() as cur:
        cur.execute(
            "DELETE FROM sessions WHERE user_id = %s AND character_id = %s",
            (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
        )
    pg_conn.commit()


# ── App with REAL DeepSeek (NOT fake!) ──────────────────────────────


@pytest.fixture
async def app_with_real_llm(migrated_pg_url: str, monkeypatch):
    """FastAPI app with real DeepSeek ModelRouter (no monkeypatch on get_model_router).

    Unlike the integration test which injects a ``_FakeModelRouter`` stub,
    this fixture lets ``wiring.get_model_router()`` build a real ModelRouter
    backed by DeepSeek.  The only monkeypatches are:

    - ``settings.database_url`` → testcontainer (or HEART_TEST_PG_URL)
    - ``settings.deepseek_api_key`` → ``DEEPSEEK_API_KEY`` env var

    All ``@lru_cache``'d wiring singletons are cleared so the orchestrator
    picks up the patched settings.
    """
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    from heart.api import wiring
    from heart.api.main import create_app
    from heart.core.config import settings

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set — required for real LLM calls")

    monkeypatch.setattr(settings, "database_url", migrated_pg_url)
    monkeypatch.setattr(settings, "deepseek_api_key", api_key)

    test_engine = create_async_engine(migrated_pg_url, echo=False)
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with test_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    # Clear all wiring caches so the orchestrator + model_router are built
    # fresh with the patched settings (including the real API key).
    wiring.get_model_router.cache_clear()
    wiring.get_orchestrator.cache_clear()
    wiring.get_session_manager.cache_clear()
    wiring.get_breaker_registry.cache_clear()
    wiring.get_safety_agent.cache_clear()
    wiring.get_emotion_service.cache_clear()
    wiring.get_relationship_service.cache_clear()
    wiring.get_inner_state_service.cache_clear()
    wiring.get_soul_registry.cache_clear()

    app = create_app()
    app.dependency_overrides[wiring.get_db] = _override_get_db

    try:
        yield app
    finally:
        app.dependency_overrides.clear()
        await test_engine.dispose()


@pytest.fixture
async def http_client(app_with_real_llm) -> AsyncIterator[Any]:
    """httpx.AsyncClient bound to the app via ASGITransport.

    Sets a generous timeout (60 s) because real DeepSeek calls can take
    several seconds under load.
    """
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app_with_real_llm)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", timeout=60.0
    ) as client:
        yield client


# ── Helper — conservative token estimate ────────────────────────────


def _estimate_tokens(text: str) -> int:
    """Rough token count (~1 token per char for CJK, ~4 for Latin).

    We deliberately overestimate (round *up*) so the cost ceiling is safe.
    """
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff" or "\u3040" <= ch <= "\u30ff")
    latin = len(text) - cjk
    return max(cjk + (latin + 3) // 4, 1)


# ── Tests ───────────────────────────────────────────────────────────


@pytest.mark.live(max_cost=0.20)
class TestApiChatWithRealLLM:
    """Full HTTP pipeline with real DeepSeek — one turn, then two turns."""

    @pytest.mark.asyncio
    async def test_live__single_turn_writes_session_and_responds_naturally(
        self,
        http_client,
        pg_conn,
        clean_sessions,
        cost_tracker,
        per_test_budget,
        real_deepseek_provider,
    ):
        """POST /api/auth/login → POST /api/chat (1 turn) → assert 200,
        non-empty DeepSeek response, sessions row, and cost within budget.
        """
        # 1. Login
        login = await http_client.post(
            "/api/auth/login",
            json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
        )
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]

        # 2. Chat — this is the real DeepSeek call
        chat = await http_client.post(
            "/api/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "messages": [{"role": "user", "content": "こんにちは、今日はいい天気ですね"}],
                "character_id": _DEMO_CHARACTER_ID,
            },
        )
        assert chat.status_code == 200, chat.text
        body = chat.json()

        # 3. Response schema
        assert set(body.keys()) >= {"response", "character_id", "message_id"}
        assert body["character_id"] == _DEMO_CHARACTER_ID
        assert isinstance(body["response"], str) and len(body["response"]) > 0
        UUID(body["message_id"])

        # 4. Prove it's real DeepSeek (not a fake stub)
        assert "[fake-llm:" not in body["response"], (
            "Response signature matches FakeModelRouter — real DeepSeek was not reached"
        )
        # A real LLM response should be multi-word, natural Japanese/Chinese
        assert len(body["response"].split()) > 2, (
            f"Response suspiciously short for real LLM: {body['response'][:80]}..."
        )

        # 5. DB side-effect
        with pg_conn.cursor() as cur:
            cur.execute(
                "SELECT turn_count, suicide_protocol_active, character_id "
                "FROM sessions WHERE user_id = %s AND character_id = %s",
                (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
            )
            row = cur.fetchone()
        assert row is not None, "No sessions row written — orchestrator never reached DB"
        turn_count, suicide_active, character_id = row
        assert turn_count >= 1, f"Expected turn_count >= 1, got {turn_count}"
        assert suicide_active is False
        assert character_id == _DEMO_CHARACTER_ID

        # 6. Cost tracking
        estimated_output_tokens = _estimate_tokens(body["response"])
        estimated_input_tokens = 2500  # conservative: soul prompt + context blocks + user msg
        cost = real_deepseek_provider.estimate_cost(
            prompt_tokens=estimated_input_tokens,
            estimated_completion_tokens=estimated_output_tokens,
            model="deepseek-chat",
        )
        cost_tracker.record_cost(cost.total_cost_usd)
        assert cost.total_cost_usd < 0.20, (
            f"Turn cost ${cost.total_cost_usd:.6f} exceeded $0.20 budget"
        )

    @pytest.mark.asyncio
    async def test_live__two_turns_increments_count_and_no_fake_leak(
        self,
        http_client,
        pg_conn,
        clean_sessions,
        cost_tracker,
        per_test_budget,
        real_deepseek_provider,
    ):
        """Two real DeepSeek turns → single session row with turn_count == 2."""
        login = await http_client.post(
            "/api/auth/login",
            json={"user_id": _DEMO_USER_ID, "email": "alice@example.com"},
        )
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        turn1_payload = {
            "messages": [{"role": "user", "content": "おはよう！"}],
            "character_id": _DEMO_CHARACTER_ID,
        }
        turn2_payload = {
            "messages": [{"role": "user", "content": "好きな食べ物は？"}],
            "character_id": _DEMO_CHARACTER_ID,
        }

        r1 = await http_client.post("/api/chat", headers=headers, json=turn1_payload)
        assert r1.status_code == 200, r1.text
        body1 = r1.json()

        r2 = await http_client.post("/api/chat", headers=headers, json=turn2_payload)
        assert r2.status_code == 200, r2.text
        body2 = r2.json()

        # Both responses must be real (no fake router signature)
        assert "[fake-llm:" not in body1["response"]
        assert "[fake-llm:" not in body2["response"]
        assert len(body1["response"].split()) > 2
        assert len(body2["response"].split()) > 2

        # DB assertion
        with pg_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*), MAX(turn_count) FROM sessions "
                "WHERE user_id = %s AND character_id = %s",
                (str(_demo_user_uuid()), _DEMO_CHARACTER_ID),
            )
            count, max_turn = cur.fetchone()
        assert count == 1, f"Expected 1 session row, got {count}"
        assert max_turn == 2, f"Expected turn_count=2, got {max_turn}"

        # Cost tracking — both turns combined
        len(body1["response"]) + len(body2["response"])
        estimated_output = _estimate_tokens(body1["response"]) + _estimate_tokens(body2["response"])
        estimated_input = 4000  # 2 turns of full context
        cost = real_deepseek_provider.estimate_cost(
            prompt_tokens=estimated_input,
            estimated_completion_tokens=estimated_output,
            model="deepseek-chat",
        )
        cost_tracker.record_cost(cost.total_cost_usd)
        assert cost.total_cost_usd < 0.20, (
            f"Combined cost ${cost.total_cost_usd:.6f} exceeded $0.20 budget"
        )
