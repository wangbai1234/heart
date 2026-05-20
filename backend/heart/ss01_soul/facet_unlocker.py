"""
Hidden Facet Unlocker - SS01 Soul Spec §5.1

Checks unlock conditions for hidden_facets based on:
- Resonance score threshold
- Multi-signal corroboration (required_triggers)
- Prerequisites (other facets)

Emits "soul.facet.unlocked" events when facets unlock.

Key principles (§2.1):
- P-7: Hidden Facets require multi-signal corroboration, not single trigger
- Idempotent: don't unlock same facet twice
- Immersion: unlock must be narratively earned

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Protocol
from uuid import UUID, uuid4

import structlog

from .registry import SoulRegistry, get_soul_registry
from .schema_validator import SoulSpec

logger = structlog.get_logger()


# ============================================================
# Event Bus Protocol
# ============================================================


class EventBus(Protocol):
    """Protocol for event emission (to be implemented in orchestration layer)."""

    def emit(self, event_type: str, payload: dict) -> None:
        """Emit an event with type and payload."""
        ...


# ============================================================
# Data Structures
# ============================================================


@dataclass(frozen=True)
class TriggerProgress:
    """Progress toward a specific trigger's cumulative_count."""

    trigger_id: str
    current_count: int
    required_count: int
    satisfied: bool
    last_triggered_at: Optional[datetime] = None
    event_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class FacetTriggerState:
    """Current trigger progress for a facet.

    Maps trigger_id → progress for all triggers in facet.required_triggers.
    """

    facet_id: str
    triggers: dict[str, TriggerProgress]

    def satisfied_trigger_count(self) -> int:
        """Count how many triggers have met their cumulative_count."""
        return sum(1 for t in self.triggers.values() if t.satisfied)

    def is_corroboration_satisfied(self, required_count: int) -> bool:
        """Check if corroboration_count is met."""
        return self.satisfied_trigger_count() >= required_count


@dataclass(frozen=True)
class UnlockedFacet:
    """Record of an unlocked facet."""

    facet_id: str
    unlocked_at: datetime
    unlock_trigger_states: dict[str, TriggerProgress]
    dormant: bool = False


@dataclass(frozen=True)
class FacetUnlockEvent:
    """Event emitted when a facet unlocks."""

    event_id: UUID
    user_id: UUID
    character_id: str
    facet_id: str
    unlocked_at: datetime
    resonance_score_at_unlock: float
    trigger_states: dict[str, TriggerProgress]


@dataclass(frozen=True)
class FacetUnlockResult:
    """Result of check_unlock_conditions."""

    newly_unlocked: tuple[str, ...]  # facet_ids
    events: tuple[FacetUnlockEvent, ...]
    total_unlocked_count: int  # including previously unlocked


@dataclass(frozen=True)
class ActivationStateForUnlock:
    """Minimal projection of SoulActivationState for facet unlock.

    Provided by SoulActivationStateService.
    """

    resonance_score: float
    unlocked_facets: tuple[UnlockedFacet, ...]
    facet_trigger_states: dict[str, FacetTriggerState]


# ============================================================
# Facet Unlocker
# ============================================================


