"""Unit tests for SS04 ColdWarTracker and ReunionStateMachine wiring in service."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss04_relationship.cold_war import ColdWarTracker
from heart.ss04_relationship.reunion import ReunionStateMachine
from heart.ss04_relationship.service import RelationshipService
from heart.ss04_relationship.stage_engine import SignalBatch


def _make_emotion_state(coldness=0.0, cause=None):
    """Create emotion state dict for cold war testing."""
    active_stack = []
    if coldness > 0:
        emotion = {"emotion": "coldness", "intensity": coldness}
        if cause:
            emotion["cause"] = {"raw_signal": cause}
        active_stack.append(emotion)
    return {"active_stack": active_stack, "pending_repairs": []}


def _make_relationship_state(**overrides):
    """Create relationship state dict for testing."""
    state = {
        "active_special_states": [],
        "total_conflicts": 0,
        "recent_conflicts": [],
        "trust_score": 0.5,
        "attachment_strength": 0.5,
        "current_stage": "STRANGER",
        "longest_absence_days": 0,
    }
    state.update(overrides)
    return state


class TestColdWarTrackerWiring:
    """Tests for ColdWarTracker integration in RelationshipService."""

    def test_cold_war_tracker_created_per_character(self):
        """ColdWarTracker should be created lazily per character."""
        db = AsyncMock()
        service = RelationshipService(db, {"rin": {"character_id": "rin"}})
        tracker = service._get_cold_war_tracker("rin")
        assert isinstance(tracker, ColdWarTracker)
        # Same instance returned on second call
        assert service._get_cold_war_tracker("rin") is tracker

    def test_cold_war_tracker_uses_soul_config(self):
        """ColdWarTracker should receive soul_config from service."""
        db = AsyncMock()
        soul_spec = {
            "character_id": "rin",
            "relational_template": {"cold_war_modifiers": {"trigger_threshold": 0.3}},
        }
        service = RelationshipService(db, {"rin": soul_spec})
        tracker = service._get_cold_war_tracker("rin")
        assert tracker.cold_war_modifiers["trigger_threshold"] == 0.3

    def test_cold_war_trigger_with_emotion_state(self):
        """Cold war should trigger when emotion_state has high coldness."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.7, cause="user said something hurtful")
        rel_state = _make_relationship_state()

        assert tracker.should_trigger_cold_war(emotion, rel_state) is True

    def test_cold_war_no_trigger_without_cause(self):
        """Cold war should NOT trigger without a specific cause."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.7)  # no cause
        rel_state = _make_relationship_state()

        assert tracker.should_trigger_cold_war(emotion, rel_state) is False

    def test_cold_war_no_trigger_already_in_cold_war(self):
        """Cold war should NOT trigger if already in cold war."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.7, cause="conflict")
        rel_state = _make_relationship_state(active_special_states=[{"state_type": "COLD_WAR"}])

        assert tracker.should_trigger_cold_war(emotion, rel_state) is False

    def test_cold_war_initiate_creates_state(self):
        """initiate_cold_war should create proper state dict."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.8, cause="betrayal")
        rel_state = _make_relationship_state()

        result = tracker.initiate_cold_war(emotion, rel_state)

        assert result["state_type"] == "COLD_WAR"
        assert result["cold_war"]["intensity"] == 0.8
        assert result["cold_war"]["repair_progress"] == 0.0
        assert len(rel_state["active_special_states"]) == 1
        assert rel_state["total_conflicts"] == 1

    def test_cold_war_update_tracks_repair_progress(self):
        """update_cold_war should track repair progress."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.8, cause="conflict")
        rel_state = _make_relationship_state()
        tracker.initiate_cold_war(emotion, rel_state)

        # Simulate low repair progress (below reconciling threshold 0.4)
        emotion_with_repair = _make_emotion_state(coldness=0.6)
        emotion_with_repair["pending_repairs"] = [{"emotion": "coldness", "repair_progress": 0.2}]

        transition = tracker.update_cold_war(rel_state, emotion_with_repair)
        assert transition is None  # Not yet resolved, not yet reconciling

        cold_war_data = rel_state["active_special_states"][0]["cold_war"]
        assert cold_war_data["repair_progress"] == 0.2
        assert cold_war_data["turns_in_cold_war"] == 1

    def test_cold_war_update_transitions_to_reconciling(self):
        """update_cold_war should transition to reconciling when progress > 0.4."""
        tracker = ColdWarTracker()
        emotion = _make_emotion_state(coldness=0.8, cause="conflict")
        rel_state = _make_relationship_state()
        tracker.initiate_cold_war(emotion, rel_state)

        # Simulate repair progress above reconciling threshold
        emotion_with_repair = _make_emotion_state(coldness=0.6)
        emotion_with_repair["pending_repairs"] = [{"emotion": "coldness", "repair_progress": 0.6}]

        transition = tracker.update_cold_war(rel_state, emotion_with_repair)
        assert transition == "to_reconciling"
        assert any(s.get("state_type") == "RECONCILING" for s in rel_state["active_special_states"])


