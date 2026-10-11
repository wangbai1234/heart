"""Persist stable Google subjects independently of mutable email addresses."""
from alembic import op

revision = "079_google_identities"
down_revision = "078_language_follow"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
        CREATE TABLE IF NOT EXISTS oauth_identities (
            provider VARCHAR(30) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (provider, subject),
            UNIQUE (provider, user_id)
        )
    """)


def downgrade():
    # Preserve account identity bindings across application rollback.
    pass
