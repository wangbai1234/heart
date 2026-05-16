# Alembic Setup Guide - Heart AI Companion

This document describes the complete Alembic configuration for the Heart project.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Alembic Migration System                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  alembic.ini                                                │
│  ├─ sqlalchemy.url = (loaded from DATABASE_URL env var)     │
│  ├─ script_location = migrations                            │
│  └─ [logging] configuration                                 │
│                                                              │
│  migrations/env.py                                          │
│  ├─ get_db_url() → reads .env/environment                   │
│  ├─ run_async_migrations() → async SQLAlchemy 2.0 engine    │
│  ├─ run_migrations_offline() → script generation mode       │
│  └─ target_metadata = None (will be set when models added)  │
│                                                              │
│  migrations/script.py.mako                                  │
│  └─ template for generating new migration files             │
│                                                              │
│  migrations/versions/                                       │
│  ├─ e814230ade46_initial_empty_schema_revision.py (base)   │
│  ├─ (future migrations here)                                │
│  └─ ...                                                      │
│                                                              │
│  .env                                                        │
│  └─ DATABASE_URL=postgresql+asyncpg://...                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Configuration Details

### 1. alembic.ini

**Key Settings:**
```ini
[alembic]
script_location = migrations          # Where migrations are stored
prepend_sys_path = .                  # Add current dir to Python path
version_path_separator = os           # Use OS path separator
sqlalchemy.url = driver://...         # Fallback URL (not used, loaded from env)
sqlalchemy.echo = false               # Don't echo SQL statements
sqlalchemy.echo_pool = false          # Don't log pool events
```

### 2. env.py - Core Configuration

**get_db_url():**
- Loads `.env` file from parent directory
- Reads `DATABASE_URL` environment variable
- Validates URL is set, raises helpful error if not
- Supports `postgresql+asyncpg://` format for async driver

**Async SQLAlchemy 2.0 Integration:**
- `async_engine_from_config()` creates AsyncEngine
- `poolclass=pool.NullPool` for migrations (no connection pooling)
- `async with connectable.begin()` manages transactions
- `connection.run_sync(callback)` executes sync migration code

**Two Execution Modes:**

1. **Online Mode** (default):
   - Creates async engine and connection
   - Executes migrations in transaction
   - Used in CI/CD and production

2. **Offline Mode**:
   - Generates SQL script without executing
   - Used to preview SQL before running
   - Command: `alembic upgrade head --sql`

### 3. Initial Migration

**File:** `migrations/versions/e814230ade46_initial_empty_schema_revision.py`

- Empty base migration (no operations)
- Serves as revision 0 (down_revision = None)
- Future migrations will build on this

## Complete Workflow

### Step 1: Setup (Already Done ✅)

```bash
# Initialize Alembic with async support
alembic init -t async migrations

# Update env.py for environment variables
# (Already configured)

# Create initial empty migration
alembic revision -m "Initial empty schema revision"

# Test migration runs
alembic upgrade head
```

### Step 2: When Adding Database Models

1. **Create SQLAlchemy models** in `heart/infra/db.py`:

```python
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(UUID, primary_key=True)
    user_id = Column(String, unique=True)
    email = Column(String, unique=True)
    ...
```

2. **Enable autogenerate** in `migrations/env.py`:

```python
from heart.infra.db import Base
target_metadata = Base.metadata
```

3. **Generate migration**:

```bash
alembic revision --autogenerate -m "Add users table"
```

4. **Review generated migration**:
- Check `migrations/versions/xxx_add_users_table.py`
- Ensure correct schema changes
- Add custom logic if needed

5. **Apply migration**:

```bash
alembic upgrade head
```

### Step 3: Development Workflow

**Every time you change models:**

```bash
# Generate migration
alembic revision --autogenerate -m "Clear description of change"

# Review generated file
vi migrations/versions/xxx_*.py

# Apply migration
alembic upgrade head

# Run tests
pytest
```

**Before committing:**

```bash
# Ensure migration is clean
alembic history
alembic current

# Test downgrade works
alembic downgrade -1
alembic upgrade head

# Commit migration file with your code change
git add migrations/versions/xxx_*.py
git commit -m "Add users table and related indexes"
```

### Step 4: Deployment

**Development/Testing:**

```bash
# Apply all pending migrations
alembic upgrade head
```

**Production:**

```bash
# Preview migrations
alembic upgrade head --sql

# Apply with careful monitoring
alembic upgrade head

# Verify migration applied
alembic current
```

## Environment Variables

### DATABASE_URL Format

```
postgresql+asyncpg://[user[:password]@][netloc][:port][/dbname][?param1=value1&...]
```

**Examples:**

```bash
# Local development
DATABASE_URL=postgresql+asyncpg://heart:heartdev@localhost:5432/heart

# Docker container
DATABASE_URL=postgresql+asyncpg://heart:heartdev@postgres:5432/heart

# Remote with SSL
DATABASE_URL=postgresql+asyncpg://user:pass@db.example.com/heart?sslmode=require
```

### Configuration Priority

1. **Environment variable** (highest): `DATABASE_URL=...`
2. **`.env` file** (committed safely): `DATABASE_URL=postgresql+...`
3. **Error** if neither set (lowest)

## Making Migrations Safer

### 1. Always Test Rollback

```bash
# After creating migration
alembic upgrade head          # Apply
alembic downgrade -1          # Rollback
alembic upgrade head          # Re-apply
```

