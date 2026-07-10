"""Add timezone column to users table.

Revision ID: 023_user_timezone
Revises: 021_character_content
Create Date: 2026-07-10

Adds users.timezone (IANA tz name, default 'Asia/Shanghai') so the inner
loop worker can convert UTC to the user's local time before making
morning/night proactive scheduling decisions.
"""

from alembic import op

revision = "023_user_timezone"
down_revision = "021_character_content"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai'
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS timezone")
