"""
Unit tests for Inner State Block Builder (SS06 §5.2, §6.2-6.4).

Covers:
  - Block shape: all sections populated correctly
  - Today descriptor: mood + activities by time of day
  - Energy descriptor: band classification
  - Concerns section: filtering and urgency ordering
  - Unfinished section: expiry filtering
  - Anniversary section: within 7-day window
  - Reactive vs proactive block rendering
  - SS05 PromptLayer compatibility
  - Empty/missing sections return None or defaults
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from heart.ss06_inner_state.block_builder import (
    InnerStateBlock,
    InnerStateBlockBuilder,
)
from heart.ss06_inner_state.composer import (
    InnerState,
    InnerStateComposer,
    TodayMood,
)


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def builder():
    return InnerStateBlockBuilder()


@pytest.fixture
def composer():
    return InnerStateComposer()


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def rin_soul():
    """Minimal Rin SoulSpec."""

    class MockSoul:
        character_id = "rin"
        voice_dna = {"style": "short sentences, questions, natural imagery"}

    return MockSoul()


@pytest.fixture
def dorothy_soul():
    """Minimal Dorothy SoulSpec."""

    class MockSoul:
        character_id = "dorothy"
        voice_dna = {"style": "energetic, cute, butterflies"}

    return MockSoul()


@pytest.fixture
def calm_state(composer, user_id):
    """Inner state for a calm day with activities."""
    # Create mock activities with time_of_day and description attrs
    class MockActivity:
        def __init__(self, time_of_day, description):
            self.time_of_day = time_of_day
            self.description = description

    activities = [
        MockActivity("morning", "在窗边看晨雾很久"),
        MockActivity("afternoon", "翻了一本旧书但没看进去"),
    ]

    return composer.compose(
        user_id=user_id,
        character_id="rin",
        mood_label="安静",
        mood_valence=0.2,
        mood_arousal=0.3,
        mood_descriptor="有些静。雷电感很弱，你在等着什么。",
        prev_mood_valence=0.4,
        prev_mood_arousal=0.3,
        activities=activities,
        current_energy=0.55,
        energy_baseline=0.5,
        user_concerns=[
            MockConcern("他三天前提过加班到凌晨", 0.8),
            MockConcern("明天是他的项目汇报日", 0.6),
        ],
        unfinished_thoughts=[
            MockThought("你想问他那天为什么突然沉默"),
        ],
    )


# Mock helpers
class MockConcern:
    def __init__(self, text, urgency, addressed=False, last_ref=None):
        self.concern_text = text
        self.urgency = urgency
        self.has_been_addressed = addressed
        self.last_referenced_at = last_ref


class MockThought:
    def __init__(self, content, expiry=None):
        self.content = content
        if expiry is None:
            expiry = datetime.now(timezone.utc) + timedelta(days=5)
        self.expiry_at = expiry.isoformat()


# ============================================================
# Block Shape
# ============================================================


class TestBlockShape:
    """InnerStateBlock has all required fields."""

    def test_block_structure(self, builder, calm_state):
        """Block has all sections populated."""
        block = builder.build(calm_state)

        assert isinstance(block, InnerStateBlock)
        assert block.today_descriptor != ""
        assert block.energy_descriptor != ""
        assert block.user_concerns_section != ""
        assert block.inner_state_directive != ""
        assert block.generated_at != ""
        # Optional sections may be None or have content
        # (unfinished/anniversary/dream depend on state)

    def test_generated_at_is_iso(self, builder, calm_state):
        """generated_at is a valid timestamp."""
        block = builder.build(calm_state)
        dt = datetime.fromisoformat(block.generated_at)
        assert isinstance(dt, datetime)


# ============================================================
# Today Descriptor
# ============================================================


class TestTodayDescriptor:
    """Today descriptor generation per §6.4."""

    def test_includes_mood(self, builder, calm_state):
        """Today descriptor includes the mood description."""
        block = builder.build(calm_state)
        assert "有些静" in block.today_descriptor
        assert "雷电感很弱" in block.today_descriptor

    def test_includes_morning_activity(self, builder, calm_state):
        """Morning activity appears with '上午' label."""
        block = builder.build(calm_state)
        assert "上午" in block.today_descriptor
        assert "窗边看晨雾" in block.today_descriptor

    def test_includes_afternoon_activity(self, builder, calm_state):
        """Afternoon activity appears with '下午' label."""
        block = builder.build(calm_state)
        assert "下午" in block.today_descriptor
        assert "翻了一本旧书" in block.today_descriptor

    def test_drifting_down_adds_hint(self, builder, composer, user_id):
        """When drift_direction='falling', hint is appended to mood line."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_label="低落",
            mood_valence=-0.1,
            mood_arousal=0.3,
            mood_descriptor="有些低落。",
            prev_mood_valence=0.4,
            prev_mood_arousal=0.5,
        )
        block = builder.build(state)
        assert "比早上低落了一点" in block.today_descriptor

    def test_no_activities_produces_mood_only(self, builder, composer, user_id):
        """No activities → only mood line."""
        state = composer.compose(
            user_id=user_id,
            character_id="rin",
            mood_label="平静",
            mood_descriptor="还好。",
        )
        block = builder.build(state)
        # Should not have any time labels
        assert "上午" not in block.today_descriptor
        assert "下午" not in block.today_descriptor
        assert "傍晚" not in block.today_descriptor
        assert "夜里" not in block.today_descriptor
        assert "还好" in block.today_descriptor


