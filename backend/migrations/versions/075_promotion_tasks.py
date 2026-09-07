"""Add social promotion task submissions and milestone tracking.

Revision ID: 075_promotion_tasks
Revises: 074_launch_character_recommendations
"""

from alembic import op

revision = "075_promotion_tasks"
down_revision = "074_launch_character_recommendations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS promotion_submissions (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          task_type VARCHAR(24) NOT NULL CHECK (task_type IN ('ambassador', 'creator', 'likes')),
          platform VARCHAR(16) NOT NULL CHECK (platform IN ('douyin', 'xiaohongshu')),
          screenshot_url TEXT,
          post_url TEXT,
          normalized_url TEXT,
          title TEXT,
          source_submission_id UUID REFERENCES promotion_submissions(id) ON DELETE SET NULL,
          likes_count INTEGER CHECK (likes_count IS NULL OR likes_count >= 0),
          status VARCHAR(16) NOT NULL DEFAULT 'pending'
            CHECK (status IN ('pending', 'approved', 'needs_info', 'rejected')),
          review_reason TEXT,
          reviewed_at TIMESTAMPTZ,
          reviewed_by TEXT,
          reward_coins INTEGER NOT NULL DEFAULT 0,
          milestone_300_granted BOOLEAN NOT NULL DEFAULT FALSE,
          milestone_1000_granted BOOLEAN NOT NULL DEFAULT FALSE,
          submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promotion_submissions_user_day "
        "ON promotion_submissions (user_id, submitted_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promotion_submissions_review "
        "ON promotion_submissions (status, task_type, submitted_at)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_promotion_creator_url "
        "ON promotion_submissions (normalized_url) WHERE task_type = 'creator' "
        "AND normalized_url IS NOT NULL AND status IN ('pending','approved','needs_info')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promotion_source_submission "
        "ON promotion_submissions (source_submission_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS promotion_submissions")
