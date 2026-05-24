"""SS04 Relationship threshold tuning v1.1

Revision ID: 003_ss04_threshold_tuning_v1_1
Revises: 002_add_emotion_relationship_tables
Create Date: 2026-05-20 14:00:00.000000

Adds:
  - stage_thresholds JSONB column for per-stage configurable thresholds
  - Index on (current_stage, intimacy_level) for threshold-aware queries

V1.0 thresholds were hardcoded in the phase engine.
V1.1 moves them into a data column so thresholds can be tuned
per-deployment (e.g., A/B test different progression speeds)
without a schema migration.
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "003_ss04_threshold_tuning_v1_1"
down_revision = "002_add_emotion_relationship_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add stage_thresholds JSONB column with empty default
    op.execute(
        """
    ALTER TABLE relationship_states
        ADD COLUMN IF NOT EXISTS stage_thresholds JSONB NOT NULL DEFAULT '{}'::jsonb
    """
    )

    # Index for threshold-aware stage queries
    op.execute(
        """
    CREATE INDEX IF NOT EXISTS idx_rel_stage_threshold
        ON relationship_states (current_stage, intimacy_level DESC)
    """
    )


def downgrade() -> None:
    # Drop the index first (depends on column)
    op.execute("DROP INDEX IF EXISTS idx_rel_stage_threshold")
    # Remove the column
    op.execute("ALTER TABLE relationship_states DROP COLUMN IF EXISTS stage_thresholds")
