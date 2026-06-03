"""
SQLAlchemy 2.0 models for SS04 Relationship Phase Engine.

Covers:
- RelationshipState (current state per user × character)
- RelationshipEvent (append-only audit log)

Schema matches §5 (Data Structures) and §10.2 (PG Schema) exactly.
Partitioning: relationship_states BY HASH (user_id) INTO 16
              relationship_events BY RANGE (created_at) monthly

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    UUID as SQLUUID,
)
from sqlalchemy import (
    VARCHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    Float,
    Index,
    Integer,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


# ============================================================
# RelationshipState (current state per user × character)
# ============================================================


class RelationshipState(Base):
    """
    Current relationship state snapshot for a user × character pair.

    Partitioned BY HASH (user_id) INTO 16.
    Hot cache in Redis, cold storage in PostgreSQL.
    """

    __tablename__ = "relationship_states"

    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False, primary_key=True)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, primary_key=True)

    # Stage
    current_stage: Mapped[str] = mapped_column(
        VARCHAR(30),
        nullable=False,
        default="STRANGER",
    )
    previous_stage: Mapped[str] = mapped_column(
        VARCHAR(30),
        nullable=False,
        default="STRANGER",
    )
    stage_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    highest_stage_reached: Mapped[str] = mapped_column(
        VARCHAR(30),
        nullable=False,
        default="STRANGER",
    )

    # Continuous Dimensions
    intimacy_level: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "intimacy_level BETWEEN 0 AND 1"},
    )
    trust_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "trust_score BETWEEN 0 AND 1"},
    )
    attachment_strength: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "attachment_strength BETWEEN 0 AND 1"},
    )
    conflict_debt: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "conflict_debt BETWEEN 0 AND 1"},
    )
    vulnerability_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "vulnerability_score BETWEEN 0 AND 1"},
    )

    # History Counters
    total_interactions: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False, default=0)
    total_meaningful_disclosures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_promises_made: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_promises_kept: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_conflicts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_repairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_successful_repairs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Time Markers
    first_meeting_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    longest_absence_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    longest_continuous_streak_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Soul Modulation (computed at init)
    soul_modifiers: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # Structure:
    # {
    #   "progression_rate": float,
    #   "regression_resistance": float,
    #   "conflict_recovery_curve": str,
    #   "intimacy_ceiling_modifier": float
    # }

    # Special States
    active_special_states: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Stage Metadata (denormalized history per stage)
    stage_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Rituals
    rituals: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Recent Events (denormalized, limited size)
    recent_progression_events: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    recent_regression_events: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    recent_conflicts: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    recent_repairs: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Optimistic lock
    version: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("intimacy_level BETWEEN 0 AND 1"),
        CheckConstraint("trust_score BETWEEN 0 AND 1"),
        CheckConstraint("attachment_strength BETWEEN 0 AND 1"),
        CheckConstraint("conflict_debt BETWEEN 0 AND 1"),
        CheckConstraint("vulnerability_score BETWEEN 0 AND 1"),
        Index("idx_rel_stage", "current_stage"),
        Index("idx_rel_drifting", "last_interaction_at"),
        Index("idx_rel_cold_war", "user_id", "character_id")
        if False  # PostgreSQL specific, created in migration
        else None,
    )


# ============================================================
# RelationshipEvent (append-only audit log)
# ============================================================


class RelationshipEvent(Base):
    """
    Relationship state change event (audit log, append-only).

    Partitioned BY RANGE (created_at) monthly.
    Indexed for event type + user queries.
    """

    __tablename__ = "relationship_events"

    event_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=lambda: None,  # Will be set by DB
    )
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    event_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    # Types: 'stage_progression', 'stage_regression',
    #        'trust_change_significant', 'conflict_started',
    #        'repair_completed', 'ritual_milestone',
    #        'reunion_initiated', 'cold_war_entered', 'cold_war_resolved'

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # State snapshots
    state_before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    state_after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    triggered_by_turn_id: Mapped[Optional[UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_relevent_user", "user_id", "character_id", "created_at"),
        Index("idx_relevent_type", "event_type", "created_at"),
    )
