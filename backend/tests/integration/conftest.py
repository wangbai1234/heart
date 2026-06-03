"""
Tier B Integration conftest — real PG/Redis via testcontainers, fake LLM.

Per design doc §4.3:
- session-scope postgres_container (testcontainers)
- session-scope redis_container (testcontainers)
- function-scope db_session (transaction rollback)
- function-scope frozen_clock (freezegun)
- session-scope fake_llm_provider

Graceful degradation: skips integration tests when testcontainers not available.
"""

import os
from pathlib import Path
from uuid import uuid4

import pytest

# ─── Testcontainers availability check ───
try:
    import testcontainers  # noqa: F401

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


# ─── Fake LLM Provider ───


@pytest.fixture(scope="session")
def fake_llm_provider():
    """Session-scope fake LLM provider with fixtures loaded."""
    from heart.infra.llm_providers.fake import FakeLLMProvider

    fixtures_dir = Path(__file__).parent / "fixtures" / "fake_llm_responses"
    provider = FakeLLMProvider(fixtures_dir=fixtures_dir)
    return provider


# ─── PostgreSQL Testcontainer (session-scope) ───


@pytest.fixture(scope="session")
def postgres_container():
    """Session-scope PostgreSQL testcontainer with pgvector."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not installed (pip install testcontainers)")

    try:
        from testcontainers.postgres import PostgresContainer

        container = PostgresContainer(
            image="pgvector/pgvector:pg15",
            username="heart",
            password="heart_test",
            dbname="heart_test",
        )
        container.start()

        # Set env var for SQLAlchemy URL
        os.environ["TEST_DATABASE_URL"] = container.get_connection_url()
        # Replace postgresql:// with postgresql+asyncpg://
        db_url = container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
        os.environ["TEST_ASYNC_DATABASE_URL"] = db_url

    except Exception as e:
        pytest.skip(f"Failed to start PostgreSQL container: {e}")

    yield container

    container.stop()


# ─── Redis Testcontainer (session-scope) ───


@pytest.fixture(scope="session")
def redis_container():
    """Session-scope Redis testcontainer."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not installed")

    try:
        from testcontainers.redis import RedisContainer

        container = RedisContainer(image="redis:7-alpine")
        container.start()

        os.environ["TEST_REDIS_URL"] = (
            f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}"
        )

    except Exception as e:
        pytest.skip(f"Failed to start Redis container: {e}")

    yield container

    container.stop()


# ─── Database Session (function-scope, transaction rollback) ───


@pytest.fixture
async def db_session(postgres_container):
    """Function-scope async DB session with transaction rollback."""
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from heart.ss02_memory.models import Base as MemoryBase
    from heart.ss03_emotion.models import Base as EmotionBase
    from heart.ss04_relationship.models import Base as RelationshipBase

    db_url = os.environ.get(
        "TEST_ASYNC_DATABASE_URL", "postgresql+asyncpg://heart:heart_test@localhost:5432/heart_test"
    )

    engine = create_async_engine(db_url, echo=False, future=True)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(MemoryBase.metadata.create_all)
        await conn.run_sync(EmotionBase.metadata.create_all)
        await conn.run_sync(RelationshipBase.metadata.create_all)

    # Create session with transaction
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        async with session.begin():
            yield session
            # Rollback happens automatically

    await engine.dispose()


# ─── Redis Client (function-scope, flushdb teardown) ───


@pytest.fixture
def redis_client(redis_container):
    """Function-scope Redis client with key prefix isolation."""
    import redis as redis_lib

    redis_url = os.environ.get("TEST_REDIS_URL", "redis://localhost:6379")

    client = redis_lib.Redis.from_url(redis_url, decode_responses=True)
    test_prefix = f"test:{uuid4().hex[:8]}:"
    client.config_set("test_prefix", test_prefix)

    yield client

    # Flush only test keys
    for key in client.scan_iter(f"{test_prefix}*"):
        client.delete(key)
    client.close()


# ─── Frozen Clock (function-scope, freezegun) ───


@pytest.fixture
def frozen_clock():
    """Function-scope frozen clock using freezegun.

    Use: frozen_clock.move_to("2026-01-15") to set a specific date.
    """
    try:
        from datetime import datetime, timezone

        from freezegun import freeze_time

        freezer = freeze_time("2026-06-01 12:00:00", tz_offset=0)
        freezer.start()
        yield freezer
        freezer.stop()
    except ImportError:
        pytest.skip("freezegun not installed (pip install freezegun)")


# ─── Soul Registry (function-scope) ───


@pytest.fixture
def soul_registry():
    """Loaded SoulRegistry with real soul spec files."""
    from heart.ss01_soul.registry import SoulRegistry

    registry = SoulRegistry()
    registry.load_all()
    return registry


# ─── Emotion Service (function-scope) ───


@pytest.fixture
def emotion_service():
    """EmotionService initialized with real lexicon config."""
    from heart.ss03_emotion.service import EmotionService

    return EmotionService()


# ─── Memory Service (function-scope) ───


@pytest.fixture
def memory_service(db_session, redis_client):
    """MemoryService with real DB and Redis."""
    from heart.ss02_memory.service import MemoryService

    service = MemoryService(
        db_session=db_session,
        redis_client=redis_client,
    )
    return service
