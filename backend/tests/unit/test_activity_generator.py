"""
Unit tests for Activity Generator (SS06 §10.4).

Covers:
  - Determinism: same seed → same output
  - Time-of-day rules: morning/afternoon/evening/night mapping
  - Back-to-back avoidance: recent_activity_ids filter (3 days)
  - Pool exhaustion: all candidates used → allow repeats
  - Missing character → ValueError
  - generate_today_activities: 4 activities per day
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from heart.ss06_inner_state.activity_generator import (
    Activity,
    ActivityGenerator,
    TimeOfDay,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def pool_dir():
    """Path to the real activity pool YAML files."""
    repo_root = Path(__file__).resolve().parents[3]
    return str(repo_root / "config" / "activity_pools")


@pytest.fixture
def generator(pool_dir):
    """ActivityGenerator with real pool configs."""
    return ActivityGenerator(activity_pool_dir=pool_dir)


@pytest.fixture
def mock_soul():
    """Minimal soul spec with character_id."""

    class MockSoul:
        character_id = "dorothy"

    return MockSoul()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def morning_time():
    return datetime(2026, 5, 21, 8, 0, 0)


@pytest.fixture
def afternoon_time():
    return datetime(2026, 5, 21, 14, 0, 0)


@pytest.fixture
def evening_time():
    return datetime(2026, 5, 21, 20, 0, 0)


@pytest.fixture
def night_time():
    return datetime(2026, 5, 21, 23, 0, 0)


@pytest.fixture
def early_night_time():
    return datetime(2026, 5, 21, 3, 0, 0)


# ============================================================
# Time-of-Day Detection
# ============================================================


class TestTimeOfDay:
    """§3.8: 4 time-of-day windows."""

    def test_morning(self):
        """06:00-11:59 → morning."""
        for hour in range(6, 12):
            dt = datetime(2026, 5, 21, hour, 0)
            assert ActivityGenerator._determine_time_of_day(dt) == "morning"

    def test_afternoon(self):
        """12:00-17:59 → afternoon."""
        for hour in range(12, 18):
            dt = datetime(2026, 5, 21, hour, 0)
            assert ActivityGenerator._determine_time_of_day(dt) == "afternoon"

    def test_evening(self):
        """18:00-21:59 → evening."""
        for hour in range(18, 22):
            dt = datetime(2026, 5, 21, hour, 0)
            assert ActivityGenerator._determine_time_of_day(dt) == "evening"

    def test_night_late(self):
        """22:00-23:59 → night."""
        for hour in range(22, 24):
            dt = datetime(2026, 5, 21, hour, 0)
            assert ActivityGenerator._determine_time_of_day(dt) == "night"

    def test_night_early(self):
        """00:00-05:59 → night."""
        for hour in range(0, 6):
            dt = datetime(2026, 5, 22, hour, 0)
            assert ActivityGenerator._determine_time_of_day(dt) == "night"

    def test_boundaries(self):
        """Edge cases at boundaries."""
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 5, 59)
        ) == "night"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 6, 0)
        ) == "morning"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 11, 59)
        ) == "morning"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 12, 0)
        ) == "afternoon"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 17, 59)
        ) == "afternoon"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 18, 0)
        ) == "evening"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 21, 59)
        ) == "evening"
        assert ActivityGenerator._determine_time_of_day(
            datetime(2026, 5, 21, 22, 0)
        ) == "night"


# ============================================================
# Day Type Detection
# ============================================================


class TestDayType:
    """Weekday vs weekend detection."""

    def test_weekday(self):
        """Monday-Friday → weekday."""
        # 2026-05-18 is Monday, 2026-05-22 is Friday
        for day in range(18, 23):
            dt = datetime(2026, 5, day, 12, 0)
            assert ActivityGenerator._determine_day_type(dt) == "weekday"

    def test_weekend(self):
        """Saturday-Sunday → weekend."""
        # 2026-05-23 is Saturday, 2026-05-24 is Sunday
        dt_sat = datetime(2026, 5, 23, 12, 0)
        dt_sun = datetime(2026, 5, 24, 12, 0)
        assert ActivityGenerator._determine_day_type(dt_sat) == "weekend"
        assert ActivityGenerator._determine_day_type(dt_sun) == "weekend"


# ============================================================
# Determinism
# ============================================================


class TestDeterminism:
    """Same (user_id, character_id, hour) → same output."""

    def test_same_seed_same_output(self, generator, mock_soul, user_id, morning_time):
        """Identical inputs produce identical activities."""
        a1 = generator.select(mock_soul, user_id, morning_time)
        a2 = generator.select(mock_soul, user_id, morning_time)
        assert a1.pool_id == a2.pool_id
        assert a1.description == a2.description
        assert a1.time_of_day == a2.time_of_day

    def test_different_user_different_output(self, generator, mock_soul, morning_time):
        """Different user_id produces different activity."""
        a1 = generator.select(mock_soul, uuid4(), morning_time)
        a2 = generator.select(mock_soul, uuid4(), morning_time)
        # Not guaranteed to differ every time, but very high probability
        assert a1.pool_id != a2.pool_id

    def test_different_hour_different_output(self, generator, mock_soul, user_id):
        """Different hour produces different time_of_day and potentially
        different activity."""
        a1 = generator.select(mock_soul, user_id, datetime(2026, 5, 21, 8, 0))
        a2 = generator.select(mock_soul, user_id, datetime(2026, 5, 21, 14, 0))
        assert a1.time_of_day == "morning"
        assert a2.time_of_day == "afternoon"
        assert a1.pool_id != a2.pool_id  # different time_of_day → different pool

    def test_different_character_different_output(self, generator, user_id, morning_time):
        """Different character_id produces different activity."""

        class RinSoul:
            character_id = "rin"

        class DorothySoul:
            character_id = "dorothy"

        a1 = generator.select(RinSoul(), user_id, morning_time)
        a2 = generator.select(DorothySoul(), user_id, morning_time)
        assert a1.pool_id != a2.pool_id
        # Dorothy activities should be share_eligible more often
        # (this is a pool property, not a hard assertion)


# ============================================================
# Back-to-Back Repeat Avoidance
# ============================================================


class TestRepeatAvoidance:
    """机制 D: 同一 activity 不在 3 天内被选两次."""

    def test_excludes_recent(self, generator, mock_soul, user_id, morning_time):
        """Activity in recent_activity_ids is excluded."""
        # First, get an activity
        a1 = generator.select(mock_soul, user_id, morning_time)

        # Mark it as recent
        recent = {a1.pool_id}
        a2 = generator.select(mock_soul, user_id, morning_time, recent_activity_ids=recent)

        # Should be a different activity
        assert a2.pool_id != a1.pool_id

    def test_allows_repeats_when_pool_exhausted(self, generator, mock_soul, user_id):
        """When ALL candidates are in recent set, allow repeats."""
        pool = generator._load_pool("dorothy")
        weekday_morning = pool["weekday"]["morning"]

        # Collect all pool IDs for weekday morning
        all_ids = {e.id for e in weekday_morning}

        # If pool has > 1 entry, excluding all forces repeat
        if len(all_ids) > 1:
            dt = datetime(2026, 5, 21, 8, 0)
            a = generator.select(mock_soul, user_id, dt, recent_activity_ids=all_ids)
            # Should still return a valid activity (from the exhausted pool)
            assert a.pool_id in all_ids


# ============================================================
# Activity Properties
# ============================================================


class TestActivityProperties:
    """Verify returned Activity objects match pool entry."""

    def test_activity_has_all_fields(self, generator, mock_soul, user_id, morning_time):
        """Activity contains all required fields."""
        a = generator.select(mock_soul, user_id, morning_time)
        assert isinstance(a, Activity)
        assert isinstance(a.activity_id, UUID)
        assert isinstance(a.description, str)
        assert len(a.description) > 0
        assert a.time_of_day == "morning"
        assert a.scheduled_at is not None
        assert isinstance(a.associated_mood, str)
        assert isinstance(a.share_eligible, bool)
        assert a.already_shared is False
        assert isinstance(a.pool_id, str)
        assert len(a.pool_id) > 0

    def test_activity_time_of_day_matches(self, generator, mock_soul, user_id):
        """Activity time_of_day matches the input hour."""
        for hour, expected_tod in [
            (7, "morning"),
            (14, "afternoon"),
            (19, "evening"),
            (23, "night"),
            (3, "night"),
        ]:
            dt = datetime(2026, 5, 21, hour, 0)
            a = generator.select(mock_soul, user_id, dt)
            assert a.time_of_day == expected_tod, f"hour={hour}"


# ============================================================
# generate_today_activities
# ============================================================


class TestGenerateTodayActivities:
    """§10.4: pre-compute 4 activities per day."""

    def test_generates_four_activities(self, generator, mock_soul, user_id):
        """generate_today_activities returns exactly 4 activities."""
        from datetime import date
        activities = generator.generate_today_activities(
            mock_soul, user_id, date(2026, 5, 21)
        )
        assert len(activities) == 4

    def test_all_time_of_day_present(self, generator, mock_soul, user_id):
        """Each time_of_day is represented exactly once."""
        from datetime import date
        activities = generator.generate_today_activities(
            mock_soul, user_id, date(2026, 5, 21)
        )
        tods = {a.time_of_day for a in activities}
        assert tods == {"morning", "afternoon", "evening", "night"}

    def test_no_duplicates_within_day(self, generator, mock_soul, user_id):
        """Activities within a single day don't repeat pool_ids."""
        from datetime import date
        activities = generator.generate_today_activities(
            mock_soul, user_id, date(2026, 5, 21)
        )
        pool_ids = [a.pool_id for a in activities]
        assert len(pool_ids) == len(set(pool_ids))

    def test_deterministic_per_date(self, generator, mock_soul, user_id):
        """Same date → same activities."""
        from datetime import date
        a1 = generator.generate_today_activities(
            mock_soul, user_id, date(2026, 5, 21)
        )
        a2 = generator.generate_today_activities(
            mock_soul, user_id, date(2026, 5, 21)
        )
        ids1 = [a.pool_id for a in a1]
        ids2 = [a.pool_id for a in a2]
        assert ids1 == ids2


