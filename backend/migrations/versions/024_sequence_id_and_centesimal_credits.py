"""Add chat_messages.sequence_id and convert credits to centesimal (×100).

Revision ID: 024_sequence_id_and_centesimal_credits
Revises: 023_user_timezone
Create Date: 2026-07-10

Changes:
  1. chat_messages: ADD COLUMN sequence_id SMALLINT NOT NULL DEFAULT 0
     (ordering within a multi-bubble turn)
  2. users.credits_balance: multiply by 100 (1 display credit → 100 fen)
  3. credit_transactions.delta + balance_after: multiply by 100
  4. redemption_codes.credits_value: multiply by 100
"""

from alembic import op

revision = "024_sequence_id_and_centesimal_credits"
down_revision = "023_user_timezone"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. sequence_id on chat_messages ───────────────────────────────────────
    op.execute(
        "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS sequence_id SMALLINT NOT NULL DEFAULT 0"
    )

    # ── 2. Centesimal credits: multiply all amounts by 100 ────────────────────
    op.execute("UPDATE users SET credits_balance = credits_balance * 100")
    op.execute("UPDATE credit_transactions SET delta = delta * 100")
    op.execute("UPDATE credit_transactions SET balance_after = balance_after * 100")
    op.execute("UPDATE redemption_codes SET credits_value = credits_value * 100")


def downgrade() -> None:
    # Reverse centesimal conversion
    op.execute("UPDATE redemption_codes SET credits_value = credits_value / 100")
    op.execute("UPDATE credit_transactions SET balance_after = balance_after / 100")
    op.execute("UPDATE credit_transactions SET delta = delta / 100")
    op.execute("UPDATE users SET credits_balance = credits_balance / 100")

    op.execute(
        "ALTER TABLE chat_messages DROP COLUMN IF EXISTS sequence_id"
    )
