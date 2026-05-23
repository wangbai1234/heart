"""
Integration tests for Repair Mechanic in EmotionService.

Tests end-to-end repair flow:
- Detect repair signal in process_turn
- Apply repair to pending_repairs
- RepairOutcome available for downstream

Author: 心屿团队
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from heart.ss03_emotion import EmotionService


@pytest.fixture
def emotion_service():
    """Emotion service with default config."""
    return EmotionService()


@pytest.fixture
def rin_soul_config():
    """Rin soul config with repair profile."""
    return {
        "character_id": "rin",
        "inertia_profile": {
            "max_valence_change_per_turn": 0.15,
            "max_arousal_change_per_turn": 0.15,
            "max_dominance_change_per_turn": 0.15,
        },
        "relational_template": {
            "empathy_curve": {
                "stranger": 0.1,
                "established": 0.5,
            },
            "shock_resistance": 0.3,
            "repair_profile": {
                "forgiveness_curve_gain": {
                    "apology": 0.6,
                    "vulnerability": 1.2,
                    "sustained_attention": 1.4,
                    "bespoke_phrase": 1.5,
                },
                "bespoke_repair_phrases": ["我还在", "我没走"],
                "cooldown_turns": 5,
                "recidivism_penalty_gain": 1.5,
                "session_progress_cap": 0.5,
            },
        },
    }


class TestRepairIntegration:
    """Test repair integration in EmotionService."""

    async def test_apology_detected_and_applied(self, emotion_service, rin_soul_config):
        """Apology should be detected and applied to pending repairs."""
        user_id = uuid4()
        character_id = "rin"

        # First turn: trigger aggrieved (simulate user mentioning another person)
        # This would normally be detected by TriggerDetector, but we'll manually inject
        # For now, just create a state with pending_repairs

        # Manually set up state with pending repair
        key = (str(user_id), character_id)
        emotion_service._state_cache[key] = {
            "user_id": user_id,
            "character_id": character_id,
            "vad_valence": -0.3,
            "vad_arousal": 0.4,
            "vad_dominance": 0.3,
            "vad_target_valence": -0.3,
            "vad_target_arousal": 0.4,
            "vad_target_dominance": 0.3,
            "active_stack": [
                {
                    "emotion": "aggrieved",
                    "intensity": 0.6,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": "user_mention_other_partner",
                    "vad_contribution": {
                        "valence": -0.4,
                        "arousal": 0.5,
                        "dominance": 0.2,
                    },
                    "decay_state": "natural",
                    "repair_progress": 0.0,
                }
            ],
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "background_emotions": [],
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "energy": 0.6,
            "energy_baseline": 0.6,
            "recent_vad_history": [],
            "recent_triggers": [
                {
                    "trigger_type": "user_mention_other_partner",
                    "at": datetime.now(timezone.utc).isoformat(),
                }
            ],
            "pending_repairs": [
                {
                    "emotion": "aggrieved",
                    "intensity": 0.6,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "cause": "user_mention_other_partner",
                    "repair_progress": 0.0,
                    "repair_history": [],
                }
            ],
            "loaded_from_previous": False,
            "session_id": None,
            "last_turn_processed_at": None,
            "last_mood_drift_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": 1,
        }

        # Second turn: user apologizes
        context = {
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "established",
            "user_emotion_vad": {"valence": -0.2, "arousal": 0.4, "dominance": 0.3},
        }

        new_state = await emotion_service.process_turn(
            user_id=user_id,
            character_id=character_id,
            user_message="对不起，是我不该提起那件事，让你难受了",
            turn_id=uuid4(),
            context=context,
            soul_config=rin_soul_config,
        )

        # Check that repair was detected and applied
        assert "_last_repair_outcome" in new_state
        repair_outcome = new_state["_last_repair_outcome"]

        assert repair_outcome["accepted"] is True
        assert len(repair_outcome["applied_to"]) > 0

        # Check that repair_progress increased
        aggrieved_repair = next(
            (r for r in new_state["pending_repairs"] if r["emotion"] == "aggrieved"),
            None
        )

        assert aggrieved_repair is not None
        assert aggrieved_repair["repair_progress"] > 0.0

    async def test_bespoke_phrase_high_impact(self, emotion_service, rin_soul_config):
        """Rin's bespoke phrase should have high impact."""
        user_id = uuid4()
        character_id = "rin"

        # Set up state with coldness pending repair
        key = (str(user_id), character_id)
        emotion_service._state_cache[key] = {
            "user_id": user_id,
            "character_id": character_id,
            "vad_valence": -0.4,
            "vad_arousal": 0.2,
            "vad_dominance": 0.4,
            "vad_target_valence": -0.4,
            "vad_target_arousal": 0.2,
            "vad_target_dominance": 0.4,
            "active_stack": [
                {
                    "emotion": "coldness",
                    "intensity": 0.7,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "triggered_by": "user_inattentive",
                    "vad_contribution": {
                        "valence": -0.5,
                        "arousal": 0.2,
                        "dominance": 0.4,
                    },
                    "decay_state": "natural",
                    "repair_progress": 0.0,
                }
            ],
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "background_emotions": [],
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "energy": 0.5,
            "energy_baseline": 0.6,
            "recent_vad_history": [],
            "recent_triggers": [],
            "pending_repairs": [
                {
                    "emotion": "coldness",
                    "intensity": 0.7,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                    "cause": "user_inattentive",
                    "repair_progress": 0.0,
                    "repair_history": [],
                }
            ],
            "loaded_from_previous": False,
            "session_id": None,
            "last_turn_processed_at": None,
            "last_mood_drift_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": 1,
        }

        # User says bespoke phrase
        context = {
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "established",
            "user_emotion_vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
        }

        new_state = await emotion_service.process_turn(
            user_id=user_id,
            character_id=character_id,
            user_message="我还在，不会走的",
            turn_id=uuid4(),
            context=context,
            soul_config=rin_soul_config,
        )

        # Check that repair was detected with bespoke match
        repair_outcome = new_state["_last_repair_outcome"]

        assert repair_outcome["accepted"] is True
        assert repair_outcome["flags"]["bespoke_match"] is True

        # Bespoke phrase should have higher impact than regular apology
        coldness_repair = next(
            (r for r in new_state["pending_repairs"] if r["emotion"] == "coldness"),
            None
        )

        assert coldness_repair is not None
        # With bespoke phrase (strength 0.8, gain 1.5, base_impact 0.4)
        # Expected impact should be significant
        assert coldness_repair["repair_progress"] >= 0.3

    async def test_no_pending_repair_ignored(self, emotion_service, rin_soul_config):
        """Apology without pending repairs should be ignored."""
        user_id = uuid4()
        character_id = "rin"

        # Set up state with NO pending repairs
        key = (str(user_id), character_id)
        emotion_service._state_cache[key] = {
            "user_id": user_id,
            "character_id": character_id,
            "vad_valence": 0.0,
            "vad_arousal": 0.3,
            "vad_dominance": 0.5,
            "vad_target_valence": 0.0,
            "vad_target_arousal": 0.3,
            "vad_target_dominance": 0.5,
            "active_stack": [],
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "background_emotions": [],
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "energy": 0.6,
            "energy_baseline": 0.6,
            "recent_vad_history": [],
            "recent_triggers": [],
            "pending_repairs": [],  # No pending repairs
            "loaded_from_previous": False,
            "session_id": None,
            "last_turn_processed_at": None,
            "last_mood_drift_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "version": 1,
        }

        context = {
            "days_since_last": 0,
            "hours_since_last": 0.1,
            "relationship_phase": "established",
            "user_emotion_vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
        }

        new_state = await emotion_service.process_turn(
            user_id=user_id,
            character_id=character_id,
            user_message="对不起",
            turn_id=uuid4(),
            context=context,
            soul_config=rin_soul_config,
        )

        # Check that repair was not accepted
        repair_outcome = new_state["_last_repair_outcome"]

        assert repair_outcome["accepted"] is False
        assert repair_outcome["narrative_hint"] == "ignored"