# ============================================================
# Pool Loading
# ============================================================


class TestPoolLoading:
    """YAML pool loading and caching."""

    def test_loads_dorothy_pool(self, generator):
        """Dorothy pool has entries for all 8 slots."""
        pool = generator._load_pool("dorothy")
        for day_type in ["weekday", "weekend"]:
            for tod in ["morning", "afternoon", "evening", "night"]:
                entries = pool[day_type][tod]
                assert len(entries) == 4, f"{day_type}:{tod}"

    def test_loads_rin_pool(self, generator):
        """Rin pool has entries for all 8 slots."""
        pool = generator._load_pool("rin")
        for day_type in ["weekday", "weekend"]:
            for tod in ["morning", "afternoon", "evening", "night"]:
                entries = pool[day_type][tod]
                assert len(entries) == 4, f"{day_type}:{tod}"

    def test_missing_character_raises(self, generator, mock_soul, user_id, morning_time):
        """Non-existent character_id raises ValueError."""
        mock_soul.character_id = "nonexistent"
        with pytest.raises(ValueError, match="Activity pool not found"):
            generator.select(mock_soul, user_id, morning_time)

    def test_get_pool_size(self, generator):
        """get_pool_size returns correct counts."""
        sizes = generator.get_pool_size("dorothy")
        assert sizes["weekday:morning"] == 4
        assert sizes["weekday:afternoon"] == 4
        assert sizes["weekday:evening"] == 4
        assert sizes["weekday:night"] == 4
        assert sizes["weekend:morning"] == 4
        assert sizes["weekend:afternoon"] == 4
        assert sizes["weekend:evening"] == 4
        assert sizes["weekend:night"] == 4
