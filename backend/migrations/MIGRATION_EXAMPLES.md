# Migration Examples - Heart AI Companion

This document provides example migrations following SQLAlchemy 2.0 and engineering best practices.

## Example 1: Creating a Simple Table

```python
"""Create users table

Revision ID: abc123def456
Revises: 
Create Date: 2026-05-16 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    """Create users table with indexes."""
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(as_uuid=True), server_default=sa.func.gen_random_uuid(), primary_key=True),
        sa.Column('user_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),  # Soft delete
    )
    
    # Create additional indexes
    op.create_index('idx_users_created_at', 'users', ['created_at'])
    op.create_index('idx_users_deleted_at', 'users', ['deleted_at'])


def downgrade() -> None:
    """Drop users table."""
    op.drop_table('users')
```

## Example 2: Partitioned Table (by user_id hash)

```python
"""Create partitioned episodic_memories table

Revision ID: def456ghi789
Revises: abc123def456
Create Date: 2026-05-16 12:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Create partitioned episodic_memories table.
    
    Partition by HASH(user_id) into 16 partitions.
    Allows horizontal scaling across users.
    """
    
    # Create base table (partitioned)
    op.execute("""
        CREATE TABLE episodic_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            character_id VARCHAR(255) NOT NULL,
            semantic_vector vector(1024),
            event_text TEXT NOT NULL,
            context JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
            deleted_at TIMESTAMP WITH TIME ZONE
        ) PARTITION BY HASH (user_id);
    """)
    
    # Create 16 partitions
    for i in range(16):
        op.execute(f"""
            CREATE TABLE episodic_memories_p{i} 
            PARTITION OF episodic_memories 
            FOR VALUES WITH (MODULUS 16, REMAINDER {i});
        """)
    
    # Create indexes on base table (inherited by partitions)
    op.create_index(
        'idx_episodic_user_recent',
        'episodic_memories',
        ['user_id', 'character_id', 'created_at'],
        postgresql_using='btree'
    )
    
    # Vector index with HNSW algorithm
    op.execute("""
        CREATE INDEX idx_episodic_semantic ON episodic_memories 
        USING hnsw (semantic_vector vector_cosine_ops)
        WITH (m=16, ef_construction=128);
    """)


def downgrade() -> None:
    """Drop partitioned table."""
    op.execute("DROP TABLE IF EXISTS episodic_memories;")
```

## Example 3: Time-based Partitioning

```python
"""Create monthly partitioned events table

Revision ID: ghi789jkl012
Revises: def456ghi789
Create Date: 2026-05-16 12:00:02.000000
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


def upgrade() -> None:
    """Create emotion_events table partitioned by month."""
    
    # Create base partitioned table
    op.execute("""
        CREATE TABLE emotion_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            character_id VARCHAR(255) NOT NULL,
            emotion_type VARCHAR(50) NOT NULL,
            intensity FLOAT NOT NULL CHECK (intensity >= 0 AND intensity <= 1),
            trigger_description TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        ) PARTITION BY RANGE (created_at);
    """)
    
    # Create partition for current month
    current_date = datetime.now()
    partition_name = f"emotion_events_{current_date.strftime('%Y%m')}"
    next_month = (current_date.replace(day=1) + sa.text("INTERVAL '1 month'")).date()
    
    op.execute(f"""
        CREATE TABLE {partition_name} 
        PARTITION OF emotion_events 
        FOR VALUES FROM ('{current_date.date()}') TO ('{next_month}');
    """)
    
    # Create indexes
    op.create_index(
        'idx_emotion_user_recent',
        'emotion_events',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )


def downgrade() -> None:
    """Drop emotion_events table."""
    op.execute("DROP TABLE IF EXISTS emotion_events;")
```

## Example 4: Adding Column to Large Table (Zero-downtime)

