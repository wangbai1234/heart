"""
Unit tests for Inner State Composer (SS06 §3.4, §3.5, §4.1).

Covers:
  - Basic compose: all fields populate correctly
  - Mood drift: rising / falling / stable classification
  - Since-last-talk: time quantization to human labels
  - Activity aggregation into today state
  - Concerns + unfinished thoughts passthrough
  - Default values for optional fields
  - Energy trajectory aggregation
  - Anniversary passthrough
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from heart.ss06_inner_state.composer import (
    DailyRitualState,
    EnergyPoint,
    InnerState,
    InnerStateComposer,
    ProactiveState,
    RitualState,
    TodayMood,
    TodayState,
    compose_inner_state,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def composer():
    return InnerStateComposer()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def character_id():
    return "rin"


# ============================================================
# Basic Composition
# ============================================================


class TestBasicCompose:
    """Minimal compose produces valid InnerState."""

    def test_minimal_compose(self, composer, user_id):
        """Minimal compose with only required args."""
        state = composer.compose(user_id=user_id, character_id="rin")

        assert isinstance(state, InnerState)
        assert state.user_id == user_id
        assert state.character_id == "rin"
        assert state.current_energy == 0.5
        assert isinstance(state.today, TodayState)
        assert isinstance(state.rituals, RitualState)
        assert isinstance(state.rituals.daily_check_in, DailyRitualState)
        assert isinstance(state.proactive_state, ProactiveState)

    def test_compose_with_mood(self, composer, user_id):
        """Compose with mood inputs produces TodayMood."""
        state = composer.compose(
            user_id=user_id,
            character_id="dorothy",
            mood_label="开心",
            mood_valence=0.7,
            mood_arousal=0.8,
            mood_descriptor="你今天心情很好，像小蝴蝶一样。",
            prev_mood_valence=0.5,
            prev_mood_arousal=0.6,
        )

        mood = state.today.mood
        assert mood is not None
        assert mood.label == "开心"
        assert mood.valence == pytest.approx(0.7)
        assert mood.arousal == pytest.approx(0.8)
        assert mood.descriptor == "你今天心情很好，像小蝴蝶一样。"
        assert "小蝴蝶" in mood.descriptor

    def test_compose_with_activities(self, composer, user_id):
        """Activities flow through to today state."""
        activities = ["在窗边看雾", "翻了一本旧书"]

        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            activities=activities,
        )

        assert state.today.activities == activities
        assert len(state.today.activities) == 2

    def test_compose_with_concerns(self, composer, user_id):
        """User concerns and unfinished thoughts pass through."""
        concerns = ["担心加班", "明天考试"]
        thoughts = ["想问为什么沉默"]

        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            user_concerns=concerns,
            unfinished_thoughts=thoughts,
        )

        assert state.user_concerns == concerns
        assert state.unfinished_thoughts == thoughts

    def test_compose_with_anniversaries(self, composer, user_id):
        """Anniversaries pass through."""
        anniversaries = [
            {"name": "生日", "hours_until": 48, "actual_sent": False},
        ]

        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            upcoming_anniversaries=anniversaries,
        )

        assert state.upcoming_anniversaries == anniversaries

    def test_convenience_function(self, user_id):
        """compose_inner_state convenience function works."""
        state = compose_inner_state(
            user_id=user_id,
            character_id="dorothy",
            mood_label="happy",
        )
        assert isinstance(state, InnerState)
        assert state.user_id == user_id
        assert state.character_id == "dorothy"


# ============================================================
# Mood Drift
# ============================================================


class TestMoodDrift:
    """Mood drift calculation and classification."""

    def test_rising_drift(self, composer, user_id):
        """Valence increase > 0.15 → rising."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=0.5,
            prev_mood_valence=0.2,
        )
        mood = state.today.mood
        assert mood.drift_direction == "rising"
        assert mood.delta_valence == pytest.approx(0.3)

    def test_falling_drift(self, composer, user_id):
        """Valence decrease < -0.15 → falling."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=-0.2,
            prev_mood_valence=0.3,
        )
        mood = state.today.mood
        assert mood.drift_direction == "falling"
        assert mood.delta_valence == pytest.approx(-0.5)

    def test_stable_drift_small_positive(self, composer, user_id):
        """Small valence change → stable."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=0.35,
            prev_mood_valence=0.3,
        )
        mood = state.today.mood
        assert mood.drift_direction == "stable"
        assert mood.delta_valence == pytest.approx(0.05)

    def test_stable_drift_small_negative(self, composer, user_id):
        """Small negative valence change → stable."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=0.25,
            prev_mood_valence=0.3,
        )
        mood = state.today.mood
        assert mood.drift_direction == "stable"
        assert mood.delta_valence == pytest.approx(-0.05)

    def test_drift_at_threshold(self, composer, user_id):
        """Exact threshold values."""
        # Exactly 0.15 increase → stable (not > threshold)
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=0.45,
            prev_mood_valence=0.3,
        )
        assert state.today.mood.drift_direction == "stable"

        # Exactly -0.15 decrease → stable (not < threshold)
        state2 = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_valence=0.15,
            prev_mood_valence=0.3,
        )
        assert state2.today.mood.drift_direction == "stable"


# ============================================================
# Emotion Name Derivation
# ============================================================


class TestEmotionDerivation:
    """Primary emotion name from valence × arousal quadrant."""

    def test_excited(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=0.5, mood_arousal=0.8,
        )
        assert state.today.mood.primary_emotion == "excited"

    def test_content(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=0.4, mood_arousal=0.4,
        )
        assert state.today.mood.primary_emotion == "content"

    def test_serene(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=0.6, mood_arousal=0.2,
        )
        assert state.today.mood.primary_emotion == "serene"

    def test_restless(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=0.0, mood_arousal=0.7,
        )
        assert state.today.mood.primary_emotion == "restless"

    def test_neutral(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=0.1, mood_arousal=0.5,
        )
        assert state.today.mood.primary_emotion == "neutral"

    def test_lethargic(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=-0.1, mood_arousal=0.2,
        )
        assert state.today.mood.primary_emotion == "lethargic"

    def test_distressed(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=-0.5, mood_arousal=0.8,
        )
        assert state.today.mood.primary_emotion == "distressed"

    def test_sad(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=-0.6, mood_arousal=0.4,
        )
        assert state.today.mood.primary_emotion == "sad"

    def test_depressed(self, composer, user_id):
        state = composer.compose(
            user_id=user_id, character_id="rin",
            mood_valence=-0.8, mood_arousal=0.1,
        )
        assert state.today.mood.primary_emotion == "depressed"


# ============================================================
# Since Last Talk
# ============================================================


class TestSinceLastTalk:
    """Time since last user interaction computation."""

    def test_no_interaction(self, composer, user_id):
        """None → '刚刚'."""
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=None,
        )
        assert state.since_last_talk_seconds == 0.0
        assert state.since_last_talk_label == "刚刚"

    def test_just_now(self, composer, user_id):
        """Recent interaction (< 1 min ago)."""
        now = datetime.now(timezone.utc)
        recent = now.isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=recent,
        )
        assert state.since_last_talk_label == "刚刚"

    def test_minutes_ago(self, composer, user_id):
        """A few minutes ago."""
        now = datetime.now(timezone.utc)
        five_min_ago = (now - timedelta(minutes=5)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=five_min_ago,
        )
        assert state.since_last_talk_label == "几分钟前"

    def test_hours_ago(self, composer, user_id):
        """A few hours ago."""
        now = datetime.now(timezone.utc)
        three_hours_ago = (now - timedelta(hours=3)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=three_hours_ago,
        )
        assert state.since_last_talk_label == "几小时前"

    def test_half_day_ago(self, composer, user_id):
        """Half a day ago."""
        now = datetime.now(timezone.utc)
        half_day_ago = (now - timedelta(hours=8)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=half_day_ago,
        )
        assert state.since_last_talk_label == "半天前"

    def test_one_day_ago(self, composer, user_id):
        """One day ago."""
        now = datetime.now(timezone.utc)
        one_day_ago = (now - timedelta(hours=30)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=one_day_ago,
        )
        assert state.since_last_talk_label == "一天前"

    def test_several_days_ago(self, composer, user_id):
        """Several days ago."""
        now = datetime.now(timezone.utc)
        three_days_ago = (now - timedelta(days=3)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=three_days_ago,
        )
        assert state.since_last_talk_label == "几天前"

    def test_seconds_are_computed(self, composer, user_id):
        """Since-last-talk seconds is a concrete number."""
        now = datetime.now(timezone.utc)
        one_hour_ago = (now - timedelta(hours=1)).isoformat()
        state = composer.compose(
            user_id=user_id, character_id="rin",
            last_user_interaction_at=one_hour_ago,
        )
        assert state.since_last_talk_seconds >= 3500
        assert state.since_last_talk_seconds <= 3700


# ============================================================
# Energy Trajectory
# ============================================================


class TestEnergy:
    """Energy and trajectory aggregation."""

    def test_energy_values(self, composer, user_id):
        """Energy and baseline flow through."""
        trajectory = [
            EnergyPoint(hour=8, energy=0.6, source="circadian"),
            EnergyPoint(hour=12, energy=0.4, source="recent_activity"),
        ]
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            current_energy=0.75,
            energy_baseline=0.5,
            energy_trajectory=trajectory,
        )
        assert state.current_energy == pytest.approx(0.75)
        assert state.energy_baseline == pytest.approx(0.5)
        assert len(state.today.energy_trajectory) == 2


# ============================================================
# Rituals & Proactive State
# ============================================================


class TestRitualState:
    """Ritual tracking passes through."""

    def test_ritual_streaks(self, composer, user_id):
        """Morning/night/longest streaks."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            morning_streak=5,
            night_streak=3,
            longest_streak=12,
        )
        rituals = state.rituals.daily_check_in
        assert rituals.morning_streak == 5
        assert rituals.night_streak == 3
        assert rituals.longest_streak == 12


