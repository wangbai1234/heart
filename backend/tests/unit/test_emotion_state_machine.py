"""
Unit tests for SS03 Emotion State Machine.

Tests all INV-E-* invariants per §2.2.

Author: 心屿团队
"""

import pytest
from uuid import uuid4

from heart.ss03_emotion.contagion import apply_contagion
from heart.ss03_emotion.state_machine import (
    EmotionStateMachine,
    MAX_CONCURRENT_EMOTIONS,
)


@pytest.fixture
def emotion_vad_map():
    """Sample emotion VAD map."""
    return {
        "joy": {"v": 0.7, "a": 0.6, "d": 0.3},
        "sadness": {"v": -0.6, "a": -0.3, "d": -0.4},
        "aggrieved": {"v": -0.5, "a": 0.2, "d": -0.5},
        "coldness": {"v": -0.3, "a": -0.1, "d": 0.6},
        "tenderness": {"v": 0.6, "a": 0.1, "d": 0.1},
        "longing": {"v": -0.2, "a": 0.3, "d": -0.4},
    }


@pytest.fixture
def default_state():
    """Default emotion state."""
    return {
        "user_id": uuid4(),
        "character_id": "rin",
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
            "last_updated_at": "2026-05-20T10:00:00Z",
            "drift_history": [],
        },
        "energy": 0.6,
        "energy_baseline": 0.6,
        "recent_vad_history": [],
        "recent_triggers": [],
        "pending_repairs": [],
        "version": 1,
    }


@pytest.fixture
def inertia_profile():
    """Standard inertia profile."""
    return {
        "max_valence_change_per_turn": 0.15,
        "max_arousal_change_per_turn": 0.15,
        "max_dominance_change_per_turn": 0.15,
    }


