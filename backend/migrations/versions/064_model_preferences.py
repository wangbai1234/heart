"""Per-user, per-character selectable model preferences.

Revision ID: 064_model_preferences
Revises: 063_chat_msg_soft_delete
Create Date: 2026-08-20
"""

from alembic import op

revision = "064_model_preferences"
down_revision = "063_chat_msg_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_character_model_preferences (
            user_id UUID NOT NULL REFERENCES users(id),
            character_id TEXT NOT NULL,
            model_id TEXT NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, character_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_character_model_preferences")

