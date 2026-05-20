"""
Relationship Service for SS04 Relationship Phase Engine.

Orchestrates stage transitions, dimension updates, and state persistence.
Implements §10.2 Relationship Service interface.

Author: 心屿团队
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ss04_relationship.attachment_tracker import AttachmentTracker
from ..ss04_relationship.models import RelationshipEvent, RelationshipState
from ..ss04_relationship.stage_engine import (
    RelationshipStage,
    SignalBatch,
    StageDecision,
    StagePhaseEngine,
    TransitionAction,
)
from ..ss04_relationship.trust_tracker import TrustTracker


logger = logging.getLogger(__name__)


# ============================================================
# Relationship Service
# ============================================================


class RelationshipService:
    """
    Core service for relationship state management (§10.2).

    Responsibilities:
    - Load/persist RelationshipState
    - Orchestrate dimension updates (trust, attachment, intimacy)
    - Evaluate stage transitions
    - Generate RelationshipContextBlock
    - Handle event subscribers
    """

    def __init__(self, db_session: AsyncSession, soul_specs: dict[str, dict]):
        """
        Initialize service.

        Args:
            db_session: SQLAlchemy async session
            soul_specs: Map of character_id -> Soul Spec dict
        """
        self.db = db_session
        self.soul_specs = soul_specs

        # Component instances (per-character)
        self._stage_engines: dict[str, StagePhaseEngine] = {}
        self._trust_trackers: dict[str, TrustTracker] = {}
        self._attachment_trackers: dict[str, AttachmentTracker] = {}

    def _get_stage_engine(self, character_id: str) -> StagePhaseEngine:
        """Get or create StagePhaseEngine for character."""
        if character_id not in self._stage_engines:
            soul_spec = self.soul_specs.get(character_id, {})
            self._stage_engines[character_id] = StagePhaseEngine(soul_spec)
        return self._stage_engines[character_id]

    def _get_trust_tracker(self, character_id: str) -> TrustTracker:
        """Get or create TrustTracker for character."""
        if character_id not in self._trust_trackers:
            self._trust_trackers[character_id] = TrustTracker()
        return self._trust_trackers[character_id]

    def _get_attachment_tracker(self, character_id: str) -> AttachmentTracker:
        """Get or create AttachmentTracker for character."""
        if character_id not in self._attachment_trackers:
            self._attachment_trackers[character_id] = AttachmentTracker()
        return self._attachment_trackers[character_id]

    # ─── Read API ───────────────────────────────────────────

    async def get_state(
        self, user_id: UUID, character_id: str
    ) -> Optional[RelationshipState]:
        """
        Get current relationship state (§10.2).

        TODO: Add Redis cache layer (§10.4).

        Args:
            user_id: User UUID
            character_id: Character ID

        Returns:
            RelationshipState or None if not found
        """
        stmt = select(RelationshipState).where(
            RelationshipState.user_id == user_id,
            RelationshipState.character_id == character_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create_state(
        self, user_id: UUID, character_id: str
    ) -> RelationshipState:
        """
        Get existing state or create new one.

        Args:
            user_id: User UUID
            character_id: Character ID

        Returns:
            RelationshipState (guaranteed non-null)
        """
        state = await self.get_state(user_id, character_id)
        if state:
            return state

        # Create new state
        soul_spec = self.soul_specs.get(character_id, {})
        relational_template = soul_spec.get("relational_template", {})

        now = datetime.now(timezone.utc)
        state = RelationshipState(
            user_id=user_id,
            character_id=character_id,
            current_stage=RelationshipStage.STRANGER.value,
            previous_stage=RelationshipStage.STRANGER.value,
            stage_entered_at=now,
            highest_stage_reached=RelationshipStage.STRANGER.value,
            first_meeting_at=now,
            last_interaction_at=now,
            soul_modifiers={
                "progression_rate": 1.0 - relational_template.get("intimacy_resistance", 0.5),
                "regression_resistance": 0.7,
                "conflict_recovery_curve": "logistic",
                "intimacy_ceiling_modifier": 1.0,
            },
        )

        self.db.add(state)
        await self.db.flush()

        logger.info(
            f"Created new relationship state for user={user_id}, character={character_id}"
        )
        return state

    # ─── Update API (per turn) ─────────────────────────────

    async def process_turn(
        self,
        user_id: UUID,
        character_id: str,
        signals: SignalBatch,
        turn_id: UUID,
    ) -> RelationshipState:
        """
        Process a single turn and update relationship state (§3.5).

        Steps (§3.5):
        1. Load state
        2. Update continuous dimensions (trust, attachment, intimacy)
        3. Update special states
        4. Evaluate stage transition
        5. Persist state
        6. Write audit event if transition occurred

        Args:
            user_id: User UUID
            character_id: Character ID
            signals: Aggregated signals from this turn
            turn_id: Turn UUID (for audit trail)

        Returns:
            Updated RelationshipState
        """
        # 1. Load state
        state = await self.get_or_create_state(user_id, character_id)

        # Calculate time deltas
        now = datetime.now(timezone.utc)
        days_since_last = 0.0
        if state.last_interaction_at:
            delta = now - state.last_interaction_at.replace(tzinfo=timezone.utc)
            days_since_last = delta.total_seconds() / 86400

        # Track continuous streak
        if days_since_last <= 1:
            # Continuous interaction
            days_continuous = int((now - state.first_meeting_at).total_seconds() / 86400)
        else:
            days_continuous = 0

        # 2. Update continuous dimensions (§3.5 step 3)
        trust_tracker = self._get_trust_tracker(character_id)
        attachment_tracker = self._get_attachment_tracker(character_id)

        new_trust = trust_tracker.update(state, signals, days_since_last)
        new_attachment = attachment_tracker.update(
            state, signals, days_since_last, days_continuous
        )
        new_intimacy = self._compute_intimacy(state, new_trust, new_attachment)

        # Apply deltas with clamping
        state.trust_score = new_trust
        state.attachment_strength = new_attachment
        state.intimacy_level = new_intimacy

        # Update counters
        state.total_interactions += 1
        state.last_interaction_at = now
        state.updated_at = now

        # Update longest streak if applicable
        if days_since_last <= 1:
            current_streak = days_continuous
            if current_streak > state.longest_continuous_streak_days:
                state.longest_continuous_streak_days = current_streak

        # Update longest absence
        if days_since_last > state.longest_absence_days:
            state.longest_absence_days = int(days_since_last)

        # 3. Update special states (§3.5 step 4)
        # TODO: Implement DRIFTING, COLD_WAR, REUNION state updates

        # 4. Evaluate stage transition (§3.5 step 5)
        stage_engine = self._get_stage_engine(character_id)
        decision = stage_engine.evaluate(state, signals)

        # Apply transition if approved
        if decision.action in [TransitionAction.PROGRESS, TransitionAction.REGRESS]:
            await self._apply_stage_transition(state, decision, turn_id)

        # 5. Persist state (§3.5 step 6)
        state.version += 1
        await self.db.flush()

        logger.info(
            f"Processed turn for user={user_id}, character={character_id}, "
            f"stage={state.current_stage}, trust={state.trust_score:.2f}, "
            f"attachment={state.attachment_strength:.2f}, intimacy={state.intimacy_level:.2f}"
        )

        return state

    async def _apply_stage_transition(
        self,
        state: RelationshipState,
        decision: StageDecision,
        turn_id: UUID,
    ) -> None:
        """
        Apply stage transition and write audit event (§3.5 step 6).

        INV-R-2: Every transition must produce audit event.

        Args:
            state: Current relationship state
            decision: Transition decision from StagePhaseEngine
            turn_id: Turn UUID for audit trail
        """
        old_stage = state.current_stage
        new_stage = decision.to_stage.value if decision.to_stage else old_stage

        # Update stage fields
        state.previous_stage = old_stage
        state.current_stage = new_stage
        state.stage_entered_at = datetime.now(timezone.utc)

        # Update highest_stage_reached (INV-R-1: never decreases)
        new_stage_enum = RelationshipStage(new_stage)
        old_highest = RelationshipStage(state.highest_stage_reached)
        if STAGE_ORDER[new_stage_enum] > STAGE_ORDER[old_highest]:
            state.highest_stage_reached = new_stage

        # Update stage_metadata
        if new_stage not in state.stage_metadata:
            state.stage_metadata[new_stage] = {
                "entered_at": state.stage_entered_at.isoformat(),
                "exited_at": None,
                "duration_seconds": 0,
                "key_events": [],
            }

        # Write audit event (§10.2)
        event_type = (
            "stage_progression"
            if decision.action == TransitionAction.PROGRESS
            else "stage_regression"
        )

        event = RelationshipEvent(
            user_id=state.user_id,
            character_id=state.character_id,
            event_type=event_type,
            payload={
                "from_stage": old_stage,
                "to_stage": new_stage,
                "reason": decision.reason,
                "blocked_by": decision.blocked_by,
            },
            state_before={
                "stage": old_stage,
                "trust": state.trust_score,
                "attachment": state.attachment_strength,
                "intimacy": state.intimacy_level,
            },
            state_after={
                "stage": new_stage,
                "trust": state.trust_score,
                "attachment": state.attachment_strength,
                "intimacy": state.intimacy_level,
            },
            triggered_by_turn_id=turn_id,
        )

        self.db.add(event)

        # Add to recent_progression_events or recent_regression_events
        event_summary = {
            "from_stage": old_stage,
            "to_stage": new_stage,
            "at": state.stage_entered_at.isoformat(),
            "triggering_signals": [],
            "intimacy_at_transition": state.intimacy_level,
            "trust_at_transition": state.trust_score,
        }

        if decision.action == TransitionAction.PROGRESS:
            state.recent_progression_events.append(event_summary)
            # Keep only last 20
            state.recent_progression_events = state.recent_progression_events[-20:]
        else:
            state.recent_regression_events.append(event_summary)
            state.recent_regression_events = state.recent_regression_events[-20:]

        logger.info(
            f"Stage transition: {old_stage} → {new_stage}, reason={decision.reason}"
        )

    def _compute_intimacy(
        self, state: RelationshipState, trust: float, attachment: float
    ) -> float:
        """
        Compute intimacy level (综合指标, §3.9).

        Intimacy = weighted combination of:
        - trust (25%)
        - attachment (25%)
        - shared disclosure (20%)
        - ritual strength (15%)
        - continuous engagement (15%)

        Args:
            state: Current relationship state
            trust: New trust score
            attachment: New attachment strength

        Returns:
            Intimacy level in [0, 1]
        """
        weights = {
            "trust": 0.25,
            "attachment": 0.25,
            "disclosure": 0.20,
            "ritual": 0.15,
            "engagement": 0.15,
        }

        # Disclosure factor
        disclosure = min(1.0, state.total_meaningful_disclosures / 20.0)

        # Ritual strength (simplified)
        ritual_data = state.rituals.get("daily_check_in", {})
        streak = ritual_data.get("streak_days", 0)
        ritual_strength = min(1.0, streak / 30.0)

        # Engagement (simplified - based on interaction count)
        engagement = min(1.0, state.total_interactions / 100.0)

        # Compute weighted sum
        intimacy = (
            weights["trust"] * trust
            + weights["attachment"] * attachment
            + weights["disclosure"] * disclosure
            + weights["ritual"] * ritual_strength
            + weights["engagement"] * engagement
        )

        # Apply single-turn change limit (§3.9)
        delta = intimacy - state.intimacy_level
        if abs(delta) > 0.10:
            delta = 0.10 if delta > 0 else -0.10
            intimacy = state.intimacy_level + delta

        return max(0.0, min(1.0, intimacy))

    # ─── Event Subscribers ─────────────────────────────────

    async def on_l4_promoted(self, event: dict[str, Any]) -> None:
        """
        Handle L4 memory promotion event (§7.3).

        Called by Memory Runtime when L4 memory is created.

        Args:
            event: L4Event with user_id, character_id, memory_type
        """
        user_id = UUID(event["user_id"])
        character_id = event["character_id"]
        memory_type = event.get("memory_type", "")

        state = await self.get_state(user_id, character_id)
        if not state:
            return

        # Increment meaningful disclosures
        if "vulnerability" in memory_type or "disclosure" in memory_type:
            state.total_meaningful_disclosures += 1
            state.updated_at = datetime.now(timezone.utc)
            await self.db.flush()

        logger.info(
            f"L4 promoted: user={user_id}, character={character_id}, type={memory_type}"
        )

    async def on_emotion_event(self, event: dict[str, Any]) -> None:
        """
        Handle emotion event (§7.3).

        Called by Emotion Runtime for:
        - Conflict started
        - Repair completed
        - Cold war triggered

        Args:
            event: EmotionEvent with user_id, character_id, event_type
        """
        user_id = UUID(event["user_id"])
        character_id = event["character_id"]
        event_type = event.get("event_type", "")

        state = await self.get_state(user_id, character_id)
        if not state:
            return

        if event_type == "conflict_started":
            state.total_conflicts += 1
        elif event_type == "repair_completed":
            state.total_repairs += 1
            state.total_successful_repairs += 1

        state.updated_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info(
            f"Emotion event: user={user_id}, character={character_id}, type={event_type}"
        )

    async def on_conflict_started(self, conflict: dict[str, Any]) -> None:
        """
        Handle conflict start (§7.3).

        Args:
            conflict: ConflictRecord dict
        """
        await self.on_emotion_event(
            {"user_id": conflict["user_id"], "character_id": conflict["character_id"], "event_type": "conflict_started"}
        )

    async def on_repair_completed(self, repair: dict[str, Any]) -> None:
        """
        Handle repair completion (§7.3).

        Args:
            repair: RepairRecord dict
        """
        await self.on_emotion_event(
            {"user_id": repair["user_id"], "character_id": repair["character_id"], "event_type": "repair_completed"}
        )


# ============================================================
# Stage Order Lookup (for highest_stage comparison)
# ============================================================


STAGE_ORDER = {
    RelationshipStage.STRANGER: 0,
    RelationshipStage.ACQUAINTANCE: 1,
    RelationshipStage.FRIEND: 2,
    RelationshipStage.CONFIDANT: 3,
    RelationshipStage.ROMANTIC_INTEREST: 4,
    RelationshipStage.LOVER: 5,
    RelationshipStage.BONDED: 6,
}