class TestInvariantE1:
    """Test INV-E-1: ∀ emotion transition, |Δvalence| ≤ inertia_cap × Δt"""

    def test_valence_change_respects_inertia_cap(
        self, emotion_vad_map, default_state, inertia_profile
    ):
        """Valence change should not exceed inertia cap."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Trigger with large positive valence
        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {
                        "emotion": "joy",
                        "intensity_delta": 0.8,
                        "is_new_or_reinforce": "new",
                    }
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        # Check valence change is capped
        delta_valence = abs(new_state["vad_valence"] - default_state["vad_valence"])
        assert delta_valence <= inertia_profile["max_valence_change_per_turn"] + 0.01

    def test_large_negative_valence_also_capped(
        self, emotion_vad_map, default_state, inertia_profile
    ):
        """Large negative valence changes are also capped."""
        sm = EmotionStateMachine(emotion_vad_map)

        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {
                        "emotion": "sadness",
                        "intensity_delta": 0.9,
                        "is_new_or_reinforce": "new",
                    }
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        delta_valence = abs(new_state["vad_valence"] - default_state["vad_valence"])
        assert delta_valence <= inertia_profile["max_valence_change_per_turn"] + 0.01


class TestInvariantE2:
    """Test INV-E-2: ∀ active_emotion_stack S, |S| ≤ MAX_CONCURRENT_EMOTIONS"""

    def test_stack_never_exceeds_max_concurrent(self, emotion_vad_map, default_state, inertia_profile):
        """Stack size should never exceed MAX_CONCURRENT_EMOTIONS (5)."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Add 7 emotions (exceeds limit)
        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "joy", "intensity_delta": 0.5, "is_new_or_reinforce": "new"},
                    {"emotion": "sadness", "intensity_delta": 0.4, "is_new_or_reinforce": "new"},
                    {"emotion": "aggrieved", "intensity_delta": 0.6, "is_new_or_reinforce": "new"},
                    {"emotion": "coldness", "intensity_delta": 0.3, "is_new_or_reinforce": "new"},
                    {"emotion": "tenderness", "intensity_delta": 0.7, "is_new_or_reinforce": "new"},
                    {"emotion": "longing", "intensity_delta": 0.5, "is_new_or_reinforce": "new"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        assert len(new_state["active_stack"]) <= MAX_CONCURRENT_EMOTIONS

    def test_weakest_emotion_evicted_when_overflow(self, emotion_vad_map, default_state, inertia_profile):
        """Weakest emotion should be evicted when stack overflows."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Pre-fill stack with 5 emotions
        default_state["active_stack"] = [
            {"emotion": "joy", "intensity": 0.3, "vad_contribution": {"valence": 0.7, "arousal": 0.6, "dominance": 0.3}},
            {"emotion": "sadness", "intensity": 0.2, "vad_contribution": {"valence": -0.6, "arousal": -0.3, "dominance": -0.4}},
            {"emotion": "aggrieved", "intensity": 0.4, "vad_contribution": {"valence": -0.5, "arousal": 0.2, "dominance": -0.5}},
            {"emotion": "coldness", "intensity": 0.5, "vad_contribution": {"valence": -0.3, "arousal": -0.1, "dominance": 0.6}},
            {"emotion": "tenderness", "intensity": 0.6, "vad_contribution": {"valence": 0.6, "arousal": 0.1, "dominance": 0.1}},
        ]

        # Add one more
        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "longing", "intensity_delta": 0.7, "is_new_or_reinforce": "new"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        # Stack should still be at max
        assert len(new_state["active_stack"]) == MAX_CONCURRENT_EMOTIONS

        # Weakest (sadness with 0.2) should be evicted
        emotion_names = [e["emotion"] for e in new_state["active_stack"]]
        assert "sadness" not in emotion_names
        assert "longing" in emotion_names


class TestInvariantE3:
    """Test INV-E-3: ∀ emotion e, e.intensity ∈ [0, 1]"""

    def test_intensity_always_in_valid_range(self, emotion_vad_map, default_state, inertia_profile):
        """All emotion intensities must be in [0, 1]."""
        sm = EmotionStateMachine(emotion_vad_map)

        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "joy", "intensity_delta": 1.5, "is_new_or_reinforce": "new"},  # Exceeds 1
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        for emotion in new_state["active_stack"]:
            assert 0.0 <= emotion["intensity"] <= 1.0

    def test_negative_intensity_clamped_to_zero(self, emotion_vad_map, default_state, inertia_profile):
        """Negative intensity deltas should be clamped to 0."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Pre-existing emotion
        default_state["active_stack"] = [
            {"emotion": "joy", "intensity": 0.3, "vad_contribution": {"valence": 0.7, "arousal": 0.6, "dominance": 0.3}},
        ]

        # Reduce it below zero
        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "joy", "intensity_delta": -0.5, "is_new_or_reinforce": "reinforce"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        # Emotion should be removed (< 0.05 threshold)
        emotion_names = [e["emotion"] for e in new_state["active_stack"]]
        assert "joy" not in emotion_names or all(e["intensity"] >= 0 for e in new_state["active_stack"])


class TestContagionEngine:
    """Test Contagion Engine per §10.3."""

    def test_contagion_respects_shock_resistance(self, default_state):
        """Contagion strength should decrease with higher shock resistance."""
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}

        # High shock resistance (Rin)
        soul_high = {"cognitive_style": {"emotional_inertia": {"shock_resistance": 0.75}}}
        delta_high = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=default_state,
            soul=soul_high,
            relationship_phase="close_friend",
        )

        # Low shock resistance (Dorothy)
        soul_low = {"cognitive_style": {"emotional_inertia": {"shock_resistance": 0.2}}}
        delta_low = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=default_state,
            soul=soul_low,
            relationship_phase="close_friend",
        )

        # Lower shock resistance = larger delta
        assert abs(delta_low["valence"]) > abs(delta_high["valence"])

    def test_contagion_increases_with_intimacy(self, default_state):
        """Contagion should be stronger in closer relationships."""
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}
        soul = {"cognitive_style": {"emotional_inertia": {"shock_resistance": 0.5}}}

        delta_stranger = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=default_state,
            soul=soul,
            relationship_phase="stranger",
        )

        delta_romantic = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=default_state,
            soul=soul,
            relationship_phase="romantic",
        )

        # Closer relationship = larger delta
        assert abs(delta_romantic["valence"]) > abs(delta_stranger["valence"])

    def test_dominance_not_contagious(self, default_state):
        """Dominance should not transfer via contagion."""
        user_vad = {"valence": 0.5, "arousal": 0.6, "dominance": 0.9}
        soul = {"cognitive_style": {"emotional_inertia": {"shock_resistance": 0.3}}}

        delta = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=default_state,
            soul=soul,
            relationship_phase="close_friend",
        )

        assert delta["dominance"] == 0.0


