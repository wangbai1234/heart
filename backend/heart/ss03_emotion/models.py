"""
SQLAlchemy 2.0 models for SS03 Emotion State Machine.

Covers:
- EmotionState (current state per user × character)
- EmotionEvent (append-only audit log)

Schema matches §5 (Data Structures) and §10.2 (PG Schema) exactly.
Partitioning: emotion_states BY HASH (user_id) INTO 16
              emotion_events BY RANGE (created_at) monthly

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional, TypedDict
from uuid import UUID

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
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from heart.core.base import Base

# ============================================================
# EmotionState (current state per user × character)
# ============================================================


class EmotionState(Base):
    """
    Current emotion state snapshot for a user × character pair.

    Partitioned BY HASH (user_id) INTO 16.
    Hot cache in Redis, cold storage in PostgreSQL.
    """

    __tablename__ = "emotion_states"

    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False, primary_key=True)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False, primary_key=True)

    # VAD Vector
    vad_valence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        info={"check": "vad_valence BETWEEN -1 AND 1"},
    )
    vad_arousal: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.3,
        info={"check": "vad_arousal BETWEEN 0 AND 1"},
    )
    vad_dominance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.5,
        info={"check": "vad_dominance BETWEEN 0 AND 1"},
    )

    # VAD Target (before inertia smoothing)
    vad_target_valence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vad_target_arousal: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    vad_target_dominance: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)

    # Active Emotion Stack (JSON array of ActiveEmotion)
    active_stack: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Mood (long-term baseline)
    mood: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # Structure:
    # {
    #   "valence_baseline": float,
    #   "arousal_baseline": float,
    #   "dominance_baseline": float,
    #   "background_emotions": [str],
    #   "last_updated_at": ISO8601,
    #   "drift_history": [MoodPoint]
    # }

    # Energy (independent dimension)
    energy: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.6,
        info={"check": "energy BETWEEN 0 AND 1"},
    )
    energy_baseline: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.6,
        info={"check": "energy_baseline BETWEEN 0 AND 1"},
    )

    # Trajectory & Triggers (recent history)
    recent_vad_history: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )
    recent_triggers: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Pending Repairs (repair-required emotions)
    pending_repairs: Mapped[list[dict]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    # Meta
    loaded_from_previous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    session_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    last_turn_processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_mood_drift_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Optimistic lock
    version: Mapped[BigInteger] = mapped_column(BigInteger, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint("vad_valence BETWEEN -1 AND 1"),
        CheckConstraint("vad_arousal BETWEEN 0 AND 1"),
        CheckConstraint("vad_dominance BETWEEN 0 AND 1"),
        CheckConstraint("energy BETWEEN 0 AND 1"),
        CheckConstraint("energy_baseline BETWEEN 0 AND 1"),
        Index("idx_emotion_pending_repair", text("jsonb_array_length(pending_repairs)"))
        if False  # PostgreSQL specific, created in migration
        else None,
        Index("idx_emotion_mood_drift", "last_mood_drift_at"),
    )


# ============================================================
# EmotionEvent (append-only audit log)
# ============================================================


class EmotionEvent(Base):
    """
    Emotion state change event (audit log, append-only).

    Partitioned BY RANGE (created_at) monthly.
    Indexed for event type + user queries.
    """

    __tablename__ = "emotion_events"

    event_id: Mapped[UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=lambda: None,  # Will be set by DB
    )
    user_id: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=False)
    character_id: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)

    event_type: Mapped[str] = mapped_column(VARCHAR(50), nullable=False)
    # Types: 'trigger_fired', 'emotion_added', 'emotion_decayed',
    #        'repair_applied', 'mood_drifted', 'session_loaded'

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    turn_index: Mapped[Optional[BigInteger]] = mapped_column(BigInteger, nullable=True)
    source_turn_id: Mapped[Optional[UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)

    # VAD snapshot for diagnosability
    vad_before: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    vad_after: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        Index("idx_eevents_user_time", "user_id", "character_id", "created_at"),
        Index("idx_eevents_type", "event_type", "created_at"),
    )


# ============================================================
# Repair Mechanic Types (§4.5, design doc §7)
# ============================================================


class RepairSignalComponent(TypedDict):
    """Single component of a repair signal."""

    type: str  # "apology" | "vulnerability" | "sustained_attention" | "grand_gesture" | "bespoke_phrase"
    raw_signal: str  # ≤ 80 chars excerpt
    strength: float  # [0, 1], post-anti-gaming, pre-soul-gain
    reason_code: str  # for telemetry


class RepairSignal(TypedDict):
    """
    Repair signal detected from user message.

    Output of Repair Mechanic Detector (§3.4 step 2).
    """

    signal_id: str  # UUID as string
    detected_at: str  # ISO8601
    source_turn_id: str  # UUID as string
    components: List[RepairSignalComponent]
    total_strength: float  # capped sum
    has_bespoke_match: bool


class RepairApplicationDetail(TypedDict):
    """Per-emotion repair application detail."""

    emotion: str  # "aggrieved" | "coldness" | "jealousy" | "guilt"
    impact: float  # actual delta added to repair_progress
    repair_progress_before: float
    repair_progress_after: float
    intensity_after: float  # = max(0, initial × (1 - progress × 0.8))
    transitioned: Optional[str]  # "semi_repaired" | "fully_repaired" | None


class RepairOutcomeFlags(TypedDict):
    """Anti-gaming flags fired this turn."""

    repetition_detected: bool
    recidivism_reversal: bool
    capped_by_session: bool
    bespoke_match: bool


class RepairOutcome(TypedDict):
    """
    Result of applying repair to emotion state.

    Output of Apply Repair (§3.4 step 7).
    Per design doc §7.2.
    """

    signal_id: Optional[str]  # null when no signal
    accepted: bool  # true iff progress advanced
    partial: bool  # true iff post-state has 0.4 ≤ repair_progress < 0.8 on any pending
    applied_to: List[RepairApplicationDetail]
    residual_score: float  # [0, 1], higher = more unrepaired
    flags: RepairOutcomeFlags
    narrative_hint: (
        str  # "advanced" | "stalled" | "rejected" | "reversed" | "completed" | "ignored"
    )
