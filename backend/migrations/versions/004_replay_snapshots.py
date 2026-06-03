"""Add replay_snapshots table for conversation replay/debug tool.

Revision ID: 004_replay_snapshots
Revises: 003_ss04_threshold_tuning_v1_1
Create Date: 2026-05-27 10:00:00.000000

Schema: PostgreSQL 15+
Purpose: Persist per-turn prompt bundles for debugging and replay.
  - Stores: system prompt, full messages, layer breakdown, raw/final responses,
    anti-pattern hits, critic scores.
  - Auto-pruned after 7 days (handled by application layer).
  - Not partitioned (operational table, not user-facing scale).
"""

from alembic import op

revision = "004_replay_snapshots"
down_revision = "003_ss04_threshold_tuning_v1_1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE replay_snapshots (
        id UUID DEFAULT gen_random_uuid(),
        turn_id UUID NOT NULL,
        session_id UUID NOT NULL,
        user_id VARCHAR(255) NOT NULL,
        character_id VARCHAR(255) NOT NULL,

        -- Prompt bundle (JSONB):
        --   { system_prompt, messages: [{role, content}],
        --     layers: { soul: {...}, memory: {...}, emotion: {...},
        --               relationship: {...}, inner_state: {...}, director: {...} },
        --     token_budget_allocations: {...} }
        prompt_bundle JSONB NOT NULL,

        -- LLM interaction
        raw_response TEXT NOT NULL,
        final_response TEXT NOT NULL,
        latency_ms INTEGER,
        model_name VARCHAR(100),
        token_count INTEGER,

        -- Filtering
        anti_pattern_hits JSONB NOT NULL DEFAULT '[]'::jsonb,
        blocked BOOLEAN NOT NULL DEFAULT false,

        -- Critic (NULL if not sampled)
        critic_score DECIMAL(3, 2),
        critic_feedback TEXT,

        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """
    )

    op.execute("ALTER TABLE replay_snapshots ADD PRIMARY KEY (id)")
    op.execute("CREATE INDEX idx_replay_session_turn ON replay_snapshots (session_id, created_at)")
    op.execute("CREATE INDEX idx_replay_user ON replay_snapshots (user_id)")
    op.execute("CREATE INDEX idx_replay_turn ON replay_snapshots (turn_id)")
    op.execute("CREATE INDEX idx_replay_created ON replay_snapshots (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS replay_snapshots")
