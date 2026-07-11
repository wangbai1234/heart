"""028 — Add deletion_grace_end to users; stop anonymizing email on delete.

Root cause of the re-signup credit exploit:
  delete_account() anonymized email to deleted+uuid@invalid
  → verify_otp() could not find user by email
  → is_new_user = True → INSERT new user → signup_grant issued again
  → Infinite credits via register-spend-delete-reregister loop.

Fix: keep the original email on delete; set deletion_grace_end so
verify_otp() can detect the grace period and return needs_restoration
instead of creating a fresh account.
"""

from alembic import op

revision = "028_soft_delete_email"
down_revision = "027_preset_voice_gender"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deletion_grace_end TIMESTAMPTZ NULL
    """)

    # Back-fill existing deleted accounts: their emails are already anonymized
    # (deleted+uuid@invalid) so we can't undo that, but we can set a
    # grace_end = NOW() (expired) so they're not offered restoration.
    op.execute("""
        UPDATE users
        SET deletion_grace_end = NOW()
        WHERE status = 'deleted' AND deletion_grace_end IS NULL
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS deletion_grace_end")
