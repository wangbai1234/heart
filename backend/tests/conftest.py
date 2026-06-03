"""
Pytest configuration and fixtures — global (all tiers).

Tier 0: unit tests (existing, unchanged)
Tier A: contract tests — pure Python, no IO
Tier B: integration tests — real PG/Redis testcontainers + fake LLM
Tier C: live tests — real DeepSeek, cost-capped, opt-in via --live
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from heart.ss02_memory.models import Base

# Test database URL (in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def pytest_addoption(parser):
    """Add CLI options for Tier C live tests."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help="Enable Tier C live tests with real DeepSeek calls",
    )
    parser.addoption(
        "--max-cost",
        type=float,
        default=2.0,
        help="Maximum USD cost per Tier C run (default: 2.0)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "contract: Tier A contract tests")
    config.addinivalue_line("markers", "integration: Tier B integration tests")
    config.addinivalue_line("markers", "live: Tier C live tests (real LLM, cost-capped)")
    config.addinivalue_line("markers", "drift: voice drift regression tests (Tier C subcategory)")
    config.addinivalue_line("markers", "requires_postgres: tests requiring real Postgres")


def pytest_collection_modifyitems(config, items):
    """Deselect live tests when --live flag is not passed."""
    if not config.getoption("--live"):
        skip_live = pytest.mark.skip(reason="Tier C skipped (use --live to opt in)")
        for item in items:
            if "live" in item.keywords:
                item.add_marker(skip_live)


@pytest.fixture
def client():
    """FastAPI test client."""
    from heart.api.main import app

    return TestClient(app)


@pytest.fixture
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def async_session(async_engine):
    """Async database session fixture."""
    async_session_maker = sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest.fixture
def db_session():
    """Database session fixture (sync)."""
    # TODO: Implement sync DB session fixture if needed
    pass


@pytest.fixture
def redis_client():
    """Redis client fixture."""
    # TODO: Implement Redis client fixture
    pass
