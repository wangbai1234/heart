"""
Unit tests for Concerns Tracker (SS06 §5.5, §6.6).

Covers:
  - Concern extraction with urgency formula
  - Expiry: concerns and thoughts expire correctly
  - Top-3 surfacing with cooldown (has_been_addressed → 24h)
  - High-emotional thoughts → 30-day expiry
  - Cap at MAX_CONCERNS / MAX_UNFINISHED
  - cleanup_expired removal
  - mark_addressed / reference_thought mutations
"""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from heart.ss06_inner_state.concerns_tracker import (
    ConcernSource,
    ConcernsTracker,
    UnfinishedThought,
    UserConcern,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def tracker():
    return ConcernsTracker()


@pytest.fixture
def now():
    return datetime(2026, 5, 21, 12, 0, 0)


@pytest.fixture
def sample_sources(now):
    """5 concern sources matching §5.5 types."""
    return [
        ConcernSource(
            source_type="unresolved_distress",
            concern_text="他昨天加班到很晚",
            valence_peak=-0.7,
            created_at=now - timedelta(hours=12),
            days_since_addressed=0.0,
        ),
        ConcernSource(
            source_type="upcoming_event",
            concern_text="明天有重要的考试",
            valence_peak=-0.4,
            created_at=now - timedelta(hours=6),
            days_since_addressed=0.0,
        ),
        ConcernSource(
            source_type="health_mention",
            concern_text="他说有点头疼",
            valence_peak=-0.3,
            created_at=now - timedelta(hours=3),
            days_since_addressed=0.0,
        ),
        ConcernSource(
            source_type="promise_pending",
            concern_text="答应要一起去看电影",
            valence_peak=0.5,
            created_at=now - timedelta(days=2),
            days_since_addressed=1.0,
        ),
        ConcernSource(
            source_type="anniversary_imminent",
            concern_text="明天是认识的第100天",
            valence_peak=0.8,
            created_at=now - timedelta(hours=24),
            days_since_addressed=0.0,
        ),
    ]


# ============================================================
# Concern Extraction
# ============================================================


class TestConcernExtraction:
    """Concern extraction from raw sources."""

    def test_extracts_all_sources(self, tracker, sample_sources, now):
        """All 5 sources produce concerns."""
        concerns = tracker.extract_concerns(sample_sources, now)
        assert len(concerns) == 5

    def test_sorted_by_urgency(self, tracker, sample_sources, now):
        """Concerns are sorted by urgency descending."""
        concerns = tracker.extract_concerns(sample_sources, now)
        for i in range(len(concerns) - 1):
            assert concerns[i].urgency >= concerns[i + 1].urgency

    def test_urgency_uses_formula(self, tracker, now):
        """Urgency follows spec formula: |valence| × recency × (1 - addressed/7)."""
        src = ConcernSource(
            source_type="test",
            concern_text="test concern",
            valence_peak=-0.5,
            created_at=now,
            days_since_addressed=0.0,
        )
        concerns = tracker.extract_concerns([src], now)
        assert len(concerns) == 1
        # intensity=0.5, recency≈1.0, addressed_factor=1.0 → urgency ≈ 0.5
        assert concerns[0].urgency == pytest.approx(0.5, abs=0.01)

    def test_urgency_decays_with_age(self, tracker, now):
        """Older concerns have lower urgency."""
        recent = ConcernSource(
            source_type="test", concern_text="recent",
            valence_peak=-0.5, created_at=now, days_since_addressed=0.0,
        )
        old = ConcernSource(
            source_type="test", concern_text="old",
            valence_peak=-0.5, created_at=now - timedelta(days=7),
            days_since_addressed=0.0,
        )
        concerns = tracker.extract_concerns([recent, old], now)
        assert concerns[0].urgency > concerns[1].urgency  # recent first

    def test_urgency_decays_when_addressed(self, tracker, now):
        """Addressed concerns have lower urgency."""
        not_addressed = ConcernSource(
            source_type="test", concern_text="fresh",
            valence_peak=-0.5, created_at=now, days_since_addressed=0.0,
        )
        addressed = ConcernSource(
            source_type="test", concern_text="addressed",
            valence_peak=-0.5, created_at=now, days_since_addressed=3.5,
        )
        concerns = tracker.extract_concerns([not_addressed, addressed], now)
        # fresh should rank higher
        assert concerns[0].urgency > concerns[1].urgency

    def test_respects_max_concerns(self, tracker, now):
        """Capped at MAX_CONCERNS."""
        tracker.max_concerns = 3
        sources = [
            ConcernSource(source_type="test", concern_text=f"c{i}",
                          valence_peak=-0.5, created_at=now)
            for i in range(10)
        ]
        concerns = tracker.extract_concerns(sources, now)
        assert len(concerns) == 3

    def test_creates_valid_user_concern(self, tracker, sample_sources, now):
        """Extracted concern has all required fields."""
        concerns = tracker.extract_concerns(sample_sources, now)
        for c in concerns:
            assert c.concern_id is not None
            assert isinstance(c.concern_text, str)
            assert 0.0 <= c.urgency <= 1.0
            assert c.created_at is not None
            assert c.expiry_at > c.created_at
            assert c.has_been_addressed is False

    def test_empty_sources(self, tracker, now):
        """Empty source list returns empty list."""
        assert tracker.extract_concerns([], now) == []


# ============================================================
# Unfinished Thought Extraction
# ============================================================


class TestUnfinishedThoughtExtraction:
    """Unfinished thought extraction from recent turns."""

    def test_extracts_interrupted_turns(self, tracker, now):
        """Only interrupted turns become unfinished thoughts."""
        turns = [
            {
                "turn_id": uuid4(),
                "content": "我想和你说一件事...",
                "was_interrupted": True,
            },
            {
                "turn_id": uuid4(),
                "content": "今天天气真好",
                "was_interrupted": False,
            },
        ]
        thoughts = tracker.extract_unfinished_thoughts(turns, emotional_intensity=0.3, now=now)
        assert len(thoughts) == 1
        assert "我想和你说一件事" in thoughts[0].content

    def test_default_expiry_7_days(self, tracker, now):
        """Normal emotional intensity → 7 day expiry."""
        turns = [{"turn_id": uuid4(), "content": "test", "was_interrupted": True}]
        thoughts = tracker.extract_unfinished_thoughts(turns, emotional_intensity=0.3, now=now)
        expiry_delta = thoughts[0].expiry_at - now
        assert expiry_delta.days == 7

    def test_high_emotional_30_day_expiry(self, tracker, now):
        """|valence| > 0.7 → 30 day expiry (§6.6 机制 B)."""
        turns = [{"turn_id": uuid4(), "content": "deep thought", "was_interrupted": True}]
        thoughts = tracker.extract_unfinished_thoughts(
            turns, emotional_intensity=0.85, now=now,
        )
        expiry_delta = thoughts[0].expiry_at - now
        assert expiry_delta.days == 30

    def test_boundary_at_threshold(self, tracker, now):
        """Exactly at 0.7 → 7 days (not strictly greater)."""
        turns = [{"turn_id": uuid4(), "content": "borderline", "was_interrupted": True}]
        thoughts = tracker.extract_unfinished_thoughts(
            turns, emotional_intensity=0.7, now=now,
        )
        expiry_delta = thoughts[0].expiry_at - now
        assert expiry_delta.days == 7  # 0.7 is NOT > 0.7

    def test_respects_max_unfinished(self, tracker, now):
        """Capped at MAX_UNFINISHED (INV-I-6)."""
        tracker.max_unfinished = 3
        turns = [
            {"turn_id": uuid4(), "content": f"t{i}", "was_interrupted": True}
            for i in range(10)
        ]
        thoughts = tracker.extract_unfinished_thoughts(turns, now=now)
        assert len(thoughts) == 3

    def test_add_unfinished_thought(self, tracker, now):
        """add_unfinished_thought appends and caps."""
        existing = [
            UnfinishedThought(
                thought_id=uuid4(),
                content="old thought",
                from_turn_id=uuid4(),
                created_at=now - timedelta(days=1),
            )
        ]
        updated = tracker.add_unfinished_thought(
            existing, "new thought", uuid4(), emotional_intensity=0.2, now=now,
        )
        assert len(updated) == 2
        assert updated[0].content == "new thought"  # most recent first

    def test_add_unfinished_respects_max(self, tracker, now):
        """add_unfinished caps at max."""
        tracker.max_unfinished = 2
        existing = [
            UnfinishedThought(thought_id=uuid4(), content="t1",
                              from_turn_id=uuid4(), created_at=now),
            UnfinishedThought(thought_id=uuid4(), content="t2",
                              from_turn_id=uuid4(), created_at=now),
        ]
        updated = tracker.add_unfinished_thought(
            existing, "new", uuid4(), now=now,
        )
        assert len(updated) == 2


# ============================================================
# Top-3 Surfacing
# ============================================================


class TestSurfacing:
    """Surface top-3 concerns/thoughts for current turn."""

    def test_surfaces_concerns_sorted(self, tracker, sample_sources, now):
        """Top concerns surfaced in priority order."""
        concerns = tracker.extract_concerns(sample_sources, now)
        top = tracker.surface_top_concerns(concerns, n=3, now=now)
        assert len(top) == 3

    def test_excludes_expired(self, tracker, now):
        """Expired concerns are not surfaced."""
        expired = UserConcern(
            concern_id=uuid4(),
            concern_text="expired",
            urgency=0.9,
            created_at=now - timedelta(days=10),
            expiry_at=now - timedelta(hours=1),
        )
        top = tracker.surface_top_concerns([expired], n=3, now=now)
        assert len(top) == 0

    def test_excludes_addressed_within_cooldown(self, tracker, now):
        """Addressed concerns within 24h cooldown are excluded (机制 C)."""
        addressed = UserConcern(
            concern_id=uuid4(),
            concern_text="addressed recently",
            urgency=0.9,
            created_at=now,
            expiry_at=now + timedelta(days=7),
            has_been_addressed=True,
            last_referenced_at=now - timedelta(hours=1),
        )
        top = tracker.surface_top_concerns([addressed], n=3, now=now)
        assert len(top) == 0

    def test_includes_addressed_after_cooldown(self, tracker, now):
        """Addressed concerns after 24h can be re-surfaced."""
        addressed = UserConcern(
            concern_id=uuid4(),
            concern_text="addressed long ago",
            urgency=0.9,
            created_at=now - timedelta(days=2),
            expiry_at=now + timedelta(days=7),
            has_been_addressed=True,
            last_referenced_at=now - timedelta(hours=25),
        )
        top = tracker.surface_top_concerns([addressed], n=3, now=now)
        assert len(top) == 1

    def test_includes_unfinished_thoughts(self, tracker, now):
        """Unfinished thoughts are surfaced alongside concerns."""
        concern = UserConcern(
            concern_id=uuid4(),
            concern_text="concern",
            urgency=0.5,
            created_at=now,
            expiry_at=now + timedelta(days=7),
        )
        thought = UnfinishedThought(
            thought_id=uuid4(),
            content="unfinished thought",
            from_turn_id=uuid4(),
            created_at=now,
            expiry_at=now + timedelta(days=7),
        )
        top = tracker.surface_top_concerns([concern], [thought], n=3, now=now)
        assert len(top) == 2

    def test_empty_inputs(self, tracker, now):
        """Empty inputs return empty list."""
        assert tracker.surface_top_concerns([], [], now=now) == []


# ============================================================
# Cleanup
# ============================================================


class TestCleanup:
    """Expiry cleanup (机制 B + 机制 C)."""

    def test_removes_expired_concerns(self, tracker, now):
        """Expired concerns are removed."""
        active = UserConcern(
            concern_id=uuid4(),
            concern_text="active",
            urgency=0.5,
            created_at=now,
            expiry_at=now + timedelta(days=7),
        )
        expired = UserConcern(
            concern_id=uuid4(),
            concern_text="expired",
            urgency=0.5,
            created_at=now - timedelta(days=10),
            expiry_at=now - timedelta(hours=1),
        )
        cleaned_c, cleaned_t = tracker.cleanup_expired([active, expired], now=now)
        assert len(cleaned_c) == 1
        assert cleaned_c[0].concern_text == "active"

    def test_removes_expired_thoughts(self, tracker, now):
        """Expired thoughts are removed."""
        active = UnfinishedThought(
            thought_id=uuid4(),
            content="active",
            from_turn_id=uuid4(),
            created_at=now,
            expiry_at=now + timedelta(days=7),
        )
        expired = UnfinishedThought(
            thought_id=uuid4(),
            content="expired",
            from_turn_id=uuid4(),
            created_at=now - timedelta(days=10),
            expiry_at=now - timedelta(hours=1),
        )
        _, cleaned_t = tracker.cleanup_expired([], [active, expired], now=now)
        assert len(cleaned_t) == 1
        assert cleaned_t[0].content == "active"

    def test_none_thoughts_handled(self, tracker, now):
        """None for unfinished_thoughts is handled gracefully."""
        _, cleaned_t = tracker.cleanup_expired([], None, now=now)
        assert cleaned_t == []


# ============================================================
# Mutations
# ============================================================


class TestMutations:
    """mark_addressed and reference_thought."""

    def test_mark_addressed(self, tracker, now):
        """mark_addressed sets flags correctly."""
        concern = UserConcern(
            concern_id=uuid4(),
            concern_text="test",
            urgency=0.5,
            created_at=now,
        )
        updated = tracker.mark_addressed(concern, now)
        assert updated.has_been_addressed is True
        assert updated.last_referenced_at == now

    def test_reference_thought(self, tracker):
        """reference_thought increments counter."""
        thought = UnfinishedThought(
            thought_id=uuid4(),
            content="test",
            from_turn_id=uuid4(),
        )
        assert thought.reference_count == 0
        updated = tracker.reference_thought(thought)
        assert updated.reference_count == 1
        updated = tracker.reference_thought(updated)
        assert updated.reference_count == 2


# ============================================================
# Data Class Defaults
# ============================================================


class TestDataClassDefaults:
    """Verify default values on data classes."""

    def test_user_concern_defaults(self):
        """UserConcern has sensible defaults."""
        c = UserConcern(concern_id=uuid4(), concern_text="test", urgency=0.5)
        assert c.source_memory_ids == []
        assert c.created_at is not None
        assert c.expiry_at > c.created_at
        assert c.has_been_addressed is False
        assert c.last_referenced_at is None

    def test_unfinished_thought_defaults(self):
        """UnfinishedThought has sensible defaults."""
        t = UnfinishedThought(
            thought_id=uuid4(), content="test", from_turn_id=uuid4(),
        )
        assert t.reference_count == 0
        assert t.created_at is not None
        assert t.expiry_at > t.created_at


# ============================================================
# Urgency Formula
# ============================================================


class TestUrgencyFormula:
    """Verification of the urgency formula from §5.5."""

    def test_fresh_max_intensity(self, tracker, now):
        """Fresh concern with |valence|=1.0 → urgency ~1.0."""
        src = ConcernSource(
            source_type="test", concern_text="max",
            valence_peak=-1.0, created_at=now, days_since_addressed=0.0,
        )
        concerns = tracker.extract_concerns([src], now)
        assert concerns[0].urgency == pytest.approx(1.0, abs=0.01)

    def test_old_converges_to_zero(self, tracker, now):
        """Very old concern → urgency → 0."""
        src = ConcernSource(
            source_type="test", concern_text="ancient",
            valence_peak=-1.0,
            created_at=now - timedelta(days=30),
            days_since_addressed=0.0,
        )
        concerns = tracker.extract_concerns([src], now)
        assert concerns[0].urgency < 0.01

    def test_fully_addressed_min_urgency(self, tracker, now):
        """Concern addressed 7+ days ago → addressed_factor → 0."""
        src = ConcernSource(
            source_type="test", concern_text="done",
            valence_peak=-0.5, created_at=now, days_since_addressed=7.0,
        )
        concerns = tracker.extract_concerns([src], now)
        assert concerns[0].urgency == pytest.approx(0.0, abs=0.01)

    def test_urgency_clamped_0_to_1(self, tracker, now):
        """Urgency is always in [0, 1]."""
        extreme_cases = [
            ConcernSource(source_type="t", concern_text="t", valence_peak=10.0,
                          created_at=now, days_since_addressed=0.0),
            ConcernSource(source_type="t", concern_text="t", valence_peak=-10.0,
                          created_at=now - timedelta(days=100), days_since_addressed=100.0),
        ]
        concerns = tracker.extract_concerns(extreme_cases, now)
        for c in concerns:
            assert 0.0 <= c.urgency <= 1.0
