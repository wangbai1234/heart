"""Dual-provider voices: per-(character, provider) rows + per-user selection.

Issue 3 requires a character (e.g. rin/dorothy) to carry BOTH a MiMo clone and
a Fish clone at once, with paid users toggling between them instantly. The old
``character_voices UNIQUE(character_id)`` allowed only one row per character, so
this migration:

  1. Relaxes ``character_voices`` to ``UNIQUE(character_id, voice_provider)`` —
     one voice row per provider per character (mimo / fish / minimax).
  2. Adds ``user_character_settings.voice_provider`` — the per-user choice of
     which engine to speak with (default 'mimo'; free tier is locked to mimo by
     the API tier gate, not by this column).

Revision ID: 039_dual_provider_voices
Revises: 038_mimo_preset_seeds
Create Date: 2026-07-19
"""

from __future__ import annotations

from alembic import op

revision = "039_dual_provider_voices"
down_revision = "038_mimo_preset_seeds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. character_voices: make voice_provider authoritative + widen uniqueness.
    #    Backfill any residual NULLs (036 backfilled existing rows, but be safe
    #    for rows created between 036 and here) before enforcing NOT NULL.
    op.execute(
        """
        UPDATE character_voices
        SET voice_provider = 'mimo'
        WHERE voice_provider IS NULL
        """
    )
    op.execute(
        """
        ALTER TABLE character_voices
            ALTER COLUMN voice_provider SET DEFAULT 'mimo'
        """
    )
    op.execute(
        """
        ALTER TABLE character_voices
            ALTER COLUMN voice_provider SET NOT NULL
        """
    )
    # Drop the single-row-per-character constraint (auto-named by 025's inline
    # UNIQUE(character_id)) and any stray unique index, then add the compound.
    op.execute(
        "ALTER TABLE character_voices "
        "DROP CONSTRAINT IF EXISTS character_voices_character_id_key"
    )
    op.execute("DROP INDEX IF EXISTS character_voices_character_id_key")
    op.execute(
        """
        ALTER TABLE character_voices
            ADD CONSTRAINT uq_character_voices_char_provider
            UNIQUE (character_id, voice_provider)
        """
    )

    # 2. user_character_settings: per-user engine selection.
    op.execute(
        """
        ALTER TABLE user_character_settings
            ADD COLUMN IF NOT EXISTS voice_provider VARCHAR(32) NOT NULL DEFAULT 'mimo'
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE user_character_settings DROP COLUMN IF EXISTS voice_provider"
    )
    op.execute(
        "ALTER TABLE character_voices "
        "DROP CONSTRAINT IF EXISTS uq_character_voices_char_provider"
    )
    # Restore the single-row-per-character uniqueness (best effort — will fail if
    # duplicate providers exist for a character; that is intentional so a
    # downgrade surfaces the data conflict rather than silently dropping rows).
    op.execute(
        """
        ALTER TABLE character_voices
            ADD CONSTRAINT character_voices_character_id_key UNIQUE (character_id)
        """
    )
