"""
Unit tests for Resonance Tracker (SS01 §3.2 + §5.2).

Covers design requirements:
- Track trigger events with weights
- Enforce daily caps per trigger
- Apply decay for inactive users (>30 days)
- Apply reunion bonus (30-60 days)
- Resonance score clamped to [0, 1]

Author: 心屿团队
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from heart.ss01_soul.resonance_tracker import (
    ResonanceTracker,
    ResonanceStateSnapshot,
    ResonanceEvent,
    ResonanceTrackResult,
    SoulActivationStateService,
)
from heart.ss01_soul.registry import SoulRegistry


# ============================================================
# Mock State Service
# ============================================================

class MockStateService:
    """Mock SoulActivationStateService for testing."""

    def __init__(self):
        self._states: dict[tuple, ResonanceStateSnapshot] = {}
        self._events: list[tuple] = []  # (user_id, character_id, event)

    def get_resonance_state(
        self,
        user_id,
        character_id,
    ) -> ResonanceStateSnapshot:
        key = (user_id, character_id)
        if key not in self._states:
            # New user - initialize with 0.0 score
            self._states[key] = ResonanceStateSnapshot(
                resonance_score=0.0,
                last_interaction_at=None,
                resonance_history=(),
            )
        return self._states[key]

    def write_resonance_event(
        self,
        user_id,
        character_id,
        event: ResonanceEvent,
    ) -> None:
        key = (user_id, character_id)
        current_state = self.get_resonance_state(user_id, character_id)

        # Update state with new event
        new_history = current_state.resonance_history + (event,)
        self._states[key] = ResonanceStateSnapshot(
            resonance_score=event.resulting_score,
            last_interaction_at=event.created_at,
            resonance_history=new_history,
        )
        self._events.append((user_id, character_id, event))

    def set_state(
        self,
        user_id,
        character_id,
        state: ResonanceStateSnapshot,
    ):
        """Test helper to set state directly."""
        self._states[(user_id, character_id)] = state


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_state_service():
    return MockStateService()


@pytest.fixture
def tracker(mock_state_service):
    return ResonanceTracker(state_service=mock_state_service)


@pytest.fixture
def user_id():
    return uuid4()


# ============================================================
# Basic Trigger Tests
# ============================================================

class TestBasicTrigger:

    def test_track_valid_trigger(self, tracker, mock_state_service, user_id):
        # Rin has trigger: "用户主动询问凛的过去/内心/感受" with weight 0.15
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=5,
        )

        assert result.reason == "triggered"
        assert result.event is not None
        assert result.event.weight_applied == 0.15
        assert result.new_score == 0.15
        assert result.event.trigger_cue == "用户主动询问凛的过去 / 内心 / 感受"

    def test_track_invalid_trigger(self, tracker, mock_state_service, user_id):
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="invalid_trigger_cue",
            turn_index=5,
        )

        assert result.reason == "invalid_trigger"
        assert result.event is None
        assert result.new_score == 0.0

    def test_score_accumulation(self, tracker, mock_state_service, user_id):
        # First trigger: +0.15
        tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=1,
        )

        # Second trigger: +0.12
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户精确引用凛说过的话（Memory Runtime 确认）",
            turn_index=2,
        )

        assert result.new_score == 0.27  # 0.15 + 0.12

    def test_score_capped_at_one(self, tracker, mock_state_service, user_id):
        # Set initial state to 0.95
        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.95,
                last_interaction_at=datetime.now(timezone.utc),
                resonance_history=(),
            ),
        )

        # Trigger +0.15 → should cap at 1.0
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=10,
        )

        assert result.new_score == 1.0


# ============================================================
# Daily Cap Tests
# ============================================================

class TestDailyCap:

    def test_enforce_daily_cap(self, tracker, mock_state_service, user_id):
        # Rin trigger "用户主动询问凛的过去/内心/感受" has max_per_day=2
        now = datetime.now(timezone.utc)

        # Event 1 - OK
        result1 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=1,
        )
        assert result1.reason == "triggered"

        # Event 2 - OK (at cap)
        result2 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=2,
        )
        assert result2.reason == "triggered"

        # Event 3 - CAPPED
        result3 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=3,
        )
        assert result3.reason == "capped"
        assert result3.event is None
        assert result3.new_score == result2.new_score  # No change

    def test_different_triggers_independent_caps(self, tracker, mock_state_service, user_id):
        # Trigger A: max 2/day
        tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=1,
        )
        tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=2,
        )

        # Trigger B should still work (independent cap)
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户精确引用凛说过的话（Memory Runtime 确认）",
            turn_index=3,
        )
        assert result.reason == "triggered"

    def test_cap_resets_next_day(self, tracker, mock_state_service, user_id):
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        # Create events from yesterday
        yesterday_event = ResonanceEvent(
            event_id=uuid4(),
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            weight_applied=0.15,
            resulting_score=0.15,
            turn_index=1,
            created_at=yesterday,
        )

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.15,
                last_interaction_at=yesterday,
                resonance_history=(yesterday_event, yesterday_event),  # 2 events yesterday
            ),
        )

        # Today's event should work (cap reset)
        result = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=10,
        )
        assert result.reason == "triggered"


# ============================================================
# Get Score Tests (Decay + Reunion Bonus)
# ============================================================

class TestGetScore:

    def test_get_score_no_decay(self, tracker, mock_state_service, user_id):
        # Recent interaction (< 30 days) - no decay
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=10)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.5,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)
        assert score == 0.5

    def test_get_score_with_decay(self, tracker, mock_state_service, user_id):
        # 65 days inactive = 5 weeks past decay start (outside reunion bonus range)
        # decay_rate = 0.95 ** 5 ≈ 0.774
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=65)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.6,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)
        expected = 0.6 * (0.95 ** 5)
        assert abs(score - expected) < 0.01

    def test_get_score_heavy_decay(self, tracker, mock_state_service, user_id):
        # 100 days inactive = 10 weeks past decay start
        # decay_rate = 0.95 ** 10 ≈ 0.599
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=100)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.8,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)
        expected = 0.8 * (0.95 ** 10)
        assert abs(score - expected) < 0.01

    def test_reunion_bonus_applied(self, tracker, mock_state_service, user_id):
        # 45 days inactive (within 30-60 range) → +0.05 bonus
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=45)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.4,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)

        # Apply decay first: weeks_inactive = (45-30)/7 ≈ 2.14
        # decay_rate = 0.95 ** 2.14 ≈ 0.899
        # decayed = 0.4 * 0.899 ≈ 0.3596
        # then +0.05 reunion bonus = 0.4096
        expected_decay = 0.4 * (0.95 ** ((45 - 30) / 7))
        expected = min(1.0, expected_decay + 0.05)
        assert abs(score - expected) < 0.01

    def test_reunion_bonus_not_applied_too_early(self, tracker, mock_state_service, user_id):
        # 25 days inactive (< 30) → no bonus
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=25)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.5,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)
        assert score == 0.5  # No decay, no bonus

    def test_reunion_bonus_not_applied_too_late(self, tracker, mock_state_service, user_id):
        # 70 days inactive (> 60) → no bonus
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=70)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.6,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)

        # Only decay, no bonus
        expected = 0.6 * (0.95 ** ((70 - 30) / 7))
        assert abs(score - expected) < 0.01

    def test_reunion_bonus_capped_at_one(self, tracker, mock_state_service, user_id):
        # Score 0.98, +0.05 bonus → should cap at 1.0
        now = datetime.now(timezone.utc)
        last_interaction = now - timedelta(days=40)

        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.98,
                last_interaction_at=last_interaction,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=now)
        assert score <= 1.0

    def test_new_user_no_decay(self, tracker, mock_state_service, user_id):
        # New user (last_interaction_at = None)
        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=0.0,
                last_interaction_at=None,
                resonance_history=(),
            ),
        )

        score = tracker.get_score(user_id, "rin")
        assert score == 0.0


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:

    def test_full_lifecycle(self, tracker, mock_state_service, user_id):
        """Test full lifecycle: trigger → accumulate → cap → decay."""

        # Day 1: First trigger
        result1 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=1,
        )
        assert result1.new_score == 0.15

        # Day 1: Second trigger (same)
        result2 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=2,
        )
        assert result2.new_score == 0.30

        # Day 1: Third trigger (capped)
        result3 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户主动询问凛的过去 / 内心 / 感受",
            turn_index=3,
        )
        assert result3.reason == "capped"

        # Day 1: Different trigger (works)
        result4 = tracker.track_event(
            user_id=user_id,
            character_id="rin",
            trigger_cue="用户精确引用凛说过的话（Memory Runtime 确认）",
            turn_index=4,
        )
        assert result4.new_score == 0.42  # 0.30 + 0.12

        # 40 days later: check decay + reunion bonus
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=40)

        # Manually set last_interaction_at to 40 days ago
        state = mock_state_service.get_resonance_state(user_id, "rin")
        mock_state_service.set_state(
            user_id,
            "rin",
            ResonanceStateSnapshot(
                resonance_score=state.resonance_score,
                last_interaction_at=now,
                resonance_history=state.resonance_history,
            ),
        )

        score = tracker.get_score(user_id, "rin", current_time=future)

        # 40 days = 10 days past decay start = 10/7 ≈ 1.43 weeks
        # decay_rate = 0.95 ** 1.43 ≈ 0.93
        # decayed = 0.42 * 0.93 ≈ 0.3906
        # reunion bonus = +0.05 (because 30 < 40 < 60)
        # final ≈ 0.4406
        expected_decay = 0.42 * (0.95 ** ((40 - 30) / 7))
        expected = min(1.0, expected_decay + 0.05)
        assert abs(score - expected) < 0.01

    def test_gradual_build_to_unlock_threshold(self, tracker, mock_state_service, user_id):
        """Simulate gradual resonance build toward facet unlock."""
        # Target: resonance_score >= 0.6 (facet-ancient-loneliness threshold)

        triggers = [
            ("用户主动询问凛的过去 / 内心 / 感受", 0.15),  # max 2/day
            ("用户主动询问凛的过去 / 内心 / 感受", 0.15),
            ("用户精确引用凛说过的话（Memory Runtime 确认）", 0.12),  # max 3/day
            ("用户用凛的句式说话（『……』/ 省略问号 / 精确时间）", 0.10),  # max 2/day
            ("用户在凛冷漠时仍温柔", 0.08),  # max 2/day
        ]

        cumulative_score = 0.0
        for i, (cue, weight) in enumerate(triggers, start=1):
            result = tracker.track_event(
                user_id=user_id,
                character_id="rin",
                trigger_cue=cue,
                turn_index=i,
            )
            if result.reason == "triggered":
                cumulative_score = result.new_score

        # 0.15 + 0.15 + 0.12 + 0.10 + 0.08 = 0.60
        assert cumulative_score == 0.60

        # Verify via get_score (no decay)
        score = tracker.get_score(user_id, "rin")
        assert score == 0.60
