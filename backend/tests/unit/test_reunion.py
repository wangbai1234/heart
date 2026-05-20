"""
Unit tests for SS04 Reunion State Machine.

Tests per spec §3.10:
- Trigger conditions (7+ day absence)
- Phase transitions (initial → settling → settled)
- Turn counting and advancement logic
- Trust decay during absence
- 30-day absence simulation
- Soul-specific behavioral overlays

Author: 心屿团队
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from heart.ss04_relationship.reunion import ReunionStateMachine


class TestReunionStateMachine:
    """Test suite for ReunionStateMachine."""

    @pytest.fixture
    def reunion_machine(self):
        """Create reunion state machine with default config."""
        return ReunionStateMachine()

    @pytest.fixture
    def rin_reunion_machine(self):
        """Create reunion machine for Rin."""
        soul_config = {
            "character_id": "rin",
            "relational_template": {
                "reunion_modifiers": {
                    "initial_duration_turns": 3,
                    "settling_min_turns": 4,
                    "settling_max_turns": 10,
                    "trust_restoration_rate": 0.8,  # Rin slower to restore trust
                }
            }
        }
        return ReunionStateMachine(soul_config)

    @pytest.fixture
    def dorothy_reunion_machine(self):
        """Create reunion machine for Dorothy."""
        soul_config = {
            "character_id": "dorothy",
            "relational_template": {
                "reunion_modifiers": {
                    "initial_duration_turns": 2,  # Dorothy faster
                    "settling_min_turns": 3,
                    "settling_max_turns": 8,
                    "trust_restoration_rate": 1.2,
                }
            }
        }
        return ReunionStateMachine(soul_config)

    @pytest.fixture
    def base_relationship_state(self):
        """Create base relationship state."""
        return {
            "user_id": str(uuid4()),
            "character_id": "test_char",
            "current_stage": "FRIEND",
            "trust_score": 0.6,
            "attachment_strength": 0.5,
            "intimacy_level": 0.5,
            "active_special_states": [],
            "longest_absence_days": 0,
            "highest_stage_reached": "FRIEND",
        }

    def test_should_trigger_reunion_over_7_days(self, reunion_machine, base_relationship_state):
        """Test reunion triggers after 7+ day absence."""
        # Test trigger at exactly 7 days
        assert not reunion_machine.should_trigger_reunion(7, base_relationship_state)

        # Test trigger at 8 days
        assert reunion_machine.should_trigger_reunion(8, base_relationship_state)

        # Test trigger at 30 days
        assert reunion_machine.should_trigger_reunion(30, base_relationship_state)

    def test_should_not_trigger_if_already_in_reunion(self, reunion_machine, base_relationship_state):
        """Test reunion doesn't re-trigger if already active."""
        # Add existing reunion state
        base_relationship_state["active_special_states"] = [{
            "state_type": "REUNION",
            "entered_at": datetime.now(timezone.utc).isoformat(),
        }]

        assert not reunion_machine.should_trigger_reunion(10, base_relationship_state)

    def test_initiate_reunion(self, reunion_machine, base_relationship_state):
        """Test reunion initiation creates correct state."""
        user_id = uuid4()
        character_id = "rin"
        absence_days = 10

        reunion_state = reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=absence_days,
            user_id=user_id,
            character_id=character_id,
        )

        # Check reunion state structure
        assert reunion_state["state_type"] == "REUNION"
        assert reunion_state["cause"] == f"user_returned_after_{absence_days}_days"

        reunion_data = reunion_state["reunion"]
        assert reunion_data["phase"] == "initial"
        assert reunion_data["turn_in_phase"] == 0
        assert reunion_data["pre_absence_stage"] == "FRIEND"
        assert reunion_data["absence_days"] == absence_days
        assert reunion_data["total_turns_in_reunion"] == 0

        # Check state was added to active_special_states
        assert len(base_relationship_state["active_special_states"]) == 1
        assert base_relationship_state["longest_absence_days"] == absence_days

    def test_phase_transition_initial_to_settling_by_turns(
        self, reunion_machine, base_relationship_state
    ):
        """Test transition from initial to settling after 3 turns."""
        # Initiate reunion
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        # Advance 3 turns without special signals
        for _ in range(3):
            reunion_state = reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        # Should transition to settling
        assert reunion_state is not None
        assert reunion_state["reunion"]["phase"] == "settling"
        assert reunion_state["reunion"]["turn_in_phase"] == 0  # Reset counter

    def test_phase_transition_initial_to_settling_by_engagement(
        self, reunion_machine, base_relationship_state
    ):
        """Test early transition from initial to settling with strong engagement."""
        # Initiate reunion
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        # User explains absence on turn 1
        reunion_state = reunion_machine.advance_reunion(
            relationship_state=base_relationship_state,
            user_engagement_signals={
                "absence_explained": True,
            },
        )

        # Should transition early to settling
        assert reunion_state is not None
        assert reunion_state["reunion"]["phase"] == "settling"
        assert reunion_state["reunion"]["transition_reason"] == "strong_engagement"

    def test_phase_transition_settling_to_complete(
        self, reunion_machine, base_relationship_state
    ):
        """Test transition from settling to complete (reunion ends)."""
        # Initiate and advance to settling
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        # Fast forward to settling
        for _ in range(3):
            reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        # Now in settling phase - advance with sustained attention
        for turn in range(5):
            signals = {}
            if turn >= 3:  # After min turns
                signals["sustained_attention"] = True

            reunion_state = reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals=signals,
            )

            if reunion_state is None:
                # Reunion completed
                break

        # Should have completed and removed reunion state
        assert reunion_state is None
        assert len(base_relationship_state["active_special_states"]) == 0

    def test_phase_force_completion_after_max_turns(
        self, reunion_machine, base_relationship_state
    ):
        """Test reunion force completes after max turns in settling."""
        # Initiate and advance to settling
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        # Fast forward to settling
        for _ in range(3):
            reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        # Advance 10 more turns (max) without sustained attention
        for _ in range(10):
            reunion_state = reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        # Should force complete
        assert reunion_state is None

    def test_get_reunion_phase(self, reunion_machine, base_relationship_state):
        """Test getting current reunion phase."""
        # No reunion initially
        assert reunion_machine.get_reunion_phase(base_relationship_state) is None

        # Initiate reunion
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        # Check initial phase
        assert reunion_machine.get_reunion_phase(base_relationship_state) == "initial"

        # Advance to settling
        for _ in range(3):
            reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        assert reunion_machine.get_reunion_phase(base_relationship_state) == "settling"

    def test_trust_decay_during_absence(self, reunion_machine):
        """Test trust decay calculation per spec §4.4."""
        # No decay under 14 days
        trust = 0.8
        decayed = reunion_machine.compute_trust_decay_during_absence(
            absence_days=10,
            current_trust=trust,
            highest_stage_reached="FRIEND",
        )
        assert decayed == trust

        # Decay 14-30 days (×0.995/day)
        decayed = reunion_machine.compute_trust_decay_during_absence(
            absence_days=20,
            current_trust=0.8,
            highest_stage_reached="FRIEND",
        )
        # 6 days at 0.995: 0.8 * 0.995^6 ≈ 0.776
        assert 0.77 < decayed < 0.78

        # Decay 30-90 days (×0.99/day)
        decayed = reunion_machine.compute_trust_decay_during_absence(
            absence_days=44,  # 30 days over threshold
            current_trust=0.8,
            highest_stage_reached="FRIEND",
        )
        # 30 days at 0.99: 0.8 * 0.99^30 ≈ 0.592
        assert 0.59 < decayed < 0.60

        # Test floor for CONFIDANT stage (floor = 0.3)
        decayed = reunion_machine.compute_trust_decay_during_absence(
            absence_days=100,
            current_trust=0.8,
            highest_stage_reached="CONFIDANT",
        )
        assert decayed >= 0.3  # Floor applied

    def test_30_day_absence_full_simulation(self, reunion_machine, base_relationship_state):
        """Test full 30-day absence scenario."""
        absence_days = 30
        initial_trust = 0.7

        base_relationship_state["trust_score"] = initial_trust
        base_relationship_state["current_stage"] = "CONFIDANT"
        base_relationship_state["highest_stage_reached"] = "CONFIDANT"

        # Compute trust decay
        decayed_trust = reunion_machine.compute_trust_decay_during_absence(
            absence_days=absence_days,
            current_trust=initial_trust,
            highest_stage_reached="CONFIDANT",
        )

        # Trust should decay but not below floor
        assert decayed_trust < initial_trust
        assert decayed_trust >= 0.3  # Floor

        # Initiate reunion
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=absence_days,
            user_id=uuid4(),
            character_id="rin",
        )

        # Simulate initial phase (3 turns)
        for turn in range(3):
            reunion_state = reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals={},
            )

        assert reunion_state["reunion"]["phase"] == "settling"

        # Simulate settling phase (8 turns with sustained attention after turn 4)
        for turn in range(8):
            signals = {}
            if turn >= 4:
                signals["sustained_attention"] = True

            reunion_state = reunion_machine.advance_reunion(
                relationship_state=base_relationship_state,
                user_engagement_signals=signals,
            )

            if reunion_state is None:
                break

        # Should complete
        assert reunion_state is None
        assert base_relationship_state["longest_absence_days"] == 30

    def test_behavioral_overlay_rin_initial(self, rin_reunion_machine):
        """Test behavioral overlay for Rin in initial phase."""
        soul_config = {"character_id": "rin"}

        reunion_state = {
            "state_type": "REUNION",
            "reunion": {
                "phase": "initial",
                "absence_days": 10,
                "turn_in_phase": 1,
            },
        }

        overlay = rin_reunion_machine.get_behavioral_overlay(reunion_state, soul_config)

        # Check for key phrases
        assert "消失了" in overlay
        assert "想念" in overlay or "委屈" in overlay
        assert "更短" in overlay  # Short sentences
        assert "不会主动延续话题" in overlay

    def test_behavioral_overlay_dorothy_settling(self, dorothy_reunion_machine):
        """Test behavioral overlay for Dorothy in settling phase."""
        soul_config = {"character_id": "dorothy"}

        reunion_state = {
            "state_type": "REUNION",
            "reunion": {
                "phase": "settling",
                "absence_days": 15,
                "turn_in_phase": 5,
            },
        }

        overlay = dorothy_reunion_machine.get_behavioral_overlay(reunion_state, soul_config)

        # Check for key phrases
        assert "慢慢恢复" in overlay or "正在" in overlay
        assert "温和" in overlay or "谨慎" in overlay
        assert "委屈" in overlay

    def test_rin_slower_progression(self, rin_reunion_machine, dorothy_reunion_machine):
        """Test Rin takes longer than Dorothy in reunion."""
        # Rin initial phase: 3 turns
        rin_config = rin_reunion_machine.reunion_modifiers
        assert rin_config["initial_duration_turns"] == 3

        # Dorothy initial phase: 2 turns
        dorothy_config = dorothy_reunion_machine.reunion_modifiers
        assert dorothy_config["initial_duration_turns"] == 2

        # Rin settling: 4-10 turns
        assert rin_config["settling_min_turns"] == 4
        assert rin_config["settling_max_turns"] == 10

        # Dorothy settling: 3-8 turns
        assert dorothy_config["settling_min_turns"] == 3
        assert dorothy_config["settling_max_turns"] == 8

    def test_multiple_absences_tracking(self, reunion_machine, base_relationship_state):
        """Test that multiple absences update longest_absence_days correctly."""
        # First absence: 10 days
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=10,
            user_id=uuid4(),
            character_id="test",
        )

        assert base_relationship_state["longest_absence_days"] == 10

        # Complete first reunion
        base_relationship_state["active_special_states"] = []

        # Second absence: 8 days (shorter)
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=8,
            user_id=uuid4(),
            character_id="test",
        )

        # Should not update (8 < 10)
        assert base_relationship_state["longest_absence_days"] == 10

        # Complete second reunion
        base_relationship_state["active_special_states"] = []

        # Third absence: 20 days (longer)
        reunion_machine.initiate_reunion(
            relationship_state=base_relationship_state,
            absence_days=20,
            user_id=uuid4(),
            character_id="test",
        )

        # Should update
        assert base_relationship_state["longest_absence_days"] == 20
