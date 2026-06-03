"""
Unit tests for Hidden Facet Unlocker (SS01 §5.1).

Covers design requirements:
- Resonance score threshold check
- Multi-signal corroboration (required_triggers)
- Prerequisites (other facets)
- Idempotent unlock (don't unlock twice)
- Event emission on unlock

Author: 心屿团队
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from heart.ss01_soul.facet_unlocker import (
    ActivationStateForUnlock,
    FacetTriggerState,
    FacetUnlocker,
    TriggerProgress,
    UnlockedFacet,
    build_facet_trigger_state,
)
from heart.ss01_soul.registry import get_soul_registry

# ============================================================
# Mock Event Bus
# ============================================================


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.events: list[tuple[str, dict]] = []

    def emit(self, event_type: str, payload: dict) -> None:
        self.events.append((event_type, payload))

    def get_events_by_type(self, event_type: str) -> list[dict]:
        return [payload for et, payload in self.events if et == event_type]


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mock_event_bus():
    return MockEventBus()


@pytest.fixture
def unlocker(mock_event_bus):
    return FacetUnlocker(event_bus=mock_event_bus)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def soul():
    """Get Rin soul spec for testing."""
    registry = get_soul_registry()
    return registry.get_soul("rin")


# ============================================================
# Helper: Create Activation State
# ============================================================


def make_activation_state(
    resonance_score: float = 0.0,
    unlocked_facets: list[UnlockedFacet] | None = None,
    facet_trigger_states: dict[str, FacetTriggerState] | None = None,
) -> ActivationStateForUnlock:
    """Helper to create activation state."""
    return ActivationStateForUnlock(
        resonance_score=resonance_score,
        unlocked_facets=tuple(unlocked_facets or []),
        facet_trigger_states=facet_trigger_states or {},
    )


# ============================================================
# Basic Threshold Tests
# ============================================================


class TestThresholdChecks:
    def test_resonance_below_threshold_no_unlock(self, unlocker, user_id):
        # facet-found-witness requires resonance >= 0.55
        state = make_activation_state(resonance_score=0.40)

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        assert len(result.newly_unlocked) == 0
        assert len(result.events) == 0

    def test_resonance_at_threshold_but_no_triggers_no_unlock(self, unlocker, user_id):
        # Resonance met, but no triggers satisfied
        state = make_activation_state(resonance_score=0.60)

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        assert len(result.newly_unlocked) == 0


# ============================================================
# Corroboration Tests (Multi-Signal Requirement)
# ============================================================


class TestCorroboration:
    def test_single_trigger_satisfied_no_unlock(self, unlocker, user_id, soul):
        # facet-found-witness requires corroboration_count=3
        # Only satisfy 1 trigger → no unlock
        facet_id = "facet-found-witness"

        # Build trigger state: only "patient-silence" satisfied
        triggers = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=0,
                required_count=2,
                satisfied=False,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=0,
                required_count=1,
                satisfied=False,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        assert len(result.newly_unlocked) == 0

    def test_two_triggers_satisfied_no_unlock(self, unlocker, user_id, soul):
        # facet-found-witness requires corroboration_count=3
        # Only satisfy 2 triggers → no unlock
        facet_id = "facet-found-witness"

        triggers = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=0,
                required_count=1,
                satisfied=False,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        assert len(result.newly_unlocked) == 0

    def test_all_triggers_satisfied_unlock(self, unlocker, user_id, mock_event_bus):
        # facet-found-witness: all 3 triggers satisfied → unlock
        facet_id = "facet-found-witness"

        triggers = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=1,
                required_count=1,
                satisfied=True,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Should unlock
        assert len(result.newly_unlocked) == 1
        assert result.newly_unlocked[0] == facet_id

        # Event emitted
        assert len(result.events) == 1
        event = result.events[0]
        assert event.facet_id == facet_id
        assert event.resonance_score_at_unlock == 0.60

        # Event bus received event
        bus_events = mock_event_bus.get_events_by_type("soul.facet.unlocked")
        assert len(bus_events) == 1
        assert bus_events[0]["facet_id"] == facet_id

    def test_corroboration_count_two_unlocks_with_two_triggers(self, unlocker, user_id):
        # facet-allows-want requires corroboration_count=2
        # Satisfy 2 out of 3 triggers → unlock
        facet_id = "facet-allows-want"

        triggers = {
            "rebuff-caught": TriggerProgress(
                trigger_id="rebuff-caught",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "want-prompt": TriggerProgress(
                trigger_id="want-prompt",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "daily-presence": TriggerProgress(
                trigger_id="daily-presence",
                current_count=0,
                required_count=1,
                satisfied=False,
            ),
        }

        # Also need facet-found-witness unlocked (prerequisite)
        unlocked_facets = [
            UnlockedFacet(
                facet_id="facet-found-witness",
                unlocked_at=datetime.now(timezone.utc),
                unlock_trigger_states={},
            )
        ]

        state = make_activation_state(
            resonance_score=0.80,  # >= 0.75
            unlocked_facets=unlocked_facets,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Should unlock (2 out of 3 triggers satisfied, corroboration_count=2)
        assert len(result.newly_unlocked) == 1
        assert result.newly_unlocked[0] == facet_id


# ============================================================
# Idempotent Tests
# ============================================================


class TestIdempotent:
    def test_already_unlocked_not_unlocked_again(self, unlocker, user_id):
        # facet-found-witness already unlocked
        facet_id = "facet-found-witness"

        unlocked_facets = [
            UnlockedFacet(
                facet_id=facet_id,
                unlocked_at=datetime.now(timezone.utc),
                unlock_trigger_states={},
            )
        ]

        triggers = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=1,
                required_count=1,
                satisfied=True,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            unlocked_facets=unlocked_facets,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Should NOT unlock again
        assert len(result.newly_unlocked) == 0
        assert result.total_unlocked_count == 1  # counts previously unlocked


# ============================================================
# Prerequisites Tests
# ============================================================


class TestPrerequisites:
    def test_prerequisite_not_met_no_unlock(self, unlocker, user_id):
        # facet-allows-want requires facet-found-witness to be unlocked
        facet_id = "facet-allows-want"

        triggers = {
            "rebuff-caught": TriggerProgress(
                trigger_id="rebuff-caught",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "want-prompt": TriggerProgress(
                trigger_id="want-prompt",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
        }

        state = make_activation_state(
            resonance_score=0.80,
            unlocked_facets=[],  # No prerequisites unlocked
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Should NOT unlock (prerequisite not met)
        assert len(result.newly_unlocked) == 0

    def test_prerequisite_met_unlock(self, unlocker, user_id):
        # facet-allows-want with prerequisite met
        facet_id = "facet-allows-want"

        triggers = {
            "rebuff-caught": TriggerProgress(
                trigger_id="rebuff-caught",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "want-prompt": TriggerProgress(
                trigger_id="want-prompt",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
        }

        unlocked_facets = [
            UnlockedFacet(
                facet_id="facet-found-witness",
                unlocked_at=datetime.now(timezone.utc),
                unlock_trigger_states={},
            )
        ]

        state = make_activation_state(
            resonance_score=0.80,
            unlocked_facets=unlocked_facets,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Should unlock (prerequisite met)
        assert len(result.newly_unlocked) == 1
        assert result.newly_unlocked[0] == facet_id


# ============================================================
# Event Emission Tests
# ============================================================


class TestEventEmission:
    def test_unlock_emits_event(self, unlocker, user_id, mock_event_bus):
        facet_id = "facet-found-witness"

        triggers = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=1,
                required_count=1,
                satisfied=True,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            facet_trigger_states={
                facet_id: FacetTriggerState(facet_id=facet_id, triggers=triggers)
            },
        )

        unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # Check event emitted to bus
        bus_events = mock_event_bus.get_events_by_type("soul.facet.unlocked")
        assert len(bus_events) == 1

        event_payload = bus_events[0]
        assert event_payload["facet_id"] == facet_id
        assert event_payload["character_id"] == "rin"
        assert event_payload["user_id"] == str(user_id)
        assert event_payload["resonance_score"] == 0.60

    def test_no_unlock_no_event(self, unlocker, user_id, mock_event_bus):
        # Threshold not met
        state = make_activation_state(resonance_score=0.40)

        unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # No events emitted
        bus_events = mock_event_bus.get_events_by_type("soul.facet.unlocked")
        assert len(bus_events) == 0


# ============================================================
# Integration Tests
# ============================================================


class TestIntegration:
    def test_gradual_unlock_sequence(self, unlocker, user_id):
        """Test realistic unlock sequence: facet-found-witness → facet-allows-want."""

        # Step 1: Start with low resonance, no triggers
        state = make_activation_state(resonance_score=0.30)

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )
        assert len(result.newly_unlocked) == 0

        # Step 2: Resonance increases, triggers accumulate
        triggers_step2 = {
            "patient-silence": TriggerProgress(
                trigger_id="patient-silence",
                current_count=3,
                required_count=3,
                satisfied=True,
            ),
            "precise-quote": TriggerProgress(
                trigger_id="precise-quote",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "voice-mimicry": TriggerProgress(
                trigger_id="voice-mimicry",
                current_count=1,
                required_count=1,
                satisfied=True,
            ),
        }

        state = make_activation_state(
            resonance_score=0.60,
            facet_trigger_states={
                "facet-found-witness": FacetTriggerState(
                    facet_id="facet-found-witness",
                    triggers=triggers_step2,
                )
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # facet-found-witness unlocks
        assert len(result.newly_unlocked) == 1
        assert "facet-found-witness" in result.newly_unlocked

        # Step 3: Continue to higher resonance, unlock facet-allows-want
        triggers_step3 = {
            "rebuff-caught": TriggerProgress(
                trigger_id="rebuff-caught",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
            "want-prompt": TriggerProgress(
                trigger_id="want-prompt",
                current_count=2,
                required_count=2,
                satisfied=True,
            ),
        }

        unlocked_facets = [
            UnlockedFacet(
                facet_id="facet-found-witness",
                unlocked_at=datetime.now(timezone.utc),
                unlock_trigger_states={},
            )
        ]

        state = make_activation_state(
            resonance_score=0.80,
            unlocked_facets=unlocked_facets,
            facet_trigger_states={
                "facet-allows-want": FacetTriggerState(
                    facet_id="facet-allows-want",
                    triggers=triggers_step3,
                )
            },
        )

        result = unlocker.check_unlock_conditions(
            user_id=user_id,
            character_id="rin",
            activation_state=state,
        )

        # facet-allows-want unlocks
        assert len(result.newly_unlocked) == 1
        assert "facet-allows-want" in result.newly_unlocked
        assert result.total_unlocked_count == 2


# ============================================================
# Helper Function Tests
# ============================================================


class TestBuildFacetTriggerState:
    def test_build_from_empty_events(self, soul):
        facet_id = "facet-found-witness"
        events = []

        state = build_facet_trigger_state(soul, facet_id, events)

        assert state.facet_id == facet_id
        assert len(state.triggers) == 3
        assert all(not t.satisfied for t in state.triggers.values())

    def test_build_from_events(self, soul):
        facet_id = "facet-found-witness"

        # Mock events
        from dataclasses import dataclass

        @dataclass
        class MockEvent:
            event_id: str
            trigger_id: str
            created_at: datetime

        now = datetime.now(timezone.utc)
        events = [
            MockEvent("e1", "patient-silence", now),
            MockEvent("e2", "patient-silence", now),
            MockEvent("e3", "patient-silence", now),
            MockEvent("e4", "precise-quote", now),
            MockEvent("e5", "precise-quote", now),
        ]

        state = build_facet_trigger_state(soul, facet_id, events)

        # Check counts
        assert state.triggers["patient-silence"].current_count == 3
        assert state.triggers["patient-silence"].satisfied
        assert state.triggers["precise-quote"].current_count == 2
        assert state.triggers["precise-quote"].satisfied
        assert state.triggers["voice-mimicry"].current_count == 0
        assert not state.triggers["voice-mimicry"].satisfied

        # Corroboration check
        assert state.satisfied_trigger_count() == 2
        assert not state.is_corroboration_satisfied(3)  # need 3, only have 2
