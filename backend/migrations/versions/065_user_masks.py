"""Add user-owned masks (explicit personas) for character conversations."""

from alembic import op

revision = "065_user_masks"
down_revision = "064_model_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE user_masks (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(80) NOT NULL,
            gender VARCHAR(20) NOT NULL DEFAULT 'unspecified',
            bio TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX ix_user_masks_user_id ON user_masks(user_id)")
    op.execute(
        """
        CREATE TABLE user_character_mask_bindings (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            character_id TEXT NOT NULL,
            mask_id UUID NOT NULL REFERENCES user_masks(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_user_character_active_mask
        ON user_character_mask_bindings(user_id, character_id)
        WHERE deleted_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_user_character_mask_bindings_mask
        ON user_character_mask_bindings(mask_id)
        WHERE deleted_at IS NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_character_mask_bindings")
    op.execute("DROP TABLE IF EXISTS user_masks")
