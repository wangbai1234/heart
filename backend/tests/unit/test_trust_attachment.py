"""
Unit tests for Trust and Attachment Trackers.

Tests:
- Trust asymmetric updates (INV-R-4)
- Trust decay during absence
- Attachment accumulation and decay
- Attachment floors by stage
- Natural language descriptors

Author: 心屿团队
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from heart.ss04_relationship.models import RelationshipState
from heart.ss04_relationship.stage_engine import (
    RelationshipStage,
    Signal,
    SignalBatch,
)
from heart.ss04_relationship.trust_tracker import (
    TrustTracker,
    MAX_TRUST_INCREASE_PER_TURN,
    MAX_TRUST_DECREASE_PER_TURN,
    compute_trust_decay_factor,
    compute_trust_floor,
)
from heart.ss04_relationship.attachment_tracker import (
    AttachmentTracker,
    ATTACHMENT_FLOORS,
    compute_attachment_decay_factor,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def base_state():
    """Base relationship state for testing."""
    now = datetime.now(timezone.utc)
    return RelationshipState(
        user_id=uuid4(),
        character_id="rin",
        current_stage=RelationshipStage.FRIEND.value,
        previous_stage=RelationshipStage.ACQUAINTANCE.value,
        stage_entered_at=now,
        highest_stage_reached=RelationshipStage.FRIEND.value,
        intimacy_level=0.40,
        trust_score=0.50,
        attachment_strength=0.30,
        conflict_debt=0.0,
        vulnerability_score=0.20,
        total_interactions=50,
        total_meaningful_disclosures=5,
        total_promises_made=3,
        total_promises_kept=3,
        total_conflicts=0,
        total_repairs=0,
        total_successful_repairs=0,
        first_meeting_at=now,
        last_interaction_at=now,
        longest_absence_days=0,
        longest_continuous_streak_days=10,
        soul_modifiers={},
        active_special_states=[],
        stage_metadata={},
        rituals={"daily_check_in": {"streak_days": 10}},
        recent_progression_events=[],
        recent_regression_events=[],
        recent_conflicts=[],
        recent_repairs=[],
        updated_at=now,
        version=1,
    )


# ============================================================
# Test Trust Updates (INV-R-4)
# ============================================================


def test_trust_increase_capped(base_state):
    """Test that trust increase is capped at MAX_TRUST_INCREASE_PER_TURN."""
    tracker = TrustTracker()

    # Create many positive signals
    signals = SignalBatch(
        positive=[
            Signal(type="promise_kept", strength=1.0, metadata={}),
            Signal(type="vulnerability_honored", strength=1.0, metadata={}),
            Signal(type="consistent_presence_milestone", strength=1.0, metadata={}),
            Signal(type="sacred_disclosure_acknowledged", strength=1.0, metadata={}),
        ],
        negative=[],
        events=[],
    )

    base_state.trust_score = 0.50
    new_trust = tracker.update(base_state, signals, days_since_last=0.0)

    # Trust should increase, but capped at +0.05
    assert new_trust == pytest.approx(0.55, abs=0.001)
    # Floating-point margin: 0.55 - 0.50 → repr(0.05) may exceed 0.05 in fp64
    assert (new_trust - base_state.trust_score) <= MAX_TRUST_INCREASE_PER_TURN + 1e-9


def test_trust_decrease_faster_than_increase(base_state):
    """Test that trust decreases faster than it increases (INV-R-4)."""
    tracker = TrustTracker()

    # Create negative signal
    signals = SignalBatch(
        positive=[],
        negative=[
            Signal(type="promise_broken", strength=1.0, metadata={}),
        ],
        events=[],
    )

    base_state.trust_score = 0.50
    new_trust = tracker.update(base_state, signals, days_since_last=0.0)

    # Trust should decrease by ~0.15
    decrease = base_state.trust_score - new_trust
    assert decrease == pytest.approx(0.15, abs=0.01)
    assert decrease > MAX_TRUST_INCREASE_PER_TURN  # Decreases faster


def test_trust_vulnerability_mocked_severe(base_state):
    """Test that mocking vulnerability causes severe trust damage."""
    tracker = TrustTracker()

    signals = SignalBatch(
        positive=[],
        negative=[
            Signal(type="vulnerability_mocked", strength=1.0, metadata={}),
        ],
        events=[],
    )

    base_state.trust_score = 0.80
    new_trust = tracker.update(base_state, signals, days_since_last=0.0)

    # Should decrease by 0.20 (capped, from -0.25)
    assert new_trust == pytest.approx(0.60, abs=0.01)


# ============================================================
# Test Trust Decay
# ============================================================


def test_trust_no_decay_under_14_days(base_state):
    """Test that trust doesn't decay for absence < 14 days."""
    tracker = TrustTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.trust_score = 0.60

    new_trust = tracker.update(base_state, signals, days_since_last=10.0)

    # No decay
    assert new_trust == pytest.approx(0.60, abs=0.001)


