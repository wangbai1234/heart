"""Track whether replies follow the interface language."""

from alembic import op

revision = "078_language_follow"
down_revision = "077_language_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable only during backfill, preserving pre-existing independent choices.
    op.execute(
        "ALTER TABLE user_language_preferences ADD COLUMN IF NOT EXISTS response_follows_interface BOOLEAN"
    )
    op.execute(
        "UPDATE user_language_preferences SET response_follows_interface = (response_language = interface_language) WHERE response_follows_interface IS NULL"
    )
    op.execute(
        "ALTER TABLE user_language_preferences ALTER COLUMN response_follows_interface SET DEFAULT TRUE"
    )
    op.execute(
        "ALTER TABLE user_language_preferences ALTER COLUMN response_follows_interface SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE user_language_preferences ALTER COLUMN action_style SET DEFAULT 'fullwidth'"
    )


def downgrade() -> None:
    # Retain saved preferences across application rollback.
    pass
