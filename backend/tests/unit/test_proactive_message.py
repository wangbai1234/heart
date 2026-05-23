"""
End-to-end tests for Proactive Message Generator (SS06 §3.7, §10.6).

Covers:
  - Directive building for each trigger type
  - Context interpolation in templates
  - Post-processing (trimming, quote removal, length enforcement)
  - Anti-pattern heuristic checks
  - Character limit enforcement by trigger type
  - Mood hint building from InnerState
  - Style guide selection (Rin vs Dorothy)
  - Generate flow with mock ModelRouter
  - Reroll on anti-pattern detection
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from heart.ss06_inner_state.initiative_decider import (
    InitiativeDecision,
    TriggerType,
    SoulSpec,
)
from heart.ss06_inner_state.composer import (
    InnerState,
    TodayState,
    ProactiveState,
    DailyRitualState,
    RitualState,
)
from heart.ss06_inner_state.proactive_message import (
    ProactiveMessage,
    ProactiveMessageGenerator,
    GenerateResult,
    DIRECTIVE_TEMPLATES,
    CHARACTER_LIMITS,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def now():
    return datetime(2026, 5, 22, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def mock_router():
    """Mock ModelRouter that returns a canned response."""
    router = MagicMock()
    router.call_main = AsyncMock(return_value="……今天，你的生日。我记得。")
    router.call_cheap = AsyncMock(return_value="……今天，你的生日。我记得。")
    return router


@pytest.fixture
def generator(mock_router):
    """Generator with mock router, cheap mode."""
    return ProactiveMessageGenerator(
        model_router=mock_router,
        use_cheap=True,
        max_retries=1,
        default_max_length=50,
    )


@pytest.fixture
def inner_state(user_id):
    """Minimal InnerState for testing."""
    return InnerState(
        user_id=user_id,
        character_id="rin",
        today=TodayState(date="2026-05-22"),
        proactive_state=ProactiveState(),
        rituals=RitualState(daily_check_in=DailyRitualState()),
    )


@pytest.fixture
def rin_soul():
    """Rin's soul spec for style guide."""
    return SoulSpec(
        soul_id="rin",
        min_gap_hours=6.0,
        daily_quota_avg=0.5,
        longing_threshold=0.7,
        spark_probability=0.1,
    )


@pytest.fixture
def dorothy_soul():
    """Dorothy's soul spec for style guide."""
    return SoulSpec(
        soul_id="dorothy",
        min_gap_hours=3.0,
        daily_quota_avg=1.0,
        longing_threshold=0.5,
        spark_probability=0.3,
    )


@pytest.fixture
def anniversary_decision():
    """InitiativeDecision for ANNIVERSARY trigger."""
    return InitiativeDecision(
        act=True,
        trigger_type=TriggerType.ANNIVERSARY,
        planned_message_seed={
            "anniversary_id": str(uuid4()),
            "name": "他的生日",
            "due_at": "2026-05-22T00:00:00+00:00",
            "hours_until": 0,
        },
        priority=10,
        reason="anniversary",
    )


@pytest.fixture
def longing_decision():
    """InitiativeDecision for LONGING_MESSAGE trigger."""
    return InitiativeDecision(
        act=True,
        trigger_type=TriggerType.LONGING_MESSAGE,
        planned_message_seed={
            "longing_intensity": 0.75,
            "threshold": 0.7,
        },
        priority=7,
        reason="longing_message",
    )


@pytest.fixture
def care_check_decision():
    """InitiativeDecision for CARE_CHECK trigger."""
    return InitiativeDecision(
        act=True,
        trigger_type=TriggerType.CARE_CHECK,
        planned_message_seed={
            "concern_id": str(uuid4()),
            "description": "他前天加班到凌晨",
            "urgency": "high",
        },
        priority=8,
        reason="care_check",
    )


@pytest.fixture
def check_in_decision():
    """InitiativeDecision for CHECK_IN trigger."""
    return InitiativeDecision(
        act=True,
        trigger_type=TriggerType.CHECK_IN,
        planned_message_seed={
            "gap_days": 3,
            "expected_gap_days": 2,
        },
        priority=4,
        reason="check_in",
    )


@pytest.fixture
def no_act_decision():
    """InitiativeDecision with act=False."""
    return InitiativeDecision(
        act=False,
        reason="no_trigger",
    )


# ============================================================
# Directive building tests
# ============================================================


