"""Persist interface, response-language and action-format preferences."""

from alembic import op

revision = "077_language_preferences"
down_revision = "076_lottery_pool_v2_probabilities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_language_preferences (
            user_id UUID PRIMARY KEY REFERENCES users(id),
            interface_language VARCHAR(2) NOT NULL DEFAULT 'en'
                CHECK (interface_language IN ('en', 'ja', 'ko')),
            response_language VARCHAR(2) NOT NULL DEFAULT 'en'
                CHECK (response_language IN ('en', 'ja', 'ko')),
            action_style VARCHAR(16) NOT NULL DEFAULT 'parentheses'
                CHECK (action_style IN ('parentheses', 'asterisks', 'fullwidth')),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    # User preferences are retained across application rollback.
    pass