### 2. Use Backwards-Compatible Changes

```python
def upgrade():
    # GOOD: Add column with default (old code still works)
    op.add_column('table', sa.Column('new_col', sa.String(100), default=''))
    
    # BAD: Make column NOT NULL (breaks old code that doesn't set it)
    op.alter_column('table', 'col', nullable=False)
```

### 3. Large Table Changes

```python
def upgrade():
    # GOOD: Use CONCURRENTLY (non-blocking)
    op.create_index('idx_name', 'table', ['col'],
                    postgresql_concurrently=True)
    
    # BAD: Without CONCURRENTLY (blocks reads/writes)
    op.create_index('idx_name', 'table', ['col'])
```

### 4. Data Migrations

```python
def upgrade():
    # Add column
    op.add_column('table', sa.Column('new_col', sa.String(100)))
    
    # Backfill data
    op.execute("""
        UPDATE table SET new_col = old_col 
        WHERE new_col IS NULL
    """)
    
    # Later migration: add NOT NULL constraint
```

## Troubleshooting

### Problem: DATABASE_URL not found

```bash
# Check .env exists in root directory
ls -la .env

# Check DATABASE_URL is set
grep DATABASE_URL .env

# Or set environment variable
export DATABASE_URL=postgresql+asyncpg://...
```

### Problem: Migration won't apply

```bash
# Check current revision
alembic current

# Check revision history
alembic history

# Try to see what SQL would be executed
alembic upgrade head --sql

# Check database connection directly
psql $DATABASE_URL -c "SELECT 1"
```

### Problem: Can't use autogenerate

```bash
# Make sure target_metadata is set in env.py:
# from heart.infra.db import Base
# target_metadata = Base.metadata

# Check that Base and models are importable
python3 -c "from heart.infra.db import Base; print(Base.metadata.tables)"

# If models exist, try again
alembic revision --autogenerate -m "Description"
```

### Problem: Revision conflicts

```bash
# Two people created migrations at same time
# Manual fix: edit down_revision in newer migration
alembic history  # Check order

# Then test:
alembic upgrade head
alembic downgrade -1
alembic upgrade head
```

## Integration with Other Tools

### GitHub Actions / CI-CD

```yaml
# .github/workflows/test.yml
- name: Run migrations
  env:
    DATABASE_URL: postgresql+asyncpg://test:test@postgres:5432/test_db
  run: |
    alembic upgrade head
    pytest tests/
```

### Docker Compose

```yaml
# docker-compose.yml
postgres:
  image: pgvector/pgvector:pg15
  environment:
    POSTGRES_USER: heart
    POSTGRES_PASSWORD: heartdev
    POSTGRES_DB: heart

api:
  depends_on:
    - postgres
  environment:
    DATABASE_URL: postgresql+asyncpg://heart:heartdev@postgres:5432/heart
  command: sh -c "alembic upgrade head && uvicorn heart.api.main:app"
```

## Testing Migrations

```bash
# Unit test a specific migration
pytest tests/integration/test_migrations.py::test_alembic_revision_list

# Integration test with real database
pytest tests/integration/test_migrations.py -v

# Test migration performance
time alembic upgrade head
```

## Performance Considerations

### NullPool for Migrations

```python
poolclass=pool.NullPool  # Migrations use this
```

**Why:**
- No connection pooling overhead
- Each operation gets fresh connection
- Avoids "stale connection" issues
- Non-blocking for other operations

### Production

```python
# Regular application code uses QueuePool (default)
# engine = create_async_engine(url)  # Uses QueuePool
```

## Security

### Protecting DATABASE_URL

1. **Never commit secrets**:
   ```bash
   # .gitignore
   .env          # Local development
   .env.local    # Secret overrides
   ```

2. **Use environment variables in production**:
   ```bash
   # On server/container
   export DATABASE_URL=postgresql+asyncpg://...
   alembic upgrade head
   ```

3. **Use secrets manager**:
   ```bash
   # AWS Secrets Manager / HashiCorp Vault
   DATABASE_URL=$(aws secretsmanager get-secret-value --secret-id prod/db_url)
   ```

## Related Documentation

- **Engineering Spec**: `/runtime_specs/08_engineering_architecture.md`
  - §4.2: Database Partitioning Strategy
  - §4.3: Cache Strategy
  - §5: Data Structures (complete Schema index)
  
- **Migration Examples**: `/migrations/MIGRATION_EXAMPLES.md`
  - Partitioned tables
  - Time-based partitioning
  - Safe column changes
  - RLS setup
  
- **Best Practices**: `/migrations/README.md`
  - Zero-downtime deployments
  - Large table changes
  - Type migrations
  
- **SQLAlchemy Async**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- **Alembic Tutorial**: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- **PostgreSQL Partitioning**: https://www.postgresql.org/docs/current/ddl-partitioning.html

## Summary

✅ **Alembic is fully configured for Heart project:**

1. ✅ `alembic.ini` - configured with async support
2. ✅ `env.py` - loads DATABASE_URL from environment
3. ✅ `script.py.mako` - template for new migrations
4. ✅ `versions/` - initial empty migration created
5. ✅ `.env` - DATABASE_URL configured
6. ✅ Tests - migration integration tests passing

**Next steps:**
1. Create `heart/infra/db.py` with SQLAlchemy models
2. Set `target_metadata` in `migrations/env.py`
3. Use `alembic revision --autogenerate` for future changes