class FacetUnlocker:
    """Checks and unlocks hidden facets based on resonance + triggers.

    Thread-safe (no mutable shared state).
    """

    def __init__(
        self,
        registry: Optional[SoulRegistry] = None,
        event_bus: Optional[EventBus] = None,
    ):
        """Initialize FacetUnlocker.

        Args:
            registry: Soul Registry (defaults to global singleton)
            event_bus: Event bus for emitting unlock events (optional for tests)
        """
        self._registry = registry or get_soul_registry()
        self._event_bus = event_bus

    def check_unlock_conditions(
        self,
        user_id: UUID,
        character_id: str,
        activation_state: ActivationStateForUnlock,
        current_time: Optional[datetime] = None,
    ) -> FacetUnlockResult:
        """Check if any hidden facets should unlock.

        Args:
            user_id: User UUID
            character_id: Character ID (e.g., "rin")
            activation_state: Current activation state
            current_time: Current time (defaults to now, injected for testing)

        Returns:
            FacetUnlockResult with newly unlocked facets and events
        """
        current_time = current_time or datetime.now(timezone.utc)

        # 1. Load soul spec
        soul = self._registry.get_soul(character_id)

        # 2. Get already unlocked facet IDs
        already_unlocked = {f.facet_id for f in activation_state.unlocked_facets}

        # 3. Check each hidden facet
        newly_unlocked = []
        events = []

        for facet_def in soul.identity_anchor.hidden_facets:
            facet_id = facet_def.id

            # Skip if already unlocked (idempotent)
            if facet_id in already_unlocked:
                continue

            # Check unlock conditions
            if self._should_unlock(
                facet_def,
                activation_state,
                already_unlocked,
            ):
                # Unlock!
                trigger_states = activation_state.facet_trigger_states.get(
                    facet_id,
                    FacetTriggerState(facet_id=facet_id, triggers={}),
                ).triggers

                event = FacetUnlockEvent(
                    event_id=uuid4(),
                    user_id=user_id,
                    character_id=character_id,
                    facet_id=facet_id,
                    unlocked_at=current_time,
                    resonance_score_at_unlock=activation_state.resonance_score,
                    trigger_states=trigger_states,
                )

                newly_unlocked.append(facet_id)
                events.append(event)

                logger.info(
                    "soul_facet_unlocked",
                    user_id=str(user_id),
                    character_id=character_id,
                    facet_id=facet_id,
                    resonance_score=activation_state.resonance_score,
                    trigger_count=len(trigger_states),
                )

                # Emit event to event bus
                if self._event_bus:
                    self._event_bus.emit(
                        "soul.facet.unlocked",
                        {
                            "event_id": str(event.event_id),
                            "user_id": str(user_id),
                            "character_id": character_id,
                            "facet_id": facet_id,
                            "unlocked_at": event.unlocked_at.isoformat(),
                            "resonance_score": activation_state.resonance_score,
                        },
                    )

        return FacetUnlockResult(
            newly_unlocked=tuple(newly_unlocked),
            events=tuple(events),
            total_unlocked_count=len(already_unlocked) + len(newly_unlocked),
        )

    def _should_unlock(
        self,
        facet_def,
        activation_state: ActivationStateForUnlock,
        already_unlocked: set[str],
    ) -> bool:
        """Check if a facet should unlock.

        Checks:
        1. Resonance score threshold
        2. Prerequisites (other facets unlocked)
        3. Required triggers (corroboration_count)
        """
        # 1. Check resonance score
        if activation_state.resonance_score < facet_def.threshold.resonance_score:
            return False

        # 2. Check prerequisites (if any)
        prerequisites = getattr(facet_def.threshold, "prerequisites", None)
        if prerequisites:
            for prereq in prerequisites:
                # Parse prerequisite (format: "facet-xxx 必须已解锁 ≥ N 天")
                # For MVP, we just check if the facet is unlocked
                # Full time-based check would require UnlockedFacet.unlocked_at
                prereq_facet_id = self._parse_prerequisite_facet_id(prereq)
                if prereq_facet_id and prereq_facet_id not in already_unlocked:
                    return False

        # 3. Check required triggers (corroboration)
        facet_trigger_state = activation_state.facet_trigger_states.get(
            facet_def.id,
            FacetTriggerState(facet_id=facet_def.id, triggers={}),
        )

        corroboration_count = facet_def.threshold.corroboration_count
        if not facet_trigger_state.is_corroboration_satisfied(corroboration_count):
            return False

        # All conditions met
        return True

    def _parse_prerequisite_facet_id(self, prereq_str: str) -> Optional[str]:
        """Parse facet ID from prerequisite string.

        Example: "facet-found-witness 必须已解锁 ≥ 14 天" → "facet-found-witness"
        """
        # Simple parsing: extract first token (facet-xxx)
        parts = prereq_str.split()
        if parts and parts[0].startswith("facet-"):
            return parts[0]
        return None


# ============================================================
# Helper: Build FacetTriggerState from Events
# ============================================================


def build_facet_trigger_state(
    soul: SoulSpec,
    facet_id: str,
    recent_events: list,
) -> FacetTriggerState:
    """Build FacetTriggerState from recent events.

    This is a helper for tests and state service implementations.

    Args:
        soul: Soul Spec
        facet_id: Facet ID to build state for
        recent_events: List of events with trigger_id and event_id

    Returns:
        FacetTriggerState with trigger progress
    """
    # Find facet definition
    facet_def = next(
        (f for f in soul.identity_anchor.hidden_facets if f.id == facet_id),
        None,
    )
    if not facet_def:
        return FacetTriggerState(facet_id=facet_id, triggers={})

    # Count events per trigger
    trigger_counts: dict[str, list] = {}
    for event in recent_events:
        trigger_id = getattr(event, "trigger_id", None)
        if trigger_id:
            if trigger_id not in trigger_counts:
                trigger_counts[trigger_id] = []
            trigger_counts[trigger_id].append(event)

    # Build trigger progress
    triggers = {}
    for trigger_def in facet_def.threshold.required_triggers:
        trigger_id = trigger_def.id
        events_for_trigger = trigger_counts.get(trigger_id, [])
        current_count = len(events_for_trigger)
        required_count = trigger_def.cumulative_count

        triggers[trigger_id] = TriggerProgress(
            trigger_id=trigger_id,
            current_count=current_count,
            required_count=required_count,
            satisfied=current_count >= required_count,
            last_triggered_at=max(
                (getattr(e, "created_at", None) for e in events_for_trigger),
                default=None,
            ),
            event_ids=tuple(str(getattr(e, "event_id", "")) for e in events_for_trigger),
        )

    return FacetTriggerState(facet_id=facet_id, triggers=triggers)
