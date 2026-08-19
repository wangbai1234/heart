"""Soft-delete (logical hide) support for chat_messages.

Revision ID: 063_chat_msg_soft_delete
Revises: 062_rename_tag_chunjie_to_jie
Create Date: 2026-08-19 00:00:00.000000

Adds two nullable columns to the HASH-partitioned chat_messages table:

    rewound_at    TIMESTAMPTZ NULL  -- when the row was logically hidden (NULL = live)
    hidden_reason TEXT        NULL  -- discriminator: 'list_delete' | 'rewind' | 'restart'

Motivation
----------
Two product features share ONE visibility marker on chat_messages but keep
their side effects strictly separate (this is deliberate — see routes):

  - 左滑删除 (list delete): hides bubbles on the inbox, marker only.
    Memory / emotion / relationship are PRESERVED.
  - 时光回溯 (rewind) / 重新开始 (restart): hide bubbles AND roll back the
    associated memory (do_not_recall) + emotion/relationship state.

We never physically DELETE user chat rows (AGENTS.md: "No hard deletes on
user data — use logical delete"). All read paths gain a ``rewound_at IS NULL``
predicate; a partial index keeps the live-row scan cheap.

ALTER TABLE on the partitioned parent propagates the columns to all 32
partitions automatically. The partial index is created on the parent with a
predicate, which Postgres cascades to each partition.
"""

from alembic import op

revision = "063_chat_msg_soft_delete"
down_revision = "062_rename_tag_chunjie_to_jie"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent column adds (dev/prod re-run safe).
    op.execute(
        "ALTER TABLE chat_messages "
        "ADD COLUMN IF NOT EXISTS rewound_at TIMESTAMPTZ NULL"
    )
    op.execute(
        "ALTER TABLE chat_messages "
        "ADD COLUMN IF NOT EXISTS hidden_reason TEXT NULL"
    )

    # Partial index over LIVE rows only: matches the hot read pattern
    # (user_id, character_id, created_at DESC WHERE rewound_at IS NULL).
    # Hidden rows fall out of the index entirely, so the live-history scan
    # stays as cheap as before the feature landed.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_msg_live_user_char_created "
        "ON chat_messages (user_id, character_id, created_at DESC) "
        "WHERE rewound_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_msg_live_user_char_created")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS hidden_reason")
    op.execute("ALTER TABLE chat_messages DROP COLUMN IF EXISTS rewound_at")
