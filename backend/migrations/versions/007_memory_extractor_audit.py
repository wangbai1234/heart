"""Add memory extraction queue, audit log, and L3 supersede columns.

Revision ID: 007_memory_extractor_audit
Revises: 006_sessions
Create Date: 2026-06-19 10:00:00.000000

Schema: PostgreSQL 15+
Purpose: Phase A infrastructure for SS02 Memory LLM Extractor refactor.
  - memory_extraction_queue: async queue for slow-path LLM extraction jobs
  - memory_audit_log: immutable audit trail for all L2/L3/L4 state changes
  - Alter fact_nodes (L3): add columns for source tracking, mention count,
    confidence EWMA, and supersession support (INV-M-NEW-A/B)

Fields:
  memory_extraction_queue:
    id: UUID primary key.
    session_id: UUID, indexed for worker polling.
    turn_id: BIGINT, indexed for batch lookups.
    hints_json: JSONB, nullable, regex hints as auxiliary signals.
    status: VARCHAR, one of pending/processing/done/failed/skipped.
    enqueued_at/started_at/finished_at: TIMESTAMPTZ lifecycle.
    extractor_run_id: UUID, nullable, links to audit log.
    error_message: TEXT, nullable.
    retry_count: INTEGER, default 0.

  memory_audit_log:
    id: UUID primary key.
    user_id/session_id: UUID, indexed.
    tier: VARCHAR, one of L1/L2/L3/L4.
    operation: VARCHAR, one of create/update/supersede/soft_delete/promote/demote.
    entity_type/entity_ref/attribute: VARCHAR for fact identification.
    old_value/new_value: JSONB for before/after snapshots.
    source_turns: INTEGER[], not null, provenance chain.
    extractor_run_id: UUID, nullable.
    actor: VARCHAR, one of extractor/resolver/promoter/admin.
    reasoning: TEXT, nullable, LLM rationale.
    created_at: TIMESTAMPTZ.

  fact_nodes (alter):
    source_turns: INTEGER[], not null, default '{}'
    mention_count: INTEGER, not null, default 1
    confidence_ewma: FLOAT, not null, default 0.5
    last_extractor_run_id: UUID, nullable
    is_active: BOOLEAN, not null, default TRUE (supersession support)
    superseded_by_id: UUID, nullable, FK self

Indexes:
  memory_extraction_queue: (status, enqueued_at) for worker poll.
  memory_audit_log: (user_id, created_at DESC) for chronological audit.
"""

from alembic import op

revision = "007_memory_extractor_audit"
down_revision = "006_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. memory_extraction_queue ──
    op.execute(
        """
    CREATE TABLE memory_extraction_queue (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        session_id      UUID NOT NULL,
        turn_id         BIGINT NOT NULL,
        hints_json      JSONB,
        status          VARCHAR(20) NOT NULL DEFAULT 'pending',
        enqueued_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        started_at      TIMESTAMPTZ,
        finished_at     TIMESTAMPTZ,
        extractor_run_id UUID,
        error_message   TEXT,
        retry_count     INTEGER NOT NULL DEFAULT 0
    )
    """
    )
    op.execute(
        "CREATE INDEX ix_extraction_queue_poll ON memory_extraction_queue (status, enqueued_at)"
    )

    # ── 2. memory_audit_log ──
    op.execute(
        """
    CREATE TABLE memory_audit_log (
        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        user_id         UUID NOT NULL,
        session_id      UUID NOT NULL,
        tier            VARCHAR(5) NOT NULL,
        operation       VARCHAR(20) NOT NULL,
        entity_type     VARCHAR(50) NOT NULL,
        entity_ref      VARCHAR(100),
        attribute       VARCHAR(50),
        old_value       JSONB,
        new_value       JSONB,
        source_turns    INTEGER[] NOT NULL DEFAULT '{}',
        extractor_run_id UUID,
        actor           VARCHAR(20) NOT NULL,
        reasoning       TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """
    )
    op.execute("CREATE INDEX ix_audit_log_user_time ON memory_audit_log (user_id, created_at DESC)")

    # ── 3. Alter fact_nodes — add LLM extractor columns ──
    op.execute("ALTER TABLE fact_nodes ADD COLUMN source_turns INTEGER[] NOT NULL DEFAULT '{}'")
    op.execute("ALTER TABLE fact_nodes ADD COLUMN mention_count INTEGER NOT NULL DEFAULT 1")
    op.execute(
        "ALTER TABLE fact_nodes ADD COLUMN confidence_ewma DOUBLE PRECISION NOT NULL DEFAULT 0.5"
    )
    op.execute("ALTER TABLE fact_nodes ADD COLUMN last_extractor_run_id UUID")
    op.execute("ALTER TABLE fact_nodes ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT TRUE")
    op.execute("ALTER TABLE fact_nodes ADD COLUMN superseded_by_id UUID")


def downgrade() -> None:
    # ── 3. Remove fact_nodes columns (reverse order) ──
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS superseded_by_id")
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS is_active")
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS last_extractor_run_id")
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS confidence_ewma")
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS mention_count")
    op.execute("ALTER TABLE fact_nodes DROP COLUMN IF EXISTS source_turns")

    # ── 2. Drop audit log ──
    op.execute("DROP TABLE IF EXISTS memory_audit_log")

    # ── 1. Drop extraction queue ──
    op.execute("DROP TABLE IF EXISTS memory_extraction_queue")
