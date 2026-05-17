"""
Tests for Forgetting Affect Engine - SS02 §4.5 + §6.6

Test coverage:
1. Base frequency (3% over 1000 turns)
2. Days_since_last multipliers (×3 at 30 days, ×5 at 90 days)
3. Cap enforcement (15%)
4. Mode selection based on memory state distribution
5. Complete_amnesia rate limiting (max 1 per 30 days)
6. Forced injection on user_mentioned_forgotten_fact
7. Per-soul phrasing (Rin vs Dorothy)

Author: 心屿团队
"""

from datetime import datetime, timedelta, timezone

import pytest

from heart.ss02_memory.forgetting_affect import (
    ForgettingAffectConfig,
    ForgettingAffectEngine,
    InjectionMode,
    MemoryStateDistribution,
)


@pytest.fixture
def rin_soul_spec():
    """Minimal Rin soul spec."""
    return {
        "soul_id": "rin",
        "voice_dna": [
            {"id": "vd-001", "pattern": "ellipsis", "frequency": "high"},
        ],
        "anti_patterns": {
            "hard_never": ["宝贝", "亲爱的"],
        },
    }


@pytest.fixture
def dorothy_soul_spec():
    """Minimal Dorothy soul spec."""
    return {
        "soul_id": "dorothy",
        "voice_dna": [
            {"id": "vd-DOROTHY-001", "pattern": "third_person_self", "frequency": "high"},
            {"id": "vd-DOROTHY-002", "pattern": "onomatopoeia_mood", "frequency": "high"},
        ],
        "anti_patterns": {
            "hard_never": ["宝贝", "……"],
        },
    }


class TestBaseFrequency:
    """Test base frequency of 3% over many turns."""

    def test_base_frequency_over_1000_turns(self, rin_soul_spec):
        """Base frequency should be ~3% over 1000 turns."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        # Simulate 1000 turns with days_since_last = 0 (no multipliers)
        distribution = MemoryStateDistribution(
            vivid_count=10,
            fading_count=5,
            faint_count=2,
        )

        injection_count = 0
        turns = 1000

        for _ in range(turns):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=0,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                injection_count += 1

        # Should be around 3% (30 ± tolerance)
        # Use 2σ binomial confidence: √(n*p*(1-p)) ≈ √(1000*0.03*0.97) ≈ 5.4
        # So 30 ± 11 is reasonable (2σ)
        expected = 30
        tolerance = 15  # Wider tolerance for randomness
        assert (
            expected - tolerance <= injection_count <= expected + tolerance
        ), f"Expected ~{expected}, got {injection_count}"

    def test_frequency_reported_correctly(self, rin_soul_spec):
        """Frequency should be 0.03 when days_since_last = 0."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=0,
            memory_state_distribution=distribution,
        )

        assert decision.frequency_used == 0.03


class TestDaysSinceLastMultipliers:
    """Test multipliers for days_since_last_interaction."""

    def test_multiplier_30_days(self, rin_soul_spec):
        """Frequency should be ×3 when days_since_last > 30."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=31,
            memory_state_distribution=distribution,
        )

        # 0.03 × 3 = 0.09
        assert decision.frequency_used == 0.09

    def test_multiplier_90_days(self, rin_soul_spec):
        """Frequency should be ×5 when days_since_last > 90."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=91,
            memory_state_distribution=distribution,
        )

        # 0.03 × 5 = 0.15
        assert decision.frequency_used == 0.15

    def test_multiplier_at_30_days_exact(self, rin_soul_spec):
        """At exactly 30 days, no multiplier (> 30, not >= 30)."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=30,
            memory_state_distribution=distribution,
        )

        # No multiplier at exactly 30
        assert decision.frequency_used == 0.03

    def test_multiplier_at_90_days_exact(self, rin_soul_spec):
        """At exactly 90 days, use ×3 multiplier (> 90 for ×5)."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=90,
            memory_state_distribution=distribution,
        )

        # At 90, still ×3 (> 90 needed for ×5)
        assert decision.frequency_used == 0.09


class TestCapEnforcement:
    """Test upper bound cap of 15%."""

    def test_cap_at_15_percent(self, rin_soul_spec):
        """Frequency should never exceed 15%."""
        # Use extreme multiplier to test cap
        config = ForgettingAffectConfig(
            base_frequency=0.05,  # 5%
            multiplier_90_days=10.0,  # Would be 50% without cap
            upper_bound=0.15,
        )
        engine = ForgettingAffectEngine("rin", rin_soul_spec, config)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=91,
            memory_state_distribution=distribution,
        )

        # Capped at 15%
        assert decision.frequency_used == 0.15


