"""Create opening_history table for idempotent opening generation.

Revision ID: 054_opening_history
Revises: 053_chat_messages_is_opening
"""

from alembic import op
from sqlalchemy import text

revision = "054_opening_history"
down_revision = "053_chat_messages_is_opening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text("""
            CREATE TABLE IF NOT EXISTS opening_history (
                user_id      UUID NOT NULL,
                character_id VARCHAR(64) NOT NULL,
                created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (user_id, character_id)
            )
        """)
    )


def downgrade() -> None:
    op.execute(text("DROP TABLE IF EXISTS opening_history"))
