"""
Unit tests for SS03 Contagion Engine.

Tests Soul-aware empathy curve modulation per character.

Author: 心屿团队
"""

import pytest
from uuid import uuid4

from heart.ss03_emotion.contagion import (
    apply_contagion,
    compute_empathy_curve,
)


@pytest.fixture
def soul_rin():
    """Rin's Soul configuration: high shock_resistance."""
    return {
        "character_id": "rin",
        "cognitive_style": {
            "emotional_inertia": {
                "shock_resistance": "high",  # 0.75
                "mood_volatility": 0.20,
            }
        },
        "baseline_mood": {
            "valence": 0.0,
            "arousal": 0.3,
            "dominance": 0.5,
        },
    }


@pytest.fixture
def soul_dorothy():
    """Dorothy's Soul configuration: low shock_resistance."""
    return {
        "character_id": "dorothy",
        "cognitive_style": {
            "emotional_inertia": {
                "shock_resistance": "low",  # 0.2
                "mood_volatility": 0.75,
            }
        },
        "baseline_mood": {
            "valence": 0.1,
            "arousal": 0.5,
            "dominance": 0.4,
        },
    }


@pytest.fixture
def neutral_state():
    """Neutral emotion state."""
    return {
        "user_id": uuid4(),
        "character_id": "rin",
        "vad_valence": 0.0,
        "vad_arousal": 0.3,
        "vad_dominance": 0.5,
        "active_stack": [],
        "mood": {
            "valence_baseline": 0.0,
            "arousal_baseline": 0.3,
            "dominance_baseline": 0.5,
        },
    }


class TestShockResistanceModulation:
    """Test that shock_resistance correctly modulates contagion strength."""

    def test_high_shock_resistance_reduces_contagion(self, soul_rin, neutral_state):
        """Rin (high shock_resistance) should have weak contagion."""
        # User is very happy
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}

        delta = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=neutral_state,
            soul=soul_rin,
            relationship_phase="close_friend",
        )

        # Rin's shock_resistance = 0.75 → strength = (1 - 0.75) × 0.85 = 0.2125
        # delta_v = (0.8 - 0.0) × 0.2125 × 0.15 = 0.0255
        assert 0.02 < delta["valence"] < 0.04
        assert delta["dominance"] == 0.0  # Dominance never transfers

    def test_low_shock_resistance_increases_contagion(self, soul_dorothy, neutral_state):
        """Dorothy (low shock_resistance) should have strong contagion."""
        neutral_state["character_id"] = "dorothy"
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}

        delta = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=neutral_state,
            soul=soul_dorothy,
            relationship_phase="close_friend",
        )

        # Dorothy's shock_resistance = 0.2 → strength = (1 - 0.2) × 0.85 = 0.68
        # delta_v = (0.8 - 0.0) × 0.68 × 0.15 = 0.0816
        assert delta["valence"] > 0.06
        assert delta["dominance"] == 0.0

    def test_rin_contagion_weaker_than_dorothy(self, soul_rin, soul_dorothy, neutral_state):
        """Rin's contagion delta should be significantly smaller than Dorothy's."""
        user_vad = {"valence": 0.9, "arousal": 0.8, "dominance": 0.7}

        delta_rin = apply_contagion(user_vad, neutral_state, soul_rin, "close_friend")

        neutral_state["character_id"] = "dorothy"
        delta_dorothy = apply_contagion(user_vad, neutral_state, soul_dorothy, "close_friend")

        # Dorothy should be > 2.5x more affected than Rin
        assert abs(delta_dorothy["valence"]) > abs(delta_rin["valence"]) * 2.5
        assert abs(delta_dorothy["arousal"]) > abs(delta_rin["arousal"]) * 2.5


class TestRelationshipPhaseModulation:
    """Test that relationship phase modulates contagion strength."""

    def test_stranger_has_weak_contagion(self, soul_dorothy, neutral_state):
        """Even empathetic Dorothy has weak contagion with strangers."""
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}

        delta = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=neutral_state,
            soul=soul_dorothy,
            relationship_phase="stranger",
        )

        # Phase modifier = 0.3 for stranger
        # strength = (1 - 0.2) × 0.3 = 0.24
        assert abs(delta["valence"]) < 0.04

    def test_romantic_has_strong_contagion(self, soul_dorothy, neutral_state):
        """Dorothy has very strong contagion in romantic relationship."""
        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}

        delta = apply_contagion(
            user_emotion_vad=user_vad,
            current_state=neutral_state,
            soul=soul_dorothy,
            relationship_phase="romantic",
        )

        # Phase modifier = 0.95 for romantic
        # strength = (1 - 0.2) × 0.95 = 0.76
        assert abs(delta["valence"]) > 0.08

    def test_contagion_increases_with_intimacy(self, soul_dorothy, neutral_state):
        """Contagion strength should monotonically increase with intimacy."""
        user_vad = {"valence": 0.7, "arousal": 0.6, "dominance": 0.5}

        phases = ["stranger", "acquaintance", "friend", "close_friend", "romantic", "bonded"]
        deltas = []

        for phase in phases:
            delta = apply_contagion(user_vad, neutral_state, soul_dorothy, phase)
            deltas.append(abs(delta["valence"]))

        # Each phase should have >= contagion than previous
        for i in range(len(deltas) - 1):
            assert deltas[i + 1] >= deltas[i]


