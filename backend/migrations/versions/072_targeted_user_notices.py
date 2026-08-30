"""Add account-targeted one-off notices.

Revision ID: 072_targeted_user_notices
Revises: 071_recovery_notice_receipts
"""

from alembic import op

revision = "072_targeted_user_notices"
down_revision = "071_recovery_notice_receipts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_notices (
          id VARCHAR(80) PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          eyebrow VARCHAR(40) NOT NULL DEFAULT '专属消息',
          title VARCHAR(160) NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          content TEXT NOT NULL,
          confirm_label VARCHAR(40) NOT NULL DEFAULT '我已了解',
          qr_image_url TEXT,
          starts_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          ends_at TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CHECK (ends_at IS NULL OR ends_at > starts_at)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_user_notices_user_active "
        "ON user_notices (user_id, starts_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_user_notices_user_active")
    op.execute("DROP TABLE IF EXISTS user_notices")