```python
"""Add new_field to large_table

Revision ID: jkl012mno345
Revises: ghi789jkl012
Create Date: 2026-05-16 12:00:03.000000
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Add column to large table without blocking reads/writes.
    
    Strategy:
    1. Add column with default (non-blocking on PostgreSQL)
    2. Add index CONCURRENTLY (non-blocking)
    3. Backfill NULL values asynchronously (in application)
    4. Add NOT NULL constraint in separate migration
    """
    
    # Add column with NULL default (fast, non-blocking)
    op.add_column(
        'large_table',
        sa.Column('new_field', sa.String(100), nullable=True, default='')
    )
    
    # Add index CONCURRENTLY (doesn't block reads or writes)
    op.create_index(
        'idx_large_table_new_field',
        'large_table',
        ['new_field'],
        postgresql_concurrently=True
    )


def downgrade() -> None:
    """Remove column and index."""
    op.drop_index('idx_large_table_new_field', postgresql_concurrently=True)
    op.drop_column('large_table', 'new_field')
```

## Example 5: Row-Level Security (RLS)

```python
"""Enable RLS on users table

Revision ID: mno345pqr678
Revises: jkl012mno345
Create Date: 2026-05-16 12:00:04.000000
"""

from alembic import op


def upgrade() -> None:
    """Enable Row-Level Security on users table.
    
    Ensures users can only access their own data.
    """
    
    # Enable RLS
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY;")
    
    # Create policy for user isolation
    op.execute("""
        CREATE POLICY users_user_isolation ON users
            USING (user_id = current_user_id());
    """)


def downgrade() -> None:
    """Disable RLS."""
    op.execute("DROP POLICY IF EXISTS users_user_isolation ON users;")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY;")
```

## Example 6: Type Migration (Safe Pattern)

```python
"""Change user_age from VARCHAR to INTEGER

Revision ID: pqr678stu901
Revises: mno345pqr678
Create Date: 2026-05-16 12:00:05.000000
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Safely migrate VARCHAR(age) to INTEGER.
    
    Safe migration pattern:
    1. Create new column
    2. Copy and transform data
    3. Add constraints
    4. Drop old column (can be deferred to separate migration)
    """
    
    # Phase 1: Create new column
    op.add_column('users', sa.Column('age_new', sa.Integer(), nullable=True))
    
    # Phase 2: Migrate data with error handling
    op.execute("""
        UPDATE users 
        SET age_new = CAST(age AS INTEGER) 
        WHERE age ~ '^\d+$';  -- Only convert valid numbers
    """)
    
    # Phase 3: Handle invalid data
    op.execute("""
        UPDATE users 
        SET age_new = 0 
        WHERE age IS NOT NULL AND age_new IS NULL;  -- Invalid entries
    """)
    
    # Phase 4: Add NOT NULL constraint
    op.alter_column('users', 'age_new', nullable=False)
    
    # Phase 5: Drop old column (or defer to next migration for safety)
    # op.drop_column('users', 'age')
    # 
    # In next migration after confirming application update:
    # op.drop_column('users', 'age')


def downgrade() -> None:
    """Revert to VARCHAR type."""
    op.execute("""
        UPDATE users 
        SET age = CAST(age_new AS VARCHAR(10))
        WHERE age_new IS NOT NULL;
    """)
    op.drop_column('users', 'age_new')
```

## Example 7: Batch Data Migration

```python
"""Populate user_tier column with default values

Revision ID: stu901vwx234
Revises: pqr678stu901
Create Date: 2026-05-16 12:00:06.000000
"""

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    """Backfill user_tier column.
    
    For large tables, use batch processing to avoid
    locking the entire table.
    """
    
    # Add column
    op.add_column(
        'users',
        sa.Column('user_tier', sa.String(50), default='free', nullable=False)
    )
    
    # Batch update (example for small table)
    # For production large tables, do this in application:
    op.execute("""
        UPDATE users SET user_tier = 'free' WHERE user_tier IS NULL;
    """)


def downgrade() -> None:
    """Drop user_tier column."""
    op.drop_column('users', 'user_tier')
```

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Test rollback
alembic downgrade -1

# Re-apply
alembic upgrade head
```

## Related Documentation

- Alembic docs: https://alembic.sqlalchemy.org/
- PostgreSQL partitioning: https://www.postgresql.org/docs/current/ddl-partitioning.html
- Row-Level Security: https://www.postgresql.org/docs/current/sql-createpolicy.html
- Engineering spec: `/runtime_specs/08_engineering_architecture.md`