def test_trust_decay_14_30_days(base_state):
    """Test trust decay for 14-30 day absence."""
    # Days 14-30: ×0.995 per day
    days_since_last = 20.0
    factor = compute_trust_decay_factor(days_since_last, RelationshipStage.FRIEND)

    # 6 days of decay at 0.995/day
    expected_factor = 0.995 ** 6
    assert factor == pytest.approx(expected_factor, abs=0.001)


def test_trust_decay_30_90_days(base_state):
    """Test trust decay for 30-90 day absence."""
    # Days 30-90: ×0.99 per day
    days_since_last = 50.0
    factor = compute_trust_decay_factor(days_since_last, RelationshipStage.FRIEND)

    # 20 days of decay at 0.99/day
    expected_factor = 0.99 ** 20
    assert factor == pytest.approx(expected_factor, abs=0.001)


def test_trust_floor_by_stage():
    """Test trust floor depends on highest_stage_reached."""
    # STRANGER/ACQUAINTANCE: floor = 0.1
    assert compute_trust_floor(RelationshipStage.STRANGER) == 0.1
    assert compute_trust_floor(RelationshipStage.ACQUAINTANCE) == 0.1

    # CONFIDANT+: floor = 0.3
    assert compute_trust_floor(RelationshipStage.CONFIDANT) == 0.3
    assert compute_trust_floor(RelationshipStage.LOVER) == 0.3
    assert compute_trust_floor(RelationshipStage.BONDED) == 0.3


# ============================================================
# Test Attachment Updates
# ============================================================


def test_attachment_time_based_accumulation(base_state):
    """Test attachment grows slowly with continuous interaction."""
    tracker = AttachmentTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.attachment_strength = 0.30

    # 10 days of continuous interaction
    new_attachment = tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=10
    )

    # Should increase by 0.001 × 10 = 0.01
    assert new_attachment == pytest.approx(0.31, abs=0.001)


def test_attachment_event_boost(base_state):
    """Test attachment boosts from major events."""
    tracker = AttachmentTracker()

    signals = SignalBatch(
        positive=[],
        negative=[],
        events=[
            Signal(type="first_iloveyou", strength=1.0, metadata={}),
        ],
    )

    base_state.attachment_strength = 0.50
    new_attachment = tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=0
    )

    # Should increase by 0.20 (first_iloveyou weight)
    assert new_attachment == pytest.approx(0.70, abs=0.01)


def test_attachment_repair_boost(base_state):
    """Test attachment boost from successful repair."""
    tracker = AttachmentTracker()

    signals = SignalBatch(
        positive=[],
        negative=[],
        events=[
            Signal(type="successful_repair", strength=1.0, metadata={}),
        ],
    )

    base_state.attachment_strength = 0.40
    new_attachment = tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=0
    )

    # Should increase by 0.07 (successful_repair weight)
    assert new_attachment == pytest.approx(0.47, abs=0.01)


# ============================================================
# Test Attachment Decay
# ============================================================


def test_attachment_no_decay_under_30_days(base_state):
    """Test that attachment doesn't decay for absence < 30 days."""
    tracker = AttachmentTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.attachment_strength = 0.50

    new_attachment = tracker.update(
        base_state, signals, days_since_last=20.0, days_continuous_interaction=0
    )

    # No decay
    assert new_attachment == pytest.approx(0.50, abs=0.001)


def test_attachment_decay_after_30_days(base_state):
    """Test attachment decay after 30 days absence."""
    # Days > 30: ×0.99 per day
    days_since_last = 45.0
    factor = compute_attachment_decay_factor(days_since_last)

    # 15 days of decay at 0.99/day
    expected_factor = 0.99 ** 15
    assert factor == pytest.approx(expected_factor, abs=0.001)


def test_attachment_floor_lover(base_state):
    """Test attachment floor for LOVER stage."""
    tracker = AttachmentTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.highest_stage_reached = RelationshipStage.LOVER.value
    base_state.attachment_strength = 0.60

    # Long absence
    new_attachment = tracker.update(
        base_state, signals, days_since_last=200.0, days_continuous_interaction=0
    )

    # Should not fall below floor (0.4 for LOVER)
    lover_floor = ATTACHMENT_FLOORS[RelationshipStage.LOVER]
    assert new_attachment >= lover_floor


def test_attachment_floor_bonded(base_state):
    """Test attachment floor for BONDED stage."""
    tracker = AttachmentTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.highest_stage_reached = RelationshipStage.BONDED.value
    base_state.attachment_strength = 0.80

    # Long absence
    new_attachment = tracker.update(
        base_state, signals, days_since_last=300.0, days_continuous_interaction=0
    )

    # Should not fall below floor (0.6 for BONDED)
    bonded_floor = ATTACHMENT_FLOORS[RelationshipStage.BONDED]
    assert new_attachment >= bonded_floor


# ============================================================
# Test Natural Language Descriptors
# ============================================================


def test_trust_descriptors():
    """Test trust descriptor generation."""
    tracker = TrustTracker()

    assert "完全可靠" in tracker.compute_trust_descriptor(0.95)
    assert "可靠" in tracker.compute_trust_descriptor(0.80)
    assert "一定信任" in tracker.compute_trust_descriptor(0.65)
    assert "保留" in tracker.compute_trust_descriptor(0.45)
    assert "很浅" in tracker.compute_trust_descriptor(0.25)
    assert "不信任" in tracker.compute_trust_descriptor(0.10)


