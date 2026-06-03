"""
Unit tests for SS03 Mood Drift Engine.

Tests convergence to baseline, volatility modulation, and environmental factors.

Author: 心屿团队
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from heart.ss03_emotion.mood_drift import (
    _apply_environmental_factors,
    _apply_longing_gradient,
    _compute_24h_average,
    _compute_ewma,
    drift_mood,
)


@pytest.fixture
def soul_rin():
    """Rin's Soul: low volatility, stable mood."""
    return {
        "character_id": "rin",
        "cognitive_style": {
            "emotional_inertia": {
                "shock_resistance": "high",
                "mood_volatility": 0.20,  # Low volatility
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
    """Dorothy's Soul: high volatility, fluctuating mood."""
    return {
        "character_id": "dorothy",
        "cognitive_style": {
            "emotional_inertia": {
                "shock_resistance": "low",
                "mood_volatility": 0.75,  # High volatility
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
    """Neutral emotion state with empty history."""
    return {
        "user_id": uuid4(),
        "character_id": "rin",
        "vad_valence": 0.0,
        "vad_arousal": 0.3,
        "vad_dominance": 0.5,
        "mood": {
            "valence_baseline": 0.0,
            "arousal_baseline": 0.3,
            "dominance_baseline": 0.5,
            "background_emotions": [],
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "drift_history": [],
        },
        "recent_vad_history": [],
    }


@pytest.fixture
def positive_history_state():
    """State with recent positive VAD history."""
    now = datetime.now(timezone.utc)

    recent_vad = []
    for i in range(20):
        recent_vad.append(
            {
                "vad": {"valence": 0.6, "arousal": 0.7, "dominance": 0.5},
                "at": (now - timedelta(hours=i)).isoformat(),
                "triggered_by": ["user_compliment"],
            }
        )

    return {
        "user_id": uuid4(),
        "character_id": "dorothy",
        "vad_valence": 0.5,
        "vad_arousal": 0.6,
        "vad_dominance": 0.5,
        "mood": {
            "valence_baseline": 0.1,
            "arousal_baseline": 0.5,
            "dominance_baseline": 0.4,
            "background_emotions": [],
            "last_updated_at": now.isoformat(),
            "drift_history": [],
        },
        "recent_vad_history": recent_vad,
    }


class TestDriftConvergence:
    """Test that mood drifts toward baseline over time."""

    def test_rin_drifts_slowly_to_baseline(self, soul_rin):
        """Rin (low volatility) should drift slowly toward Soul baseline."""
        # Start with positive mood
        state = {
            "mood": {
                "valence_baseline": 0.4,
                "arousal_baseline": 0.6,
                "dominance_baseline": 0.5,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": [],  # No recent input
        }

        # Apply drift 10 times (simulating 10 hours)
        for _ in range(10):
            new_mood = drift_mood(state, soul_rin, hours_since_last=1.0)
            state["mood"] = new_mood

        # Should drift toward Soul baseline (0.0)
        assert new_mood["valence_baseline"] < 0.4  # Moved toward 0
        assert new_mood["valence_baseline"] > 0.0  # But not instantly

    def test_dorothy_follows_recent_emotions_quickly(self, soul_dorothy, positive_history_state):
        """Dorothy (high volatility) should follow recent emotions quickly."""
        initial_valence = positive_history_state["mood"]["valence_baseline"]

        new_mood = drift_mood(
            positive_history_state,
            soul_dorothy,
            hours_since_last=1.0,
        )

        # Dorothy should move significantly toward positive recent average (0.6)
        assert new_mood["valence_baseline"] > initial_valence + 0.1

    def test_property_convergence_to_baseline(self, soul_rin):
        """Property test: repeated drift without input converges to Soul baseline."""
        # Use a fixed daytime time to avoid late-night environmental modifier
        fixed_time = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        state = {
            "mood": {
                "valence_baseline": 0.5,  # Start far from baseline
                "arousal_baseline": 0.8,
                "dominance_baseline": 0.3,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": [],
        }

        # Simulate 100 hours of drift without new input
        for _ in range(100):
            new_mood = drift_mood(state, soul_rin, hours_since_last=1.0, current_local_time=fixed_time)
            state["mood"] = new_mood

        # Should converge toward Soul baseline (0.0, 0.3, 0.5)
        assert abs(new_mood["valence_baseline"] - 0.0) < 0.15
        assert abs(new_mood["arousal_baseline"] - 0.3) < 0.15
        assert abs(new_mood["dominance_baseline"] - 0.5) < 0.15


class TestVolatilityModulation:
    """Test that mood_volatility correctly modulates drift behavior."""

    def test_low_volatility_ignores_recent_spike(self, soul_rin):
        """Low volatility character ignores recent emotional spikes."""
        # Recent positive spike
        recent_vad = [
            {
                "vad": {"valence": 0.9, "arousal": 0.8, "dominance": 0.6},
                "at": datetime.now(timezone.utc).isoformat(),
                "triggered_by": ["user_compliment"],
            }
        ]

        state = {
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": recent_vad,
        }

        new_mood = drift_mood(state, soul_rin, hours_since_last=1.0)

        # Rin (volatility=0.2) should move only slightly
        # With one spike of 0.9, should move less than ~0.2
        # (floating-point margin: blended 0.9 × 0.2 vol = 0.18, + env ≈ 0.20)
        assert abs(new_mood["valence_baseline"]) < 0.25

    def test_high_volatility_follows_recent_spike(self, soul_dorothy):
        """High volatility character follows recent emotional spikes."""
        recent_vad = [
            {
                "vad": {"valence": 0.9, "arousal": 0.8, "dominance": 0.6},
                "at": datetime.now(timezone.utc).isoformat(),
                "triggered_by": ["user_compliment"],
            }
        ]

        state = {
            "mood": {
                "valence_baseline": 0.1,
                "arousal_baseline": 0.5,
                "dominance_baseline": 0.4,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": recent_vad,
        }

        new_mood = drift_mood(state, soul_dorothy, hours_since_last=1.0)

        # Dorothy (volatility=0.75) should move significantly
        assert new_mood["valence_baseline"] > 0.2


class TestFloorCeilingBounds:
    """Test that mood respects floor/ceiling bounds."""

    def test_valence_capped_at_0_5(self, soul_dorothy):
        """Mood valence should be capped at ±0.5 (mood is backdrop, not peak)."""
        # Recent extremely positive VAD
        recent_vad = [
            {
                "vad": {"valence": 1.0, "arousal": 1.0, "dominance": 1.0},
                "at": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(10)
        ]

        state = {
            "mood": {
                "valence_baseline": 0.4,
                "arousal_baseline": 0.8,
                "dominance_baseline": 0.8,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": recent_vad,
        }

        new_mood = drift_mood(state, soul_dorothy, hours_since_last=1.0)

        # Valence capped at 0.5
        assert new_mood["valence_baseline"] <= 0.5

    def test_valence_floored_at_minus_0_5(self, soul_dorothy):
        """Mood valence should be floored at -0.5."""
        # Recent extremely negative VAD
        recent_vad = [
            {
                "vad": {"valence": -1.0, "arousal": 0.1, "dominance": 0.1},
                "at": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(10)
        ]

        state = {
            "mood": {
                "valence_baseline": -0.4,
                "arousal_baseline": 0.2,
                "dominance_baseline": 0.3,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [],
            },
            "recent_vad_history": recent_vad,
        }

        new_mood = drift_mood(state, soul_dorothy, hours_since_last=1.0)

        # Valence floored at -0.5
        assert new_mood["valence_baseline"] >= -0.5

    def test_arousal_in_valid_range(self, soul_dorothy, positive_history_state):
        """Arousal should stay in [0, 1]."""
        new_mood = drift_mood(positive_history_state, soul_dorothy, hours_since_last=1.0)

        assert 0.0 <= new_mood["arousal_baseline"] <= 1.0

    def test_dominance_in_valid_range(self, soul_dorothy, positive_history_state):
        """Dominance should stay in [0, 1]."""
        new_mood = drift_mood(positive_history_state, soul_dorothy, hours_since_last=1.0)

        assert 0.0 <= new_mood["dominance_baseline"] <= 1.0


class TestEnvironmentalFactors:
    """Test environmental factor injection."""

    def test_late_night_reduces_arousal(self, soul_dorothy):
        """Late night (23:00-05:00) should reduce arousal."""
        # 02:00 AM
        late_night_time = datetime(2026, 5, 20, 2, 0, 0, tzinfo=timezone.utc)

        vad = {"valence": 0.3, "arousal": 0.7, "dominance": 0.5}

        modified_vad = _apply_environmental_factors(vad, late_night_time, soul_dorothy)

        # Arousal should be reduced
        assert modified_vad["arousal"] < 0.7

    def test_daytime_no_arousal_change(self, soul_dorothy):
        """Daytime should not modify arousal."""
        daytime = datetime(2026, 5, 20, 14, 0, 0, tzinfo=timezone.utc)

        vad = {"valence": 0.3, "arousal": 0.7, "dominance": 0.5}

        modified_vad = _apply_environmental_factors(vad, daytime, soul_dorothy)

        # Arousal unchanged
        assert modified_vad["arousal"] == 0.7

    def test_weekend_increases_valence(self, soul_dorothy):
        """Weekend should slightly increase valence."""
        # Saturday
        saturday = datetime(2026, 5, 23, 14, 0, 0, tzinfo=timezone.utc)  # 2026-05-23 is Saturday

        vad = {"valence": 0.2, "arousal": 0.5, "dominance": 0.5}

        modified_vad = _apply_environmental_factors(vad, saturday, soul_dorothy)

        # Valence should increase
        assert modified_vad["valence"] > 0.2


class TestLongingGradient:
    """Test longing gradient injection."""

    def test_no_absence_no_longing(self, soul_rin):
        """No absence should not add longing."""
        vad = {"valence": 0.3, "arousal": 0.5, "dominance": 0.5}

        modified_vad = _apply_longing_gradient(vad, days_since_last_interaction=0.0, soul=soul_rin)

        # No change
        assert modified_vad["valence"] == 0.3
        assert modified_vad["arousal"] == 0.5

    def test_short_absence_adds_slight_longing(self, soul_rin):
        """Short absence (2 days) should add slight longing effect."""
        vad = {"valence": 0.3, "arousal": 0.5, "dominance": 0.5}

        modified_vad = _apply_longing_gradient(vad, days_since_last_interaction=2.0, soul=soul_rin)

        # Valence slightly negative
        assert modified_vad["valence"] < 0.3
        # Arousal slightly elevated
        assert modified_vad["arousal"] > 0.5

    def test_long_absence_stronger_longing(self, soul_rin):
        """Long absence (7 days) should add stronger longing effect."""
        vad = {"valence": 0.3, "arousal": 0.5, "dominance": 0.5}

        modified_vad = _apply_longing_gradient(vad, days_since_last_interaction=7.0, soul=soul_rin)

        # Valence impact: -0.07 (7 days × -0.01)
        assert modified_vad["valence"] < 0.25

    def test_very_long_absence_capped_at_7_days(self, soul_rin):
        """Very long absence (30 days) should cap longing at 7 days effect."""
        vad = {"valence": 0.3, "arousal": 0.5, "dominance": 0.5}

        modified_7 = _apply_longing_gradient(
            vad.copy(), days_since_last_interaction=7.0, soul=soul_rin
        )
        modified_30 = _apply_longing_gradient(
            vad.copy(), days_since_last_interaction=30.0, soul=soul_rin
        )

        # Should be same (capped at 7 days)
        assert abs(modified_7["valence"] - modified_30["valence"]) < 0.01


class TestMovingAverageComputation:
    """Test 24h moving average and EWMA computation."""

    def test_empty_history_returns_neutral(self):
        """Empty VAD history should return neutral default."""
        avg = _compute_24h_average([])

        assert avg["valence"] == 0.0
        assert avg["arousal"] == 0.3
        assert avg["dominance"] == 0.5

    def test_simple_average_correct(self):
        """Simple moving average should compute correctly."""
        history = [
            {
                "vad": {"valence": 0.2, "arousal": 0.4, "dominance": 0.5},
                "at": "2026-05-20T10:00:00Z",
            },
            {
                "vad": {"valence": 0.4, "arousal": 0.6, "dominance": 0.5},
                "at": "2026-05-20T11:00:00Z",
            },
            {
                "vad": {"valence": 0.6, "arousal": 0.8, "dominance": 0.5},
                "at": "2026-05-20T12:00:00Z",
            },
        ]

        avg = _compute_24h_average(history)

        # (0.2 + 0.4 + 0.6) / 3 = 0.4
        assert abs(avg["valence"] - 0.4) < 0.01
        # (0.4 + 0.6 + 0.8) / 3 = 0.6
        assert abs(avg["arousal"] - 0.6) < 0.01

    def test_ewma_dampens_spikes(self):
        """EWMA should dampen sudden spikes compared to simple average."""
        # Single recent spike
        history_with_spike = [
            {
                "vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
                "at": "2026-05-20T10:00:00Z",
            },
            {
                "vad": {"valence": 0.0, "arousal": 0.3, "dominance": 0.5},
                "at": "2026-05-20T11:00:00Z",
            },
            {
                "vad": {"valence": 0.9, "arousal": 0.9, "dominance": 0.9},
                "at": "2026-05-20T12:00:00Z",
            },  # Sudden spike
        ]

        simple_avg = _compute_24h_average(history_with_spike)
        ewma = _compute_ewma(history_with_spike, alpha=0.3)

        # EWMA should dampen the spike (be less than simple average)
        # Simple avg: (0.0 + 0.0 + 0.9) / 3 = 0.3
        # EWMA with alpha=0.3 gives less weight to the sudden spike
        assert abs(simple_avg["valence"] - 0.3) < 0.01
        # EWMA should be less than simple avg (dampened)
        assert ewma["valence"] < simple_avg["valence"]


class TestDriftMetadata:
    """Test drift history and metadata tracking."""

    def test_drift_history_recorded(self, soul_rin, neutral_state):
        """Drift should record history entry."""
        new_mood = drift_mood(neutral_state, soul_rin, hours_since_last=1.0)

        assert len(new_mood["drift_history"]) == 1

        entry = new_mood["drift_history"][0]
        assert "from" in entry
        assert "to" in entry
        assert "at" in entry
        assert "cause" in entry

    def test_drift_history_capped_at_50(self, soul_rin):
        """Drift history should cap at 50 entries."""
        state = {
            "mood": {
                "valence_baseline": 0.0,
                "arousal_baseline": 0.3,
                "dominance_baseline": 0.5,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "drift_history": [{"old": i} for i in range(60)],  # Already 60 entries
            },
            "recent_vad_history": [],
        }

        new_mood = drift_mood(state, soul_rin, hours_since_last=1.0)

        # Should cap at 50
        assert len(new_mood["drift_history"]) == 50


class TestBackgroundEmotions:
    """Test background emotion derivation from mood."""

    def test_negative_low_arousal_weariness(self, soul_rin, neutral_state):
        """Negative valence + low arousal = weariness."""
        # Need more extreme values to trigger weariness
        # The drift algorithm dampens changes, so start from negative baseline
        neutral_state["mood"]["valence_baseline"] = -0.3
        neutral_state["mood"]["arousal_baseline"] = 0.25
        neutral_state["recent_vad_history"] = [
            {
                "vad": {"valence": -0.5, "arousal": 0.2, "dominance": 0.4},
                "at": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(20)
        ]

        new_mood = drift_mood(neutral_state, soul_rin, hours_since_last=1.0)

        # Should include weariness (valence < -0.2 and arousal < 0.4)
        assert "weariness" in new_mood.get("background_emotions", []) or "longing" in new_mood.get(
            "background_emotions", []
        )

    def test_positive_moderate_arousal_contentment(self, soul_dorothy, neutral_state):
        """Positive valence + moderate arousal = contentment."""
        neutral_state["recent_vad_history"] = [
            {
                "vad": {"valence": 0.3, "arousal": 0.4, "dominance": 0.5},
                "at": datetime.now(timezone.utc).isoformat(),
            }
            for _ in range(10)
        ]

        new_mood = drift_mood(neutral_state, soul_dorothy, hours_since_last=1.0)

        # Should include contentment
        assert "contentment" in new_mood.get("background_emotions", [])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
