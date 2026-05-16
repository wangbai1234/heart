"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client."""
    from heart.api.main import app

    return TestClient(app)


@pytest.fixture
def db_session():
    """Database session fixture."""
    # TODO: Implement DB session fixture
    pass


@pytest.fixture
def redis_client():
    """Redis client fixture."""
    # TODO: Implement Redis client fixture
    pass
