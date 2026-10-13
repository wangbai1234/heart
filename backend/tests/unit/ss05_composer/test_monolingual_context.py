"""Test the entire assembled context, including generated defaults and history."""

import json
import re
from pathlib import Path

import pytest

from heart.ss01_soul.draft import CharacterDraft, GreetingStyle
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss03_emotion.service import EmotionService
from heart.ss05_composer.directive_compiler import DirectiveCompiler
from heart.ss05_composer.prompt_resources import prompt_text
from heart.ss05_composer.service import (
    AnchorContextBlock,
    ComposerService,
    EmotionContextBlock,
    InnerStateContextBlock,
    MemoryContextBlock,
    RelationshipContextBlock,
)

FIXTURES = json.loads(
    (Path(__file__).parents[2] / "fixtures/monolingual_characters.json").read_text()
)


@pytest.mark.parametrize("sample", FIXTURES, ids=lambda s: s["source_id"] + "-" + s["locale"])
@pytest.mark.parametrize("style", list(GreetingStyle))
def test_complete_native_payload_without_chinese_scaffolding(sample, style):
    language = sample["locale"]
    draft = CharacterDraft.model_validate(sample["draft"])
    draft.greeting_style = style
    draft.speech_samples = [sample["question"]]
    draft.age_range = "20-30"
    spec = build_soul_spec_from_draft(draft, character_id="native_test", now="2026-10-13")
    emotion_service = EmotionService.__new__(EmotionService)
    state = {
        "active_stack": [
            {"emotion": "joy", "intensity": 0.6},
            {"emotion": "longing", "intensity": 0.4},
        ]
    }
    summary = emotion_service._generate_emotion_summary(
        state["active_stack"], "native_test", language
    )
    mood = emotion_service._generate_mood_descriptor({"valence_baseline": 0.0}, language)
    guidelines = emotion_service._derive_expression_guidelines(state)
    service = ComposerService.__new__(ComposerService)
    service._sanitizer_config = None
    service._directive_compiler = DirectiveCompiler()
    prompt = service._build_system_prompt(
        anchor=AnchorContextBlock(hard_never=spec.identity_anchor.anti_patterns.hard_never),
        memory=MemoryContextBlock(),
        emotion=EmotionContextBlock(
            emotion_summary=summary, mood_descriptor=mood, expression_guidelines=guidelines
        ),
        relationship=RelationshipContextBlock(relationship_phase="ACQUAINTANCE"),
        inner_state=InnerStateContextBlock(),
        soul_spec=spec,
        response_language=language,
    )
    payload = prompt + draft.opening + sample["question"]
    assert not re.search(r"[\u3400-\u9fff]", payload)
    assert draft.persona in prompt and draft.backstory in prompt
    assert sample["question"] in prompt  # same-language voice example retained
    assert prompt_text(language, "phase_acquaintance") in prompt
    assert prompt_text(language, "emotion_joy") in prompt
    assert "sentence_length_modifier" not in prompt
    if language == "bn":
        # The only Latin text in this fixture's prompt is protocol delimiters.
        prose = prompt.replace("<<<USER_MESSAGE>>>", "").replace("<<</USER_MESSAGE>>>", "")
        assert not re.search("[A-Za-z]", prose)
    if language == "vi":
        for legacy in (
            "OUTPUT LANGUAGE",
            "Gentle Companion",
            "Secondary register",
            "Background notes",
        ):
            assert legacy not in prompt


def test_every_configured_emotion_and_relationship_has_native_text():
    import yaml

    from heart.ss04_relationship.stage_engine import RelationshipStage
    from heart.ss05_composer.prompt_resources import prompt_catalog

    repo = Path(__file__).parents[4]
    emotions = yaml.safe_load((repo / "config/emotion_lexicon.yaml").read_text())["emotion_vad_map"]
    for language in ("en", "vi", "bn"):
        catalog = prompt_catalog(language)
        assert all("emotion_" + emotion in catalog for emotion in emotions)
        assert all("phase_" + phase.value.lower() in catalog for phase in RelationshipStage)