class TestProactiveState:
    """Proactive state passthrough."""

    def test_default_proactive_state(self, composer, user_id):
        """Default proactive state is created."""
        state = composer.compose(user_id=user_id, character_id="rin")
        assert isinstance(state.proactive_state, ProactiveState)
        assert state.proactive_state.proactive_today_count == 0

    def test_custom_proactive_state(self, composer, user_id):
        """Custom proactive state passes through."""
        ps = ProactiveState(
            last_proactive_at="2026-05-21T10:00:00Z",
            proactive_today_count=2,
            last_proactive_type="care_check",
        )
        state = composer.compose(
            user_id=user_id, character_id="rin", proactive_state=ps,
        )
        assert state.proactive_state.proactive_today_count == 2
        assert state.proactive_state.last_proactive_type == "care_check"


# ============================================================
# Edge Cases
# ============================================================


class TestEdgeCases:
    """Edge-case handling."""

    def test_empty_lists_default(self, composer, user_id):
        """None for lists → empty lists."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            activities=None,
            user_concerns=None,
            unfinished_thoughts=None,
            upcoming_anniversaries=None,
            energy_trajectory=None,
        )
        assert state.today.activities == []
        assert state.user_concerns == []
        assert state.unfinished_thoughts == []
        assert state.upcoming_anniversaries == []
        assert state.today.energy_trajectory == []

    def test_invalid_last_interaction(self, composer, user_id):
        """Invalid ISO format → treats as None."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            last_user_interaction_at="not-a-date",
        )
        assert state.since_last_talk_label == "刚刚"
        assert state.since_last_talk_seconds == 0.0

    def test_next_inner_loop_auto(self, composer, user_id):
        """next_inner_loop_at is auto-set if not provided."""
        state = composer.compose(user_id=user_id, character_id="rin")
        assert state.next_inner_loop_at != ""
        # Should be roughly 1 hour from now
        dt = datetime.fromisoformat(state.next_inner_loop_at)
        delta = dt - datetime.now(timezone.utc)
        assert timedelta(minutes=55) < delta < timedelta(minutes=65)

    def test_meta_fields(self, composer, user_id):
        """Meta fields are populated."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            loop_iteration_count=42,
        )
        assert state.loop_iteration_count == 42
        assert state.updated_at != ""