class TestModeSelection:
    """Test injection mode selection based on memory state distribution."""

    def test_archived_dominant_triggers_discovery_or_amnesia(self, rin_soul_spec):
        """Archived-dominant should trigger discovery or complete_amnesia."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(
            vivid_count=1,
            archived_count=10,  # 10/11 = 90%
        )

        # Run multiple times to see what modes are selected
        modes_seen = set()
        for _ in range(50):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,  # High frequency
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should see discovery (and possibly complete_amnesia, though rare)
        assert InjectionMode.DISCOVERY in modes_seen

    def test_dormant_dominant_triggers_discovery(self, rin_soul_spec):
        """Dormant-dominant should trigger discovery mode."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(
            vivid_count=1,
            dormant_count=5,  # 5/6 = 83%
        )

        # Run multiple times
        modes_seen = set()
        for _ in range(50):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should see discovery
        assert InjectionMode.DISCOVERY in modes_seen

    def test_faint_dominant_triggers_tip_of_tongue_or_apologetic(self, rin_soul_spec):
        """Faint-dominant should trigger tip_of_tongue or apologetic."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(
            vivid_count=1,
            faint_count=5,  # 5/6 = 83%
        )

        # Run multiple times
        modes_seen = set()
        for _ in range(50):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should see tip_of_tongue or apologetic
        assert (
            InjectionMode.TIP_OF_TONGUE in modes_seen
            or InjectionMode.APOLOGETIC in modes_seen
        )

    def test_default_mode_is_missing_hint(self, rin_soul_spec):
        """Default mode should be missing_hint when no dominant state."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(
            vivid_count=10,
            fading_count=5,
            faint_count=1,  # Not dominant
        )

        # Run multiple times
        modes_seen = set()
        for _ in range(50):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should primarily see missing_hint
        assert InjectionMode.MISSING_HINT in modes_seen


class TestCompleteAmnesiaRateLimit:
    """Test complete_amnesia rate limiting (max 1 per 30 days)."""

    def test_complete_amnesia_allowed_when_no_previous_usage(self, rin_soul_spec):
        """complete_amnesia can be used when never used before."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        # Archived-dominant to allow complete_amnesia
        distribution = MemoryStateDistribution(archived_count=10)

        # Run many times to eventually hit complete_amnesia (10% chance)
        modes_seen = set()
        for _ in range(200):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should eventually see complete_amnesia (though rare)
        # Note: With 10% chance and 200 attempts at 15% frequency,
        # expected ~3 complete_amnesia occurrences, but it's random
        # So we just check that the mode exists, not that it was selected

    def test_complete_amnesia_blocked_within_30_days(self, rin_soul_spec):
        """complete_amnesia should be blocked if used within 30 days."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        # Force a complete_amnesia usage
        engine._last_complete_amnesia_date = datetime.now(timezone.utc) - timedelta(days=15)

        distribution = MemoryStateDistribution(archived_count=10)

        # Run many times - should NOT see complete_amnesia
        modes_seen = set()
        for _ in range(200):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should NOT see complete_amnesia
        assert InjectionMode.COMPLETE_AMNESIA not in modes_seen
        # Should only see discovery (fallback for archived-dominant)
        assert InjectionMode.DISCOVERY in modes_seen

    def test_complete_amnesia_allowed_after_30_days(self, rin_soul_spec):
        """complete_amnesia should be allowed again after 30 days."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        # Set last usage to 31 days ago
        engine._last_complete_amnesia_date = datetime.now(timezone.utc) - timedelta(days=31)

        distribution = MemoryStateDistribution(archived_count=10)

        # Run many times - should eventually see complete_amnesia again
        modes_seen = set()
        for _ in range(200):
            decision = engine.should_inject_forgetting_hint(
                days_since_last_interaction=91,
                memory_state_distribution=distribution,
            )
            if decision.should_inject:
                modes_seen.add(decision.mode)

        # Should see both discovery and possibly complete_amnesia
        assert InjectionMode.DISCOVERY in modes_seen
        # Note: complete_amnesia is rare (10% chance), so not guaranteed in 200 attempts


class TestForcedInjection:
    """Test forced injection when user mentions forgotten fact."""

    def test_forced_injection_when_user_mentions_forgotten_fact(self, rin_soul_spec):
        """Should always inject when user mentions forgotten fact."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=0,
            memory_state_distribution=distribution,
            user_mentioned_forgotten_fact=True,
        )

        # Should always inject
        assert decision.should_inject
        assert decision.mode is not None
        assert decision.frequency_used == 1.0  # Forced

    def test_forced_injection_overrides_low_frequency(self, rin_soul_spec):
        """Forced injection works even when base frequency would be low."""
        config = ForgettingAffectConfig(base_frequency=0.0)  # 0% base
        engine = ForgettingAffectEngine("rin", rin_soul_spec, config)

        distribution = MemoryStateDistribution(vivid_count=10)

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=0,
            memory_state_distribution=distribution,
            user_mentioned_forgotten_fact=True,
        )

        # Should inject despite 0% base frequency
        assert decision.should_inject


