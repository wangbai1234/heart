"""Add safety_events table for PURPLE crisis audit trail.

Revision ID: 005_safety_events
Revises: 004_replay_snapshots
Create Date: 2026-06-02 10:00:00.000000

Schema: PostgreSQL 15+
Purpose: Persist safety classification events for audit, compliance, and
  false-positive/false-negative post-review. Each row documents a safety
  classification result, with encrypted message payload for retrospective
  lexicon validation.

Fields:
  id: Auto-incrementing primary key.
  user_id: UUID of the user.
  turn_id: UUID of the conversation turn.
  severity: Classified severity (GREEN/YELLOW/ORANGE/RED/PURPLE).
  layer: Classification layer (heuristic/llm/accumulator).
  reason: Human-readable classification reason.
  category: Top-level category (suicide/self_harm/others_harm/abuse/despair/...).
  payload: Full classification metadata as JSONB.
  created_at: Event timestamp with timezone.

Indexes:
  - (user_id, created_at): Per-user audit trail queries.
  - (severity, created_at): Severity-filtered retrospective queries.
"""

from alembic import op

revision = "005_safety_events"
down_revision = "004_replay_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE safety_events (
        id              BIGSERIAL PRIMARY KEY,
        user_id         UUID NOT NULL,
        turn_id         UUID NOT NULL,
        severity        TEXT NOT NULL,
        layer           TEXT NOT NULL DEFAULT 'heuristic',
        reason          TEXT NOT NULL,
        category        TEXT,
        payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
    )

    op.execute(
        "CREATE INDEX ix_safety_events_user_created ON safety_events (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_safety_events_severity_created ON safety_events (severity, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS safety_events")
