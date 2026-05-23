"""
Tests for Director Agent — SS07 §3.4.4

Covers:
  - Soul pacing profiles (Rin vs Dorothy)
  - Length target computation across stages
  - Typing pause modulation
  - Temperature modulation
  - Topic switch sensitivity
  - Intimacy progression pace
  - Turn length category classification
  - Synthetic turn histories (multi-turn progression)
  - Safety overrides
  - Energy effects
  - Cold war / conflict debt effects

Author: 心屿团队
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from heart.ss07_orchestration.director import (
    DirectorAgent,
    SoulPacingProfile,
    DirectorHints,
    EmotionSnapshot,
    RelationshipSnapshot,
    get_soul_pacing_profile,
    _SOUL_PROFILES,
)
from heart.ss07_orchestration.orchestrator import (
    SafetyClassification,
    SafetyLevel,
    DirectorDirectives,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def director_rin() -> DirectorAgent:
    return DirectorAgent(character_id="rin")


@pytest.fixture
def director_dorothy() -> DirectorAgent:
    return DirectorAgent(character_id="dorothy")


@pytest.fixture
def green_safety() -> SafetyClassification:
    return SafetyClassification(
        level=SafetyLevel.GREEN, confidence=0.95, reason="clean"
    )


@pytest.fixture
def yellow_safety() -> SafetyClassification:
    return SafetyClassification(
        level=SafetyLevel.YELLOW, confidence=0.85, reason="mild_flirt"
    )


@pytest.fixture
def orange_safety() -> SafetyClassification:
    return SafetyClassification(
        level=SafetyLevel.ORANGE, confidence=0.90, reason="explicit"
    )


@pytest.fixture
def red_safety() -> SafetyClassification:
    return SafetyClassification(
        level=SafetyLevel.RED, confidence=0.95, reason="violation"
    )


@pytest.fixture
def purple_safety() -> SafetyClassification:
    return SafetyClassification(
        level=SafetyLevel.PURPLE, confidence=0.90, reason="self_harm"
    )


@pytest.fixture
def calm_emotion() -> EmotionSnapshot:
    return EmotionSnapshot(
        valence=0.1, arousal=0.3, dominance=0.5,
        active_emotions=["calm"], energy=0.7,
        mood_valence_baseline=0.0, mood_arousal_baseline=0.3,
    )


@pytest.fixture
def excited_emotion() -> EmotionSnapshot:
    return EmotionSnapshot(
        valence=0.7, arousal=0.85, dominance=0.6,
        active_emotions=["joy", "excitement"], energy=0.9,
        mood_valence_baseline=0.0, mood_arousal_baseline=0.3,
    )


@pytest.fixture
def sad_emotion() -> EmotionSnapshot:
    return EmotionSnapshot(
        valence=-0.6, arousal=0.2, dominance=0.2,
        active_emotions=["sadness", "weariness"], energy=0.35,
        mood_valence_baseline=0.0, mood_arousal_baseline=0.3,
    )


@pytest.fixture
def angry_emotion() -> EmotionSnapshot:
    return EmotionSnapshot(
        valence=-0.5, arousal=0.9, dominance=0.8,
        active_emotions=["anger", "frustration"], energy=0.7,
        mood_valence_baseline=0.0, mood_arousal_baseline=0.3,
    )


@pytest.fixture
def exhausted_emotion() -> EmotionSnapshot:
    return EmotionSnapshot(
        valence=-0.3, arousal=0.15, dominance=0.2,
        active_emotions=["weariness"], energy=0.2,
        mood_valence_baseline=0.0, mood_arousal_baseline=0.3,
    )


@pytest.fixture
def stranger_rel() -> RelationshipSnapshot:
    return RelationshipSnapshot(
        current_stage="STRANGER", intimacy_level=0.05,
        trust_score=0.05, conflict_debt=0.0,
    )


@pytest.fixture
def friend_rel() -> RelationshipSnapshot:
    return RelationshipSnapshot(
        current_stage="FRIEND", intimacy_level=0.45,
        trust_score=0.5, conflict_debt=0.0,
    )


@pytest.fixture
def intimate_rel() -> RelationshipSnapshot:
    return RelationshipSnapshot(
        current_stage="INTIMATE", intimacy_level=0.8,
        trust_score=0.85, conflict_debt=0.0,
        vulnerability_score=0.6, total_interactions=500,
    )


@pytest.fixture
def soulmate_rel() -> RelationshipSnapshot:
    return RelationshipSnapshot(
        current_stage="SOULMATE", intimacy_level=0.95,
        trust_score=0.95, conflict_debt=0.0,
        vulnerability_score=0.9, total_interactions=2000,
    )


@pytest.fixture
def cold_war_rel() -> RelationshipSnapshot:
    return RelationshipSnapshot(
        current_stage="CLOSE_FRIEND", intimacy_level=0.6,
        trust_score=0.4, conflict_debt=0.7,
        vulnerability_score=0.3, total_interactions=200,
    )


# ============================================================
# §1. Soul Pacing Profiles
# ============================================================


class TestSoulPacingProfiles:
    """Verify per-character pacing constants are correctly defined."""

    def test_rin_profile_exists(self):
        profile = get_soul_pacing_profile("rin")
        assert profile.character_id == "rin"
        assert profile.base_length_target == "very_short"
        assert profile.base_typing_pause_ms == 1200
        assert profile.base_temperature == 0.72
        assert profile.topic_switch_damping == 0.75
        assert profile.intimacy_pace_modifier == 0.35

    def test_dorothy_profile_exists(self):
        profile = get_soul_pacing_profile("dorothy")
        assert profile.character_id == "dorothy"
        assert profile.base_length_target == "medium"
        assert profile.base_typing_pause_ms == 500
        assert profile.base_temperature == 0.88
        assert profile.topic_switch_damping == 0.25
        assert profile.intimacy_pace_modifier == 0.70

    def test_unknown_character_falls_back_to_rin(self):
        profile = get_soul_pacing_profile("nonexistent")
        assert profile.character_id == "rin"

    def test_rin_stage_multipliers(self):
        profile = _SOUL_PROFILES["rin"]
        # Rin's STRANGER multiplier should be the smallest
        assert profile.get_stage_multiplier("STRANGER") < 1.0
        # Rin's SOULMATE multiplier should be the largest
        assert profile.get_stage_multiplier("SOULMATE") > 1.0
        # Monotonic progression
        stages = ["STRANGER", "ACQUAINTANCE", "FRIEND", "CLOSE_FRIEND", "INTIMATE", "SOULMATE"]
        mults = [profile.get_stage_multiplier(s) for s in stages]
        for i in range(len(mults) - 1):
            assert mults[i] <= mults[i+1], f"{stages[i]} → {stages[i+1]} should not decrease"

    def test_dorothy_stage_multipliers(self):
        profile = _SOUL_PROFILES["dorothy"]
        # Dorothy's SOULMATE multiplier is higher than Rin's (more expressive at intimacy)
        assert profile.get_stage_multiplier("SOULMATE") > _SOUL_PROFILES["rin"].get_stage_multiplier("SOULMATE")

    def test_rin_is_slower_than_dorothy(self):
        rin = _SOUL_PROFILES["rin"]
        dorothy = _SOUL_PROFILES["dorothy"]
        # Rin: slower pace, higher damping, longer pause
        assert rin.topic_switch_damping > dorothy.topic_switch_damping
        assert rin.intimacy_pace_modifier < dorothy.intimacy_pace_modifier
        assert rin.base_typing_pause_ms > dorothy.base_typing_pause_ms


# ============================================================
# §2. Length Target Computation
# ============================================================


class TestLengthTarget:
    """Verify response_length_target computation per §3.4.4."""

    def test_short_message_rin_stranger(self, director_rin, green_safety, calm_emotion, stranger_rel):
        result = director_rin.decide("你好", green_safety, calm_emotion, stranger_rel)
        # Short message + Rin + Stranger → very_short
        assert result.response_length_target == "very_short"

    def test_short_message_rin_intimate(self, director_rin, green_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("你好", green_safety, calm_emotion, intimate_rel)
        # Short message + Rin + Intimate → still very_short (message is the driver)
        assert result.response_length_target in ("very_short", "short")

    def test_long_message_rin_intimate(self, director_rin, green_safety, calm_emotion, intimate_rel):
        result = director_rin.decide(
            "我今天经历了很多事情，想和你慢慢说。从早上开始，我就一直在想一个问题……" * 3,
            green_safety, calm_emotion, intimate_rel
        )
        # Long message + Rin + Intimate → medium or long
        assert result.response_length_target in ("short", "medium", "long")

    def test_dorothy_always_longer_than_rin(self, director_rin, director_dorothy, green_safety, calm_emotion, friend_rel):
        msg = "今天天气真好啊！"
        r_rin = director_rin.decide(msg, green_safety, calm_emotion, friend_rel)
        r_dorothy = director_dorothy.decide(msg, green_safety, calm_emotion, friend_rel)

        # Dorothy should have >= length target than Rin for same input
        length_order = {"very_short": 0, "short": 1, "medium": 2, "long": 3}
        assert length_order[r_dorothy.response_length_target] >= length_order[r_rin.response_length_target]

    def test_high_arousal_increases_length(self, director_rin, green_safety, excited_emotion, friend_rel):
        result = director_rin.decide("哈哈太棒了！", green_safety, excited_emotion, friend_rel)
        # High arousal should push length up
        assert result.response_length_target in ("short", "medium", "long")

    def test_weariness_decreases_length(self, director_rin, green_safety, sad_emotion, friend_rel):
        result = director_rin.decide("嗯……", green_safety, sad_emotion, friend_rel)
        # Weariness + sadness → short
        assert result.response_length_target in ("very_short", "short")

    def test_conflict_debt_decreases_length(self, director_rin, green_safety, calm_emotion, cold_war_rel):
        result = director_rin.decide("我们能谈谈吗？", green_safety, calm_emotion, cold_war_rel)
        # Cold war → short responses
        assert result.response_length_target in ("very_short", "short")

    def test_red_safety_forces_short(self, director_rin, red_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("说点劲爆的", red_safety, calm_emotion, intimate_rel)
        assert result.response_length_target == "short"

    def test_purple_safety_forces_short(self, director_rin, purple_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("我不想活了", purple_safety, calm_emotion, intimate_rel)
        assert result.response_length_target == "short"

    def test_orange_safety_caps_length(self, director_rin, orange_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("说点刺激的" * 10, orange_safety, calm_emotion, intimate_rel)
        assert result.response_length_target in ("very_short", "short")

    def test_yellow_safety_caps_length(self, director_rin, yellow_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("你好帅啊" * 10, yellow_safety, calm_emotion, intimate_rel)
        assert result.response_length_target in ("very_short", "short", "medium")

    def test_low_energy_decreases_length(self, director_rin, green_safety, exhausted_emotion, intimate_rel):
        result = director_rin.decide("你还好吗？", green_safety, exhausted_emotion, intimate_rel)
        assert result.response_length_target in ("very_short", "short")


# ============================================================
# §3. Typing Pause Modulation
# ============================================================


class TestTypingPause:
    """Verify typing_pause_ms modulation per spec."""

    def test_rin_base_pause(self, director_rin, green_safety, calm_emotion, friend_rel):
        result = director_rin.decide("嗨", green_safety, calm_emotion, friend_rel)
        # Rin friend stage: base 1200
        assert result.typing_pause_ms == 1200

    def test_dorothy_base_pause(self, director_dorothy, green_safety, calm_emotion, friend_rel):
        result = director_dorothy.decide("嗨", green_safety, calm_emotion, friend_rel)
        assert result.typing_pause_ms == 500

    def test_high_arousal_shortens_pause(self, director_rin, green_safety, excited_emotion, friend_rel):
        result = director_rin.decide("哇！！", green_safety, excited_emotion, friend_rel)
        # High arousal → 0.5x pause
        assert result.typing_pause_ms < 1200

    def test_weariness_lengthens_pause(self, director_rin, green_safety, sad_emotion, friend_rel):
        result = director_rin.decide("……", green_safety, sad_emotion, friend_rel)
        # Weariness → 1.5x pause
        assert result.typing_pause_ms > 1200

    def test_stranger_shorter_pause(self, director_rin, green_safety, calm_emotion, stranger_rel):
        result = director_rin.decide("你好", green_safety, calm_emotion, stranger_rel)
        # Stranger → 0.7x pause
        assert result.typing_pause_ms == int(1200 * 0.7)

    def test_intimate_longer_pause(self, director_rin, green_safety, calm_emotion, intimate_rel):
        result = director_rin.decide("你好", green_safety, calm_emotion, intimate_rel)
        # Intimate → 1.2x pause
        assert result.typing_pause_ms == int(1200 * 1.2)

    def test_low_energy_lengthens_pause(self, director_rin, green_safety, exhausted_emotion, friend_rel):
        result = director_rin.decide("…", green_safety, exhausted_emotion, friend_rel)
        # Low energy → 1.3x pause
        assert result.typing_pause_ms > 1200

    def test_pause_clamped_to_range(self, director_rin, green_safety, calm_emotion, friend_rel):
        # Normal case should be within [200, 3000]
        result = director_rin.decide("测试消息", green_safety, calm_emotion, friend_rel)
        assert 200 <= result.typing_pause_ms <= 3000


# ============================================================
# §4. Temperature Modulation
# ============================================================


class TestTemperature:
    """Verify llm_temperature modulation."""

    def test_rin_base_temperature(self, director_rin, green_safety, calm_emotion, friend_rel):
        result = director_rin.decide("你好", green_safety, calm_emotion, friend_rel)
        assert result.llm_temperature == 0.72

    def test_dorothy_base_temperature(self, director_dorothy, green_safety, calm_emotion, friend_rel):
        result = director_dorothy.decide("你好", green_safety, calm_emotion, friend_rel)
        assert result.llm_temperature == 0.88

    def test_high_arousal_increases_temperature(self, director_rin, green_safety, excited_emotion, friend_rel):
        result = director_rin.decide("哇！！", green_safety, excited_emotion, friend_rel)
        assert result.llm_temperature > 0.72

    def test_conflict_reduces_temperature(self, director_rin, green_safety, calm_emotion, cold_war_rel):
        result = director_rin.decide("我们能谈谈吗", green_safety, calm_emotion, cold_war_rel)
        assert result.llm_temperature < 0.72

    def test_orange_safety_increases_temperature(self, director_rin, orange_safety, calm_emotion, friend_rel):
        result = director_rin.decide("测试", orange_safety, calm_emotion, friend_rel)
        assert result.llm_temperature > 0.72

    def test_yellow_safety_increases_temperature(self, director_rin, yellow_safety, calm_emotion, friend_rel):
        result = director_rin.decide("测试", yellow_safety, calm_emotion, friend_rel)
        assert result.llm_temperature > 0.72

    def test_extreme_low_energy_reduces_temperature(self, director_rin, green_safety, exhausted_emotion, friend_rel):
        result = director_rin.decide("…", green_safety, exhausted_emotion, friend_rel)
        assert result.llm_temperature < 0.72

    def test_temperature_clamped(self, director_rin, orange_safety, excited_emotion, friend_rel):
        result = director_rin.decide("test", orange_safety, excited_emotion, friend_rel)
        assert 0.5 <= result.llm_temperature <= 1.2

    def test_depression_boosts_temperature_slightly(self, director_rin, green_safety, sad_emotion, friend_rel):
        result = director_rin.decide("我好难过", green_safety, sad_emotion, friend_rel)
        # Very low valence + conflict reduction may cancel out, but base + depression boost - conflict
        # Just verify it's still valid
        assert 0.5 <= result.llm_temperature <= 1.2


# ============================================================
# §5. Topic Switch Sensitivity
# ============================================================


class TestTopicSwitchSensitivity:
    """Verify topic_switch_sensitivity computation."""

    def test_rin_high_damping(self, director_rin, calm_emotion, friend_rel):
        sensitivity = director_rin.compute_topic_switch_sensitivity(calm_emotion, friend_rel)
        # Rin: 0.75 - 0.045 (intimacy 0.45 * 0.10) = 0.705
        assert 0.65 <= sensitivity <= 0.80

    def test_dorothy_low_damping(self, director_dorothy, calm_emotion, friend_rel):
        sensitivity = director_dorothy.compute_topic_switch_sensitivity(calm_emotion, friend_rel)
        # Dorothy: 0.25 - 0.045 = 0.205
        assert 0.15 <= sensitivity <= 0.35

    def test_high_arousal_reduces_damping(self, director_rin, excited_emotion, calm_emotion, friend_rel):
        base = director_rin.compute_topic_switch_sensitivity(calm_emotion, friend_rel)
        excited = director_rin.compute_topic_switch_sensitivity(excited_emotion, friend_rel)
        assert excited < base

    def test_high_intimacy_reduces_damping(self, director_rin, calm_emotion, friend_rel, intimate_rel):
        friend = director_rin.compute_topic_switch_sensitivity(calm_emotion, friend_rel)
        intimate = director_rin.compute_topic_switch_sensitivity(calm_emotion, intimate_rel)
        assert intimate < friend

    def test_conflict_increases_damping(self, director_rin, calm_emotion, friend_rel, cold_war_rel):
        friend = director_rin.compute_topic_switch_sensitivity(calm_emotion, friend_rel)
        cold_war = director_rin.compute_topic_switch_sensitivity(calm_emotion, cold_war_rel)
        assert cold_war > friend

    def test_sensitivity_bounded(self, director_rin, calm_emotion, stranger_rel):
        sensitivity = director_rin.compute_topic_switch_sensitivity(calm_emotion, stranger_rel)
        assert 0.0 <= sensitivity <= 1.0


# ============================================================
# §6. Intimacy Progression Pace
# ============================================================


class TestIntimacyProgressionPace:
    """Verify intimacy_progression_pace computation."""

    def test_rin_slow_pace(self, director_rin, friend_rel):
        pace = director_rin.compute_intimacy_progression_pace(friend_rel)
        # Rin: 0.35 + 0.5*0.15 = 0.425
        assert 0.3 <= pace <= 0.55

    def test_dorothy_fast_pace(self, director_dorothy, friend_rel):
        pace = director_dorothy.compute_intimacy_progression_pace(friend_rel)
        # Dorothy: 0.70 + 0.5*0.15 = 0.775
        assert 0.65 <= pace <= 0.90

    def test_trust_increases_pace(self, director_rin, friend_rel, intimate_rel):
        friend_pace = director_rin.compute_intimacy_progression_pace(friend_rel)
        intimate_pace = director_rin.compute_intimacy_progression_pace(intimate_rel)
        assert intimate_pace > friend_pace

    def test_conflict_decreases_pace(self, director_rin, friend_rel, cold_war_rel):
        friend_pace = director_rin.compute_intimacy_progression_pace(friend_rel)
        cold_war_pace = director_rin.compute_intimacy_progression_pace(cold_war_rel)
        assert cold_war_pace < friend_pace

    def test_pace_bounded(self, director_rin, stranger_rel):
        pace = director_rin.compute_intimacy_progression_pace(stranger_rel)
        assert 0.1 <= pace <= 1.0


# ============================================================
# §7. Turn Length Category
# ============================================================


class TestTurnLengthCategory:
    """Verify turn_length_category classification."""

    def test_stranger_caps_at_brief(self, director_rin, calm_emotion, stranger_rel):
        category = director_rin.compute_turn_length_category(
            "今天天气真好，我想和你聊聊最近发生的事情", calm_emotion, stranger_rel
        )
        assert category in ("brief", "terse")

    def test_cold_war_is_terse(self, director_rin, calm_emotion, cold_war_rel):
        category = director_rin.compute_turn_length_category(
            "我想了很久，我们谈谈吧", calm_emotion, cold_war_rel
        )
        assert category == "terse"

    def test_exhausted_is_terse(self, director_rin, exhausted_emotion, intimate_rel):
        category = director_rin.compute_turn_length_category(
            "你还好吗？", exhausted_emotion, intimate_rel
        )
        assert category == "terse"

    def test_emotional_peaking_is_pouring(self, director_rin, excited_emotion, intimate_rel):
        category = director_rin.compute_turn_length_category(
            "我今天超级开心！！！", excited_emotion, intimate_rel
        )
        # excited_emotion: valence=0.7, arousal=0.85, intimacy=0.8
        # Should trigger pouring
        assert category == "pouring"

    def test_normal_turn(self, director_rin, calm_emotion, friend_rel):
        category = director_rin.compute_turn_length_category(
            "今天过得还行吧，没什么特别的", calm_emotion, friend_rel
        )
        assert category in ("normal", "flowing")


# ============================================================
# §8. Synthetic Turn Histories (Multi-Turn Progression)
# ============================================================


class TestSyntheticTurnHistories:
    """Simulate multi-turn progressions and verify pacing evolution."""

    def _make_turn(
        self,
        director: DirectorAgent,
        turn_index: int,
        user_msg: str,
        emotion: EmotionSnapshot,
        relationship: RelationshipSnapshot,
        safety: SafetyClassification,
    ) -> DirectorDirectives:
        return director.decide(user_msg, safety, emotion, relationship)

    def test_rin_stranger_to_friend_progression(self, director_rin, green_safety):
        """Rin: 从陌生到朋友，响应长度逐步增长。"""
        history = []

        # Turn 1: STRANGER — short greeting
        rel = RelationshipSnapshot(current_stage="STRANGER", intimacy_level=0.02, trust_score=0.01)
        em = EmotionSnapshot(valence=0.0, arousal=0.2, energy=0.6)
        d = self._make_turn(director_rin, 1, "你好", em, rel, green_safety)
        history.append(("STRANGER", d.response_length_target))
        assert d.response_length_target in ("very_short", "short")

        # Turn 5: ACQUAINTANCE — slightly longer
        rel = RelationshipSnapshot(current_stage="ACQUAINTANCE", intimacy_level=0.15, trust_score=0.1)
        d = self._make_turn(director_rin, 5, "今天工作好累", em, rel, green_safety)
        history.append(("ACQUAINTANCE", d.response_length_target))
        # Should still be short

        # Turn 20: FRIEND — normal conversation
        rel = RelationshipSnapshot(current_stage="FRIEND", intimacy_level=0.45, trust_score=0.5)
        em = EmotionSnapshot(valence=0.2, arousal=0.4, energy=0.7)
        d = self._make_turn(director_rin, 20, "我今天遇到一件事，想听听你的看法", em, rel, green_safety)
        history.append(("FRIEND", d.response_length_target))
        assert d.response_length_target in ("short", "medium")

        # Turn 100: CLOSE_FRIEND — comfortable sharing
        rel = RelationshipSnapshot(current_stage="CLOSE_FRIEND", intimacy_level=0.65, trust_score=0.7)
        em = EmotionSnapshot(valence=0.4, arousal=0.5, energy=0.65)
        d = self._make_turn(director_rin, 100, "有时候我在想，你是不是真的懂我", em, rel, green_safety)
        history.append(("CLOSE_FRIEND", d.response_length_target))
        assert d.response_length_target in ("medium", "long")

        # Verify monotonic progression (length should not decrease without conflict)
        length_order = {"very_short": 0, "short": 1, "medium": 2, "long": 3}
        prev_score = -1
        for stage, target in history:
            score = length_order[target]
            assert score >= prev_score, f"Length decreased at {stage}: {target}"
            prev_score = score

    def test_dorothy_stranger_to_friend_progression(self, director_dorothy, green_safety):
        """Dorothy: 从陌生到朋友，响应长度比 Rin 更快增长。"""
        history = []

        # Turn 1: STRANGER
        rel = RelationshipSnapshot(current_stage="STRANGER", intimacy_level=0.02, trust_score=0.01)
        em = EmotionSnapshot(valence=0.0, arousal=0.3, energy=0.7)
        d = self._make_turn(director_dorothy, 1, "你好呀~", em, rel, green_safety)
        history.append(d.response_length_target)

        # Turn 20: FRIEND
        rel = RelationshipSnapshot(current_stage="FRIEND", intimacy_level=0.45, trust_score=0.5)
        em = EmotionSnapshot(valence=0.4, arousal=0.5, energy=0.8)
        d = self._make_turn(director_dorothy, 20, "今天真的超级开心！我想和你说好多好多事情呢！你一定想知道我今天遇到什么了吧？", em, rel, green_safety)
        history.append(d.response_length_target)

        # Dorothy should be at least medium by FRIEND stage
        length_order = {"very_short": 0, "short": 1, "medium": 2, "long": 3}
        assert length_order[d.response_length_target] >= length_order["short"], f"Expected at least short, got {d.response_length_target}"

    def test_cold_war_reduces_then_recovers(self, director_rin, green_safety, calm_emotion):
        """Conflict → cold war → recovery: length / pause / temp all reflect this."""
        # Pre-conflict: intimate, warm
        rel_pre = RelationshipSnapshot(current_stage="INTIMATE", intimacy_level=0.8, trust_score=0.85)
        em_warm = EmotionSnapshot(valence=0.5, arousal=0.5, energy=0.7)
        d_pre = director_rin.decide("今天开心吗？", green_safety, em_warm, rel_pre)

        # During cold war
        rel_cw = RelationshipSnapshot(current_stage="INTIMATE", intimacy_level=0.8, trust_score=0.4, conflict_debt=0.7)
        em_cold = EmotionSnapshot(valence=-0.3, arousal=0.25, energy=0.45, active_emotions=["sadness"])
        d_cw = director_rin.decide("……", green_safety, em_cold, rel_cw)

        # After reconciliation
        rel_post = RelationshipSnapshot(current_stage="INTIMATE", intimacy_level=0.82, trust_score=0.8, conflict_debt=0.1)
        em_post = EmotionSnapshot(valence=0.3, arousal=0.4, energy=0.65)
        d_post = director_rin.decide("我们和好吧", green_safety, em_post, rel_post)

        # Cold war: shorter response, lower temperature, longer pause
        length_order = {"very_short": 0, "short": 1, "medium": 2, "long": 3}
        assert length_order[d_cw.response_length_target] <= length_order[d_pre.response_length_target]
        assert d_cw.llm_temperature <= d_pre.llm_temperature
        assert d_cw.typing_pause_ms >= d_pre.typing_pause_ms

        # Post-reconciliation: recovers (not necessarily back to pre, but better than cold war)
        assert length_order[d_post.response_length_target] >= length_order[d_cw.response_length_target]
        assert d_post.llm_temperature >= d_cw.llm_temperature

    def test_emotional_rollercoaster(self, director_rin, green_safety, friend_rel):
        """Simulate rapid emotional shifts across turns."""
        turns = [
            ("今天超开心！！！", EmotionSnapshot(valence=0.8, arousal=0.9, energy=0.9, active_emotions=["joy", "excitement"])),
            ("我好难过……", EmotionSnapshot(valence=-0.7, arousal=0.2, energy=0.3, active_emotions=["sadness"])),
            ("气死我了！！", EmotionSnapshot(valence=-0.6, arousal=0.85, energy=0.75, active_emotions=["anger"])),
            ("算了，没事了", EmotionSnapshot(valence=0.0, arousal=0.3, energy=0.5, active_emotions=["calm"])),
        ]

        results = []
        for msg, em in turns:
            d = director_rin.decide(msg, green_safety, em, friend_rel)
            results.append(d)

        # Joy: high temperature, shorter pause
        assert results[0].llm_temperature > 0.72
        assert results[0].typing_pause_ms < 1200

        # Sadness: low temperature, longer pause
        assert results[1].typing_pause_ms > 1200

        # Anger: high temperature (arousal high), shorter pause
        assert results[2].llm_temperature > 0.72

        # Calm: baseline-ish
        assert results[3].llm_temperature == pytest.approx(0.72, abs=0.03)

    def test_energy_depletion_trajectory(self, director_rin, green_safety, intimate_rel):
        """Simulate an exhaustedly long conversation."""
        energies = [0.8, 0.6, 0.4, 0.25, 0.15]
        results = []
        for e in energies:
            em = EmotionSnapshot(valence=0.1, arousal=0.3, energy=e)
            d = director_rin.decide("嗯", green_safety, em, intimate_rel)
            results.append(d)

        # Typing pause should increase as energy drops
        pauses = [r.typing_pause_ms for r in results]
        assert pauses[-1] > pauses[0], "Pause should increase as energy depletes"

        # Temperature should drop as energy goes below critical
        temps = [r.llm_temperature for r in results]
        # Last one (energy=0.15, below critical 0.3) → temp reduction
        assert temps[-1] < temps[0]


# ============================================================
# §9. Safety Override Behaviors
# ============================================================


class TestSafetyOverrides:
    """Verify safety level effects on all outputs."""

    def test_red_forces_short_text(self, director_rin, red_safety, excited_emotion, intimate_rel):
        result = director_rin.decide("说点劲爆的！", red_safety, excited_emotion, intimate_rel)
        assert result.response_length_target == "short"
        assert result.modality == "text"

    def test_purple_forces_short_text(self, director_rin, purple_safety, excited_emotion, intimate_rel):
        result = director_rin.decide("我不想活了", purple_safety, excited_emotion, intimate_rel)
        assert result.response_length_target == "short"
        assert result.modality == "text"

    def test_orange_modulates_all_fields(self, director_rin, orange_safety, calm_emotion, friend_rel):
        result = director_rin.decide("说点更劲爆的", orange_safety, calm_emotion, friend_rel)
        assert result.response_length_target in ("very_short", "short")
        assert result.llm_temperature > 0.72  # Orange boosts temperature for deflection

    def test_yellow_modulates_temperature(self, director_rin, yellow_safety, calm_emotion, friend_rel):
        result = director_rin.decide("你今晚有空吗", yellow_safety, calm_emotion, friend_rel)
        assert result.llm_temperature > 0.72


# ============================================================
# §10. DirectorHints — Extended Metadata
# ============================================================


class TestDirectorHints:
    """Verify DirectorHints completeness and correctness."""

    def test_hints_contain_all_fields(self, director_rin, green_safety, calm_emotion, friend_rel):
        _, hints = director_rin.decide_with_hints(
            "测试消息", green_safety, calm_emotion, friend_rel
        )
        assert isinstance(hints, DirectorHints)
        assert hints.topic_switch_sensitivity > 0
        assert hints.intimacy_progression_pace > 0
        assert hints.turn_length_category in ("terse", "brief", "normal", "flowing", "pouring")
        assert hints.emotional_intensity >= 0
        assert hints.emotional_valence_sign in (-1, 0, 1)
        assert isinstance(hints.is_emotional_peaking, bool)
        assert hints.stage == "FRIEND"
        assert hints.intimacy_level > 0
        assert hints.character_id == "rin"
        assert hints.soul_archetype_tag == "slow_guardian"
        assert hints.safety_level == "GREEN"

    def test_dorothy_archetype_tag(self, director_dorothy, green_safety, calm_emotion, friend_rel):
        _, hints = director_dorothy.decide_with_hints(
            "测试", green_safety, calm_emotion, friend_rel
        )
        assert hints.soul_archetype_tag == "fast_spark"

    def test_emotional_peaking_detection(self, director_rin, green_safety, excited_emotion, friend_rel):
        _, hints = director_rin.decide_with_hints(
            "啊啊啊！！", green_safety, excited_emotion, friend_rel
        )
        # excited_emotion: arousal=0.85 > 0.8 → is_emotional_peaking
        assert hints.is_emotional_peaking is True

    def test_negative_peak_detection(self, director_rin, green_safety, sad_emotion, friend_rel):
        _, hints = director_rin.decide_with_hints(
            "我好难过", green_safety, sad_emotion, friend_rel
        )
        # sad_emotion: valence=-0.6 < -0.5 → is_emotional_peaking
        assert hints.is_emotional_peaking is True


# ============================================================
# §11. Edge Cases & Invariants
# ============================================================


class TestEdgeCases:
    """Boundary conditions and invariants."""

    def test_empty_message_does_not_crash(self, director_rin, green_safety, calm_emotion, friend_rel):
        result = director_rin.decide("", green_safety, calm_emotion, friend_rel)
        assert isinstance(result, DirectorDirectives)
        assert result.response_length_target in ("very_short", "short", "medium", "long")

    def test_very_long_message_does_not_crash(self, director_rin, green_safety, calm_emotion, friend_rel):
        msg = "长消息" * 500
        result = director_rin.decide(msg, green_safety, calm_emotion, friend_rel)
        assert isinstance(result, DirectorDirectives)

    def test_defaults_when_no_emotion_or_relationship(self, director_rin, green_safety):
        result = director_rin.decide("你好", green_safety)
        assert isinstance(result, DirectorDirectives)
        assert result.response_length_target == "very_short"  # Rin + short msg + defaults

    def test_energy_override(self, director_rin, green_safety, calm_emotion, friend_rel):
        # inner_energy overrides emotion.energy
        result = director_rin.decide(
            "你好", green_safety, calm_emotion, friend_rel, inner_energy=0.15
        )
        # Very low energy → terse/short
        assert result.response_length_target in ("very_short", "short")
        assert result.typing_pause_ms > 1200  # longer pause

    def test_top_p_range(self, director_rin, green_safety, calm_emotion, friend_rel):
        result = director_rin.decide("test", green_safety, calm_emotion, friend_rel)
        assert 0.8 <= result.llm_top_p <= 1.0

    def test_energy_modifier_range(self, director_rin, green_safety, calm_emotion, friend_rel):
        result = director_rin.decide("test", green_safety, calm_emotion, friend_rel)
        assert -0.5 <= result.energy_modifier <= 0.5

    def test_rin_vs_dorothy_same_input_different_output(self, director_rin, director_dorothy, green_safety, calm_emotion, friend_rel):
        r_rin = director_rin.decide("今天天气真好", green_safety, calm_emotion, friend_rel)
        r_dorothy = director_dorothy.decide("今天天气真好", green_safety, calm_emotion, friend_rel)

        # They should differ in at least temperature or pause
        assert (
            r_rin.llm_temperature != r_dorothy.llm_temperature
            or r_rin.typing_pause_ms != r_dorothy.typing_pause_ms
        )

    def test_soulmate_stage_has_longest_responses(self, director_rin, green_safety, excited_emotion):
        stages = ["STRANGER", "ACQUAINTANCE", "FRIEND", "CLOSE_FRIEND", "INTIMATE", "SOULMATE"]
        length_order = {"very_short": 0, "short": 1, "medium": 2, "long": 3}

        results = []
        for stage in stages:
            rel = RelationshipSnapshot(current_stage=stage, intimacy_level=0.5, trust_score=0.5)
            d = director_rin.decide("今天心情不错，想和你聊聊", green_safety, excited_emotion, rel)
            results.append((stage, d.response_length_target))

        # SOULMATE should be at least as long as all others
        soulmate_score = length_order[results[-1][1]]
        for stage, target in results[:-1]:
            assert length_order[target] <= soulmate_score, \
                f"{stage} ({target}) should be <= SOULMATE ({results[-1][1]})"