class TestReunionStateMachineWiring:
    """Tests for ReunionStateMachine integration in RelationshipService."""

    def test_reunion_machine_created_per_character(self):
        """ReunionStateMachine should be created lazily per character."""
        db = AsyncMock()
        service = RelationshipService(db, {"rin": {"character_id": "rin"}})
        machine = service._get_reunion_machine("rin")
        assert isinstance(machine, ReunionStateMachine)
        assert service._get_reunion_machine("rin") is machine

    def test_reunion_trigger_on_long_absence(self):
        """Reunion should trigger when days_since_last > 7."""
        machine = ReunionStateMachine()
        rel_state = _make_relationship_state()

        assert machine.should_trigger_reunion(10, rel_state) is True

    def test_reunion_no_trigger_short_absence(self):
        """Reunion should NOT trigger for short absence."""
        machine = ReunionStateMachine()
        rel_state = _make_relationship_state()

        assert machine.should_trigger_reunion(5, rel_state) is False

    def test_reunion_no_trigger_already_in_reunion(self):
        """Reunion should NOT trigger if already in reunion."""
        machine = ReunionStateMachine()
        rel_state = _make_relationship_state(active_special_states=[{"state_type": "REUNION"}])

        assert machine.should_trigger_reunion(10, rel_state) is False

    def test_reunion_initiate_creates_state(self):
        """initiate_reunion should create proper state dict."""
        machine = ReunionStateMachine()
        rel_state = _make_relationship_state()
        user_id = uuid4()

        result = machine.initiate_reunion(rel_state, 15, user_id, "rin")

        assert result["state_type"] == "REUNION"
        assert result["reunion"]["phase"] == "initial"
        assert result["reunion"]["absence_days"] == 15
        assert len(rel_state["active_special_states"]) == 1

    def test_reunion_advance_phases(self):
        """advance_reunion should transition through phases."""
        machine = ReunionStateMachine()
        rel_state = _make_relationship_state()
        user_id = uuid4()
        machine.initiate_reunion(rel_state, 10, user_id, "rin")

        # Turn 1-2: stay in initial
        for _ in range(2):
            result = machine.advance_reunion(rel_state, {})
            assert result is not None
            assert result["reunion"]["phase"] == "initial"

        # Turn 3: transition to settling (initial_duration_turns=3)
        result = machine.advance_reunion(rel_state, {})
        assert result is not None
        assert result["reunion"]["phase"] == "settling"

    def test_trust_decay_during_absence(self):
        """compute_trust_decay_during_absence should apply correct decay."""
        machine = ReunionStateMachine()

        # < 14 days: no decay
        assert machine.compute_trust_decay_during_absence(10, 0.8, "STRANGER") == 0.8

        # 14-30 days: x0.995/day
        decayed = machine.compute_trust_decay_during_absence(20, 0.8, "STRANGER")
        assert decayed < 0.8
        assert decayed > 0.7

        # > 90 days with CONFIDANT: floor at 0.3
        decayed = machine.compute_trust_decay_during_absence(100, 0.8, "CONFIDANT")
        assert decayed >= 0.3


class TestStateToDict:
    """Tests for _state_to_dict helper."""

    def test_state_to_dict_converts_orm(self):
        """_state_to_dict should convert ORM fields to dict."""
        db = AsyncMock()
        service = RelationshipService(db, {})

        state = MagicMock()
        state.active_special_states = [{"state_type": "COLD_WAR"}]
        state.total_conflicts = 3
        state.recent_conflicts = [{"conflict_id": "123"}]
        state.trust_score = 0.7
        state.attachment_strength = 0.6
        state.current_stage = "FRIEND"
        state.longest_absence_days = 20

        result = service._state_to_dict(state)

        assert result["active_special_states"] == [{"state_type": "COLD_WAR"}]
        assert result["total_conflicts"] == 3
        assert result["trust_score"] == 0.7
        assert result["current_stage"] == "FRIEND"

    def test_state_to_dict_handles_none_fields(self):
        """_state_to_dict should handle None fields gracefully."""
        db = AsyncMock()
        service = RelationshipService(db, {})

        state = MagicMock()
        state.active_special_states = None
        state.total_conflicts = None
        state.recent_conflicts = None
        state.trust_score = None
        state.attachment_strength = None
        state.current_stage = "STRANGER"
        state.longest_absence_days = None

        result = service._state_to_dict(state)

        assert result["active_special_states"] == []
        assert result["total_conflicts"] == 0
        assert result["trust_score"] == 0.0
