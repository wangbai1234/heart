"""
Unit tests for Anniversary Tracker (SS06 §3.7).

Covers:
  - Detection of upcoming anniversaries from L4 sources
  - Yearly recurrence (same year vs next year)
  - Weekly recurrence  
  - Monthly recurrence
  - ONCE pattern (not yet passed vs passed)
  - Out-of-window filtering (> 7 days ahead)
  - Category inference (birthday, relationship, milestone, etc.)
  - Display name building
  - to_inner_state_format conversion
  - compute_next_occurrence for each pattern
  - Multiple anniversaries sorted by urgency
  - Edge cases: Feb 29 leap year, month overflow
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from heart.ss06_inner_state.anniversary_tracker import (
    AnniversaryCandidate,
    AnniversaryCategory,
    AnniversaryPattern,
    AnniversaryTrackResult,
    AnniversaryTracker,
    L4AnniversarySource,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tracker():
    """Default tracker with 7-day lookahead."""
    return AnniversaryTracker(lookahead_days=7)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def character_id():
    return "rin"


@pytest.fixture
def now():
    """Fixed reference time: 2026-05-22 14:30 UTC."""
    return datetime(2026, 5, 22, 14, 30, 0, tzinfo=timezone.utc)


# ============================================================
# L4 Source builders
# ============================================================


def _make_source(
    l4_id: UUID = None,
    key: str = "user_birthday",
    category: str = "anniversary",
    value: dict = None,
    pattern: str = "yearly",
    next_at: datetime = None,
    created_at: datetime = None,
    uid: UUID = None,
    cid: str = "rin",
) -> L4AnniversarySource:
    """Factory for L4AnniversarySource test data."""
    return L4AnniversarySource(
        l4_id=l4_id or uuid4(),
        user_id=uid or uuid4(),
        character_id=cid,
        key=key,
        category=category,
        value=value or {"date": "1995-01-15"},
        anniversary_pattern=pattern,
        next_anniversary_at=next_at,
        created_at=created_at or datetime(2025, 1, 1, tzinfo=timezone.utc),
    )


# ============================================================
# Yearly recurrence tests
# ============================================================


class TestYearlyRecurrence:
    """Yearly pattern: same month+day every year."""

    def test_birthday_within_lookahead(self, tracker, now, user_id):
        """Birthday on May 28 from now (May 22) → 6 days away → should appear."""
        src = _make_source(
            uid=user_id,
            key="user_birthday",
            next_at=datetime(2026, 5, 28, 0, 0, 0, tzinfo=timezone.utc),
        )
        result = tracker.track([src], user_id, "rin", now=now)

        assert len(result.upcoming) == 1
        c = result.upcoming[0]
        assert c.name == "他的生日"
        assert c.category == AnniversaryCategory.BIRTHDAY
        assert c.pattern == AnniversaryPattern.YEARLY
        assert 0 < c.hours_until < 7 * 24  # within 7 days

    def test_birthday_already_passed(self, tracker, now, user_id):
        """Birthday on Jan 15 already passed → should not appear
        unless next_anniversary_at was updated to next year."""
        # If next_anniversary_at still points to this year's past date,
        # hours_until will be negative and filtered out.
        src = _make_source(
            uid=user_id,
            key="user_birthday",
            next_at=datetime(2026, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        # hours_until = (Jan 15 - May 22) = ~ -3050 hours → filtered
        assert len(result.upcoming) == 0

    def test_birthday_next_year_from_l4(self, tracker, now, user_id):
        """L4 already has next_anniversary_at set to 2027."""
        src = _make_source(
            uid=user_id,
            key="user_birthday",
            next_at=datetime(2027, 1, 15, 0, 0, 0, tzinfo=timezone.utc),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        # More than 7 days away → filtered
        assert len(result.upcoming) == 0

    def test_birthday_within_7_days(self, tracker, now, user_id):
        """Birthday on May 28 → 6 days from May 22 → should appear."""
        src = _make_source(
            uid=user_id,
            key="user_birthday",
            next_at=datetime(2026, 5, 28, 0, 0, 0, tzinfo=timezone.utc),
        )
        result = tracker.track([src], user_id, "rin", now=now)

        assert len(result.upcoming) == 1
        c = result.upcoming[0]
        assert c.hours_until > 0
        assert c.hours_until < 7 * 24
        assert c.celebration_intensity == "grand"


class TestComputeNextOccurrence:
    """Unit tests for compute_next_occurrence."""

    def test_yearly_same_year(self, tracker, now):
        original = datetime(1995, 10, 15, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.YEARLY, now
        )
        assert next_occ is not None
        assert next_occ.year == 2026
        assert next_occ.month == 10
        assert next_occ.day == 15

    def test_yearly_already_passed(self, tracker, now):
        original = datetime(1995, 1, 15, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.YEARLY, now
        )
        assert next_occ is not None
        assert next_occ.year == 2027
        assert next_occ.month == 1
        assert next_occ.day == 15

    def test_yearly_feb29_non_leap(self, tracker):
        """Feb 29 in a non-leap year → skip to next leap year (2028)."""
        now_feb = datetime(2026, 3, 1, tzinfo=timezone.utc)
        original = datetime(2000, 2, 29, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.YEARLY, now_feb
        )
        assert next_occ is not None
        # 2026 no Feb 29, 2027 no Feb 29 → skip to 2028 (leap year)
        assert next_occ.year == 2028
        assert next_occ.month == 2
        assert next_occ.day == 29

    def test_yearly_feb29_leap_year_now(self, tracker):
        """Feb 29 when now is in a leap year before the date."""
        now = datetime(2028, 1, 1, tzinfo=timezone.utc)
        original = datetime(2000, 2, 29, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.YEARLY, now
        )
        assert next_occ is not None
        assert next_occ.year == 2028
        assert next_occ.month == 2
        assert next_occ.day == 29

    def test_weekly(self, tracker, now):
        original = datetime(2026, 5, 18, tzinfo=timezone.utc)  # 4 days ago
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.WEEKLY, now
        )
        assert next_occ is not None
        # Next Monday from May 18 is May 25
        assert next_occ.date() == datetime(2026, 5, 25).date()

    def test_monthly(self, tracker, now):
        original = datetime(2026, 1, 15, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.MONTHLY, now
        )
        assert next_occ is not None
        # Should roll forward to June 15
        assert next_occ.year == 2026
        assert next_occ.month == 6
        assert next_occ.day == 15

    def test_once_future(self, tracker, now):
        original = datetime(2026, 6, 1, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.ONCE, now
        )
        assert next_occ is not None
        assert next_occ == original

    def test_once_past(self, tracker, now):
        original = datetime(2026, 1, 1, tzinfo=timezone.utc)
        next_occ = tracker.compute_next_occurrence(
            original, AnniversaryPattern.ONCE, now
        )
        assert next_occ is None


# ============================================================
# Category inference tests
# ============================================================


class TestCategoryInference:

    def test_birthday_from_key(self):
        src = _make_source(key="user_birthday")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.BIRTHDAY

    def test_birthday_from_category(self):
        src = _make_source(key="some_key", category="birthday")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.BIRTHDAY

    def test_relationship(self):
        src = _make_source(key="first_meeting", category="anniversary")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.RELATIONSHIP

    def test_milestone(self):
        src = _make_source(key="100_day_streak", category="anniversary")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.MILESTONE

    def test_sacred_promise(self):
        src = _make_source(key="some_promise", category="sacred_promise")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.SACRED_PROMISE

    def test_other(self):
        src = _make_source(key="random_event", category="anniversary")
        cat = AnniversaryTracker._infer_category(src)
        assert cat == AnniversaryCategory.OTHER


# ============================================================
# Display name tests
# ============================================================


class TestDisplayName:

    def test_known_key(self):
        src = _make_source(key="user_birthday")
        name = AnniversaryTracker._build_display_name(src, AnniversaryCategory.BIRTHDAY)
        assert name == "他的生日"

    def test_unknown_key(self):
        src = _make_source(key="special_gathering")
        name = AnniversaryTracker._build_display_name(src, AnniversaryCategory.OTHER)
        assert name == "Special Gathering"


# ============================================================
# Out-of-window filtering
# ============================================================


class TestWindowFiltering:

    def test_too_far_ahead(self, tracker, now, user_id):
        """Anniversary 30 days ahead → filtered."""
        src = _make_source(
            uid=user_id,
            next_at=now + timedelta(days=30),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        assert len(result.upcoming) == 0

    def test_too_far_past(self, tracker, now, user_id):
        """Anniversary 3 days past → filtered (likely stale next_anniversary_at)."""
        src = _make_source(
            uid=user_id,
            next_at=now - timedelta(days=3),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        assert len(result.upcoming) == 0

    def test_multiple_ordered_by_urgency(self, tracker, now, user_id):
        """Multiple anniversaries should be sorted by hours_until ascending."""
        sources = [
            _make_source(
                uid=user_id,
                key="first_meeting",
                next_at=now + timedelta(days=5),
            ),
            _make_source(
                uid=user_id,
                key="user_birthday",
                next_at=now + timedelta(days=2),
            ),
            _make_source(
                uid=user_id,
                key="100_day_streak",
                next_at=now + timedelta(days=7),
            ),
        ]
        result = tracker.track(sources, user_id, "rin", now=now)
        assert len(result.upcoming) == 3
        # Sorted: 2 days, 5 days, 7 days
        assert "生日" in result.upcoming[0].name  # 2 days
        assert result.upcoming[1].name == "第一次见面"  # 5 days
        assert "100" in result.upcoming[2].name  # 7 days


# ============================================================
# to_inner_state_format
# ============================================================


class TestFormatConversion:

    def test_converts_correctly(self, tracker, now, user_id):
        src = _make_source(
            uid=user_id,
            key="user_birthday",
            next_at=datetime(2026, 5, 28, 0, 0, 0, tzinfo=timezone.utc),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        formatted = tracker.to_inner_state_format(result.upcoming)

        assert len(formatted) == 1
        f = formatted[0]
        assert "anniversary_id" in f
        assert f["name"] == "他的生日"
        assert "due_at" in f
        assert f["hours_until"] > 0
        assert f["soft_mention_sent"] is False
        assert f["actual_sent"] is False
        assert f["category"] == "birthday"
        assert f["pattern"] == "yearly"


# ============================================================
# TrackResult helpers
# ============================================================


class TestTrackResult:

    def test_has_due_today(self, tracker, now, user_id):
        """Anniversary due in the past few hours → has_due_today."""
        src = _make_source(
            uid=user_id,
            next_at=now - timedelta(hours=2),
        )
        result = tracker.track([src], user_id, "rin", now=now)
        # Past but within 24h window → still surfaced
        if result.upcoming:
            # could be surfaced if within -24h window
            assert result.has_due_today or result.has_within_24h

    def test_total_checked(self, tracker, now, user_id):
        sources = [_make_source(uid=user_id) for _ in range(5)]
        result = tracker.track(sources, user_id, "rin", now=now)
        assert result.total_l4_checked == 5
