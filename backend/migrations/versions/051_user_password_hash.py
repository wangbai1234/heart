"""Add password_hash column to users table for password-based authentication.

Current system uses OTP-only login. This migration adds support for password
registration and login. Existing users have NULL password_hash (they continue
using OTP until they set a password).

Revision ID: 051_user_password_hash
Revises: 050_character_tags_cover
Create Date: 2026-07-27 12:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "051_user_password_hash"
down_revision = "050_character_tags_cover"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: safe to re-run on dev/prod (CLAUDE.md DB 铁律).
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_hash")
