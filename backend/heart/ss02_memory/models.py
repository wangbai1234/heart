"""
SQLAlchemy 2.0 models for SS02 Memory Runtime.

Covers:
- L2 Episodic Memory (episodic_memories)
- L3 Semantic Memory (fact_nodes)
- L4 Identity Memory (identity_memories)
- Encoding Events (memory_encoding_events)
- Consolidation Jobs (consolidation_jobs)
- Extraction Queue (memory_extraction_queue)
- Audit Log (memory_audit_log)

Schema matches §10.2 PG Schema exactly.
Partitioning: episodic_memories and fact_nodes BY HASH (user_id) INTO 32.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    UUID as SQLUUID,
)
from sqlalchemy import (
    VARCHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from heart.core.base import Base

# ============================================================
# L2: Episodic Memory
# ============================================================


class EpisodicMemory(Base):
    """
    L2 Episodic Memory - Compressed "scenes" with summary + emotional peaks.

    Partitioned BY HASH (user_id) INTO 32.
    Indexed on: semantic_vector (HNSW), emotional_vector (HNSW),
                user+recency, user+importance, user+state
    """

    __tablename__ = "episodic_memories"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Content
    episode_summary: Mapped[str] = mapped_column(Text, nullable=False)
    episode_raw_turn_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False
    )

    # Temporal
    episode_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    episode_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scene_context: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)

    # Emotional
    emotional_peak: Mapped[dict] = mapped_column(JSONB, nullable=False)
    emotional_end: Mapped[dict] = mapped_column(JSONB, nullable=False)
    emotional_significance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        info={"check": "emotional_significance BETWEEN 0 AND 1"},
    )

    # Decay & Importance
    importance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        info={"check": "importance_score BETWEEN 0 AND 1"},
    )
    initial_importance: Mapped[float] = mapped_column(Float, nullable=False)
    decay_immunity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    state: Mapped[str] = mapped_column(
        VARCHAR(20),
        nullable=False,
        info={"check": "state IN ('vivid','fading','faint','dormant','archived')"},
    )

    # Recall Tracking
    last_recalled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    recall_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reinforcement_history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Vectors
    semantic_vector: Mapped[Vector] = mapped_column(Vector(1024), nullable=True)
    emotional_vector: Mapped[Vector] = mapped_column(Vector(256), nullable=True)

    # Associations
    linked_episodes: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    linked_facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Reconstruction Hints
    reconstruction_hints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # User Control
    do_not_recall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("emotional_significance BETWEEN 0 AND 1"),
        CheckConstraint("importance_score BETWEEN 0 AND 1"),
        CheckConstraint("state IN ('vivid','fading','faint','dormant','archived')"),
        Index("idx_episodic_user_recent", "user_id", "character_id", "last_recalled_at"),
        Index("idx_episodic_user_importance", "user_id", "character_id", "importance_score"),
        Index("idx_episodic_state", "user_id", "character_id", "state"),
        Index("idx_episodic_semantic", "semantic_vector", postgresql_using="hnsw"),
        Index("idx_episodic_emotional", "emotional_vector", postgresql_using="hnsw"),
    )


# ============================================================
# L3: Semantic Memory (Fact Node)
# ============================================================


class FactNode(Base):
    """
    L3 Semantic Memory - Extracted facts as graph nodes.

    Partitioned BY HASH (user_id) INTO 32.
    Indexed on: semantic_vector (HNSW), user+predicate, user+importance
    """

    __tablename__ = "fact_nodes"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Fact Content
    predicate: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    subject: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    literal_text: Mapped[str] = mapped_column(Text, nullable=False)

    # Provenance
    raw_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    source_episode_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list
    )
    source_turn_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        info={"check": "confidence BETWEEN 0 AND 1"},
    )

    # Emotional Charge
    emotional_charge: Mapped[float] = mapped_column(Float, nullable=False)
    emotional_label: Mapped[Optional[str]] = mapped_column(VARCHAR(30), nullable=True)

    # Importance
    importance: Mapped[float] = mapped_column(Float, nullable=False)
    is_identity_level: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    promoted_to_l4_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    promotion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Confirmation & Contradiction
    confirmation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradicting_fact_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list
    )
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_recall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_contradicted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # State
    state: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    # Graph
    related_facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Vector
    semantic_vector: Mapped[Vector] = mapped_column(Vector(1024), nullable=True)

    # Recall Tracking
    recall_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_recalled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Reconstruction Hints
    reconstruction_hints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # LLM Extractor columns (migration 007)
    source_turns: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    mention_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    confidence_ewma: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    last_extractor_run_id: Mapped[Optional[UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    superseded_by_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)

    # Demotion tracking (migration 009)
    was_l4: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    previously_l4_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1"),
        Index("idx_fact_user_predicate", "user_id", "character_id", "predicate"),
        Index(
            "idx_fact_user_importance",
            "user_id",
            "character_id",
            "importance",
            postgresql_where=text("NOT do_not_recall"),
        ),
        Index("idx_fact_semantic", "semantic_vector", postgresql_using="hnsw"),
    )


# ============================================================
# L4: Identity Memory (Sacred)
# ============================================================


class IdentityMemory(Base):
    """
    L4 Identity Memory - Sacred, never-decaying facts.

    Not partitioned (data volume small).
    Strongly replicated, hourly backup.
    Immutable after creation.
    """

    __tablename__ = "identity_memories"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Category
    category: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Content
    key: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    # Disclosure Context
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    disclosure_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_episode_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    source_turn_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list
    )

    # Sacred Metadata
    sacred_reason: Mapped[str] = mapped_column(Text, nullable=False)
    significance_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        info={"check": "significance_score >= 0.85"},
    )
    promotion_trigger: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Anniversary Tracking
    anniversary_pattern: Mapped[Optional[str]] = mapped_column(VARCHAR(20), nullable=True)
    next_anniversary_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Reconstruction Hints
    reconstruction_hints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Audit
    promoted_from_fact_id: Mapped[Optional[UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    audit_log: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # User Control
    user_initiated_forget: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forget_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Demotion tracking (migration 009)
    demoted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    demotion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("significance_score >= 0.85"),
        UniqueConstraint("user_id", "character_id", "key"),
        Index("idx_l4_user", "user_id", "character_id"),
        Index(
            "idx_l4_anniversary",
            "next_anniversary_at",
            postgresql_where=text("next_anniversary_at IS NOT NULL"),
        ),
    )


# ============================================================
# Encoding Events Queue
# ============================================================


class MemoryEncodingEvent(Base):
    """
    Memory Encoding Event - Queue for async LLM encoding.

    Partitioned BY RANGE (created_at) monthly.
    Status: fast_done / llm_pending / llm_done / failed
    """

    __tablename__ = "memory_encoding_events"

    event_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Source
    source_turn_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    source_user_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_assistant_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Conversation context
    recent_context: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Fast Encoder signals
    fast_signals: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # LLM extraction results
    llm_extraction: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(tzinfo=None),
    )
    llm_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    llm_completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=False), nullable=True
    )
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=False), nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_encoding_status",
            "status",
            "created_at",
            postgresql_where=text("status IN ('llm_pending', 'failed')"),
        ),
    )


# ============================================================
# Consolidation Jobs
# ============================================================


class ConsolidationJob(Base):
    """
    Consolidation Job - Daily batch processing ("sleep").

    Status: pending / running / succeeded / failed
    Unique per (user_id, character_id, scheduled_for).
    """

    __tablename__ = "consolidation_jobs"

    job_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    # Schedule
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Inputs
    pending_event_ids: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    turns_to_consolidate: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )

    # Outputs
    episodes_created: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    facts_created: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    facts_reinforced: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    facts_contradicted: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    promotions_to_l4: Mapped[Optional[list[UUID]]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=True
    )
    associations_created: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="pending")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "character_id", "scheduled_for"),
        Index(
            "idx_consolidation_pending",
            "scheduled_for",
            "status",
            postgresql_where=text("status = 'pending'"),
        ),
    )


# ============================================================
# Extraction Queue (Slow Path)
# ============================================================


class MemoryExtractionQueue(Base):
    """
    Extraction Queue - Async queue for slow-path LLM extraction.

    Status: pending / processing / done / failed / skipped
    Worker polls pending items, processes through Extractor→Resolver→Writer.
    """

    __tablename__ = "memory_extraction_queue"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    session_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False, index=True)
    turn_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Regex hints as auxiliary signals
    hints_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(VARCHAR(20), nullable=False, default="pending")

    # Lifecycle
    enqueued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Tracking
    extractor_run_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (Index("ix_extraction_queue_poll", "status", "enqueued_at"),)


# ============================================================
# Audit Log
# ============================================================


class MemoryAuditLog(Base):
    """
    Audit Log - Immutable trail for all L2/L3/L4 state changes.

    Every create/update/supersede/soft_delete/promote/demote is recorded
    with before/after snapshots and source provenance.
    """

    __tablename__ = "memory_audit_log"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    session_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)

    # What
    tier: Mapped[str] = mapped_column(VARCHAR(5), nullable=False)  # L1/L2/L3/L4
    operation: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    entity_ref: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    attribute: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)

    # Before / After
    old_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Provenance
    source_turns: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    extractor_run_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)

    # Actor
    actor: Mapped[str] = mapped_column(
        VARCHAR(20), nullable=False
    )  # extractor/resolver/promoter/admin
    reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (Index("ix_audit_log_user_time", "user_id", "created_at"),)


# ============================================================
# Dead Letter Queue (DLQ) — failed extractions for HUMAN inspection
# ============================================================


class MemoryExtractionDLQ(Base):
    """
    Dead Letter Queue — failed extraction envelopes for HUMAN inspection.

    When the Writer fails to commit an envelope (partial failure, constraint
    violation, etc.), the full envelope is pushed here for manual review.
    Never auto-retried — a HUMAN must inspect and decide.
    """

    __tablename__ = "memory_extraction_dlq"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    extractor_run_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    session_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)

    # Full envelope for inspection
    envelope_json: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # HUMAN-readable summary
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    candidates_count: Mapped[int] = mapped_column(Integer, nullable=False)
    model: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    prompt_version: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    # Resolution tracking
    resolved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    resolved_by: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (Index("ix_dlq_unresolved", "resolved", "created_at"),)


class MemoryL3FactShadowRegex(Base):
    """Shadow table for regex-extracted L3 facts in dual-mode comparison.

    When MEMORY_EXTRACTOR_MODE=dual, the regex path writes its extracted facts
    here instead of the main ``fact_nodes`` table.  The LLM path continues to
    write to ``fact_nodes``.  The daily diff report compares both tables to
    measure recall/precision gaps before retiring the regex path.

    Matching key for cross-path alignment:
        (user_id, character_id, predicate, subject)

    Columns mirror ``FactNode`` but omit vectors, emotional metadata, and the
    full L3 state machine (no vivid/fading/dormant, no L4 promotion tracking).
    """

    __tablename__ = "memory_l3_facts_shadow_regex"

    id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    predicate: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    subject: Mapped[str] = mapped_column(VARCHAR(100), nullable=False)
    object: Mapped[str] = mapped_column(Text, nullable=False)
    literal_text: Mapped[str] = mapped_column(Text, nullable=False)

    raw_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    source_turn_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list
    )
    source_turns: Mapped[list[int]] = mapped_column(ARRAY(Integer), nullable=False, default=list)
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, info={"check": "confidence BETWEEN 0 AND 1"}
    )

    extractor_run_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    matched_llm_fact_id: Mapped[Optional[UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint("confidence BETWEEN 0 AND 1"),
        Index("ix_shadow_regex_user_predicate", "user_id", "character_id", "predicate"),
        Index("ix_shadow_regex_run_id", "extractor_run_id"),
        Index("ix_shadow_regex_created", "created_at"),
    )