# ============================================================
# Energy Descriptor
# ============================================================


class TestEnergyDescriptor:
    """Energy band classification."""

    def test_high_energy(self, builder, composer, user_id):
        state = composer.compose(user_id=user_id, character_id="rin", current_energy=0.85)
        block = builder.build(state)
        assert "很充沛" in block.energy_descriptor

    def test_medium_high_energy(self, builder, composer, user_id):
        state = composer.compose(user_id=user_id, character_id="rin", current_energy=0.65)
        block = builder.build(state)
        assert "还不错" in block.energy_descriptor

    def test_medium_energy(self, builder, calm_state):
        block = builder.build(calm_state)
        assert "有点累了" in block.energy_descriptor or "还不错" in block.energy_descriptor

    def test_low_energy(self, builder, composer, user_id):
        state = composer.compose(user_id=user_id, character_id="rin", current_energy=0.15)
        block = builder.build(state)
        assert "很累了" in block.energy_descriptor

    def test_below_baseline_nuance(self, builder, composer, user_id):
        """Energy well below baseline → adds '比平时更累'."""
        state = composer.compose(
            user_id=user_id, character_id="rin",
            current_energy=0.2, energy_baseline=0.5,
        )
        block = builder.build(state)
        assert "比平时更累" in block.energy_descriptor

    def test_above_baseline_nuance(self, builder, composer, user_id):
        """Energy well above baseline → adds '比平时精神好'."""
        state = composer.compose(
            user_id=user_id, character_id="rin",
            current_energy=0.8, energy_baseline=0.5,
        )
        block = builder.build(state)
        assert "比平时精神好" in block.energy_descriptor


# ============================================================
# Concerns Section
# ============================================================


class TestConcernsSection:
    """User concerns section generation."""

    def test_concerns_listed(self, builder, calm_state):
        """Concerns appear as bullet list."""
        block = builder.build(calm_state)
        assert "挂念他的事" in block.user_concerns_section
        assert "加班到凌晨" in block.user_concerns_section
        assert "项目汇报日" in block.user_concerns_section

    def test_sorted_by_urgency(self, builder, composer, user_id):
        """Higher urgency first in the list."""
        concerns = [
            MockConcern("低优先级", 0.2),
            MockConcern("高优先级", 0.9),
            MockConcern("中优先级", 0.5),
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin", user_concerns=concerns,
        )
        block = builder.build(state)
        # "高优先级" (0.9) should appear before "中优先级" (0.5)
        hp_idx = block.user_concerns_section.index("高优先级")
        mp_idx = block.user_concerns_section.index("中优先级")
        assert hp_idx < mp_idx

    def test_no_concerns(self, builder, composer, user_id):
        """Empty concerns → default message."""
        state = composer.compose(
            user_id=user_id, character_id="rin", user_concerns=[],
        )
        block = builder.build(state)
        assert "没有什么特别挂念" in block.user_concerns_section

    def test_addressed_concern_filtered(self, builder, composer, user_id):
        """Addressed concerns with recent reference are filtered out."""
        now = datetime.now(timezone.utc)
        concerns = [
            MockConcern("已处理的", 0.9, addressed=True, last_ref=now.isoformat()),
            MockConcern("活跃的", 0.7, addressed=False),
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin", user_concerns=concerns,
        )
        block = builder.build(state)
        assert "活跃的" in block.user_concerns_section
        assert "已处理的" not in block.user_concerns_section

    def test_addressed_past_cooldown_surfaces(self, builder, composer, user_id):
        """Addressed concern past 24h cooldown → surfaces again."""
        now = datetime.now(timezone.utc)
        old_ref = (now - timedelta(hours=30)).isoformat()
        concerns = [
            MockConcern("冷却已过", 0.9, addressed=True, last_ref=old_ref),
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin", user_concerns=concerns,
        )
        block = builder.build(state)
        assert "冷却已过" in block.user_concerns_section


