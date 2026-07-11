"""End-to-end tests: slider values → spec_builder → _build_system_prompt output.

Unlike test_service_layer_1_5.py (which patches baselines directly), these tests
verify the full pipeline: SliderSet → build_soul_spec_from_draft → Layer 1.5 phrases.
No database required; _build_system_prompt is a pure function.
"""
from __future__ import annotations

import pytest

from heart.ss01_soul.draft import CharacterDraft, DisplayNameDraft, GreetingStyle, SliderSet
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss05_composer.service import (
    AnchorContextBlock,
    ComposerService,
    EmotionContextBlock,
    InnerStateContextBlock,
    MemoryContextBlock,
    RelationshipContextBlock,
)

_LONG_PERSONA = "这是一段足够长的人设描述，用于测试确定性展开器能否正确处理。" * 2


def _make_spec(sliders: SliderSet):
    draft = CharacterDraft(
        display_name=DisplayNameDraft(zh="测试角色", en="TestChar"),
        persona=_LONG_PERSONA,
        greeting_style=GreetingStyle.warm,
        sliders=sliders,
        locale="zh",
    )
    return build_soul_spec_from_draft(draft, character_id="test_e2e", now="2026-07-11")


def _prompt(sliders: SliderSet) -> str:
    spec = _make_spec(sliders)
    service = ComposerService.__new__(ComposerService)
    return service._build_system_prompt(
        anchor=AnchorContextBlock(),
        memory=MemoryContextBlock(),
        emotion=EmotionContextBlock(),
        relationship=RelationshipContextBlock(),
        inner_state=InnerStateContextBlock(),
        soul_spec=spec,
    )


# ── talkativeness → sentence_length ──────────────────────────────────────────

def test_low_talkativeness_produces_short_hint():
    """talkativeness=0 → baseline='very_short' or 'short' → 说话简短 appears."""
    prompt = _prompt(SliderSet(talkativeness=0.0))
    assert "说话简短" in prompt, f"Expected '说话简短' in prompt, got:\n{prompt}"


def test_high_talkativeness_produces_verbose_hint():
    """talkativeness=1 → baseline='long' → 表达详细 appears."""
    prompt = _prompt(SliderSet(talkativeness=1.0))
    assert "表达详细" in prompt, f"Expected '表达详细' in prompt, got:\n{prompt}"


def test_mid_talkativeness_produces_no_length_hint():
    """talkativeness=0.5 → baseline='medium' (index 2) → neither short nor verbose hint."""
    prompt = _prompt(SliderSet(talkativeness=0.5))
    assert "说话简短" not in prompt
    assert "表达详细" not in prompt


# ── warmth → emotional_directness ────────────────────────────────────────────

def test_high_warmth_produces_direct_emotion_hint():
    """warmth=1.0 → emotional_directness.baseline ≈ 1.0 > 0.7 → 情感表达直接 appears."""
    prompt = _prompt(SliderSet(warmth=1.0))
    assert "情感表达直接" in prompt, f"Expected '情感表达直接', got:\n{prompt}"


def test_low_warmth_produces_reserved_emotion_hint():
    """warmth=0.0 → emotional_directness.baseline ≈ 0.0 < 0.3 → 情感含蓄 appears."""
    prompt = _prompt(SliderSet(warmth=0.0))
    assert "情感含蓄" in prompt, f"Expected '情感含蓄', got:\n{prompt}"


def test_warmth_hints_are_different():
    """High vs low warmth characters must produce different prompt styles."""
    high = _prompt(SliderSet(warmth=1.0))
    low = _prompt(SliderSet(warmth=0.0))
    assert high != low, "warmth=1.0 and warmth=0.0 should produce different prompts"
    # Cross-assertion: hints must not bleed across characters.
    assert "情感表达直接" not in low
    assert "情感含蓄" not in high


# ── directness → hedge_words ─────────────────────────────────────────────────

def test_high_directness_produces_no_hedging_hint():
    """directness=1.0 → hedge_baseline=0.0 < 0.25 → 说话直接 appears."""
    prompt = _prompt(SliderSet(directness=1.0))
    assert "说话直接" in prompt, f"Expected '说话直接', got:\n{prompt}"


def test_low_directness_produces_hedging_hint():
    """directness=0.0 → hedge_baseline=1.0 > 0.65 → 说话委婉 appears."""
    prompt = _prompt(SliderSet(directness=0.0))
    assert "说话委婉" in prompt, f"Expected '说话委婉', got:\n{prompt}"


# ── playfulness → use_of_metaphor ────────────────────────────────────────────

def test_high_playfulness_produces_metaphor_hint():
    """playfulness=1.0 → use_of_metaphor.baseline ≈ 1.0 > 0.65 → 比喻 appears."""
    prompt = _prompt(SliderSet(playfulness=1.0))
    assert "比喻" in prompt, f"Expected '比喻' in prompt, got:\n{prompt}"


def test_low_playfulness_produces_no_metaphor_hint():
    """playfulness=0.0 → use_of_metaphor.baseline ≈ 0.0 ≤ 0.65 → no 比喻 hint."""
    prompt = _prompt(SliderSet(playfulness=0.0))
    assert "比喻和意象" not in prompt


# ── steadiness → mood_volatility ─────────────────────────────────────────────

def test_low_steadiness_produces_mood_volatility_hint():
    """steadiness=0.0 → mood_volatility ≈ 0.8 > 0.65 → 情绪起伏 appears."""
    prompt = _prompt(SliderSet(steadiness=0.0))
    assert "情绪起伏" in prompt, f"Expected '情绪起伏', got:\n{prompt}"


def test_high_steadiness_produces_no_volatility_hint():
    """steadiness=1.0 → mood_volatility ≈ 0.1 ≤ 0.65 → no 情绪起伏 hint."""
    prompt = _prompt(SliderSet(steadiness=1.0))
    assert "情绪起伏" not in prompt


# ── No TypeError on any extreme combination ───────────────────────────────────

@pytest.mark.parametrize("sliders", [
    SliderSet(warmth=0.0, talkativeness=0.0, directness=0.0, playfulness=0.0, steadiness=0.0, humor=0.0),
    SliderSet(warmth=1.0, talkativeness=1.0, directness=1.0, playfulness=1.0, steadiness=1.0, humor=1.0),
    SliderSet(warmth=0.5, talkativeness=0.5, directness=0.5, playfulness=0.5, steadiness=0.5, humor=0.5),
])
def test_no_type_error_on_extremes(sliders):
    """_build_system_prompt must never raise TypeError regardless of slider values."""
    prompt = _prompt(sliders)
    assert isinstance(prompt, str)
    assert len(prompt) > 50  # sanity: not empty
