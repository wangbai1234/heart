"""
Unit tests for Ritual Manager (SS06 §3.9).

Covers:
  - Streak increments correctly on record_completed
  - Streak resets to 0 on record_missed
  - Milestone detection at 7, 30, 100 days
  - Window checks: morning (07:00–10:00) and night (21:00–23:30)
  - Daily reset at 06:00 clears done_today flags
  - Soul-aware flavor: Rin vs Dorothy have different directives
  - Trust delta computation
  - Jitter is within ±20 minutes
  - Edge cases: consecutive completes, consecutive misses, multiple milestones
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from heart.ss06_inner_state.ritual_manager import (
    RitualCheckResult,
    RitualCompleteResult,
    RitualEvent,
    RitualManager,
    RitualStreakState,
    RitualType,
    SOUL_RITUAL_FLAVOR,
    StreakMilestone,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def mgr():
    return RitualManager()


@pytest.fixture
def fresh_state():
    return RitualStreakState()


@pytest.fixture
def morning_time():
    return datetime(2026, 5, 22, 8, 30, 0)  # 08:30 = inside morning window


@pytest.fixture
def night_time():
    return datetime(2026, 5, 22, 21, 15, 0)  # 21:15 = inside night window


@pytest.fixture
def outside_time():
    return datetime(2026, 5, 22, 14, 0, 0)  # 14:00 = outside all windows


# ============================================================
# Window checks
# ============================================================


class TestWindowChecks:
    def test_morning_window_start(self, mgr):
        """07:00 is inside morning window."""
        assert mgr.is_morning_window(datetime(2026, 5, 22, 7, 0, 0)) is True

    def test_morning_window_middle(self, mgr):
        """08:30 is inside morning window."""
        assert mgr.is_morning_window(datetime(2026, 5, 22, 8, 30, 0)) is True

    def test_morning_window_end_exclusive(self, mgr):
        """10:00 is NOT inside morning window (exclusive end)."""
        assert mgr.is_morning_window(datetime(2026, 5, 22, 10, 0, 0)) is False

    def test_morning_window_before(self, mgr):
        """06:59 is NOT inside morning window."""
        assert mgr.is_morning_window(datetime(2026, 5, 22, 6, 59, 0)) is False

    def test_night_window_start(self, mgr):
        """21:00 is inside night window."""
        assert mgr.is_night_window(datetime(2026, 5, 22, 21, 0, 0)) is True

    def test_night_window_middle(self, mgr):
        """22:30 is inside night window."""
        assert mgr.is_night_window(datetime(2026, 5, 22, 22, 30, 0)) is True

    def test_night_window_end_inclusive(self, mgr):
        """23:30 is inside night window (inclusive end)."""
        assert mgr.is_night_window(datetime(2026, 5, 22, 23, 30, 0)) is True

    def test_night_window_after(self, mgr):
        """23:31 is NOT inside night window."""
        assert mgr.is_night_window(datetime(2026, 5, 22, 23, 31, 0)) is False

    def test_night_window_before(self, mgr):
        """20:59 is NOT inside night window."""
        assert mgr.is_night_window(datetime(2026, 5, 22, 20, 59, 0)) is False

    def test_any_window_morning(self, mgr, morning_time):
        assert mgr.is_any_window(morning_time) is True

    def test_any_window_night(self, mgr, night_time):
        assert mgr.is_any_window(night_time) is True

    def test_any_window_outside(self, mgr, outside_time):
        assert mgr.is_any_window(outside_time) is False


# ============================================================
# Ritual due checks
# ============================================================


class TestRitualDue:
    def test_morning_due_in_window(self, mgr, fresh_state, morning_time):
        result = mgr.check_ritual_due(fresh_state, morning_time)
        assert result.due is True
        assert result.ritual_type == RitualType.MORNING
        assert result.window == "morning"
        assert result.streak == 0  # fresh state has 0 streak

    def test_night_due_in_window(self, mgr, fresh_state, night_time):
        result = mgr.check_ritual_due(fresh_state, night_time)
        assert result.due is True
        assert result.ritual_type == RitualType.NIGHT
        assert result.window == "night"

    def test_not_due_outside_window(self, mgr, fresh_state, outside_time):
        result = mgr.check_ritual_due(fresh_state, outside_time)
        assert result.due is False
        assert result.reason == "no_ritual_window_open_or_already_done"

    def test_not_due_already_done_morning(self, mgr, fresh_state, morning_time):
        fresh_state.morning_done_today = True
        result = mgr.check_ritual_due(fresh_state, morning_time)
        assert result.due is False

    def test_not_due_already_done_night(self, mgr, fresh_state, night_time):
        fresh_state.night_done_today = True
        result = mgr.check_ritual_due(fresh_state, night_time)
        assert result.due is False


# ============================================================
# Streak: record_completed (increment)
# ============================================================


class TestStreakIncrement:
    def test_first_completion_starts_streak(self, mgr, fresh_state):
        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.new_streak == 1
        assert result.streak_up is True
        assert result.previous_streak == 0
        assert RitualEvent.RITUAL_COMPLETED in result.events
        assert RitualEvent.STREAK_MILESTONE not in result.events  # 1 < 7
        assert fresh_state.morning_streak == 1
        assert fresh_state.morning_done_today is True

    def test_consecutive_completions_increment(self, mgr, fresh_state):
        # Day 1
        r1 = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert r1.new_streak == 1

        # Reset daily flags (simulate new day)
        mgr.reset_daily(fresh_state)

        # Day 2
        r2 = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert r2.new_streak == 2
        assert fresh_state.morning_streak == 2

        # Day 3
        mgr.reset_daily(fresh_state)
        r3 = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert r3.new_streak == 3

    def test_morning_and_night_independent(self, mgr, fresh_state):
        # Complete morning
        r1 = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert r1.new_streak == 1
        assert fresh_state.morning_streak == 1
        assert fresh_state.night_streak == 0  # unaffected

        # Complete night
        r2 = mgr.record_completed(fresh_state, RitualType.NIGHT)
        assert r2.new_streak == 1
        assert fresh_state.night_streak == 1
        assert fresh_state.morning_streak == 1  # still 1

    def test_longest_streak_tracks_max(self, mgr, fresh_state):
        # Build morning streak to 5
        for _ in range(5):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.longest_streak == 5

        # Now break morning streak, then build to 3
        mgr.record_missed(fresh_state, RitualType.MORNING)
        assert fresh_state.morning_streak == 0
        assert fresh_state.longest_streak == 5  # longest stays

        for _ in range(3):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 3
        assert fresh_state.longest_streak == 5  # 3 < 5, longest unchanged

        # Build night streak to 8
        for _ in range(8):
            mgr.record_completed(fresh_state, RitualType.NIGHT)
            mgr.reset_daily(fresh_state)
        assert fresh_state.longest_streak == 8  # updated

    def test_last_timestamps_recorded(self, mgr, fresh_state):
        before = datetime(2026, 5, 1, 12, 0, 0)
        r1 = mgr.record_completed(fresh_state, RitualType.MORNING, completed_at=before)
        assert fresh_state.last_morning_at == before

        after = datetime(2026, 5, 2, 22, 0, 0)
        r2 = mgr.record_completed(fresh_state, RitualType.NIGHT, completed_at=after)
        assert fresh_state.last_night_at == after


# ============================================================
# Streak: record_missed (reset)
# ============================================================


class TestStreakReset:
    def test_miss_resets_streak_to_zero(self, mgr, fresh_state):
        # Build streak to 3
        for _ in range(3):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 3

        # Miss one day
        result = mgr.record_missed(fresh_state, RitualType.MORNING)
        assert result.new_streak == 0
        assert result.streak_up is False
        assert result.previous_streak == 3
        assert RitualEvent.STREAK_BROKEN in result.events
        assert fresh_state.morning_streak == 0

    def test_miss_at_zero_no_broken_event(self, mgr, fresh_state):
        """Missing when streak is already 0 should not emit STREAK_BROKEN."""
        result = mgr.record_missed(fresh_state, RitualType.MORNING)
        assert result.new_streak == 0
        assert result.previous_streak == 0
        assert RitualEvent.STREAK_BROKEN not in result.events

    def test_miss_then_rebuild(self, mgr, fresh_state):
        # Build to 2, miss, rebuild to 1
        for _ in range(2):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 2

        mgr.record_missed(fresh_state, RitualType.MORNING)
        assert fresh_state.morning_streak == 0

        mgr.record_completed(fresh_state, RitualType.MORNING)
        assert fresh_state.morning_streak == 1

    def test_miss_night_does_not_affect_morning(self, mgr, fresh_state):
        # Build both streaks
        mgr.record_completed(fresh_state, RitualType.MORNING)
        mgr.record_completed(fresh_state, RitualType.NIGHT)
        assert fresh_state.morning_streak == 1
        assert fresh_state.night_streak == 1

        # Miss only night
        mgr.record_missed(fresh_state, RitualType.NIGHT)
        assert fresh_state.morning_streak == 1  # unchanged
        assert fresh_state.night_streak == 0


# ============================================================
# Milestone detection
# ============================================================


class TestMilestoneDetection:
    def test_hit_7_day_milestone(self, mgr, fresh_state):
        for i in range(6):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 6
        assert "7" not in fresh_state.milestones_hit  # not yet hit

        # Day 7 → milestone
        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.milestone_hit == 7
        assert RitualEvent.STREAK_MILESTONE in result.events
        assert fresh_state.milestones_hit.get("7") is True

    def test_hit_30_day_milestone(self, mgr, fresh_state):
        # Build to 29, skip 7-day milestone by pre-marking it
        fresh_state.milestones_hit["7"] = True
        for _ in range(29):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 29

        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.milestone_hit == 30
        assert RitualEvent.STREAK_MILESTONE in result.events

    def test_hit_100_day_milestone(self, mgr, fresh_state):
        fresh_state.milestones_hit["7"] = True
        fresh_state.milestones_hit["30"] = True
        for _ in range(99):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 99

        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.milestone_hit == 100

    def test_milestone_only_fires_once(self, mgr, fresh_state):
        # Hit 7
        for _ in range(7):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.milestones_hit.get("7") is True

        # Day 8 → no milestone
        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.milestone_hit is None
        assert RitualEvent.STREAK_MILESTONE not in result.events

    def test_miss_resets_but_milestones_remembered(self, mgr, fresh_state):
        # Hit day 7 milestone
        for _ in range(7):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.milestones_hit.get("7") is True

        # Miss and streak resets
        mgr.record_missed(fresh_state, RitualType.MORNING)
        assert fresh_state.morning_streak == 0

        # Build back to 7 — milestone already hit, should not re-fire
        for _ in range(6):
            mgr.record_completed(fresh_state, RitualType.MORNING)
            mgr.reset_daily(fresh_state)
        assert fresh_state.morning_streak == 6

        result = mgr.record_completed(fresh_state, RitualType.MORNING)
        assert result.milestone_hit is None  # no re-fire


# ============================================================
# Daily reset
# ============================================================


class TestDailyReset:
    def test_reset_clears_done_flags(self, mgr, fresh_state):
        fresh_state.morning_done_today = True
        fresh_state.night_done_today = True

        mgr.reset_daily(fresh_state)

        assert fresh_state.morning_done_today is False
        assert fresh_state.night_done_today is False

    def test_reset_does_not_affect_streaks(self, mgr, fresh_state):
        fresh_state.morning_streak = 15
        fresh_state.night_streak = 8
        fresh_state.longest_streak = 20

        mgr.reset_daily(fresh_state)

        assert fresh_state.morning_streak == 15
        assert fresh_state.night_streak == 8
        assert fresh_state.longest_streak == 20

    def test_daily_cycle_complete(self, mgr, fresh_state, morning_time, night_time):
        """Simulate a full day: morning → night, then next day."""
        # Morning ritual
        result = mgr.check_ritual_due(fresh_state, morning_time)
        assert result.due is True
        mgr.record_completed(fresh_state, RitualType.MORNING)
        assert fresh_state.morning_done_today is True

        # Same day morning check → blocked
        result2 = mgr.check_ritual_due(fresh_state, morning_time)
        assert result2.due is False  # already done

        # Night ritual
        result3 = mgr.check_ritual_due(fresh_state, night_time)
        assert result3.due is True
        mgr.record_completed(fresh_state, RitualType.NIGHT)

        # Reset for next day
        mgr.reset_daily(fresh_state)

        # Next day morning check → open again
        result4 = mgr.check_ritual_due(fresh_state, morning_time)
        assert result4.due is True


# ============================================================
# Trust delta computation
# ============================================================


class TestTrustDelta:
    def test_completed_adds_trust(self, mgr):
        delta = mgr.compute_trust_delta(completed=True)
        assert delta == 0.005

    def test_missed_subtracts_trust(self, mgr):
        delta = mgr.compute_trust_delta(completed=False)
        assert delta == -0.005

    def test_30_day_milestone_bonus(self, mgr):
        delta = mgr.compute_trust_delta(completed=True, milestone_hit=30)
        assert delta == 0.055  # 0.005 + 0.05

    def test_7_day_milestone_no_extra_trust(self, mgr):
        """7-day milestone does not grant extra trust delta."""
        delta = mgr.compute_trust_delta(completed=True, milestone_hit=7)
        assert delta == 0.005

    def test_100_day_milestone_no_extra_trust(self, mgr):
        """100-day milestone grants attachment (not trust). Trust delta is base."""
        delta = mgr.compute_trust_delta(completed=True, milestone_hit=100)
        assert delta == 0.005


# ============================================================
# Soul-aware flavor
# ============================================================


class TestSoulFlavor:
    def test_rin_morning_flavor(self, mgr):
        flavor = mgr.get_soul_flavor("rin", RitualType.MORNING)
        assert "极简" in flavor["style"]
        assert "简短" in flavor["directive"]
        assert flavor["max_chars"] == 15

    def test_rin_night_flavor(self, mgr):
        flavor = mgr.get_soul_flavor("rin", RitualType.NIGHT)
        assert "极简" in flavor["style"]

    def test_dorothy_morning_flavor(self, mgr):
        flavor = mgr.get_soul_flavor("dorothy", RitualType.MORNING)
        assert "活泼" in flavor["style"]
        assert "元气" in flavor["directive"]
        assert flavor["max_chars"] == 30

    def test_dorothy_night_flavor(self, mgr):
        flavor = mgr.get_soul_flavor("dorothy", RitualType.NIGHT)
        assert "活泼" in flavor["style"]

    def test_unknown_character_fallback(self, mgr):
        flavor = mgr.get_soul_flavor("unknown_char", RitualType.MORNING)
        assert flavor["style"] == "自然"
        assert flavor["max_chars"] == 20

    def test_ritual_directive_includes_streak(self, mgr):
        directive = mgr.get_ritual_directive("rin", RitualType.MORNING, streak=7)
        assert "连续第 7 天" in directive

    def test_ritual_directive_includes_milestone_language(self, mgr):
        directive = mgr.get_ritual_directive("rin", RitualType.MORNING, streak=30)
        assert "心里觉得温暖" in directive

        directive = mgr.get_ritual_directive("rin", RitualType.MORNING, streak=100)
        assert "很重要的里程碑" in directive


# ============================================================
# Jitter
# ============================================================


class TestJitter:
    def test_jitter_within_range(self, mgr):
        base = datetime(2026, 5, 22, 8, 0, 0)
        for _ in range(100):
            jittered = mgr.compute_jittered_time(base, jitter_minutes=20)
            delta = abs((jittered - base).total_seconds())
            assert delta <= 20 * 60 + 1  # allow 1s float tolerance

    def test_jitter_default_20_minutes(self, mgr):
        base = datetime(2026, 5, 22, 8, 0, 0)
        jittered = mgr.compute_jittered_time(base)
        delta = abs((jittered - base).total_seconds())
        assert delta <= 20 * 60 + 1


# ============================================================
# SOUL_RITUAL_FLAVOR constant
# ============================================================


class TestSoulRitualFlavorConstant:
    def test_has_rin(self):
        assert "rin" in SOUL_RITUAL_FLAVOR

    def test_has_dorothy(self):
        assert "dorothy" in SOUL_RITUAL_FLAVOR

    def test_rin_has_both_times_of_day(self):
        r = SOUL_RITUAL_FLAVOR["rin"]
        assert "morning" in r
        assert "night" in r
        assert "morning_example" in r
        assert "night_example" in r

    def test_dorothy_has_both_times_of_day(self):
        d = SOUL_RITUAL_FLAVOR["dorothy"]
        assert "morning" in d
        assert "night" in d
