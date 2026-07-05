"""Redemption codes and Afdian orders for credits system.

Revision ID: 012_credits_and_redemption
Revises: 011_users_and_auth
Create Date: 2026-07-04 01:00:00.000000

Tables:
  - redemption_codes: code pool for Afdian auto-delivery
  - afdian_orders: webhook reconciliation records

Note: credit_transactions was already created in 011_users_and_auth.
"""

from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC

revision = "012_credits_and_redemption"
down_revision = "011_users_and_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── redemption_codes ──
    op.execute(
        """
    CREATE TABLE redemption_codes (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        code          TEXT NOT NULL,
        credits_value BIGINT NOT NULL CHECK (credits_value > 0),
        batch_id      TEXT,
        status        TEXT NOT NULL DEFAULT 'active',
        redeemed_by   UUID,
        redeemed_at   TIMESTAMPTZ,
        expires_at    TIMESTAMPTZ,
        created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT uq_redemption_code UNIQUE (code),
        CONSTRAINT chk_code_status CHECK (status IN ('active', 'redeemed', 'disabled')),
        CONSTRAINT fk_code_redeemed_by
            FOREIGN KEY (redeemed_by) REFERENCES users(id) ON DELETE SET NULL
    )
    """
    )
    op.execute("CREATE INDEX ix_redemption_codes_status ON redemption_codes (status)")
    op.execute("CREATE INDEX ix_redemption_codes_batch ON redemption_codes (batch_id)")

    # ── afdian_orders (webhook reconciliation) ──
    op.execute(
        """
    CREATE TABLE afdian_orders (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        out_trade_no  TEXT NOT NULL,
        plan_id       TEXT,
        sku_detail    JSONB,
        total_amount  NUMERIC(10, 2),
        remark        TEXT,
        raw_payload   JSONB,
        received_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT uq_afdian_out_trade UNIQUE (out_trade_no)
    )
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS afdian_orders")
    op.execute("DROP TABLE IF EXISTS redemption_codes")
