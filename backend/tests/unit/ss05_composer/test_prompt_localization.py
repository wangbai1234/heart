"""Prompt catalogs must preserve identity, boundaries and source data across locales."""

import re
from string import Formatter

import pytest

from heart.ss01_soul.draft import CharacterDraft, DisplayNameDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss05_composer.directive_compiler import DirectiveCompiler
from heart.ss05_composer.prompt_resources import prompt_catalog, prompt_text
from heart.ss05_composer.service import (
    AnchorContextBlock,
    ComposerService,
    EmotionContextBlock,
    InnerStateContextBlock,
    MemoryContextBlock,
    RelationshipContextBlock,
    _ADULT_CONTENT_DIRECTIVE,
    _STANDARD_CONTENT_DIRECTIVE,
)


@pytest.mark.parametrize("language", ["en", "vi", "bn"])
def test_catalog_completeness_and_placeholder_contract(language):
    baseline = prompt_catalog("zh")
    localized = prompt_catalog(language)
    assert localized.keys() == baseline.keys()
    fields = lambda s: {field for _, field, _, _ in Formatter().parse(s) if field}
    for key, value in localized.items():
        assert value.strip(), key
        assert fields(value) == fields(baseline[key]), key
        assert not re.search(r"[\u4e00-\u9fff]", value), key
    assert prompt_text(language, "identity", v0="名字{literal}").count("名字{literal}") == 1


def test_chinese_boundaries_unchanged_and_unknown_catalog_falls_back():
    assert prompt_text("zh", "adult_boundary") == _ADULT_CONTENT_DIRECTIVE
    assert prompt_text("zh", "standard_boundary") == _STANDARD_CONTENT_DIRECTIVE
    assert prompt_catalog("../../private") == prompt_catalog("en")


@pytest.mark.parametrize("language", ["en", "vi", "bn"])
@pytest.mark.parametrize("tier", ["free", "plus"])
def test_localized_builder_preserves_source_data_identity_and_constraints(language, tier):
    persona = "三十岁的作家。旧书店里的故事{不可改写}。"
    spec = build_soul_spec_from_draft(
        CharacterDraft(display_name=DisplayNameDraft(zh="林舟"), persona=persona, locale="zh"),
        character_id="localized_test",
        now="2026-10-13",
    )
    service = ComposerService.__new__(ComposerService)
    service._sanitizer_config = None
    service._directive_compiler = DirectiveCompiler()
    prompt = service._build_system_prompt(
        anchor=AnchorContextBlock(hard_never=["SECRET_FORBIDDEN_LITERAL", "永远"]),
        memory=MemoryContextBlock(
            retrieved_memories=[{"text": "上次去了旧书店。"}],
            historical_identity_memories=[{"text": "以前叫阿明。"}],
        ),
        emotion=EmotionContextBlock(emotion_summary="很开心"),
        relationship=RelationshipContextBlock(relationship_phase="cold_war"),
        inner_state=InnerStateContextBlock(internal_monologue="今天还想聊书。"),
        soul_spec=spec,
        response_language=language,
        membership_tier=tier,
        user_mask={"name": "小林", "gender": "male", "bio": "现在是一位成年书商。"},
    )
    for source in (
        persona,
        "上次去了旧书店。",
        "以前叫阿明。",
        "现在是一位成年书商。",
        "今天还想聊书。",
    ):
        assert source in prompt
    assert "SECRET_FORBIDDEN_LITERAL" not in prompt
    assert prompt_text(language, "constraint_permanent_promise") in prompt
    assert prompt_text(language, "constraint_OTHER") in prompt
    assert (
        prompt_text(language, "adult_boundary" if tier == "plus" else "standard_boundary") in prompt
    )
    assert prompt_text(language, "cold_war") in prompt
    address = prompt_text(language, "address", v0="小林", v1="小林")
    assert prompt.index(address) > prompt.index("以前叫阿明。")
    assert prompt.endswith(prompt_text(language, "generation"))
    assert "【当前用户身份】" not in prompt
    assert "你是 林舟" not in prompt
