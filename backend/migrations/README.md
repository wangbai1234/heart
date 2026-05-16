# Alembic Database Migrations - Heart AI Companion

This directory contains database schema migrations for the Heart project using Alembic with SQLAlchemy 2.0 async support.

## Quick Start

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific number of migrations
alembic upgrade +2

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base
```

### Creating New Migrations

#### Automatic Generation (Recommended with models)

Once you've defined SQLAlchemy models in `heart.infra.db.Base`, generate migrations automatically:

```bash
# In backend/ directory
alembic revision --autogenerate -m "Add users table"
```

#### Manual Creation

For changes that autogenerate can't detect:

```bash
alembic revision -m "Add custom index on users.email"
```

Then edit the generated file in `versions/` to add custom SQL.

## Configuration

### Environment Variables

The migration system uses the following environment variables (from `.env`):

- **DATABASE_URL**: PostgreSQL connection URL with asyncpg driver
  ```
  postgresql+asyncpg://user:password@localhost:5432/dbname
  ```

### Key Files

- **alembic.ini**: Main Alembic configuration
- **env.py**: Runtime migration environment setup
  - Loads DATABASE_URL from environment
  - Configures async SQLAlchemy 2.0 engine
  - Manages connection pooling and transactions
- **script.py.mako**: Template for new migration files

## SQLAlchemy 2.0 Async Integration

The configuration uses SQLAlchemy 2.0's async API:

1. **Async Engine**: `async_engine_from_config()` creates AsyncEngine
2. **NullPool**: Used for migrations to avoid connection pooling issues
3. **Async Context**: `async with connectable.begin()` manages transactions
4. **run_sync**: Uses `connection.run_sync()` to execute sync migration code

### Important Notes

- Migrations always run synchronously (SQLAlchemy limitation)
- The async engine ensures connection is properly managed
- Use `await connection.run_sync(callback)` for blocking operations

## Database Schema Rules

Per engineering spec (SS08 §4.2, §4.3):

### Partitioning Strategy

Tables should be partitioned by:

- **by_user_hash**: 16-32 partitions for large tables
  - Tables: soul_activation_states, episodic_memories, sessions, etc.
  - Enables horizontal scaling by user_id
  
- **by_time_range**: Monthly partitions for event logs
  - Tables: memory_encoding_events, emotion_events, traces, etc.
  - Supports archival and retention policies

### Indexing Strategy

```sql
-- Standard indexes for frequent queries
CREATE INDEX idx_{table}_user_recent ON {table} 
  (user_id, character_id, updated_at DESC);

-- Vector indexes for embeddings
CREATE INDEX idx_semantic ON {table} 
  USING hnsw (embedding_column vector_cosine_ops);

-- Time-based queries
CREATE INDEX idx_recent ON {table} 
  (created_at DESC) WHERE created_at > NOW() - INTERVAL '30 days';
```

### RLS (Row-Level Security)

All tables with user_id must have RLS policies:

```sql
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;

CREATE POLICY {table}_user_isolation ON {table}
  USING (user_id = current_user_id());
```

## Migration Best Practices

### 1. Zero-Downtime Deployments

Follow this three-phase approach:

```python
# Phase 1: Backward-compatible migration
def upgrade():
    # Add column with default value (non-blocking)
    op.add_column('users', sa.Column('new_field', sa.String(100), default=''))
    
def downgrade():
    op.drop_column('users', 'new_field')

# Phase 2: Deploy code that uses new schema

# Phase 3 (Optional): Remove old schema
# (Create separate migration)
def upgrade():
    op.drop_column('users', 'old_field')
```

### 2. Large Table Changes

For tables with millions of rows:

```python
def upgrade():
    # Add column with NULL default (fast)
    op.add_column('large_table', 
                  sa.Column('new_field', sa.String(100)))
    
    # Add index CONCURRENTLY (non-blocking)
    op.create_index('idx_new_field', 'large_table', 
                    ['new_field'], postgresql_concurrently=True)
    
    # Backfill in application or separate migration

def downgrade():
    op.drop_column('large_table', 'new_field')
```

### 3. Type Changes

Use a safe migration pattern:

```python
def upgrade():
    # 1. Create new column
    op.add_column('table', sa.Column('new_column', sa.Integer()))
    
    # 2. Copy and transform data
    op.execute("UPDATE table SET new_column = CAST(old_column AS INTEGER)")
    
    # 3. Add constraints
    op.alter_column('table', 'new_column', nullable=False)
    
    # 4. Drop old column (optional, can be deferred)
    # op.drop_column('table', 'old_column')
```

## Checking Migration Status

```bash
# Show current revision
alembic current

# Show all revisions and their status
alembic history

# Show only pending migrations
alembic history -r <current>:head

# Get branch information
alembic branches
```

## Testing Migrations

### In CI/CD

```bash
# Create test database
createdb test_heart

# Run migrations
alembic upgrade head

# Run tests
pytest tests/integration

# Cleanup
dropdb test_heart
```

### Local Development

```bash
# Docker-based test database
docker-compose -f docker-compose.test.yml up postgres

# Run with test DATABASE_URL
DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test \
  alembic upgrade head
```

## Troubleshooting

### Migration fails with "table already exists"

```bash
# Check current migration state
alembic current

# Reset to clean state (development only!)
alembic downgrade base
alembic upgrade head
```

### Can't find new columns in database after migration

Ensure you ran `alembic upgrade head` and check with:

```bash
# Check schema
docker-compose exec postgres psql -U heart -d heart \
  -c "\d table_name"
```

### Migration is slow

Check for:
- Large data migrations without background processing
- Adding indexes to large tables without CONCURRENTLY flag
- Missing SERIAL/BIGSERIAL when creating ID columns

## Integration with SQLAlchemy Models

Once you've set up `heart.infra.db.Base`:

```python
# In heart/infra/db.py
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# In migrations/env.py
from heart.infra.db import Base
target_metadata = Base.metadata
```

Then autogenerate becomes available:

```bash
alembic revision --autogenerate -m "Add users table"
```

## Related Documentation

- Engineering spec: `/runtime_specs/08_engineering_architecture.md` §4.2-§5
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- Alembic tutorial: https://alembic.sqlalchemy.org/en/latest/tutorial.html
