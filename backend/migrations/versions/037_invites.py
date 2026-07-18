"""Invite codes and invite-use tracking tables.

Revision ID: 037_invites
Revises: 036_voice_providers
Create Date: 2026-07-18
"""

from __future__ import annotations

from alembic import op

revision = "037_invites"
down_revision = "036_voice_providers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_invite_codes (
            id          BIGSERIAL PRIMARY KEY,
            user_id     UUID        NOT NULL UNIQUE,
            code        VARCHAR(16) NOT NULL UNIQUE,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_invite_codes_code "
        "ON user_invite_codes (code)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_invite_uses (
            id              BIGSERIAL   PRIMARY KEY,
            inviter_id      UUID        NOT NULL,
            invitee_id      UUID        NOT NULL UNIQUE,
            code            VARCHAR(16) NOT NULL,
            created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            first_chat_at   TIMESTAMPTZ,
            milestone_5_at  TIMESTAMPTZ,
            milestone_10_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_invite_uses_inviter "
        "ON user_invite_uses (inviter_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_invite_uses")
    op.execute("DROP TABLE IF EXISTS user_invite_codes")
