"""Add user_character_read_state table for per-character read tracking.

Revision ID: 029_read_state
Revises: 028_soft_delete_email
Create Date: 2026-07-11
"""
from alembic import op

revision = "029_read_state"
down_revision = "028_soft_delete_email"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE user_character_read_state (
            user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            character_id TEXT NOT NULL,
            last_read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, character_id)
        )
    """)
    op.execute(
        "CREATE INDEX ix_ucrs_user_id ON user_character_read_state(user_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_character_read_state")
