"""
Resonance Tracker - SS01 Soul Spec §3.2 + §5.2

Tracks user × character resonance score based on resonance_triggers (§5.1).

Key behaviors:
- Track trigger events with weights from soul.resonance_triggers
- Enforce daily caps per trigger (max_per_day)
- Apply decay for inactive users (>30 days)
- Apply reunion bonus (30-60 days)
- Resonance score clamped to [0, 1]

State storage:
- Read/write via SoulActivationStateService (injected dependency)

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol
from uuid import UUID, uuid4

import structlog

from .registry import SoulRegistry, get_soul_registry
from .schema_validator import SoulSpec

logger = structlog.get_logger()


# ============================================================
# State Service Protocol
# ============================================================

class SoulActivationStateService(Protocol):
    """Protocol for state persistence (to be implemented in future subsystem).

    ResonanceTracker depends on this abstraction, not concrete DB.
    """

    def get_resonance_state(
        self,
        user_id: UUID,
        character_id: str,
    ) -> ResonanceStateSnapshot:
        """Get current resonance state for (user, character)."""
        ...

    def write_resonance_event(
        self,
        user_id: UUID,
        character_id: str,
        event: ResonanceEvent,
    ) -> None:
        """Write resonance event to history (also updates resonance_score)."""
        ...


# ============================================================
# Data Structures
# ============================================================

@dataclass(frozen=True)
class ResonanceStateSnapshot:
    """Minimal projection of SoulActivationState for resonance tracking.

    Populated by SoulActivationStateService.
    """
    resonance_score: float                      # [0, 1]
    last_interaction_at: Optional[datetime]     # None for new users
    resonance_history: tuple[ResonanceEvent, ...]  # recent events (for daily cap check)


@dataclass(frozen=True)
class ResonanceEvent:
    """Resonance event record (§5.2)."""
    event_id: UUID
    trigger_cue: str
    weight_applied: float
    resulting_score: float
    turn_index: int
    created_at: datetime


@dataclass(frozen=True)
class ResonanceTrackResult:
    """Result of track_event call."""
    event: Optional[ResonanceEvent]    # None if cap reached / invalid trigger
    new_score: float                   # Updated resonance_score
    reason: str                        # "triggered" / "capped" / "invalid_trigger"


# ============================================================
# Resonance Tracker
# ============================================================

class ResonanceTracker:
    """Tracks user × character resonance based on soul.resonance_triggers.

    Thread-safe (no mutable shared state).
    """

    # Decay constants (§5.2)
    _DECAY_START_DAYS = 30
    _DECAY_BASE = 0.95

    # Reunion bonus (§5.2)
    _REUNION_BONUS_MIN_DAYS = 30
    _REUNION_BONUS_MAX_DAYS = 60
    _REUNION_BONUS_AMOUNT = 0.05

    def __init__(
        self,
        registry: Optional[SoulRegistry] = None,
        state_service: Optional[SoulActivationStateService] = None,
    ):
        """Initialize ResonanceTracker.

        Args:
            registry: Soul Registry (defaults to global singleton)
            state_service: State persistence service (must be provided in prod)
        """
        self._registry = registry or get_soul_registry()
        self._state_service = state_service

    def track_event(
        self,
        user_id: UUID,
        character_id: str,
        trigger_cue: str,
        turn_index: int,
    ) -> ResonanceTrackResult:
        """Track a resonance trigger event.

        Args:
            user_id: User UUID
            character_id: Character ID (e.g., "rin")
            trigger_cue: Trigger cue string (must match soul.resonance_triggers[].cue)
            turn_index: Current turn index

        Returns:
            ResonanceTrackResult with event (if triggered) and new score
        """
        if not self._state_service:
            raise RuntimeError("ResonanceTracker requires state_service")

        # 1. Load soul spec
        soul = self._registry.get_soul(character_id)

        # 2. Find trigger definition
        trigger_def = next(
            (t for t in soul.identity_anchor.resonance_triggers if t.cue == trigger_cue),
            None,
        )
        if not trigger_def:
            logger.warning(
                "resonance_trigger_not_found",
                character_id=character_id,
                trigger_cue=trigger_cue,
            )
            state = self._state_service.get_resonance_state(user_id, character_id)
            return ResonanceTrackResult(
                event=None,
                new_score=state.resonance_score,
                reason="invalid_trigger",
            )

        # 3. Load current state
        state = self._state_service.get_resonance_state(user_id, character_id)

        # 4. Check daily cap
        today_events = self._count_today_events(state.resonance_history, trigger_cue)
        if today_events >= trigger_def.max_per_day:
            logger.info(
                "resonance_daily_cap_reached",
                character_id=character_id,
                trigger_cue=trigger_cue,
                count=today_events,
                max_per_day=trigger_def.max_per_day,
            )
            return ResonanceTrackResult(
                event=None,
                new_score=state.resonance_score,
                reason="capped",
            )

        # 5. Apply weight
        new_score = min(1.0, state.resonance_score + trigger_def.weight)

        # 6. Create event
        event = ResonanceEvent(
            event_id=uuid4(),
            trigger_cue=trigger_cue,
            weight_applied=trigger_def.weight,
            resulting_score=new_score,
            turn_index=turn_index,
            created_at=datetime.now(timezone.utc),
        )

        # 7. Write to state (orchestrator will call this via state_service)
        self._state_service.write_resonance_event(user_id, character_id, event)

        logger.info(
            "resonance_event_tracked",
            user_id=str(user_id),
            character_id=character_id,
            trigger_cue=trigger_cue,
            weight=trigger_def.weight,
            new_score=new_score,
        )

        return ResonanceTrackResult(
            event=event,
            new_score=new_score,
            reason="triggered",
        )

    def get_score(
        self,
        user_id: UUID,
        character_id: str,
        current_time: Optional[datetime] = None,
    ) -> float:
        """Get current resonance score with decay applied.

        Args:
            user_id: User UUID
            character_id: Character ID
            current_time: Current time (defaults to now, injected for testing)

        Returns:
            Resonance score [0, 1] with decay and reunion bonus applied
        """
        if not self._state_service:
            raise RuntimeError("ResonanceTracker requires state_service")

        current_time = current_time or datetime.now(timezone.utc)
        state = self._state_service.get_resonance_state(user_id, character_id)

        if state.last_interaction_at is None:
            # New user
            return state.resonance_score

        days_since_last = (current_time - state.last_interaction_at).total_seconds() / 86400

        # Apply decay (§5.2)
        score = state.resonance_score
        if days_since_last > self._DECAY_START_DAYS:
            weeks_inactive = (days_since_last - self._DECAY_START_DAYS) / 7
            decay_rate = self._DECAY_BASE ** weeks_inactive
            score *= decay_rate
            logger.debug(
                "resonance_decay_applied",
                user_id=str(user_id),
                character_id=character_id,
                days_since_last=days_since_last,
                decay_rate=decay_rate,
                original_score=state.resonance_score,
                decayed_score=score,
            )

        # Apply reunion bonus (§5.2)
        if self._REUNION_BONUS_MIN_DAYS < days_since_last <= self._REUNION_BONUS_MAX_DAYS:
            score = min(1.0, score + self._REUNION_BONUS_AMOUNT)
            logger.info(
                "resonance_reunion_bonus_applied",
                user_id=str(user_id),
                character_id=character_id,
                days_since_last=days_since_last,
                bonus=self._REUNION_BONUS_AMOUNT,
                new_score=score,
            )

        return max(0.0, min(1.0, score))

    def _count_today_events(
        self,
        history: tuple[ResonanceEvent, ...],
        trigger_cue: str,
    ) -> int:
        """Count how many times trigger_cue fired today."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        count = sum(
            1
            for event in history
            if event.trigger_cue == trigger_cue and event.created_at >= today_start
        )

        return count