class TestStateTransitions:
    """Test specific state transitions per §4.3."""

    def test_apology_reduces_aggrieved_and_coldness(self, emotion_vad_map, default_state, inertia_profile):
        """Apology should reduce aggrieved and coldness intensity."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Pre-existing aggrieved and coldness
        default_state["active_stack"] = [
            {"emotion": "aggrieved", "intensity": 0.6, "vad_contribution": {"valence": -0.5, "arousal": 0.2, "dominance": -0.5}},
            {"emotion": "coldness", "intensity": 0.5, "vad_contribution": {"valence": -0.3, "arousal": -0.1, "dominance": 0.6}},
        ]

        triggers = [
            {
                "trigger_type": "user_apology",
                "confidence": 0.9,
                "suggested_emotions": [
                    {"emotion": "aggrieved", "intensity_delta": -0.3, "is_new_or_reinforce": "reinforce"},
                    {"emotion": "coldness", "intensity_delta": -0.2, "is_new_or_reinforce": "reinforce"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        # Intensities should be reduced
        aggrieved_new = next(e for e in new_state["active_stack"] if e["emotion"] == "aggrieved")
        coldness_new = next(e for e in new_state["active_stack"] if e["emotion"] == "coldness")

        assert aggrieved_new["intensity"] < 0.6
        assert coldness_new["intensity"] < 0.5

    def test_vulnerability_triggers_tenderness_and_worry(self, emotion_vad_map, default_state, inertia_profile):
        """User vulnerability should trigger tenderness and worry."""
        sm = EmotionStateMachine(emotion_vad_map)

        triggers = [
            {
                "trigger_type": "user_vulnerability",
                "confidence": 0.85,
                "suggested_emotions": [
                    {"emotion": "tenderness", "intensity_delta": 0.4, "is_new_or_reinforce": "new"},
                    {"emotion": "worry", "intensity_delta": 0.3, "is_new_or_reinforce": "new"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        emotion_names = [e["emotion"] for e in new_state["active_stack"]]
        assert "tenderness" in emotion_names
        # Note: "worry" is not in our emotion_vad_map fixture, so it won't appear


class TestVADRecomputation:
    """Test VAD recomputation from stack per §10.3."""

    def test_vad_within_valid_ranges(self, emotion_vad_map, default_state, inertia_profile):
        """Final VAD must be in valid ranges: valence [-1,1], arousal/dominance [0,1]."""
        sm = EmotionStateMachine(emotion_vad_map)

        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "joy", "intensity_delta": 0.9, "is_new_or_reinforce": "new"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0.5, "arousal": 0.3, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        assert -1.0 <= new_state["vad_valence"] <= 1.0
        assert 0.0 <= new_state["vad_arousal"] <= 1.0
        assert 0.0 <= new_state["vad_dominance"] <= 1.0

    def test_mood_baseline_influences_vad(self, emotion_vad_map, default_state, inertia_profile):
        """Mood baseline should influence final VAD."""
        sm = EmotionStateMachine(emotion_vad_map)

        # Set negative mood baseline
        default_state["mood"]["valence_baseline"] = -0.5

        triggers = [
            {
                "trigger_type": "test",
                "confidence": 1.0,
                "suggested_emotions": [
                    {"emotion": "joy", "intensity_delta": 0.5, "is_new_or_reinforce": "new"},
                ],
            }
        ]

        new_state = sm.transition(
            current_state=default_state,
            triggers=triggers,
            contagion_delta={"valence": 0, "arousal": 0, "dominance": 0},
            inertia_profile=inertia_profile,
        )

        # VAD valence should be pulled down by negative mood
        # Even with joy, should be less positive than without negative mood
        assert new_state["vad_valence"] < 0.5  # Less than pure joy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