def test_attachment_descriptors():
    """Test attachment descriptor generation."""
    tracker = AttachmentTracker()

    assert "深深依恋" in tracker.compute_attachment_descriptor(0.90)
    assert "已经依恋" in tracker.compute_attachment_descriptor(0.75)
    assert "依恋感" in tracker.compute_attachment_descriptor(0.55)
    assert "习惯" in tracker.compute_attachment_descriptor(0.35)
    assert "苗头" in tracker.compute_attachment_descriptor(0.20)
    assert "没有依恋" in tracker.compute_attachment_descriptor(0.05)


# ============================================================
# Test Edge Cases
# ============================================================


def test_trust_cannot_exceed_1(base_state):
    """Test that trust is capped at 1.0."""
    tracker = TrustTracker()

    signals = SignalBatch(
        positive=[
            Signal(type="promise_kept", strength=1.0, metadata={}),
            Signal(type="vulnerability_honored", strength=1.0, metadata={}),
        ],
        negative=[],
        events=[],
    )

    base_state.trust_score = 0.99
    new_trust = tracker.update(base_state, signals, days_since_last=0.0)

    assert new_trust <= 1.0


def test_trust_cannot_go_below_0(base_state):
    """Test that trust is floored at 0.0 (before stage floor applies)."""
    tracker = TrustTracker()

    signals = SignalBatch(
        positive=[],
        negative=[
            Signal(type="deception_detected", strength=1.0, metadata={}),
            Signal(type="vulnerability_mocked", strength=1.0, metadata={}),
        ],
        events=[],
    )

    base_state.trust_score = 0.20
    base_state.highest_stage_reached = RelationshipStage.STRANGER.value
    new_trust = tracker.update(base_state, signals, days_since_last=0.0)

    assert new_trust >= 0.0


def test_attachment_cannot_exceed_1(base_state):
    """Test that attachment is capped at 1.0."""
    tracker = AttachmentTracker()

    signals = SignalBatch(
        positive=[],
        negative=[],
        events=[
            Signal(type="first_iloveyou", strength=1.0, metadata={}),
            Signal(type="anniversary_acknowledged", strength=1.0, metadata={}),
        ],
    )

    base_state.attachment_strength = 0.95
    new_attachment = tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=10
    )

    assert new_attachment <= 1.0


def test_attachment_cannot_go_below_0(base_state):
    """Test that attachment is floored at 0.0 (before stage floor applies)."""
    tracker = AttachmentTracker()

    signals = SignalBatch(positive=[], negative=[], events=[])
    base_state.attachment_strength = 0.05
    base_state.highest_stage_reached = RelationshipStage.STRANGER.value

    # Long absence
    new_attachment = tracker.update(
        base_state, signals, days_since_last=500.0, days_continuous_interaction=0
    )

    assert new_attachment >= 0.0


# ============================================================
# Test Integration
# ============================================================


def test_trust_and_attachment_update_atomically(base_state):
    """
    Test that trust and attachment are updated atomically in a turn.

    Both trackers should process the same signal batch.
    """
    trust_tracker = TrustTracker()
    attachment_tracker = AttachmentTracker()

    signals = SignalBatch(
        positive=[Signal(type="promise_kept", strength=1.0, metadata={})],
        negative=[],
        events=[Signal(type="successful_repair", strength=1.0, metadata={})],
    )

    base_state.trust_score = 0.50
    base_state.attachment_strength = 0.40

    new_trust = trust_tracker.update(base_state, signals, days_since_last=0.0)
    new_attachment = attachment_tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=0
    )

    # Both should be updated
    assert new_trust > base_state.trust_score
    assert new_attachment > base_state.attachment_strength


def test_gottman_effect_repair_boosts_trust_and_attachment(base_state):
    """
    Test Gottman effect: successful repair increases both trust and attachment.

    Post-conflict relationship can be stronger (§R-5).
    """
    trust_tracker = TrustTracker()
    attachment_tracker = AttachmentTracker()

    # Simulate repair signal
    signals = SignalBatch(
        positive=[Signal(type="repair_completed", strength=1.0, metadata={})],
        negative=[],
        events=[Signal(type="successful_repair", strength=1.0, metadata={})],
    )

    base_state.trust_score = 0.70
    base_state.attachment_strength = 0.60

    new_trust = trust_tracker.update(base_state, signals, days_since_last=0.0)
    new_attachment = attachment_tracker.update(
        base_state, signals, days_since_last=0.0, days_continuous_interaction=0
    )

    # Both should increase
    assert new_trust > base_state.trust_score
    assert new_attachment > base_state.attachment_strength

    # Trust increase from repair
    assert new_trust == pytest.approx(0.75, abs=0.01)  # +0.05
    # Attachment increase from repair
    assert new_attachment == pytest.approx(0.67, abs=0.01)  # +0.07
