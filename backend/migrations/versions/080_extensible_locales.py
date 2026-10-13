"""Expand language storage while retaining legacy preference compatibility."""

from alembic import op

revision = "080_extensible_locales"
down_revision = "079_google_identities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE user_language_preferences
          DROP CONSTRAINT IF EXISTS user_language_preferences_interface_language_check,
          DROP CONSTRAINT IF EXISTS user_language_preferences_response_language_check;
    """)
    op.execute("""
        ALTER TABLE user_language_preferences
          ALTER COLUMN interface_language TYPE VARCHAR(64),
          ALTER COLUMN response_language TYPE VARCHAR(64);
    """)
    op.execute("""
        ALTER TABLE user_language_preferences
          ADD COLUMN IF NOT EXISTS response_mode VARCHAR(16);
    """)
    op.execute("""
        UPDATE user_language_preferences
        SET response_mode = CASE WHEN response_follows_interface THEN 'auto' ELSE 'fixed' END
        WHERE response_mode IS NULL
    """)
    op.execute("""
        ALTER TABLE user_language_preferences
          ALTER COLUMN response_mode SET DEFAULT 'auto',
          ALTER COLUMN response_mode SET NOT NULL;
    """)
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint
            WHERE conrelid = 'user_language_preferences'::regclass
              AND conname = 'language_preferences_response_mode_check') THEN
            ALTER TABLE user_language_preferences ADD CONSTRAINT language_preferences_response_mode_check
              CHECK (response_mode IN ('auto', 'interface', 'character', 'fixed'));
          END IF;
        END $$;
    """)


def downgrade() -> None:
    # Narrowing language values would destroy post-launch preferences. Keep the
    # expanded schema and roll back only to a compatible application build.
    pass
