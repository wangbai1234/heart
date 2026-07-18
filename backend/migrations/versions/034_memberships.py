"""Create user_memberships table.

Revision ID: 034_memberships
Revises: 033_chat_messages_is_proactive
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "034_memberships"
down_revision = "033_chat_messages_is_proactive"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_memberships (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL,
            tier        VARCHAR(32) NOT NULL DEFAULT 'plus',
            expires_at  TIMESTAMPTZ NOT NULL,
            granted_by  VARCHAR(64) NOT NULL DEFAULT 'manual',
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_user_memberships_user_expires
        ON user_memberships (user_id, expires_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_user_memberships_user_expires")
    op.execute("DROP TABLE IF EXISTS user_memberships")
