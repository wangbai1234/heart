"""Add fulfillment tracking columns to afdian_orders + binding_codes table.

Revision ID: 035_afdian_fulfill
Revises: 034_memberships
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op

revision = "035_afdian_fulfill"
down_revision = "034_memberships"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fulfillment state on afdian_orders
    op.execute(
        """
        ALTER TABLE afdian_orders
            ADD COLUMN IF NOT EXISTS fulfilled_at    TIMESTAMPTZ,
            ADD COLUMN IF NOT EXISTS fulfillment_error TEXT,
            ADD COLUMN IF NOT EXISTS resolved_user_id  UUID
        """
    )
    # Binding codes: user generates a short code → embeds in afdian remark
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_binding_codes (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL,
            code        VARCHAR(32) NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at  TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
            used_at     TIMESTAMPTZ,
            CONSTRAINT uq_binding_code UNIQUE (code)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_binding_codes_user
        ON user_binding_codes (user_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_binding_codes_user")
    op.execute("DROP TABLE IF EXISTS user_binding_codes")
    op.execute(
        """
        ALTER TABLE afdian_orders
            DROP COLUMN IF EXISTS fulfilled_at,
            DROP COLUMN IF EXISTS fulfillment_error,
            DROP COLUMN IF EXISTS resolved_user_id
        """
    )
