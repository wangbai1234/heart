"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from heart.ss02_memory.models import Base


# Test database URL (in-memory SQLite for unit tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


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
