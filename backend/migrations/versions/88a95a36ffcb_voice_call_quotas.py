"""voice_call_quotas

Revision ID: 88a95a36ffcb
Revises: 058_chat_messages_channel
Create Date: 2026-08-06 17:08:14.514851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a95a36ffcb'
down_revision: Union[str, Sequence[str], None] = '058_chat_messages_channel'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_voice_call_quotas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            month_key VARCHAR(7) NOT NULL,  -- YYYY-MM format
            used_minutes INTEGER NOT NULL DEFAULT 0 CHECK (used_minutes >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            UNIQUE(user_id, month_key)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_voice_call_quotas_user_month ON user_voice_call_quotas(user_id, month_key)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP TABLE IF EXISTS user_voice_call_quotas CASCADE")
