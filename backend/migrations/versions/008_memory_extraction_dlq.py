"""Add memory_extraction_dlq for failed envelope inspection.

Revision ID: 008_memory_extraction_dlq
Revises: 007_memory_extractor_audit
Create Date: 2026-06-19 16:00:00.000000

Schema: PostgreSQL 15+
Purpose: Dead Letter Queue for failed extraction envelopes.
  When the Writer fails to commit an envelope, the full envelope
  is pushed here for HUMAN inspection. Never auto-retried.
"""

from alembic import op

revision = "008_memory_extraction_dlq"
down_revision = "007_memory_extractor_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
    CREATE TABLE memory_extraction_dlq (
        id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        extractor_run_id    UUID NOT NULL,
        user_id             UUID NOT NULL,
        session_id          UUID NOT NULL,
        envelope_json       JSONB NOT NULL,
        error_message       TEXT NOT NULL,
        candidates_count    INTEGER NOT NULL,
        model               VARCHAR(100) NOT NULL,
        prompt_version      VARCHAR(20) NOT NULL,
        resolved            BOOLEAN NOT NULL DEFAULT FALSE,
        resolved_by         VARCHAR(100),
        resolved_at         TIMESTAMPTZ,
        resolution_notes    TEXT,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
    )
    op.execute("CREATE INDEX ix_dlq_unresolved ON memory_extraction_dlq (resolved, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS memory_extraction_dlq")