class TestEmpathyCurve:
    """Test empathy curve computation."""

    def test_rin_stranger_very_low_empathy(self, soul_rin):
        """Rin as stranger: minimal empathy."""
        empathy = compute_empathy_curve(soul_rin, "stranger")
        # (1 - 0.75) × 0.3 = 0.075
        assert empathy < 0.1

    def test_dorothy_romantic_high_empathy(self, soul_dorothy):
        """Dorothy in romantic relationship: high empathy."""
        empathy = compute_empathy_curve(soul_dorothy, "romantic")
        # (1 - 0.2) × 0.95 = 0.76
        assert empathy > 0.7

    def test_rin_bonded_moderate_empathy(self, soul_rin):
        """Even bonded Rin has only moderate empathy due to high shock resistance."""
        empathy = compute_empathy_curve(soul_rin, "bonded")
        # (1 - 0.75) × 1.0 = 0.25
        assert 0.2 < empathy < 0.3


class TestContagionDirection:
    """Test contagion works in both positive and negative directions."""

    def test_positive_user_emotion_increases_character_valence(self, soul_dorothy, neutral_state):
        """Happy user should increase character valence."""
        user_vad = {"valence": 0.9, "arousal": 0.8, "dominance": 0.7}

        delta = apply_contagion(user_vad, neutral_state, soul_dorothy, "close_friend")

        assert delta["valence"] > 0  # Positive delta
        assert delta["arousal"] > 0  # Positive delta

    def test_negative_user_emotion_decreases_character_valence(self, soul_dorothy):
        """Sad user should decrease character valence."""
        user_vad = {"valence": -0.8, "arousal": 0.2, "dominance": 0.3}

        # Character currently happy
        state = {
            "vad_valence": 0.5,
            "vad_arousal": 0.6,
            "vad_dominance": 0.5,
        }

        delta = apply_contagion(user_vad, state, soul_dorothy, "close_friend")

        assert delta["valence"] < 0  # Negative delta (pulling down)
        assert delta["arousal"] < 0  # Negative delta


class TestDominanceNotContagious:
    """Test that dominance does not transfer via contagion."""

    def test_high_user_dominance_no_transfer(self, soul_dorothy, neutral_state):
        """High user dominance should not affect character dominance."""
        user_vad = {"valence": 0.5, "arousal": 0.5, "dominance": 1.0}

        delta = apply_contagion(user_vad, neutral_state, soul_dorothy, "romantic")

        assert delta["dominance"] == 0.0

    def test_low_user_dominance_no_transfer(self, soul_dorothy, neutral_state):
        """Low user dominance should not affect character dominance."""
        user_vad = {"valence": 0.5, "arousal": 0.5, "dominance": 0.0}

        delta = apply_contagion(user_vad, neutral_state, soul_dorothy, "romantic")

        assert delta["dominance"] == 0.0


class TestFloatShockResistance:
    """Test that float shock_resistance values work correctly."""

    def test_explicit_float_shock_resistance(self, neutral_state):
        """Test with explicit float shock_resistance."""
        soul = {
            "cognitive_style": {
                "emotional_inertia": {
                    "shock_resistance": 0.5,  # Explicit float
                }
            }
        }

        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}
        delta = apply_contagion(user_vad, neutral_state, soul, "friend")

        # strength = (1 - 0.5) × 0.7 = 0.35
        # delta_v = 0.8 × 0.35 × 0.15 = 0.042
        assert 0.03 < abs(delta["valence"]) < 0.05


class TestMissingSoulFields:
    """Test graceful fallback when Soul fields missing."""

    def test_missing_shock_resistance_uses_default(self, neutral_state):
        """Missing shock_resistance should use default (0.5)."""
        soul = {}  # Empty soul

        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}
        delta = apply_contagion(user_vad, neutral_state, soul, "friend")

        # Should use default shock_resistance = 0.5
        # strength = (1 - 0.5) × 0.7 = 0.35
        assert abs(delta["valence"]) > 0

    def test_invalid_shock_resistance_uses_default(self, neutral_state):
        """Invalid shock_resistance should use default."""
        soul = {
            "cognitive_style": {
                "emotional_inertia": {
                    "shock_resistance": "invalid_value",
                }
            }
        }

        user_vad = {"valence": 0.8, "arousal": 0.7, "dominance": 0.6}
        delta = apply_contagion(user_vad, neutral_state, soul, "friend")

        # Should gracefully fallback
        assert abs(delta["valence"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
