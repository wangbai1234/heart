"""057 — per-user voice overrides on character_voices.

Before this migration ``character_voices`` was keyed ``UNIQUE(character_id,
voice_provider)`` — a single GLOBAL voice row per character/provider. Whoever
wrote it, everyone heard it, and only the character owner could write one. That
blocked the intended product model:

  - self-owned private character → owner configures freely (canonical);
  - public character with a creator-published voice → everyone hears it;
  - public character WITHOUT a creator voice → any user may configure a voice
    only THEY hear (a personal override), without publishing it to others.

This migration introduces ``is_public`` to split the two cases:

  - ``is_public = TRUE``  → the character's canonical voice (owner/seed set it).
    At most one per (character, voice_provider).
  - ``is_public = FALSE`` → a per-user personal override. At most one per
    (character, voice_provider, user_id).

Existing rows are all treated as canonical (backfill ``is_public = TRUE``) so
current behaviour is preserved exactly.

Revision ID: 057_per_user_voice_override
Revises: 056_character_review
Create Date: 2026-08-04
"""

from __future__ import annotations

from alembic import op

revision = "057_per_user_voice_override"
down_revision = "056_character_review"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. New discriminator column. Default TRUE so any row created by older code
    #    paths mid-deploy is treated as canonical (safe: old code is owner-only).
    op.execute(
        """
        ALTER TABLE character_voices
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT TRUE
        """
    )
    # Existing rows are the pre-migration global voices → canonical.
    op.execute("UPDATE character_voices SET is_public = TRUE WHERE is_public IS NULL")

    # 2. Drop the single-global-row constraint (added by 039) so multiple users
    #    can each hold a personal override for the same (character, provider).
    op.execute(
        "ALTER TABLE character_voices "
        "DROP CONSTRAINT IF EXISTS uq_character_voices_char_provider"
    )

    # 3a. At most one CANONICAL (public) voice per character/provider. Partial
    #     unique index so personal-override rows don't collide with it.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_char_voice_public
            ON character_voices (character_id, voice_provider)
            WHERE is_public
        """
    )
    # 3b. At most one PERSONAL override per (character, provider, user). Only
    #     applies to non-public rows with a concrete user_id (canonical seeds
    #     may have user_id NULL and are covered by 3a instead).
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_char_voice_personal
            ON character_voices (character_id, voice_provider, user_id)
            WHERE NOT is_public AND user_id IS NOT NULL
        """
    )


def downgrade() -> None:
    # Personal overrides must go before we can restore single-row uniqueness,
    # otherwise the constraint add would fail on duplicate (character, provider).
    op.execute("DELETE FROM character_voices WHERE is_public = FALSE")
    op.execute("DROP INDEX IF EXISTS uq_char_voice_personal")
    op.execute("DROP INDEX IF EXISTS uq_char_voice_public")
    op.execute(
        """
        ALTER TABLE character_voices
            ADD CONSTRAINT uq_character_voices_char_provider
            UNIQUE (character_id, voice_provider)
        """
    )
    op.execute("ALTER TABLE character_voices DROP COLUMN IF EXISTS is_public")
