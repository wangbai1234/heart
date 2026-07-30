"""053 — Add is_opening column to chat_messages.

Opening scene messages (auto-generated on first chat entry) are stored as
regular chat_messages rows with is_opening=true. This lets them appear in
history naturally while being excluded from billing and analytics.

Partitioned table: ALTER TABLE on the parent propagates to all 32 partitions.
"""

from alembic import op

revision = "053_chat_messages_is_opening"
down_revision = "052_deactivate_retired_characters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS is_opening BOOLEAN NOT NULL DEFAULT FALSE
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS is_opening")
