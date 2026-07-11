"""Unit tests for Layer 1.5 cognitive style injection in _build_system_prompt.

Covers:
- sentence_length.baseline as string enum ("short", "long", None)
- expr missing sentence_length entirely
- float fields (emotional_directness, hedge_words, etc.) are guarded with isinstance
- Exception in layer 1.5 block does NOT propagate (try/except outer guard)
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


def _make_soul_spec(sliders: SliderSet | None = None):
    draft = CharacterDraft(
        display_name=DisplayNameDraft(zh="测试", en="Test"),
        persona="这是一段足够长的人设描述，用于测试确定性展开器能否正确处理。" * 2,
        greeting_style=GreetingStyle.warm,
        sliders=sliders or SliderSet(),
        locale="zh",
    )
    return build_soul_spec_from_draft(draft, character_id="test_layer_1_5", now="2026-07-11")


def _run_build_prompt(soul_spec) -> str:
    """Call _build_system_prompt with empty context blocks (tests only care about Layer 1.5)."""
    service = ComposerService.__new__(ComposerService)
    return service._build_system_prompt(
        anchor=AnchorContextBlock(),
        memory=MemoryContextBlock(),
        emotion=EmotionContextBlock(),
        relationship=RelationshipContextBlock(),
        inner_state=InnerStateContextBlock(),
        soul_spec=soul_spec,
    )


def test_short_baseline_produces_short_hint():
    """baseline='short' (sl=1) should produce 说话简短 hint."""
    spec = _make_soul_spec(SliderSet(talkativeness=0.1))
    cs = getattr(spec, "cognitive_style", None)
    if cs is None:
        pytest.skip("cognitive_style not generated for this slider set")
    if hasattr(cs, "expression") and hasattr(cs.expression, "sentence_length"):
        cs.expression.sentence_length.baseline = "short"
    prompt = _run_build_prompt(spec)
    assert isinstance(prompt, str)
    assert "说话简短" in prompt


def test_long_baseline_produces_verbose_hint():
    """baseline='long' (sl=3) should produce 表达详细 hint."""
    spec = _make_soul_spec(SliderSet(talkativeness=0.9))
    cs = getattr(spec, "cognitive_style", None)
    if cs is None:
        pytest.skip("cognitive_style not generated for this slider set")
    if hasattr(cs, "expression") and hasattr(cs.expression, "sentence_length"):
        cs.expression.sentence_length.baseline = "long"
    prompt = _run_build_prompt(spec)
    assert isinstance(prompt, str)
    assert "表达详细" in prompt


def test_none_baseline_does_not_crash():
    """baseline=None should silently skip the sentence_length hint."""
    spec = _make_soul_spec()
    cs = getattr(spec, "cognitive_style", None)
    if cs is None:
        pytest.skip("no cognitive_style")
    if hasattr(cs, "expression") and hasattr(cs.expression, "sentence_length"):
        cs.expression.sentence_length.baseline = None
    prompt = _run_build_prompt(spec)
    assert isinstance(prompt, str)


def test_missing_sentence_length_does_not_crash():
    """cognitive_style.expression missing sentence_length entirely should not crash."""
    spec = _make_soul_spec()
    cs = getattr(spec, "cognitive_style", None)
    if cs is None:
        pytest.skip("no cognitive_style")
    if hasattr(cs, "expression"):
        try:
            del cs.expression.sentence_length
        except AttributeError:
            pass
        if hasattr(cs.expression, "sentence_length"):
            cs.expression.sentence_length = None
    prompt = _run_build_prompt(spec)
    assert isinstance(prompt, str)


def test_string_comparison_does_not_raise_type_error():
    """Regression: the old code did 'sl < 30' where sl='short', causing TypeError."""
    spec = _make_soul_spec()
    cs = getattr(spec, "cognitive_style", None)
    if cs is None:
        pytest.skip("no cognitive_style")
    if hasattr(cs, "expression"):
        expr = cs.expression
        for attr in ("sentence_length", "emotional_directness", "hedge_words", "use_of_metaphor"):
            obj = getattr(expr, attr, None)
            if obj is not None and hasattr(obj, "baseline"):
                obj.baseline = "short"  # wrong type for float fields
    # Must not raise TypeError
    prompt = _run_build_prompt(spec)
    assert isinstance(prompt, str)