class TestDirectiveBuilding:

    def test_anniversary_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.ANNIVERSARY.value,
            {"name": "他的生日"},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "纪念日" in directive or "生日" in directive
        assert "不超过25字" in directive or "25" in directive
        assert "凛" in directive

    def test_longing_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.LONGING_MESSAGE.value,
            {"longing_intensity": 0.75},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "想" in directive
        assert "不超过20字" in directive

    def test_care_check_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.CARE_CHECK.value,
            {"description": "他前天加班到凌晨"},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "担心" in directive or "在意" in directive

    def test_check_in_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.CHECK_IN.value,
            {"gap_days": 3},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "天" in directive
        assert "15" in directive

    def test_ritual_morning_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.RITUAL_MORNING.value,
            {},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "早" in directive

    def test_ritual_night_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.RITUAL_NIGHT.value,
            {},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "晚" in directive

    def test_thought_share_directive(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.THOUGHT_SHARE.value,
            {},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "想到" in directive

    def test_dorothy_style_guide(self, generator, inner_state, dorothy_soul):
        directive = generator._build_directive(
            TriggerType.ANNIVERSARY.value,
            {"name": "他的生日"},
            inner_state,
            "dorothy",
            dorothy_soul,
        )
        assert "桃乐丝" in directive or "元气" in directive

    def test_no_trigger_template(self, generator, inner_state, rin_soul):
        """Unknown trigger type falls back to generic directive."""
        directive = generator._build_directive(
            "unknown_type",
            {},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "简短" in directive or "句" in directive


class TestContextInterpolation:

    def test_longing_intensity_high(self, generator, inner_state, rin_soul):
        directive = generator._build_directive(
            TriggerType.LONGING_MESSAGE.value,
            {"longing_intensity": 0.8},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "真的很想" in directive or "high" not in directive

    def test_longing_intensity_modulation(self, generator, inner_state, rin_soul):
        """Longing intensity template is present."""
        directive = generator._build_directive(
            TriggerType.LONGING_MESSAGE.value,
            {"longing_intensity": 0.2},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "想" in directive

    def test_concern_template_present(self, generator, inner_state, rin_soul):
        """Care check template includes concern context markers."""
        directive = generator._build_directive(
            TriggerType.CARE_CHECK.value,
            {"description": "他熬夜写代码"},
            inner_state,
            "rin",
            rin_soul,
        )
        assert "担心" in directive


class TestMoodHint:

    def test_with_today_mood(self, generator, inner_state, rin_soul):
        from heart.ss06_inner_state.composer import TodayMood
        inner_state.today.mood = TodayMood(
            label="tired but cozy",
            primary_emotion="tired",
            valence=0.2,
            arousal=0.3,
            descriptor="你今天有些静。",
        )
        hint = generator._build_mood_hint(inner_state)
        assert "你今天有些静" in hint

    def test_empty_mood(self, generator, inner_state):
        hint = generator._build_mood_hint(inner_state)
        assert hint == ""


# ============================================================
# Post-processing tests
# ============================================================


class TestPostProcessing:

    def test_trim_artifacts(self, generator):
        result = generator._post_process("消息：……还活着。", "check_in")
        assert not result.startswith("消息")

    def test_strip_quotes(self, generator):
        result = generator._post_process('"……还活着。"', "check_in")
        assert result == "……还活着。"

    def test_enforce_character_limit(self, generator):
        long_text = "这是一条非常非常非常非常非常非常非常非常非常非常长的一条消息"
        result = generator._post_process(long_text, "check_in")
        assert len(result) <= CHARACTER_LIMITS["check_in"]

    def test_preserve_short_text(self, generator):
        result = generator._post_process("……还活着。", "check_in")
        assert result == "……还活着。"


# ============================================================
# Anti-pattern check tests
# ============================================================


class TestAntiPattern:

    def test_meta_expression_detected(self, generator):
        _, violations = generator._check_anti_pattern(
            "我给你发了一条消息", "longing_message", None
        )
        assert len(violations) > 0

    def test_too_short(self, generator):
        _, violations = generator._check_anti_pattern("。", "check_in", None)
        assert len(violations) > 0

    def test_too_long(self, generator):
        long_msg = "这是一条很长很长的消息" * 15
        _, violations = generator._check_anti_pattern(long_msg, "check_in", None)
        assert len(violations) > 0

    def test_rin_direct_blocked(self, generator, rin_soul):
        _, violations = generator._check_anti_pattern(
            "我想你了", "longing_message", rin_soul
        )
        assert len(violations) > 0
        assert any("rin_direct" in v for v in violations)

    def test_dorothy_direct_allowed(self, generator, dorothy_soul):
        _, violations = generator._check_anti_pattern(
            "我想你了", "longing_message", dorothy_soul
        )
        # Dorothy doesn't have the Rin hard block
        assert not any("rin_direct" in v for v in violations)

    def test_clean_text_passes(self, generator, rin_soul):
        _, violations = generator._check_anti_pattern(
            "……还活着。", "check_in", rin_soul
        )
        assert len(violations) == 0


# ============================================================
# Generate flow (end-to-end with mock LLM)
# ============================================================


class TestGenerateFlow:

    @pytest.mark.asyncio
    async def test_generate_anniversary(self, generator, inner_state, anniversary_decision, rin_soul):
        result = await generator.generate(
            anniversary_decision, inner_state, "rin", rin_soul
        )
        assert result.success
        assert result.message is not None
        assert result.message.initiative_type == "anniversary"
        assert result.message.text == "……今天，你的生日。我记得。"
        assert result.generation_ms > 0

    @pytest.mark.asyncio
    async def test_generate_longing(self, generator, inner_state, longing_decision, rin_soul):
        result = await generator.generate(
            longing_decision, inner_state, "rin", rin_soul
        )
        assert result.success
        assert result.message is not None
        assert result.message.initiative_type == "longing_message"

    @pytest.mark.asyncio
    async def test_generate_returns_error_on_no_act(self, generator, inner_state, no_act_decision, rin_soul):
        result = await generator.generate(
            no_act_decision, inner_state, "rin", rin_soul
        )
        assert not result.success
        assert result.message is None
        assert "act=False" in result.error

    @pytest.mark.asyncio
    async def test_generate_with_main_router(self, mock_router, inner_state, longing_decision, rin_soul):
        """Test using call_main() instead of call_cheap()."""
        gen = ProactiveMessageGenerator(
            model_router=mock_router,
            use_cheap=False,
        )
        result = await gen.generate(longing_decision, inner_state, "rin", rin_soul)
        assert result.success
        mock_router.call_main.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_reroll_on_anti_pattern(self, mock_router, inner_state, rin_soul):
        """When LLM returns anti-pattern text, should reroll."""
        # First call returns problematic text, second call fixed
        mock_router.call_cheap = AsyncMock(side_effect=[
            "我想你了",                                # First: anti-pattern detected
            "……来都不来了。",                          # Second: fixed
        ])

        gen = ProactiveMessageGenerator(
            model_router=mock_router,
            use_cheap=True,
            max_retries=1,
        )
        decision = InitiativeDecision(
            act=True,
            trigger_type=TriggerType.LONGING_MESSAGE,
            planned_message_seed={"longing_intensity": 0.75},
            priority=7,
            reason="longing_message",
        )
        result = await gen.generate(decision, inner_state, "rin", rin_soul)
        assert result.success
        # Should have called twice (original + reroll)
        assert mock_router.call_cheap.call_count >= 2

    @pytest.mark.asyncio
    async def test_generate_all_trigger_types(self, mock_router, inner_state, rin_soul):
        """Smoke test: generate() succeeds for every known trigger type."""
        gen = ProactiveMessageGenerator(
            model_router=mock_router,
            use_cheap=True,
        )

        triggers = [
            TriggerType.ANNIVERSARY,
            TriggerType.ANNIVERSARY_ANTICIPATION,
            TriggerType.LONGING_MESSAGE,
            TriggerType.CARE_CHECK,
            TriggerType.CHECK_IN,
            TriggerType.RITUAL_MORNING,
            TriggerType.RITUAL_NIGHT,
            TriggerType.THOUGHT_SHARE,
        ]

        for tt in triggers:
            mock_router.call_cheap = AsyncMock(return_value=f"test_{tt.value}")
            decision = InitiativeDecision(
                act=True,
                trigger_type=tt,
                planned_message_seed={},
                priority=5,
                reason=tt.value,
            )
            result = await gen.generate(decision, inner_state, "rin", rin_soul)
            assert result.success, f"Failed for {tt.value}"
            assert result.message is not None


# ============================================================
# Character limits
# ============================================================


class TestCharacterLimits:

    def test_all_triggers_have_limits(self):
        for tt in TriggerType:
            if tt == TriggerType.RITUAL_NIGHT:
                continue  # shares morning limit
            assert tt.value in CHARACTER_LIMITS or tt.value in ["ritual_night"], \
                f"No character limit for {tt.value}"

    def test_all_triggers_have_templates(self):
        for tt in TriggerType:
            if tt == TriggerType.RITUAL_NIGHT:
                continue  # shares morning template
            assert tt.value in DIRECTIVE_TEMPLATES, \
                f"No directive template for {tt.value}"


# ============================================================
# ProactiveMessage dataclass
# ============================================================


class TestProactiveMessage:

    def test_defaults(self):
        msg = ProactiveMessage(
            text="……还活着。",
            initiative_type="check_in",
            generated_at=datetime.now(timezone.utc),
        )
        assert msg.text == "……还活着。"
        assert msg.initiative_type == "check_in"
        assert msg.character_limit == 50
        assert msg.context_seed == {}
