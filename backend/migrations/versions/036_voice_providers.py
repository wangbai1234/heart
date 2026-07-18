"""Add voice_provider column to character_voices; update preset_voices catalog.

Revision ID: 036_voice_providers
Revises: 035_afdian_fulfill
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op

revision = "036_voice_providers"
down_revision = "035_afdian_fulfill"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Track which TTS provider owns each character's voice
    op.execute(
        """
        ALTER TABLE character_voices
            ADD COLUMN IF NOT EXISTS voice_provider VARCHAR(32)
        """
    )
    # Backfill existing rows: if preset_voice_id is set, look it up;
    # otherwise default to 'minimax' (legacy clone rows)
    op.execute(
        """
        UPDATE character_voices cv
        SET voice_provider = COALESCE(
            (SELECT provider FROM preset_voices WHERE id = cv.preset_voice_id),
            'minimax'
        )
        WHERE voice_provider IS NULL
        """
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE character_voices DROP COLUMN IF EXISTS voice_provider"
    )
