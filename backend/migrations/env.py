"""
Alembic migration environment script - Heart AI Companion

This script configures Alembic to work with async SQLAlchemy 2.0.
It handles both online (connected) and offline (script generation) modes.

Key features:
- Loads DATABASE_URL from environment (.env file)
- Configures async engine with proper connection pooling for migrations
- Supports autogenerate (when target_metadata is configured)
- Ensures zero-downtime deployments with transactions

Per engineering spec (SS08 §5.3):
- Database partition strategy: BY HASH(user_id) or BY TIME RANGE
- All migrations must be backwards-compatible
- Large table changes require CONCURRENTLY flag
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config object provides access to values in alembic.ini
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Load DATABASE_URL from environment variable
# This allows different databases for dev/test/prod environments
def get_db_url() -> str:
    """Get database URL from environment or .env file.

    Supports async SQLAlchemy with asyncpg driver:
      postgresql+asyncpg://user:password@host:port/dbname

    Raises:
        RuntimeError: If DATABASE_URL is not set in environment or .env
    """
    from dotenv import load_dotenv

    # Load .env if present
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)

    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        raise RuntimeError(
            'DATABASE_URL environment variable not set.\n'
            'Please set DATABASE_URL in your environment or .env file.\n'
            'Example: postgresql+asyncpg://heart:heartdev@localhost:5432/heart'
        )
    return db_url

# SQLAlchemy MetaData for autogenerate support
# Once you create your database models in heart.infra.db.Base,
# uncomment these lines to enable automatic migration generation:
#
# from heart.infra.db import Base
# target_metadata = Base.metadata
#
# Then you can use:
#   alembic revision --autogenerate -m "Add table_name"
#
# This will automatically detect schema changes from your SQLAlchemy models.
target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_db_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in async mode using SQLAlchemy 2.0 async API.

    Flow:
    1. Load DATABASE_URL from environment
    2. Create async engine with NullPool (no connection pooling during migrations)
    3. Begin transaction
    4. Execute migrations synchronously within async context
    5. Commit transaction
    6. Dispose engine and release resources

    Connection Pooling:
    - NullPool: No pooling, each operation creates/closes connection
    - Suitable for migrations to avoid stale connections
    - Production code should use QueuePool (SQLAlchemy default)

    Transaction Safety:
    - All migrations run in a single transaction
    - Rollback on failure (if database supports DDL transactions)
    - PostgreSQL supports transactional DDL by default
    """

    configuration = {
        "sqlalchemy.url": get_db_url(),
        "sqlalchemy.echo": False,
        "sqlalchemy.echo_pool": False,
    }

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.begin() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
