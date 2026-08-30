"""Add per-account notice acknowledgement receipts.

Revision ID: 071_recovery_notice_receipts
Revises: 070_referral_risk
"""

from alembic import op

revision = "071_recovery_notice_receipts"
down_revision = "070_referral_risk"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_notice_receipts (
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          notice_id VARCHAR(80) NOT NULL,
          seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          PRIMARY KEY (user_id, notice_id)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_notice_receipts")
