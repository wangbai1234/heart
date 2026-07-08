"""Characters directory table (UGC refactor C2).

Revision ID: 019_characters_directory
Revises: 018_proactive_messages
Create Date: 2026-07-08 18:30:00.000000

Introduces a global ``characters`` catalog — the single place that answers
"which character ids exist, who owns them, and are they visible". Today it holds
only the two system built-ins (``rin`` / ``dorothy``); a later UGC phase (C3+)
will let users insert their own rows here.

Design notes:
  - ``id`` is the free-text character key already used across the per-user tables
    (chat_messages, user_character_settings, ...). Backfilling the built-ins with
    their existing ids means ZERO data migration — nothing on the per-user side
    changes, this table just makes the id set explicit and validatable.
  - No ``display_name`` column: identity/display is derived from the Soul Spec via
    the SoulRegistry (see ss01_soul.character_content.get_display_name). Keeping the
    name out of this table preserves the Soul Spec as the single source of truth for
    who a character is; this catalog only tracks catalog concerns
    (ownership / visibility / status / spec-version pointer).
  - ``owner_user_id IS NULL`` marks a system built-in; a UGC character will carry
    the creating user's id.
"""

from alembic import op

revision = "019_characters_directory"
down_revision = "018_proactive_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE characters (
        id                TEXT PRIMARY KEY,
        owner_user_id     UUID,                       -- NULL = system built-in
        visibility        TEXT NOT NULL DEFAULT 'public',
        status            TEXT NOT NULL DEFAULT 'active',
        soul_spec_version TEXT,                        -- pointer to the active Soul Spec version
        created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT chk_char_visibility CHECK (visibility IN ('public', 'unlisted', 'private')),
        CONSTRAINT chk_char_status CHECK (status IN ('active', 'disabled')),
        CONSTRAINT fk_char_owner
            FOREIGN KEY (owner_user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    )
    op.execute("CREATE INDEX ix_characters_visibility ON characters (visibility, status)")
    op.execute("CREATE INDEX ix_characters_owner ON characters (owner_user_id)")

    # Backfill the two system built-ins. Idempotent-safe on re-run via ON CONFLICT.
    op.execute(
        """
    INSERT INTO characters (id, owner_user_id, visibility, status, soul_spec_version)
    VALUES ('rin',     NULL, 'public', 'active', '1.0.0'),
           ('dorothy', NULL, 'public', 'active', '1.0.0')
    ON CONFLICT (id) DO NOTHING
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS characters")
