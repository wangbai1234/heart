"""Account deletion requests and per-character settings.

Revision ID: 013_account_and_char_settings
Revises: 012_credits_and_redemption
Create Date: 2026-07-04 02:00:00.000000

Tables:
  - account_deletion_requests: soft-delete with 30-day grace period
  - user_character_settings: per-character voice toggle (persisted)
"""

from alembic import op

revision = "013_account_and_char_settings"
down_revision = "012_credits_and_redemption"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── account_deletion_requests ──
    op.execute(
        """
    CREATE TABLE account_deletion_requests (
        id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id       UUID NOT NULL,
        requested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        purge_after   TIMESTAMPTZ NOT NULL,
        status        TEXT NOT NULL DEFAULT 'pending',
        completed_at  TIMESTAMPTZ,

        CONSTRAINT chk_deletion_status CHECK (status IN ('pending', 'purged', 'cancelled')),
        CONSTRAINT fk_deletion_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    )
    op.execute(
        "CREATE INDEX ix_deletion_user ON account_deletion_requests (user_id)"
    )
    op.execute(
        "CREATE INDEX ix_deletion_purge ON account_deletion_requests (status, purge_after)"
    )

    # ── user_character_settings ──
    op.execute(
        """
    CREATE TABLE user_character_settings (
        user_id       UUID NOT NULL,
        character_id  TEXT NOT NULL,
        voice_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        PRIMARY KEY (user_id, character_id),
        CONSTRAINT fk_ucs_user
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_character_settings")
    op.execute("DROP TABLE IF EXISTS account_deletion_requests")
