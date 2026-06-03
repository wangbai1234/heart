"""Integration tests for Alembic migrations.

Tests that:
- Database connection works with async SQLAlchemy
- Migrations can be applied and rolled back
- Migration environment is properly configured
"""

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture
def database_url():
    """Get database URL from environment."""
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).parent.parent.parent.parent / ".env")
    return os.getenv("DATABASE_URL")


@pytest.mark.asyncio
async def test_database_connection(database_url):
    """Test async database connection works."""
    engine = create_async_engine(database_url)

    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT 1"))
        assert result.scalar() == 1

    await engine.dispose()


def test_alembic_revision_list():
    """Test that alembic can list revisions."""
    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)

    result = subprocess.run(
        ["python3", "-m", "alembic", "history"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Initial empty schema revision" in result.stdout


def test_alembic_current_revision():
    """Test that alembic shows current revision."""
    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)

    result = subprocess.run(
        ["python3", "-m", "alembic", "current"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0


def test_migration_upgrade_downgrade():
    """Test that migrations can be upgraded and downgraded."""
    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)

    # Get current revision before
    result = subprocess.run(
        ["python3", "-m", "alembic", "current"],
        capture_output=True,
        text=True,
    )
    result.stdout.strip()

    # Downgrade one
    result = subprocess.run(
        ["python3", "-m", "alembic", "downgrade", "-1"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 or "No revision set" in result.stderr

    # Upgrade to head
    result = subprocess.run(
        ["python3", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0

    # Check final revision
    result = subprocess.run(
        ["python3", "-m", "alembic", "current"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0


@pytest.mark.asyncio
async def test_alembic_tables_exist(database_url):
    """Test that Alembic creates necessary tables."""
    engine = create_async_engine(database_url)

    async with engine.connect() as conn:
        # Check that alembic_version table exists (created by Alembic)
        result = await conn.execute(
            text("SELECT 1 FROM information_schema.tables WHERE table_name='alembic_version'")
        )
        assert result.scalar() == 1

    await engine.dispose()


def test_migrations_directory_structure():
    """Test that migrations directory has required structure."""
    migrations_dir = Path(__file__).parent.parent.parent / "migrations"

    # Check required files
    assert (migrations_dir / "env.py").exists()
    assert (migrations_dir / "script.py.mako").exists()
    assert (migrations_dir / "README.md").exists()
    assert (migrations_dir / "versions").exists()
    assert (migrations_dir / "versions").is_dir()

    # Check initial migration
    versions = list((migrations_dir / "versions").glob("*.py"))
    assert len(versions) > 0  # At least initial migration


def test_env_py_has_docstring():
    """Test that env.py has proper documentation."""
    env_path = Path(__file__).parent.parent.parent / "migrations" / "env.py"
    content = env_path.read_text()

    # Check for key components
    assert "get_db_url" in content
    assert "async_engine_from_config" in content
    assert "run_async_migrations" in content
    assert "DATABASE_URL" in content
    assert "SQLAlchemy 2.0" in content or "async" in content
