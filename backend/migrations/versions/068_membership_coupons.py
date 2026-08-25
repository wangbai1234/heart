"""Add lottery membership experience coupon wallet.

Revision ID: 068_membership_coupons
Revises: 067_lottery_pool
"""

from alembic import op

revision = "068_membership_coupons"
down_revision = "067_lottery_pool"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS membership_reward_coupons (
          id BIGSERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          tier VARCHAR(16) NOT NULL CHECK (tier IN ('plus', 'immersive')),
          days INT NOT NULL CHECK (days IN (3, 30)),
          source VARCHAR(32) NOT NULL,
          granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          activate_by TIMESTAMPTZ NOT NULL,
          activated_at TIMESTAMPTZ,
          starts_at TIMESTAMPTZ,
          expires_at TIMESTAMPTZ,
          status VARCHAR(12) NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'activated', 'expired')),
          idem_key VARCHAR(64) NOT NULL UNIQUE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_coupons_user
        ON membership_reward_coupons (user_id, status)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS membership_reward_coupons")
