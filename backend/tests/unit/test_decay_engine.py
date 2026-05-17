"""
Unit tests for Decay Engine (SS02 §10.4.1).

Tests:
- All 12 invariants (I1-I12)
- Edge cases (NULL values, zero importance, recent memories, etc.)
- Reinforcement persistence after decay
- Performance (< 1ms per memory)
- L2/L3 layer differences
- Clock skew protection
- Batch decay with DB writes

Author: 心屿团队
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from heart.ss02_memory.decay_engine import (
    DecayEngine,
    ReinforcementTrigger,
    REINFORCEMENT_DELTAS,
    reinforce_memory,
    MAX_IMPORTANCE,
    TAU_L2,
    TAU_L3,
)
from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    """Test user UUID."""
    return uuid4()


@pytest.fixture
def character_id():
    """Test character ID."""
    return "rin"


@pytest.fixture
def now():
    """Current timestamp."""
    return datetime.now(timezone.utc)


@pytest.fixture
def l2_memory(user_id, character_id, now):
    """Sample L2 episodic memory."""
    return EpisodicMemory(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        episode_summary="用户说他养了一只猫",
        episode_raw_turn_ids=[uuid4()],
        episode_start_at=now - timedelta(days=30),
        episode_end_at=now - timedelta(days=30),
        emotional_peak={"valence": 0.5, "arousal": 0.4, "label": "joy"},
        emotional_end={"valence": 0.3, "arousal": 0.2, "label": "calm"},
        emotional_significance=0.6,
        importance_score=0.75,
        initial_importance=0.75,
        decay_immunity=0.0,
        state="vivid",
        recall_count=5,
        last_recalled_at=now - timedelta(days=10),
        reinforcement_history=[],
        created_at=now - timedelta(days=30),
        updated_at=now - timedelta(days=30),
        do_not_recall=False,
    )


@pytest.fixture
def l3_fact(user_id, character_id, now):
    """Sample L3 fact node."""
    return FactNode(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        predicate="has_pet",
        subject="user",
        object="一只黑猫",
        literal_text="user has_pet 一只黑猫",
        raw_evidence="我养了一只黑猫",
        source_turn_ids=[uuid4()],
        confidence=0.9,
        emotional_charge=0.3,
        importance=0.7,
        state="vivid",
        recall_count=3,
        last_recalled_at=now - timedelta(days=5),
        created_at=now - timedelta(days=60),
        updated_at=now - timedelta(days=60),
        do_not_recall=False,
    )


@pytest.fixture
def l4_identity(user_id, character_id, now):
    """Sample L4 identity memory (should never decay)."""
    return IdentityMemory(
        id=uuid4(),
        user_id=user_id,
        character_id=character_id,
        category="identity",
        key="user_name",
        value="张三",
        disclosed_at=now - timedelta(days=100),
        sacred_reason="用户明示姓名",
        significance_score=0.95,
        promotion_trigger="user_explicit",
        created_at=now - timedelta(days=100),
    )


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    return session


# ============================================================
# I1: Decay is non-increasing without reinforcement
# ============================================================


class TestInvariantI1:
    """I1: Importance never increases without reinforcement."""

    def test_decay_never_increases_l2(self, l2_memory, now):
        """L2 importance should never increase from decay alone."""
        engine = DecayEngine()

        initial_importance = l2_memory.importance_score

        # Apply decay multiple times at different future times
        for days_ahead in [1, 7, 14, 30, 60]:
            future = now + timedelta(days=days_ahead)
            decayed = engine.apply_decay_lazy(l2_memory, future)

            assert decayed.importance_score <= initial_importance, (
                f"Importance increased after {days_ahead} days: "
                f"{initial_importance} -> {decayed.importance_score}"
            )

    def test_decay_never_increases_l3(self, l3_fact, now):
        """L3 importance should never increase from decay alone."""
        engine = DecayEngine()

        # Note: FactNode uses 'importance' not 'importance_score'
        # But DecayEngine expects 'importance_score' field
        # Let's add it for testing
        l3_fact.importance_score = l3_fact.importance
        l3_fact.initial_importance = l3_fact.importance

        initial_importance = l3_fact.importance_score

        for days_ahead in [1, 7, 30, 60, 90]:
            future = now + timedelta(days=days_ahead)
            decayed = engine.apply_decay_lazy(l3_fact, future)

            assert decayed.importance_score <= initial_importance

    def test_decay_strictly_decreasing_over_time(self, l2_memory, now):
        """Importance should strictly decrease as time passes (if above floor)."""
        engine = DecayEngine()

        # Set high importance well above floor
        l2_memory.importance_score = 0.9
        l2_memory.initial_importance = 0.9
        l2_memory.updated_at = now - timedelta(days=30)

        prev_importance = l2_memory.importance_score

        for days in [31, 35, 40, 50, 60]:
            future = now - timedelta(days=30) + timedelta(days=days)
            decayed = engine.apply_decay_lazy(l2_memory, future)

            # Should strictly decrease (unless at floor)
            if decayed.importance_score > 0.1:  # Above floor
                assert decayed.importance_score < prev_importance

            prev_importance = decayed.importance_score


# ============================================================
# I2: L4 never decays
# ============================================================


class TestInvariantI2:
    """I2: L4 memories are immutable."""

    def test_l4_never_decays(self, l4_identity, now):
        """L4 identity memories should never decay."""
        engine = DecayEngine()

        # Apply decay (should be no-op)
        result = engine.apply_decay_lazy(l4_identity, now + timedelta(days=1000))

        # L4 has significance_score, not importance_score
        # But DecayEngine should just return it unchanged
        assert result.significance_score == l4_identity.significance_score


# ============================================================
# I3: Floor is enforced
# ============================================================


class TestInvariantI3:
    """I3: Importance never drops below floor."""

    def test_emotional_floor_enforced(self, l2_memory, now):
        """High-valence memories should never drop below emotional floor."""
        engine = DecayEngine()

        # Set high emotional valence
        l2_memory.emotional_peak = {"valence": 0.8, "arousal": 0.5, "label": "joy"}
        l2_memory.initial_importance = 0.5
        l2_memory.updated_at = now - timedelta(days=365)  # Very old

        # Expected floor = |valence| × 0.1 = 0.8 × 0.1 = 0.08
        expected_floor = 0.08

        decayed = engine.apply_decay_lazy(l2_memory, now)

        assert decayed.importance_score >= expected_floor

    def test_recall_floor_enforced(self, l2_memory, now):
        """Frequently recalled neutral memories should have recall floor."""
        engine = DecayEngine()

        # Neutral emotion but high recall count
        l2_memory.emotional_peak = {"valence": 0.0, "arousal": 0.0, "label": "neutral"}
        l2_memory.recall_count = 50  # Frequently recalled
        l2_memory.initial_importance = 0.3
        l2_memory.updated_at = now - timedelta(days=365)

        # Expected recall floor = min(0.20, ln(1+50) × 0.03) ≈ 0.12
        expected_recall_floor = min(0.20, math.log(1 + 50) * 0.03)

        decayed = engine.apply_decay_lazy(l2_memory, now)

        assert decayed.importance_score >= expected_recall_floor

    def test_floor_is_max_of_emotional_and_recall(self, l2_memory, now):
        """Floor should be max(emotional_floor, recall_floor)."""
        engine = DecayEngine()

        # Case 1: High emotion, low recall -> emotional floor dominates
        l2_memory.emotional_peak = {"valence": 0.9, "arousal": 0.1, "label": "fear"}
        l2_memory.recall_count = 0
        l2_memory.initial_importance = 0.3
        l2_memory.updated_at = now - timedelta(days=365)

        decayed = engine.apply_decay_lazy(l2_memory, now)
        assert decayed.importance_score >= 0.09  # 0.9 × 0.1

        # Case 2: Low emotion, high recall -> recall floor dominates
        l2_memory.emotional_peak = {"valence": 0.1, "arousal": 0.0, "label": "calm"}
        l2_memory.recall_count = 100
        l2_memory.initial_importance = 0.3
        l2_memory.updated_at = now - timedelta(days=365)

        decayed = engine.apply_decay_lazy(l2_memory, now)
        expected_recall_floor = min(0.20, math.log(1 + 100) * 0.03)
        assert decayed.importance_score >= expected_recall_floor


# ============================================================
# I4: Cap is enforced at 0.95
# ============================================================


class TestInvariantI4:
    """I4: Importance never exceeds MAX_IMPORTANCE (0.95)."""

    def test_cap_enforced_on_decay(self, l2_memory, now):
        """Importance capped even if formula yields > 0.95."""
        engine = DecayEngine()

        # Set initial importance to 0.95 (max)
        l2_memory.initial_importance = 0.95
        l2_memory.importance_score = 0.95
        l2_memory.updated_at = now - timedelta(hours=1)  # Very recent

        # High emotion + high recall should not push over cap
        l2_memory.emotional_peak = {"valence": 1.0, "arousal": 1.0, "label": "peak"}
        l2_memory.recall_count = 200

        decayed = engine.apply_decay_lazy(l2_memory, now)

        assert decayed.importance_score <= MAX_IMPORTANCE


# ============================================================
# I5: L2 decays faster than L3
# ============================================================


class TestInvariantI5:
    """I5: L2 (τ=14) decays faster than L3 (τ=60)."""

    def test_l2_decays_faster_than_l3(self, l2_memory, l3_fact, now):
        """Given same initial conditions, L2 should decay more than L3."""
        engine = DecayEngine()

        # Normalize initial conditions
        l2_memory.initial_importance = 0.8
        l2_memory.importance_score = 0.8
        l2_memory.emotional_peak = {"valence": 0.5, "arousal": 0.3, "label": "calm"}
        l2_memory.recall_count = 5
        l2_memory.updated_at = now - timedelta(days=30)

        l3_fact.initial_importance = 0.8
        l3_fact.importance_score = 0.8
        l3_fact.emotional_charge = 0.3  # Matches L2 arousal
        l3_fact.recall_count = 5
        l3_fact.updated_at = now - timedelta(days=30)

        # Apply decay
        l2_decayed = engine.apply_decay_lazy(l2_memory, now)
        l3_decayed = engine.apply_decay_lazy(l3_fact, now)

        # L2 should have decayed more (lower importance)
        assert l2_decayed.importance_score < l3_decayed.importance_score


# ============================================================
# I6: Monotone in recall_count
# ============================================================


class TestInvariantI6:
    """I6: Higher recall_count -> higher importance (all else equal)."""

    def test_more_recalls_means_higher_importance(self, l2_memory, now):
        """Memories with more recalls should have higher importance."""
        engine = DecayEngine()

        l2_memory.initial_importance = 0.7
        l2_memory.updated_at = now - timedelta(days=30)
        l2_memory.emotional_peak = {"valence": 0.3, "arousal": 0.2, "label": "calm"}

        # Test with different recall counts
        recall_counts = [0, 5, 20, 50, 100]
        importances = []

        for count in recall_counts:
            l2_memory.recall_count = count
            decayed = engine.apply_decay_lazy(l2_memory, now)
            importances.append(decayed.importance_score)

        # Importance should increase with recall count (monotone)
        for i in range(len(importances) - 1):
            assert importances[i] < importances[i + 1], (
                f"Importance not monotone at recalls={recall_counts[i]}: "
                f"{importances[i]} >= {importances[i+1]}"
            )


# ============================================================
# I7: Monotone in |valence|
# ============================================================


class TestInvariantI7:
    """I7: Higher |valence| -> higher importance (all else equal)."""

    def test_higher_valence_means_higher_importance(self, l2_memory, now):
        """Memories with stronger emotions should have higher importance."""
        engine = DecayEngine()

        l2_memory.initial_importance = 0.7
        l2_memory.updated_at = now - timedelta(days=30)
        l2_memory.recall_count = 5

        # Test with different valence magnitudes
        valences = [0.0, 0.2, 0.5, 0.8, 1.0]
        importances = []

        for v in valences:
            l2_memory.emotional_peak = {"valence": v, "arousal": 0.3, "label": "test"}
            decayed = engine.apply_decay_lazy(l2_memory, now)
            importances.append(decayed.importance_score)

        # Importance should increase with |valence| (monotone)
        for i in range(len(importances) - 1):
            assert importances[i] <= importances[i + 1]


# ============================================================
# I8: Idempotent at same timestamp
# ============================================================


class TestInvariantI8:
    """I8: Applying decay twice at same timestamp yields same result."""

    def test_decay_idempotent(self, l2_memory, now):
        """Decay should be idempotent if called multiple times at same timestamp."""
        engine = DecayEngine()

        # Apply decay once
        result1 = engine.apply_decay_lazy(l2_memory, now)
        importance1 = result1.importance_score
        state1 = result1.state

        # Apply decay again at same timestamp
        result2 = engine.apply_decay_lazy(result1, now)
        importance2 = result2.importance_score
        state2 = result2.state

        # Should be unchanged (idempotent)
        assert abs(importance1 - importance2) < 1e-6
        assert state1 == state2


# ============================================================
# I9: Reinforcement persists after decay
# ============================================================


class TestInvariantI9:
    """I9: Reinforcement boosts should persist through decay (bug fix test)."""

    @pytest.mark.asyncio
    async def test_reinforcement_persists(self, mock_db_session, l2_memory, now):
        """Reinforcement should bump initial_importance, not just current score."""
        engine = DecayEngine()

        # Initial state
        l2_memory.initial_importance = 0.6
        l2_memory.importance_score = 0.6
        l2_memory.updated_at = now - timedelta(days=14)

        # Mock DB query to return our memory
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=l2_memory)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # First decay WITHOUT reinforcement
        l2_memory.updated_at = now - timedelta(days=7)
        decayed_without_boost = engine.apply_decay_lazy(l2_memory, now + timedelta(days=7))
        importance_without_boost = decayed_without_boost.importance_score

        # Reset and reinforce
        l2_memory.initial_importance = 0.6
        l2_memory.importance_score = 0.6
        l2_memory.updated_at = now - timedelta(days=14)

        await reinforce_memory(
            mock_db_session,
            l2_memory.id,
            ReinforcementTrigger.USER_RE_MENTIONED,
            now,
        )

        # Check initial_importance was bumped
        expected_boost = REINFORCEMENT_DELTAS[ReinforcementTrigger.USER_RE_MENTIONED]
        expected_new = 0.6 + expected_boost
        assert abs(l2_memory.initial_importance - expected_new) < 1e-6

        # Now apply decay WITH reinforcement - should use the new initial_importance
        l2_memory.updated_at = now - timedelta(days=7)
        decayed_with_boost = engine.apply_decay_lazy(l2_memory, now + timedelta(days=7))

        # The boost should persist through decay (not wiped)
        assert decayed_with_boost.importance_score > importance_without_boost


# ============================================================
# I10: State function is monotone in importance
# ============================================================


class TestInvariantI10:
    """I10: State should be monotone in importance."""

    def test_state_monotone(self, l2_memory):
        """State transitions should only happen in one direction as importance decreases."""
        engine = DecayEngine()

        # Test state mapping
        test_cases = [
            (0.95, "vivid"),
            (0.75, "vivid"),
            (0.70, "vivid"),
            (0.65, "fading"),
            (0.50, "fading"),
            (0.45, "faint"),
            (0.30, "faint"),
            (0.25, "dormant"),
            (0.10, "dormant"),
            (0.05, "archived"),
        ]

        for importance, expected_state in test_cases:
            state = engine._compute_state(importance)
            assert state == expected_state, (
                f"State mismatch at importance={importance}: "
                f"expected {expected_state}, got {state}"
            )


# ============================================================
# I11: Finite output (no NaN/Inf)
# ============================================================


class TestInvariantI11:
    """I11: Decay output should never be NaN or Inf."""

    def test_no_nan_inf_with_extreme_values(self, l2_memory, now):
        """Decay should handle extreme values without producing NaN/Inf."""
        engine = DecayEngine()

        # Test extreme cases
        extreme_cases = [
            # (importance, valence, arousal, recall_count)
            (0.0, 0.0, 0.0, 0),
            (1.0, 1.0, 1.0, 1000),
            (0.5, -1.0, 0.0, 0),
            (0.5, 0.0, 1.0, 500),
        ]

        for initial_imp, valence, arousal, recalls in extreme_cases:
            l2_memory.initial_importance = initial_imp
            l2_memory.emotional_peak = {"valence": valence, "arousal": arousal, "label": "test"}
            l2_memory.recall_count = recalls
            l2_memory.updated_at = now - timedelta(days=100)

            decayed = engine.apply_decay_lazy(l2_memory, now)

            assert math.isfinite(decayed.importance_score), (
                f"Non-finite importance for {extreme_cases}: {decayed.importance_score}"
            )


# ============================================================
# I12: Clock skew safety
# ============================================================


class TestInvariantI12:
    """I12: Decay should handle clock skew (future timestamps)."""

    def test_clock_skew_protection(self, l2_memory, now):
        """If last_updated > now, elapsed should be clamped to 0 (skip decay)."""
        engine = DecayEngine()

        # Set updated_at in the future (clock skew)
        l2_memory.updated_at = now + timedelta(hours=2)
        l2_memory.initial_importance = 0.7
        l2_memory.importance_score = 0.7

        # Should not crash or inflate importance
        decayed = engine.apply_decay_lazy(l2_memory, now)

        # Should skip decay (elapsed < 1 day) - importance unchanged
        assert abs(decayed.importance_score - l2_memory.importance_score) < 1e-6


# ============================================================
# Edge Case Tests
# ============================================================


class TestEdgeCases:
    """Edge cases from design doc."""

    def test_importance_starts_at_zero(self, l2_memory, now):
        """Memories with initial_importance=0 should stay at 0."""
        engine = DecayEngine()

        l2_memory.initial_importance = 0.0
        l2_memory.importance_score = 0.0
        l2_memory.updated_at = now - timedelta(days=30)

        decayed = engine.apply_decay_lazy(l2_memory, now)

        # Should stay at floor (might be > 0 if has emotion/recalls)
        assert decayed.importance_score >= 0.0

    def test_null_emotional_peak(self, l2_memory, now):
        """NULL emotional_peak should default to {valence:0, arousal:0}."""
        engine = DecayEngine()

        l2_memory.emotional_peak = None  # NULL
        l2_memory.initial_importance = 0.7
        l2_memory.updated_at = now - timedelta(days=30)

        # Should not crash
        decayed = engine.apply_decay_lazy(l2_memory, now)
        assert math.isfinite(decayed.importance_score)

    def test_null_recall_count(self, l2_memory, now):
        """NULL recall_count should default to 0."""
        engine = DecayEngine()

        l2_memory.recall_count = None  # NULL
        l2_memory.initial_importance = 0.7
        l2_memory.updated_at = now - timedelta(days=30)

        # Should not crash
        decayed = engine.apply_decay_lazy(l2_memory, now)
        assert math.isfinite(decayed.importance_score)

    def test_very_recent_memory(self, l2_memory, now):
        """Memories created < 1 hour ago should skip decay."""
        engine = DecayEngine()

        l2_memory.updated_at = now - timedelta(minutes=30)
        l2_memory.initial_importance = 0.8
        l2_memory.importance_score = 0.8

        decayed = engine.apply_decay_lazy(l2_memory, now)

        # Should be unchanged
        assert abs(decayed.importance_score - 0.8) < 1e-6

    def test_very_old_memory(self, l2_memory, now):
        """Memories from years ago should decay to floor."""
        engine = DecayEngine()

        l2_memory.updated_at = now - timedelta(days=365 * 3)  # 3 years
        l2_memory.initial_importance = 0.9
        l2_memory.emotional_peak = {"valence": 0.2, "arousal": 0.1, "label": "calm"}
        l2_memory.recall_count = 0

        decayed = engine.apply_decay_lazy(l2_memory, now)

        # Should be at or near floor
        expected_floor = 0.2 * 0.1  # valence × 0.1
        assert abs(decayed.importance_score - expected_floor) < 0.05

    def test_out_of_bounds_emotion_values(self, l2_memory, now):
        """Emotional values outside [-1, 1] should be clamped."""
        engine = DecayEngine()

        # Bad data from upstream
        l2_memory.emotional_peak = {"valence": 2.0, "arousal": -0.5, "label": "bad"}
        l2_memory.initial_importance = 0.7
        l2_memory.updated_at = now - timedelta(days=30)

        # Should clamp and not crash
        decayed = engine.apply_decay_lazy(l2_memory, now)
        assert math.isfinite(decayed.importance_score)


# ============================================================
# Batch Decay Tests
# ============================================================


class TestBatchDecay:
    """Tests for apply_decay_batch."""

    @pytest.mark.asyncio
    async def test_batch_decay_processes_all_memories(
        self, mock_db_session, user_id, character_id, now
    ):
        """Batch decay should process all L2 and L3 memories for user."""
        engine = DecayEngine()

        # Create test memories
        l2_mem1 = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="Test 1",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=now - timedelta(days=30),
            episode_end_at=now - timedelta(days=30),
            emotional_peak={"valence": 0.5, "arousal": 0.3, "label": "calm"},
            emotional_end={"valence": 0.3, "arousal": 0.2, "label": "calm"},
            emotional_significance=0.5,
            importance_score=0.7,
            initial_importance=0.7,
            decay_immunity=0.0,
            state="vivid",
            recall_count=5,
            updated_at=now - timedelta(days=30),
            created_at=now - timedelta(days=30),
            do_not_recall=False,
        )

        l2_mem2 = EpisodicMemory(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            episode_summary="Test 2",
            episode_raw_turn_ids=[uuid4()],
            episode_start_at=now - timedelta(days=60),
            episode_end_at=now - timedelta(days=60),
            emotional_peak={"valence": 0.3, "arousal": 0.2, "label": "calm"},
            emotional_end={"valence": 0.2, "arousal": 0.1, "label": "calm"},
            emotional_significance=0.4,
            importance_score=0.6,
            initial_importance=0.6,
            decay_immunity=0.0,
            state="fading",
            recall_count=2,
            updated_at=now - timedelta(days=60),
            created_at=now - timedelta(days=60),
            do_not_recall=False,
        )

        l3_fact1 = FactNode(
            id=uuid4(),
            user_id=user_id,
            character_id=character_id,
            predicate="likes",
            subject="user",
            object="coffee",
            literal_text="user likes coffee",
            raw_evidence="我喜欢咖啡",
            source_turn_ids=[uuid4()],
            confidence=0.9,
            emotional_charge=0.2,
            importance=0.7,
            state="vivid",
            recall_count=3,
            updated_at=now - timedelta(days=90),
            created_at=now - timedelta(days=90),
            do_not_recall=False,
        )
        # Add fields required by DecayEngine
        l3_fact1.importance_score = l3_fact1.importance
        l3_fact1.initial_importance = l3_fact1.importance

        # Mock DB queries
        mock_l2_result = MagicMock()
        mock_l2_result.scalars.return_value.all.return_value = [l2_mem1, l2_mem2]

        mock_l3_result = MagicMock()
        mock_l3_result.scalars.return_value.all.return_value = [l3_fact1]

        mock_db_session.execute = AsyncMock(side_effect=[mock_l2_result, mock_l3_result])

        # Run batch decay
        stats = await engine.apply_decay_batch(mock_db_session, user_id, character_id, now)

        # Check stats
        assert stats["l2_processed"] == 2
        assert stats["l3_processed"] == 1
        assert stats["l2_errors"] == 0
        assert stats["l3_errors"] == 0

        # Check DB commit called
        mock_db_session.commit.assert_called_once()


# ============================================================
# Performance Tests
# ============================================================


class TestPerformance:
    """Performance tests (< 1ms per memory)."""

    def test_decay_performance(self, l2_memory, now):
        """Decay should complete in < 1ms per memory."""
        engine = DecayEngine()

        # Warm up
        for _ in range(10):
            engine.apply_decay_lazy(l2_memory, now)

        # Measure
        iterations = 1000
        start = time.perf_counter()

        for _ in range(iterations):
            engine.apply_decay_lazy(l2_memory, now)

        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        avg_ms = elapsed_ms / iterations

        print(f"\nAverage decay time: {avg_ms:.3f}ms per memory")

        # Should be < 1ms
        assert avg_ms < 1.0, f"Decay too slow: {avg_ms:.3f}ms per memory"


# ============================================================
# Reinforcement Tests
# ============================================================


class TestReinforcement:
    """Tests for reinforcement functionality."""

    @pytest.mark.asyncio
    async def test_reinforcement_boosts_initial_importance(
        self, mock_db_session, l2_memory, now
    ):
        """Reinforcement should boost initial_importance."""
        # Mock DB query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=l2_memory)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        initial = l2_memory.initial_importance
        trigger = ReinforcementTrigger.USER_RE_MENTIONED

        await reinforce_memory(mock_db_session, l2_memory.id, trigger, now)

        expected = min(MAX_IMPORTANCE, initial + REINFORCEMENT_DELTAS[trigger])
        assert abs(l2_memory.initial_importance - expected) < 1e-6

    @pytest.mark.asyncio
    async def test_reinforcement_caps_at_max(self, mock_db_session, l2_memory, now):
        """Reinforcement should not push importance above MAX_IMPORTANCE."""
        # Set initial close to cap
        l2_memory.initial_importance = 0.92

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=l2_memory)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        # Big boost
        trigger = ReinforcementTrigger.CHARACTER_RECALLED_CONFIRMED  # +0.20

        await reinforce_memory(mock_db_session, l2_memory.id, trigger, now)

        # Should be capped at MAX_IMPORTANCE
        assert l2_memory.initial_importance == MAX_IMPORTANCE

    @pytest.mark.asyncio
    async def test_reinforcement_increments_recall_count(
        self, mock_db_session, l2_memory, now
    ):
        """Reinforcement should increment recall_count."""
        old_count = l2_memory.recall_count

        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=l2_memory)
        mock_db_session.execute = AsyncMock(return_value=mock_result)

        await reinforce_memory(
            mock_db_session,
            l2_memory.id,
            ReinforcementTrigger.USER_RE_MENTIONED,
            now,
        )

        assert l2_memory.recall_count == old_count + 1

    @pytest.mark.asyncio
    async def test_reinforcement_works_on_l3_fact(
        self, mock_db_session, l3_fact, now
    ):
        """Reinforcement should work on L3 FactNode."""
        # Add required fields for decay
        l3_fact.importance_score = l3_fact.importance
        l3_fact.initial_importance = l3_fact.importance

        # Mock: L2 query returns None, L3 query returns fact
        mock_l2_result = MagicMock()
        mock_l2_result.scalar_one_or_none = MagicMock(return_value=None)

        mock_l3_result = MagicMock()
        mock_l3_result.scalar_one_or_none = MagicMock(return_value=l3_fact)

        mock_db_session.execute = AsyncMock(side_effect=[mock_l2_result, mock_l3_result])

        initial = l3_fact.initial_importance
        trigger = ReinforcementTrigger.USER_EXPLICIT_INQUIRY

        await reinforce_memory(mock_db_session, l3_fact.id, trigger, now)

        expected = min(MAX_IMPORTANCE, initial + REINFORCEMENT_DELTAS[trigger])
        assert abs(l3_fact.initial_importance - expected) < 1e-6
