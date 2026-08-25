"""Add referral commissions and yuan-denominated store-credit ledger.

Revision ID: 069_commission
Revises: 068_membership_coupons
"""

from alembic import op

revision = "069_commission"
down_revision = "068_membership_coupons"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS commission_balance_fen INT NOT NULL DEFAULT 0"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS commission_entries (
          id BIGSERIAL PRIMARY KEY,
          inviter_id UUID NOT NULL REFERENCES users(id),
          invitee_id UUID NOT NULL REFERENCES users(id),
          order_id VARCHAR(64) NOT NULL,
          paid_fen INT NOT NULL CHECK (paid_fen > 0),
          commission_fen INT NOT NULL CHECK (commission_fen > 0),
          status VARCHAR(12) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'settled', 'cancelled')),
          settle_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          settled_at TIMESTAMPTZ,
          cancelled_at TIMESTAMPTZ,
          idem_key VARCHAR(80) NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_commission_inviter
        ON commission_entries (inviter_id, status, settle_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS commission_ledger (
          id BIGSERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id),
          delta_fen INT NOT NULL,
          balance_fen INT NOT NULL,
          reason VARCHAR(24) NOT NULL,
          ref_id VARCHAR(64),
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          idem_key VARCHAR(80) NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_commission_ledger_user
        ON commission_ledger (user_id, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS commission_ledger")
    op.execute("DROP TABLE IF EXISTS commission_entries")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS commission_balance_fen")