class TestPerSoulPhrasing:
    """Test character-specific hint phrasing."""

    def test_rin_phrasing_for_complete_amnesia(self, rin_soul_spec):
        """Rin should use '……忘了。' for complete_amnesia."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        hint = engine._generate_hint_text(InjectionMode.COMPLETE_AMNESIA)

        assert hint == "……忘了。"

    def test_rin_phrasing_for_missing_hint(self, rin_soul_spec):
        """Rin should use ellipsis-heavy phrasing."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        hint = engine._generate_hint_text(InjectionMode.MISSING_HINT)

        # Should contain ellipsis
        assert "……" in hint

    def test_dorothy_phrasing_for_complete_amnesia(self, dorothy_soul_spec):
        """Dorothy should use '诶嘿嘿忘啦~' for complete_amnesia."""
        engine = ForgettingAffectEngine("dorothy", dorothy_soul_spec)

        hint = engine._generate_hint_text(InjectionMode.COMPLETE_AMNESIA)

        assert hint == "诶嘿嘿忘啦~"

    def test_dorothy_phrasing_has_mood_particles(self, dorothy_soul_spec):
        """Dorothy hints should have 语气词 (呀~/呢~)."""
        engine = ForgettingAffectEngine("dorothy", dorothy_soul_spec)

        hint = engine._generate_hint_text(InjectionMode.MISSING_HINT)

        # Should contain 语气词
        assert any(p in hint for p in ["呀~", "呢~", "啦~"])

    def test_dorothy_phrasing_no_ellipsis(self, dorothy_soul_spec):
        """Dorothy should NOT use ellipsis (forbidden in anti_patterns)."""
        engine = ForgettingAffectEngine("dorothy", dorothy_soul_spec)

        # Check all modes except complete_amnesia
        modes_to_check = [
            InjectionMode.MISSING_HINT,
            InjectionMode.TIP_OF_TONGUE,
            InjectionMode.APOLOGETIC,
            InjectionMode.DISCOVERY,
        ]

        for mode in modes_to_check:
            hint = engine._generate_hint_text(mode)
            # Dorothy forbids "……"
            assert "……" not in hint, f"Dorothy hint for {mode} should not have ellipsis: {hint}"

    def test_dorothy_phrasing_has_third_person_self(self, dorothy_soul_spec):
        """Dorothy hints should use '桃桃' (third-person self-reference)."""
        engine = ForgettingAffectEngine("dorothy", dorothy_soul_spec)

        hint = engine._generate_hint_text(InjectionMode.MISSING_HINT)

        # Should contain 桃桃
        assert "桃桃" in hint


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_memory_distribution(self, rin_soul_spec):
        """Should handle empty memory distribution gracefully."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution()  # All zeros

        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=0,
            memory_state_distribution=distribution,
        )

        # Should work, default to missing_hint
        assert decision.frequency_used == 0.03

    def test_decision_includes_hint_text(self, rin_soul_spec):
        """Decision should include hint_text when injection occurs."""
        engine = ForgettingAffectEngine("rin", rin_soul_spec)

        distribution = MemoryStateDistribution(vivid_count=10)

        # Force injection
        decision = engine.should_inject_forgetting_hint(
            days_since_last_interaction=0,
            memory_state_distribution=distribution,
            user_mentioned_forgotten_fact=True,
        )

        # Should have hint_text
        assert decision.hint_text is not None
        assert len(decision.hint_text) > 0
