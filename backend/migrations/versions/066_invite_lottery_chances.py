"""Upgrade invite qualification and add the draw chance ledger.

Revision ID: 066_invite_lottery_chances
Revises: 065_user_masks
"""

from alembic import op

revision = "066_invite_lottery_chances"
down_revision = "065_user_masks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE user_invite_uses
          ADD COLUMN IF NOT EXISTS msg_count INT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS ai_reply_count INT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS valid_char_count INT NOT NULL DEFAULT 0,
          ADD COLUMN IF NOT EXISTS first_msg_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS qualified_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS status VARCHAR(16) NOT NULL DEFAULT 'pending',
          ADD COLUMN IF NOT EXISTS risk_level VARCHAR(8) NOT NULL DEFAULT 'low',
          ADD COLUMN IF NOT EXISTS chance_granted_at TIMESTAMPTZ,
          ADD COLUMN IF NOT EXISTS chance_limit_reached_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        UPDATE user_invite_uses
        SET qualified_at = first_chat_at,
            status = 'qualified'
        WHERE first_chat_at IS NOT NULL
          AND qualified_at IS NULL
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS invite_qualification_events (
          id BIGSERIAL PRIMARY KEY,
          invite_use_id BIGINT NOT NULL REFERENCES user_invite_uses(id) ON DELETE CASCADE,
          turn_id UUID NOT NULL,
          text_hash VARCHAR(64) NOT NULL,
          valid_char_count INT NOT NULL CHECK (valid_char_count > 0),
          ai_reply_completed BOOLEAN NOT NULL DEFAULT TRUE,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CONSTRAINT uq_invite_qualification_turn UNIQUE (invite_use_id, turn_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_invite_qualification_events_use
        ON invite_qualification_events (invite_use_id, created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS invite_draw_chances (
          id BIGSERIAL PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          source VARCHAR(24) NOT NULL,
          grant_day DATE NOT NULL,
          daily_ordinal SMALLINT NOT NULL CHECK (daily_ordinal > 0),
          granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          expires_at TIMESTAMPTZ NOT NULL,
          consumed_at TIMESTAMPTZ,
          draw_id BIGINT,
          idem_key VARCHAR(64) NOT NULL UNIQUE,
          CONSTRAINT uq_draw_chance_daily_ordinal
            UNIQUE (user_id, grant_day, daily_ordinal)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_draw_chances_user_avail
        ON invite_draw_chances (user_id, expires_at)
        WHERE consumed_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS invite_draw_chances")
    op.execute("DROP TABLE IF EXISTS invite_qualification_events")
    op.execute(
        """
        ALTER TABLE user_invite_uses
          DROP COLUMN IF EXISTS chance_limit_reached_at,
          DROP COLUMN IF EXISTS chance_granted_at,
          DROP COLUMN IF EXISTS risk_level,
          DROP COLUMN IF EXISTS status,
          DROP COLUMN IF EXISTS qualified_at,
          DROP COLUMN IF EXISTS first_msg_at,
          DROP COLUMN IF EXISTS valid_char_count,
          DROP COLUMN IF EXISTS ai_reply_count,
          DROP COLUMN IF EXISTS msg_count
        """
    )
