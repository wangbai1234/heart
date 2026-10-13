"""Unit tests for SS10 authored-opening playback.

Human-reviewed openings stored on the draft are played back verbatim
(split into bubbles + persisted) with NO LLM call. This locks in that
contract so a future refactor can't silently re-introduce runtime
generation for characters that ship an authored opening.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from heart.ss10_opening.generator import (
    _resolve_authored_opening,
    generate_opening,
)

_OPENING = "（他搁下朱笔，抬眼看你。）\n这个时辰才来。\n（他偏头，声音低哑。）\n今夜哪儿都别想去。"


class _FakeDB:
    """Minimal async DB stub — records executed statements."""

    def __init__(self) -> None:
        self.executed: list[str] = []

    async def execute(self, query, params=None):  # noqa: ANN001
        self.executed.append(str(query))

        class _R:
            def scalar(self_inner):  # noqa: ANN001, N805
                return None

        return _R()

    async def commit(self) -> None:
        pass


class _FakeRouter:
    def __init__(self) -> None:
        self.called = False

    async def call_cheap(self, **kwargs):  # noqa: ANN003
        self.called = True
        return "LLM_SHOULD_NOT_RUN"


def _spec_with(opening):  # noqa: ANN001
    spec = SimpleNamespace(character_id="pei_jue")
    object.__setattr__(spec, "_draft", SimpleNamespace(opening=opening))
    return spec


def test_resolve_authored_opening_present():
    assert _resolve_authored_opening(_spec_with(_OPENING)) == _OPENING


def test_resolve_authored_opening_absent():
    assert _resolve_authored_opening(SimpleNamespace(_draft=SimpleNamespace())) is None
    assert _resolve_authored_opening(SimpleNamespace()) is None
    assert _resolve_authored_opening(_spec_with("   ")) is None


@pytest.mark.asyncio
async def test_authored_opening_played_back_without_llm():
    spec = _spec_with(_OPENING)
    router = _FakeRouter()
    reg = SimpleNamespace(get_soul=lambda cid: spec)

    result = await generate_opening(
        user_id=uuid.uuid4(),
        character_id="pei_jue",
        db=_FakeDB(),
        model_router=router,
        soul_registry=reg,
    )

    assert router.called is False, "authored opening must not call the LLM"
    kinds = [b["kind"] for b in result]
    assert kinds == ["action", "text", "action", "text"]
    assert result[1]["content"] == "这个时辰才来。"


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "vi", "bn"])
async def test_same_language_authored_opening_never_calls_translation(monkeypatch, language):
    from unittest.mock import AsyncMock

    from heart.core.config import settings
    from heart.ss01_soul.draft import CharacterDraft, DisplayNameDraft
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft

    openings = {
        "en": "（Smiles）Which flower would you like?",
        "vi": "（Mỉm cười）Bạn thích loài hoa nào?",
        "bn": "（হাসে）আপনি কোন ফুল পছন্দ করেন?",
    }
    names = {"en": "Su Wan", "vi": "Tô Vãn", "bn": "সু ওয়ান"}
    draft = CharacterDraft(
        display_name=DisplayNameDraft(**{language: names[language]}),
        persona="A kind adult florist who listens patiently.",
        locale=language,
        opening=openings[language],
    )
    spec = build_soul_spec_from_draft(draft, character_id="native_opening")
    object.__setattr__(spec, "_draft", draft)
    monkeypatch.setattr(settings, "international_localization", True)
    monkeypatch.setattr(
        "heart.i18n.character_preferences",
        AsyncMock(
            return_value=SimpleNamespace(response_language=language, action_style="fullwidth")
        ),
    )
    router = _FakeRouter()
    result = await generate_opening(
        user_id=uuid.uuid4(),
        character_id="native_opening",
        db=_FakeDB(),
        model_router=router,
        soul_registry=SimpleNamespace(get_soul=lambda cid: spec),
    )
    assert result
    assert not router.called
    from heart.ss10_opening.generator import _resolve_display_name

    assert _resolve_display_name(spec) == names[language]


@pytest.mark.asyncio
async def test_different_language_opening_still_adapts_with_native_instructions(monkeypatch):
    from unittest.mock import AsyncMock

    from heart.core.config import settings
    from heart.ss05_composer.prompt_resources import prompt_text

    spec = _spec_with(_OPENING)
    spec.locale = "zh-CN"
    monkeypatch.setattr(settings, "international_localization", True)
    monkeypatch.setattr(
        "heart.i18n.character_preferences",
        AsyncMock(return_value=SimpleNamespace(response_language="bn", action_style="fullwidth")),
    )
    router = SimpleNamespace(call_cheap=AsyncMock(return_value="（হাসে）স্বাগতম।"))
    await generate_opening(
        user_id=uuid.uuid4(),
        character_id="pei_jue",
        db=_FakeDB(),
        model_router=router,
        soul_registry=SimpleNamespace(get_soul=lambda cid: spec),
    )
    messages = router.call_cheap.call_args.kwargs["messages"]
    assert messages[0]["content"].endswith(prompt_text("bn", "generation"))
    assert messages[1]["content"] == prompt_text("bn", "opening_adapt", opening=_OPENING)
