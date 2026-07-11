"""026 — Add chat_messages.kind for text/action bubble distinction.

Semantic bubble splitter (PR 2) emits two kinds of segments:
  - 'text':   normal dialog, billed per bubble, gets TTS in voice mode
  - 'action': parenthetical action / narration, unbilled, no TTS

The column is added as a plain VARCHAR with a CHECK constraint (no ENUM
type) so adding a new kind later is a code-only change.
"""

from alembic import op

revision = "026_message_kind"
down_revision = "025_voice_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE chat_messages
            ADD COLUMN IF NOT EXISTS kind VARCHAR(16) NOT NULL DEFAULT 'text'
    """)
    op.execute("""
        ALTER TABLE chat_messages
            DROP CONSTRAINT IF EXISTS chat_messages_kind_check
    """)
    op.execute("""
        ALTER TABLE chat_messages
            ADD CONSTRAINT chat_messages_kind_check
            CHECK (kind IN ('text', 'action'))
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE chat_messages DROP CONSTRAINT IF EXISTS chat_messages_kind_check")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS kind")
