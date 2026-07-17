"""033 — Add is_proactive column to chat_messages.

Proactive v2 generates messages via the full ComposerService and stores
them directly in chat_messages (role='assistant', is_proactive=true) so
they appear naturally in conversation context. The proactive_messages table
is retained for audit/quota tracking.

Partitioned table: ALTER TABLE on the parent propagates to all 32 partitions.
"""

from alembic import op

revision = "033_chat_messages_is_proactive"
down_revision = "032_female_warm_voice_id_tianmei"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS is_proactive BOOLEAN NOT NULL DEFAULT FALSE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chat_msg_is_proactive
        ON chat_messages (user_id, character_id, is_proactive)
        WHERE is_proactive = TRUE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_msg_is_proactive")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS is_proactive")