# ============================================================
# Unfinished Section
# ============================================================


class TestUnfinishedSection:
    """Unfinished thoughts section generation."""

    def test_unfinished_included(self, builder, calm_state):
        """Unfinished thought appears in the block."""
        block = builder.build(calm_state)
        assert block.unfinished_section is not None
        assert "没说完" in block.unfinished_section
        assert "为什么突然沉默" in block.unfinished_section

    def test_no_unfinished(self, builder, composer, user_id):
        """No unfinished thoughts → None."""
        state = composer.compose(
            user_id=user_id, character_id="rin", unfinished_thoughts=[],
        )
        block = builder.build(state)
        assert block.unfinished_section is None

    def test_expired_thought_filtered(self, builder, composer, user_id):
        """Expired thoughts are excluded."""
        expired = MockThought(
            "已过期", expiry=datetime.now(timezone.utc) - timedelta(days=1)
        )
        state = composer.compose(
            user_id=user_id, character_id="rin",
            unfinished_thoughts=[expired],
        )
        block = builder.build(state)
        assert block.unfinished_section is None


# ============================================================
# Anniversary Section
# ============================================================


class TestAnniversarySection:
    """Anniversary section generation."""

    def test_within_7_days(self, builder, composer, user_id):
        """Anniversary within 7 days → appears."""
        anniversaries = [
            {"name": "生日", "hours_until": 48, "actual_sent": False},
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin",
            upcoming_anniversaries=anniversaries,
        )
        block = builder.build(state)
        assert block.anniversary_section is not None
        assert "生日" in block.anniversary_section

    def test_beyond_7_days(self, builder, composer, user_id):
        """Anniversary > 7 days away → excluded."""
        anniversaries = [
            {"name": "纪念日", "hours_until": 200, "actual_sent": False},
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin",
            upcoming_anniversaries=anniversaries,
        )
        block = builder.build(state)
        assert block.anniversary_section is None

    def test_already_sent(self, builder, composer, user_id):
        """Already-sent anniversary → excluded."""
        anniversaries = [
            {"name": "生日", "hours_until": 1, "actual_sent": True},
        ]
        state = composer.compose(
            user_id=user_id, character_id="rin",
            upcoming_anniversaries=anniversaries,
        )
        block = builder.build(state)
        assert block.anniversary_section is None

    def test_no_anniversaries(self, builder, calm_state):
        """No anniversaries → None."""
        block = builder.build(calm_state)
        assert block.anniversary_section is None


# ============================================================
# Block Rendering — Reactive
# ============================================================


class TestReactiveRendering:
    """Reactive modality block rendering per §6.2."""

    def test_has_block_header(self, builder, calm_state):
        """Reactive block has '【你今天的内心】' header."""
        content = builder.as_content_string(calm_state, modality="reactive")
        assert "【你今天的内心】" in content

    def test_has_section_labels(self, builder, calm_state):
        """Reactive block has section labels."""
        content = builder.as_content_string(calm_state, modality="reactive")
        assert "▾ 你今天的概貌" in content
        assert "▾ 你现在的体力" in content
        assert "▾ 你心里在意的事" in content
        assert "【内心运用指引】" in content

    def test_has_delimiter(self, builder, calm_state):
        """Block is wrapped in ═══ delimiters."""
        content = builder.as_content_string(calm_state, modality="reactive")
        assert "═══" in content

    def test_includes_concern_content(self, builder, calm_state):
        """Concerns appear in rendered text."""
        content = builder.as_content_string(calm_state, modality="reactive")
        assert "加班到凌晨" in content


