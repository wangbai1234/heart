"""Chat messages table for conversation persistence.

Revision ID: 014_chat_messages
Revises: 013_account_and_char_settings
Create Date: 2026-07-04 03:00:00.000000

Table: chat_messages (HASH partitioned by user_id × 32)
"""

from alembic import op

revision = "014_chat_messages"
down_revision = "013_account_and_char_settings"
branch_labels = None
depends_on = None

NUM_PARTITIONS = 32


def upgrade() -> None:
    # Parent table (partitioned)
    op.execute(
        """
    CREATE TABLE chat_messages (
        id              UUID NOT NULL,
        user_id         UUID NOT NULL,
        character_id    TEXT NOT NULL,
        session_id      UUID,
        turn_id         UUID,
        role            TEXT NOT NULL,
        content         TEXT NOT NULL,
        modality        TEXT NOT NULL DEFAULT 'text',
        audio_url       TEXT,
        audio_duration_ms INTEGER,
        credits_charged INTEGER,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        PRIMARY KEY (id, user_id),
        CONSTRAINT chk_msg_role CHECK (role IN ('user', 'assistant')),
        CONSTRAINT chk_msg_modality CHECK (modality IN ('text', 'voice'))
    ) PARTITION BY HASH (user_id)
    """
    )

    # Create 32 partitions
    for i in range(NUM_PARTITIONS):
        op.execute(
            f"CREATE TABLE chat_messages_p{i} "
            f"PARTITION OF chat_messages FOR VALUES WITH (MODULUS {NUM_PARTITIONS}, REMAINDER {i})"
        )

    # Indexes on parent (auto-propagated to partitions)
    op.execute(
        "CREATE INDEX ix_chat_msg_user_char_created "
        "ON chat_messages (user_id, character_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_chat_msg_turn ON chat_messages (turn_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS chat_messages CASCADE")
