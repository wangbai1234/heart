"""Add shadow table for regex-path L3 facts in dual-mode comparison.

Revision ID: 010_memory_regex_shadow
Revises: 009_memory_l4_extras
Create Date: 2026-06-19 20:00:00.000000

Schema: PostgreSQL 15+
Purpose: When MEMORY_EXTRACTOR_MODE=dual, the regex extraction path writes
  its facts to memory_l3_facts_shadow_regex instead of fact_nodes, so the
  daily diff report can compare regex vs LLM recall/precision without
  polluting the main L3 table.

Columns mirror FactNode's core fact fields but omit:
  - semantic_vector (vector search is LLM-path only)
  - emotional_charge / emotional_label (fast path provides these separately)
  - state machine (vivid/fading/dormant — shadow facts are static snapshots)
  - L4 promotion fields (is_identity_level, promoted_to_l4_at, etc.)
  - confirmation/contradiction tracking
"""

from alembic import op

revision = "010_memory_regex_shadow"
down_revision = "009_memory_l4_extras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE memory_l3_facts_shadow_regex (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL,
        character_id    VARCHAR(50) NOT NULL,

        -- Fact content
        predicate       VARCHAR(100) NOT NULL,
        subject         VARCHAR(100) NOT NULL,
        object          TEXT NOT NULL,
        literal_text    TEXT NOT NULL,

        -- Provenance
        raw_evidence    TEXT NOT NULL,
        source_turn_ids UUID[] NOT NULL DEFAULT '{}',
        source_turns    INTEGER[] NOT NULL DEFAULT '{}',
        confidence      DOUBLE PRECISION NOT NULL,

        -- Run tracking
        extractor_run_id UUID,
        matched_llm_fact_id UUID,

        -- Lifecycle
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

        CONSTRAINT chk_shadow_regex_confidence CHECK (confidence BETWEEN 0 AND 1)
    )
    """
    )
    op.execute(
        "CREATE INDEX ix_shadow_regex_user_predicate "
        "ON memory_l3_facts_shadow_regex (user_id, character_id, predicate)"
    )
    op.execute(
        "CREATE INDEX ix_shadow_regex_run_id ON memory_l3_facts_shadow_regex (extractor_run_id)"
    )
    op.execute("CREATE INDEX ix_shadow_regex_created ON memory_l3_facts_shadow_regex (created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_l3_facts_shadow_regex")
