"""
Unit tests for SS04 Cold War Tracker.

Tests per spec §3.11:
- Trigger conditions (coldness > 0.5 + conflict cause)
- Cold war state management
- Repair progress tracking
- Transition to RECONCILING (progress > 0.4)
- Resolution with Gottman effect (progress > 0.8 sustained 5 turns)
- Emergency decay (30+ days)
- Integration with RepairEngine

Author: 心屿团队
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from heart.ss04_relationship.cold_war import ColdWarTracker


class TestColdWarTracker:
    """Test suite for ColdWarTracker."""

    @pytest.fixture
    def cold_war_tracker(self):
        """Create cold war tracker with default config."""
        return ColdWarTracker()

    @pytest.fixture
    def rin_cold_war_tracker(self):
        """Create cold war tracker for Rin."""
        soul_config = {
            "character_id": "rin",
            "relational_template": {
                "cold_war_modifiers": {
                    "trigger_threshold": 0.55,  # Rin slightly higher threshold
                    "reconciling_threshold": 0.4,
                    "resolution_threshold": 0.8,
                    "resolution_sustained_turns": 5,
                    "forgiveness_curve_modifier": 0.9,  # Rin slower to forgive
                }
            }
        }
        return ColdWarTracker(soul_config)

    @pytest.fixture
    def base_emotion_state(self):
        """Create base emotion state."""
        return {
            "active_stack": [],
            "pending_repairs": [],
            "recent_triggers": [],
        }

    @pytest.fixture
    def base_relationship_state(self):
        """Create base relationship state."""
        return {
            "user_id": str(uuid4()),
            "character_id": "test_char",
            "current_stage": "FRIEND",
            "trust_score": 0.6,
            "attachment_strength": 0.5,
            "active_special_states": [],
            "total_conflicts": 0,
            "total_repairs": 0,
            "total_successful_repairs": 0,
            "recent_conflicts": [],
            "recent_repairs": [],
        }

    def test_should_trigger_cold_war_high_coldness(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war triggers when coldness > 0.5."""
        # Add coldness emotion with high intensity
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {
                "raw_signal": "用户说了伤人的话",
            },
        }]

        assert cold_war_tracker.should_trigger_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

    def test_should_not_trigger_without_cause(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war doesn't trigger without identifiable cause."""
        # High coldness but no cause
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {},  # No raw_signal
        }]

        assert not cold_war_tracker.should_trigger_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

    def test_should_not_trigger_if_already_in_cold_war(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war doesn't re-trigger if already active."""
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "conflict"},
        }]

        # Add existing cold war state
        base_relationship_state["active_special_states"] = [{
            "state_type": "COLD_WAR",
            "entered_at": datetime.now(timezone.utc).isoformat(),
        }]

        assert not cold_war_tracker.should_trigger_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

    def test_initiate_cold_war(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war initiation creates correct state."""
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {
                "raw_signal": "用户说了伤人的话",
            },
        }]

        conflict_id = uuid4()
        cold_war_state = cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
            conflict_id=conflict_id,
        )

        # Check cold war state structure
        assert cold_war_state["state_type"] == "COLD_WAR"
        assert cold_war_state["cause"] == "用户说了伤人的话"

        cold_war_data = cold_war_state["cold_war"]
        assert cold_war_data["intensity"] == 0.7
        assert cold_war_data["repair_progress"] == 0.0
        assert cold_war_data["cause_conflict_id"] == str(conflict_id)
        assert cold_war_data["turns_in_cold_war"] == 0

        # Check state was added
        assert len(base_relationship_state["active_special_states"]) == 1

        # Check conflict counters updated
        assert base_relationship_state["total_conflicts"] == 1
        assert len(base_relationship_state["recent_conflicts"]) == 1

        conflict_record = base_relationship_state["recent_conflicts"][0]
        assert conflict_record["severity"] == "major"  # 0.7 intensity
        assert conflict_record["cold_war_initiated"] is True

    def test_update_cold_war_tracks_progress(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war tracks repair progress from emotion state."""
        # Initiate cold war
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "conflict"},
        }]

        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        # Add pending repair with progress
        base_emotion_state["pending_repairs"] = [{
            "emotion": "coldness",
            "repair_progress": 0.3,
        }]

        # Update cold war
        transition = cold_war_tracker.update_cold_war(
            relationship_state=base_relationship_state,
            emotion_state=base_emotion_state,
        )

        # Check progress tracked
        cold_war_state = base_relationship_state["active_special_states"][0]
        assert cold_war_state["cold_war"]["repair_progress"] == 0.3
        assert cold_war_state["cold_war"]["turns_in_cold_war"] == 1

        # Should not transition yet (< 0.4)
        assert transition is None

    def test_transition_to_reconciling(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test transition to RECONCILING at progress > 0.4."""
        # Initiate cold war
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "conflict"},
        }]

        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        # Progress to 0.5
        base_emotion_state["pending_repairs"] = [{
            "emotion": "coldness",
            "repair_progress": 0.5,
        }]

        transition = cold_war_tracker.update_cold_war(
            relationship_state=base_relationship_state,
            emotion_state=base_emotion_state,
        )

        # Should transition to reconciling
        assert transition == "to_reconciling"

        # Check RECONCILING state added
        states = base_relationship_state["active_special_states"]
        reconciling_state = next(s for s in states if s["state_type"] == "RECONCILING")
        assert reconciling_state is not None
        assert reconciling_state["reconciling"]["progress"] == 0.5

    def test_resolution_after_sustained_progress(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test cold war resolves after progress > 0.8 sustained 5 turns."""
        # Initiate cold war
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "conflict"},
        }]

        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        initial_trust = base_relationship_state["trust_score"]
        initial_attachment = base_relationship_state["attachment_strength"]

        # Progress to 0.85
        base_emotion_state["pending_repairs"] = [{
            "emotion": "coldness",
            "repair_progress": 0.85,
        }]

        # Update for 5 turns
        for turn in range(5):
            transition = cold_war_tracker.update_cold_war(
                relationship_state=base_relationship_state,
                emotion_state=base_emotion_state,
            )

        # Should resolve on 5th turn
        assert transition == "resolved"

        # Check states removed
        assert len(base_relationship_state["active_special_states"]) == 0

        # Check Gottman effect applied
        assert base_relationship_state["trust_score"] > initial_trust
        assert base_relationship_state["attachment_strength"] > initial_attachment

        # Check counters updated
        assert base_relationship_state["total_repairs"] == 1
        assert base_relationship_state["total_successful_repairs"] == 1

        # Check conflict marked resolved
        conflict = base_relationship_state["recent_conflicts"][0]
        assert conflict["resolved_at"] is not None
        assert conflict["resolution_quality"] == 0.85

        # Check repair record added
        assert len(base_relationship_state["recent_repairs"]) == 1

    def test_resolution_resets_if_progress_drops(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test resolution counter resets if progress drops below threshold."""
        # Initiate cold war
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "conflict"},
        }]

        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        # Progress to 0.85 for 3 turns
        base_emotion_state["pending_repairs"] = [{
            "emotion": "coldness",
            "repair_progress": 0.85,
        }]

        for _ in range(3):
            cold_war_tracker.update_cold_war(
                relationship_state=base_relationship_state,
                emotion_state=base_emotion_state,
            )

        cold_war_state = base_relationship_state["active_special_states"][0]
        assert cold_war_state["cold_war"]["resolution_sustained_turns"] == 3

        # Progress drops to 0.6
        base_emotion_state["pending_repairs"][0]["repair_progress"] = 0.6

        cold_war_tracker.update_cold_war(
            relationship_state=base_relationship_state,
            emotion_state=base_emotion_state,
        )

        # Counter should reset
        cold_war_state = base_relationship_state["active_special_states"][0]
        assert cold_war_state["cold_war"]["resolution_sustained_turns"] == 0

    def test_intensity_adjusts_with_repair_progress(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test coldness intensity decreases as repair progresses."""
        # Initiate with intensity 0.8
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.8,
            "cause": {"raw_signal": "conflict"},
        }]

        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        # Initial intensity
        cold_war_state = base_relationship_state["active_special_states"][0]
        assert cold_war_state["cold_war"]["intensity"] == 0.8

        # Repair progress to 0.5
        base_emotion_state["pending_repairs"] = [{
            "emotion": "coldness",
            "repair_progress": 0.5,
        }]

        cold_war_tracker.update_cold_war(
            relationship_state=base_relationship_state,
            emotion_state=base_emotion_state,
        )

        # Intensity should decrease: 0.8 × (1 - 0.5 × 0.8) = 0.8 × 0.6 = 0.48
        cold_war_state = base_relationship_state["active_special_states"][0]
        assert abs(cold_war_state["cold_war"]["intensity"] - 0.48) < 0.01

    def test_behavioral_overlay_rin(self, rin_cold_war_tracker, base_relationship_state):
        """Test behavioral overlay for Rin in cold war."""
        # Add cold war state
        base_relationship_state["active_special_states"] = [{
            "state_type": "COLD_WAR",
            "cause": "用户忽视了她的感受",
            "cold_war": {
                "intensity": 0.6,
                "repair_progress": 0.2,
            },
        }]

        soul_config = {"character_id": "rin"}

        overlay = rin_cold_war_tracker.get_behavioral_overlay(
            relationship_state=base_relationship_state,
            soul_config=soul_config,
        )

        # Check for key phrases
        assert overlay is not None
        assert "没解决" in overlay or "不会先说" in overlay
        assert "更短" in overlay
        assert "不会主动延续话题" in overlay

    def test_behavioral_overlay_reconciling(self, cold_war_tracker, base_relationship_state):
        """Test behavioral overlay for RECONCILING state."""
        # Add reconciling state
        base_relationship_state["active_special_states"] = [{
            "state_type": "RECONCILING",
            "cause": "cold_war_repair_progress",
            "reconciling": {
                "progress": 0.6,
            },
        }]

        soul_config = {"character_id": "dorothy"}

        overlay = cold_war_tracker.get_behavioral_overlay(
            relationship_state=base_relationship_state,
            soul_config=soul_config,
        )

        # Check for key phrases
        assert overlay is not None
        assert "修复" in overlay or "努力" in overlay
        assert "软" in overlay or "温柔" in overlay
        assert "bittersweet" in overlay.lower() or "谨慎" in overlay

    def test_emergency_decay_after_30_days(self, cold_war_tracker, base_relationship_state):
        """Test emergency decay kicks in after 30+ days."""
        # Add cold war state with high intensity
        base_relationship_state["active_special_states"] = [{
            "state_type": "COLD_WAR",
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "cold_war": {
                "intensity": 0.8,
                "repair_progress": 0.1,
            },
        }]

        # Simulate 35 days
        applied = cold_war_tracker.check_emergency_decay(
            relationship_state=base_relationship_state,
            days_in_cold_war=35,
        )

        assert applied is True

        # Check intensity decayed
        # 5 days over 30: 0.8 * 0.95^5 ≈ 0.614
        cold_war_state = base_relationship_state["active_special_states"][0]
        decayed_intensity = cold_war_state["cold_war"]["intensity"]
        assert 0.61 < decayed_intensity < 0.62

    def test_emergency_decay_force_resolves_below_threshold(
        self, cold_war_tracker, base_relationship_state
    ):
        """Test emergency decay force resolves if intensity drops below 0.1."""
        # Add cold war state with low intensity
        base_relationship_state["active_special_states"] = [{
            "state_type": "COLD_WAR",
            "entered_at": datetime.now(timezone.utc).isoformat(),
            "cold_war": {
                "intensity": 0.15,
                "repair_progress": 0.2,
                "cause_conflict_id": str(uuid4()),
            },
        }]

        # Add conflict record
        base_relationship_state["recent_conflicts"] = [{
            "conflict_id": base_relationship_state["active_special_states"][0]["cold_war"]["cause_conflict_id"],
            "resolved_at": None,
        }]

        # Simulate 50 days (should push intensity < 0.1)
        applied = cold_war_tracker.check_emergency_decay(
            relationship_state=base_relationship_state,
            days_in_cold_war=50,
        )

        assert applied is True

        # Should have force resolved
        assert len(base_relationship_state["active_special_states"]) == 0

    def test_severity_determination(self, cold_war_tracker):
        """Test conflict severity determination from intensity."""
        # Major: >= 0.7
        assert cold_war_tracker._determine_severity(0.8) == "major"
        assert cold_war_tracker._determine_severity(0.7) == "major"

        # Medium: 0.5-0.7
        assert cold_war_tracker._determine_severity(0.6) == "medium"
        assert cold_war_tracker._determine_severity(0.5) == "medium"

        # Minor: < 0.5
        assert cold_war_tracker._determine_severity(0.4) == "minor"
        assert cold_war_tracker._determine_severity(0.2) == "minor"

    def test_rin_higher_threshold(self, rin_cold_war_tracker):
        """Test Rin has higher trigger threshold than default."""
        default_tracker = ColdWarTracker()

        # Rin threshold: 0.55
        assert rin_cold_war_tracker.cold_war_modifiers["trigger_threshold"] == 0.55

        # Default threshold: 0.5
        assert default_tracker.cold_war_modifiers["trigger_threshold"] == 0.5

    def test_recent_conflicts_limit(
        self, cold_war_tracker, base_emotion_state, base_relationship_state
    ):
        """Test recent_conflicts list is limited to 10 entries."""
        # Fill with 10 conflicts
        base_relationship_state["recent_conflicts"] = [
            {"conflict_id": str(uuid4())} for _ in range(10)
        ]

        # Add coldness
        base_emotion_state["active_stack"] = [{
            "emotion": "coldness",
            "intensity": 0.7,
            "cause": {"raw_signal": "new conflict"},
        }]

        # Initiate new cold war
        cold_war_tracker.initiate_cold_war(
            emotion_state=base_emotion_state,
            relationship_state=base_relationship_state,
        )

        # Should have only 10 (last 10)
        assert len(base_relationship_state["recent_conflicts"]) == 10
