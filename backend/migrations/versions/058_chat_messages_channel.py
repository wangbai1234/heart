"""058 — Add chat_messages.channel + extend kind CHECK for call_summary.

Voice-call turns are persisted like any other turn (billing / audio / memory
extraction all depend on the row existing) but marked channel='call' so the
chat-history endpoint can hide them: after a call the user should see ONE
WeChat-style summary bubble ("通话时长 XX:XX"), not N voice bubbles.

The summary itself is a normal row with kind='call_summary' (channel='chat'),
so it shows in history and survives refresh.

Partitioned table: ALTER TABLE on the parent propagates to all 32 partitions.
"""

from alembic import op

revision = "058_chat_messages_channel"
down_revision = "057_per_user_voice_override"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD COLUMN IF NOT EXISTS channel VARCHAR(16) NOT NULL DEFAULT 'chat'
        """
    )
    # Extend the kind CHECK to admit the call-summary bubble (idempotent).
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_kind_check")
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_kind_check
        CHECK (kind IN ('text', 'action', 'call_summary'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_kind_check")
    op.execute(
        """
        ALTER TABLE chat_messages
        ADD CONSTRAINT chat_messages_kind_check
        CHECK (kind IN ('text', 'action'))
        """
    )
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS channel")
