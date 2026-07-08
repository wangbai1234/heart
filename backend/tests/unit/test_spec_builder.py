"""Unit tests for spec_builder.py (C5a).

Covers:
- Golden expand: known input → known output shape
- VoiceDNA id regex (^vd-[A-Z0-9\\-]+$)
- GoldenDialogue id regex (^gd-\\d{3}-.+$)
- NumericStyle invariants (lo < hi, lo <= baseline <= hi) for all slider values
- SoulSpec.model_validate passes for all greeting_style × slider extremes
"""

from __future__ import annotations

import re

import pytest

from heart.ss01_soul.draft import CharacterDraft, DisplayNameDraft, GreetingStyle, SliderSet
from heart.ss01_soul.schema_validator import SoulSpec
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft

VD_ID_RE = re.compile(r"^vd-[A-Z0-9\-]+$")
GD_ID_RE = re.compile(r"^gd-\d{3}-.+$")


def _make_draft(
    greeting_style: GreetingStyle = GreetingStyle.warm,
    sliders: SliderSet | None = None,
    speech_samples: list[str] | None = None,
) -> CharacterDraft:
    return CharacterDraft(
        display_name=DisplayNameDraft(zh="测试", en="Test"),
        persona="这是一段足够长的人设描述，用于测试确定性展开器能否正确处理。" * 2,
        greeting_style=greeting_style,
        speech_samples=speech_samples or [],
        sliders=sliders or SliderSet(),
        locale="zh",
    )


def _build(draft: CharacterDraft) -> SoulSpec:
    return build_soul_spec_from_draft(draft, character_id="test_ugc_build", now="2026-07-08")


# ── Golden shape tests ────────────────────────────────────────────────────────


def test_golden_expand_passes_model_validate():
    draft = _make_draft()
    spec = _build(draft)
    # Re-validate via Pydantic to ensure the spec is fully compliant
    SoulSpec.model_validate(spec.model_dump())


def test_character_id_preserved():
    draft = _make_draft()
    spec = build_soul_spec_from_draft(draft, character_id="my_char", now="2026-07-08")
    assert spec.character_id == "my_char"


def test_display_name_preserved():
    draft = _make_draft()
    spec = _build(draft)
    assert spec.display_name.zh == "测试"
    assert spec.display_name.en == "Test"


def test_spec_version_default():
    draft = _make_draft()
    spec = _build(draft)
    assert spec.spec_version == "1.0.0"


def test_meta_author_format():
    draft = _make_draft()
    spec = _build(draft)
    assert spec.meta.author.startswith("ugc:")


def test_meta_reviewers_nonempty():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.meta.reviewers) >= 1


def test_meta_changelog_nonempty():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.meta.changelog) >= 1


def test_anti_patterns_hard_never_nonempty():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.identity_anchor.anti_patterns.hard_never) >= 1


def test_softening_triggers_nonempty():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.relational_template.softening_triggers) >= 1


# ── VoiceDNA id regex ─────────────────────────────────────────────────────────


def test_voice_dna_ids_match_regex():
    draft = _make_draft(speech_samples=["こんにちは", "Hello"])
    spec = _build(draft)
    for vd in spec.identity_anchor.voice_dna:
        assert VD_ID_RE.match(vd.id), f"VoiceDNA id {vd.id!r} does not match ^vd-[A-Z0-9\\-]+$"


def test_voice_dna_at_least_3_entries():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.identity_anchor.voice_dna) >= 3


# ── GoldenDialogue id regex ───────────────────────────────────────────────────


def test_golden_dialogue_ids_match_regex():
    draft = _make_draft()
    spec = _build(draft)
    for gd in spec.test_fixtures.golden_dialogues:
        assert GD_ID_RE.match(gd.id), f"GoldenDialogue id {gd.id!r} does not match ^gd-\\d{{3}}-.+$"


def test_golden_dialogues_at_least_1():
    draft = _make_draft()
    spec = _build(draft)
    assert len(spec.test_fixtures.golden_dialogues) >= 1


# ── NumericStyle invariants ───────────────────────────────────────────────────


def _check_numeric_styles(spec: SoulSpec) -> None:
    cs = spec.cognitive_style.expression
    for style in [
        cs.verbosity,
        cs.emotional_directness,
        cs.use_of_metaphor,
        cs.hedge_words,
        cs.ellipsis_usage,
    ]:
        lo, hi = style.evolution_bound
        assert lo < hi, f"evolution_bound lo({lo}) >= hi({hi})"
        assert lo <= style.baseline <= hi, (
            f"baseline({style.baseline}) not in [{lo}, {hi}]"
        )


def test_numeric_style_invariants_default_sliders():
    spec = _build(_make_draft())
    _check_numeric_styles(spec)


@pytest.mark.parametrize(
    "slider_value",
    [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0],
)
def test_numeric_style_invariants_extreme_sliders(slider_value: float):
    sliders = SliderSet(
        warmth=slider_value,
        talkativeness=slider_value,
        directness=slider_value,
        humor=slider_value,
        playfulness=slider_value,
        steadiness=slider_value,
    )
    draft = _make_draft(sliders=sliders)
    spec = _build(draft)
    _check_numeric_styles(spec)
    # Full Pydantic re-validate
    SoulSpec.model_validate(spec.model_dump())


# ── All greeting_style × slider extremes pass model_validate ─────────────────


@pytest.mark.parametrize("style", list(GreetingStyle))
@pytest.mark.parametrize("val", [0.0, 0.5, 1.0])
def test_all_styles_all_sliders_valid(style: GreetingStyle, val: float):
    sliders = SliderSet(
        warmth=val,
        talkativeness=val,
        directness=val,
        humor=val,
        playfulness=val,
        steadiness=val,
    )
    draft = _make_draft(greeting_style=style, sliders=sliders)
    spec = _build(draft)
    SoulSpec.model_validate(spec.model_dump())
