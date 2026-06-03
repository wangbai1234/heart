"""Add sessions table for per-(user, character) conversation sessions.

Revision ID: 006_sessions
Revises: 005_safety_events
Create Date: 2026-06-02 11:00:00.000000

Schema: PostgreSQL 15+
Purpose: Track conversation sessions per user × character pair.
  Each session aggregates turns for a single user-character conversation
  context. Supports future features: multi-device sync (via session_id),
  suicide protocol flagging, and session analytics.

Fields:
  id: UUID primary key.
  user_id: UUID of the user.
  character_id: Character identifier.
  started_at: Session creation timestamp.
  last_activity_at: Timestamp of most recent turn.
  turn_count: Number of turns in this session.
  suicide_protocol_active: Whether crisis protocol is triggered.

Indexes:
  - (user_id, character_id): Fast session lookup per user × character.
  - (last_activity_at): Session pruning and analytics queries.
"""

from alembic import op

revision = "006_sessions"
down_revision = "005_safety_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE sessions (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL,
        character_id    TEXT NOT NULL,
        started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        turn_count      INTEGER NOT NULL DEFAULT 0,
        suicide_protocol_active BOOLEAN NOT NULL DEFAULT false
    )
    """
    )

    op.execute("CREATE UNIQUE INDEX ix_sessions_user_character ON sessions (user_id, character_id)")
    op.execute("CREATE INDEX ix_sessions_last_activity ON sessions (last_activity_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS sessions")
