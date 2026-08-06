"""059 — Extend chat_messages.kind CHECK for transfer bubbles.

WeChat-style money-transfer feature persists the gesture as chat_messages rows:
  kind='transfer'          — the transfer bubble (pending / accepted / declined)
  kind='transfer_receipt'  — the "已收款" receipt bubble after the character accepts

Both are normal rows (channel='chat') so they show in history and survive refresh.
The kind CHECK constraint (last set in 058) must admit the two new values or the
INSERT fails with chat_messages_kind_check violation.

Partitioned table: ALTER TABLE on the parent propagates to all partitions.
Idempotent: DROP IF EXISTS then re-ADD.
"""

from alembic import op

revision = "059_kind_transfer"
down_revision = "88a95a36ffcb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_kind_check")
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_kind_check
        CHECK (kind IN ('text', 'action', 'call_summary', 'transfer', 'transfer_receipt'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_kind_check")
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_kind_check
        CHECK (kind IN ('text', 'action', 'call_summary'))
        """
    )
