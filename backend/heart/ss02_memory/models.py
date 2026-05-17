"""
SQLAlchemy 2.0 models for SS02 Memory Runtime.

Covers:
- L2 Episodic Memory (episodic_memories)
- L3 Semantic Memory (fact_nodes)
- L4 Identity Memory (identity_memories)
- Encoding Events (memory_encoding_events)
- Consolidation Jobs (consolidation_jobs)

Schema matches §10.2 PG Schema exactly.
Partitioning: episodic_memories and fact_nodes BY HASH (user_id) INTO 32.

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    UUID as SQLUUID,
    VARCHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
    and_,
    event,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


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
    episode_raw_turn_ids: Mapped[list[UUID]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=False)

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
    last_recalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    recall_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reinforcement_history: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Vectors
    semantic_vector: Mapped[Vector] = mapped_column(Vector(768), nullable=True)
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
        default=lambda: datetime.now(datetime.timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
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
    source_episode_ids: Mapped[list[UUID]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list)
    source_turn_ids: Mapped[list[UUID]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list)
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
    promoted_to_l4_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    promotion_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Confirmation & Contradiction
    confirmation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradiction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contradicting_fact_ids: Mapped[list[UUID]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list)
    is_corrected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    do_not_recall: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
    )
    last_contradicted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # State
    state: Mapped[str] = mapped_column(VARCHAR(20), nullable=False)

    # Graph
    related_facts: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Vector
    semantic_vector: Mapped[Vector] = mapped_column(Vector(768), nullable=True)

    # Recall Tracking
    recall_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_recalled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reconstruction Hints
    reconstruction_hints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
    )

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
    source_turn_ids: Mapped[list[UUID]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=False, default=list)

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
    next_anniversary_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Reconstruction Hints
    reconstruction_hints: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Audit
    promoted_from_fact_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    audit_log: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)

    # Lifecycle
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
    )

    # User Control
    user_initiated_forget: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    forget_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

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
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(datetime.timezone.utc),
    )
    llm_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    llm_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    pending_event_ids: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
    turns_to_consolidate: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)

    # Outputs
    episodes_created: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
    facts_created: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
    facts_reinforced: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
    facts_contradicted: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
    promotions_to_l4: Mapped[Optional[list[UUID]]] = mapped_column(ARRAY(SQLUUID(as_uuid=True)), nullable=True)
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
        default=lambda: datetime.now(datetime.timezone.utc),
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