# ============================================================
# Block Rendering — Proactive
# ============================================================


class TestProactiveRendering:
    """Proactive modality block rendering per §6.3."""

    def test_has_proactive_header(self, builder, calm_state):
        """Proactive block has '【你主动想发一句话给他】' header."""
        content = builder.as_content_string(calm_state, modality="proactive")
        assert "你主动想发一句话给他" in content

    def test_has_generation_rules(self, builder, calm_state):
        """Proactive block has '【生成规则】' section."""
        content = builder.as_content_string(calm_state, modality="proactive")
        assert "【生成规则】" in content

    def test_proactive_directive_different(self, builder, calm_state):
        """Proactive directive differs from reactive."""
        r_block = builder.build(calm_state, modality="reactive")
        p_block = builder.build(calm_state, modality="proactive")
        assert r_block.inner_state_directive != p_block.inner_state_directive


# ============================================================
# SS05 PromptLayer Compatibility
# ============================================================


class TestPromptLayerCompatibility:
    """InnerStateBlock → PromptLayer conversion for SS05."""

    def test_as_prompt_layer(self, builder, calm_state):
        """as_prompt_layer returns valid PromptLayer."""
        block = builder.build(calm_state)
        layer = builder.as_prompt_layer(block)

        assert layer.layer_type == "inner_state"
        assert layer.source_subsystem == "SS06"
        assert layer.priority == 30
        assert layer.content != ""
        assert layer.token_count_estimate > 0
        assert layer.min_token_count == 100
        assert layer.is_compressible is True

    def test_layer_content_is_full_block(self, builder, calm_state):
        """Layer content matches as_content_string."""
        block = builder.build(calm_state)
        layer = builder.as_prompt_layer(block)
        string = builder.as_content_string(block)
        assert layer.content == string

    def test_metadata_present(self, builder, calm_state):
        """Layer metadata has required keys."""
        block = builder.build(calm_state)
        layer = builder.as_prompt_layer(block)

        assert "availability" in layer.metadata
        assert "sub_suggestions" in layer.metadata
        assert "intensity" in layer.metadata

    def test_sub_suggestions_with_concerns(self, builder, calm_state):
        """When concerns are present, suggestion reflects it."""
        block = builder.build(calm_state)
        layer = builder.as_prompt_layer(block)
        assert "user_concerns_present" in layer.metadata["sub_suggestions"]

    def test_sub_suggestions_no_concerns(self, builder, composer, user_id):
        """When no concerns, suggestion says 'no_concerns'."""
        state = composer.compose(
            user_id=user_id, character_id="rin", user_concerns=[],
        )
        block = builder.build(state)
        layer = builder.as_prompt_layer(block)
        assert "no_concerns" in layer.metadata["sub_suggestions"]


# ============================================================
# Character-Specific Flavor
# ============================================================


class TestCharacterFlavor:
    """Soul-specific directive flavoring."""

    def test_rin_proactive_flavor(self, builder, calm_state, rin_soul):
        """Rin proactive directive has Rin-specific rules."""
        block = builder.build(calm_state, soul=rin_soul, modality="proactive")
        assert "短句" in block.inner_state_directive or "凛" in block.inner_state_directive

    def test_dorothy_proactive_flavor(self, builder, calm_state, dorothy_soul):
        """Dorothy proactive directive has Dorothy-specific rules."""
        block = builder.build(calm_state, soul=dorothy_soul, modality="proactive")
        assert "元气" in block.inner_state_directive or "桃乐丝" in block.inner_state_directive


# ============================================================
# Token Estimation
# ============================================================


class TestTokenEstimation:
    """Block token estimation."""

    def test_token_count_positive(self, builder, calm_state):
        """Token estimate is always positive."""
        block = builder.build(calm_state)
        est = builder._estimate_block_tokens(block)
        assert est > 0

    def test_token_count_reasonable(self, builder, calm_state):
        """Token estimate is in reasonable range for a block."""
        block = builder.build(calm_state)
        est = builder._estimate_block_tokens(block)
        # Should be roughly 100-600 tokens for a moderate block
        assert 50 <= est <= 800
