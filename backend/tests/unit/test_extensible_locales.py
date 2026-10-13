from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from heart.core.config import settings
from heart.i18n import LanguagePreferences, character_preferences, enabled_locales, negotiate_locale, normalize_locale, voice_supported
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft


@pytest.fixture
def preview(monkeypatch):
    monkeypatch.setattr(settings, "international_localization", True)
    monkeypatch.setattr(settings, "local_character_review", True)
    monkeypatch.setattr(settings, "localization_enabled_locales", "en,vi,bn")


@pytest.mark.parametrize("tag,code", [("vi-VN", "vi"), ("bn-BD", "bn"), ("bn-IN", "bn"), ("zh-Hans-CN", "zh"), ("zh-Hant-TW", None), ("en-US-x-private", "en")])
def test_alias_lookup(tag, code):
    assert normalize_locale(tag) == code


def test_negotiation_rejects_excluded_and_invalid_weights():
    assert negotiate_locale("vi;q=0,bn-BD;q=0.8,en;q=0.6") == "bn"
    assert negotiate_locale("vi;q=0,vi-VN;q=1,en;q=0.2") == "en"
    assert negotiate_locale("bn;q=nan,vi;q=2,en;q=invalid") is None


def test_draft_languages_require_preview(preview, monkeypatch):
    assert enabled_locales() == ("zh", "en", "vi", "bn")
    monkeypatch.setattr(settings, "local_character_review", False)
    assert enabled_locales() == ("zh", "en", "vi", "bn")
    monkeypatch.setattr(settings, "localization_enabled_locales", "en,ja")
    with pytest.raises(ValueError):
        enabled_locales()


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,author,spec,expected", [("auto", "vi", "bn-BD", "vi"), ("auto", None, "bn-BD", "en"), ("character", None, "bn-BD", "bn"), ("interface", "vi", "bn-BD", "en"), ("fixed", "vi", "bn-BD", "bn")])
async def test_response_modes(preview, mode, author, spec, expected):
    prefs = LanguagePreferences(interface_language="en", response_language="bn", response_mode=mode)
    db = AsyncMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = {"response_language": author, "locale": spec}
    db.execute.return_value = result
    with patch("heart.i18n.load_preferences", AsyncMock(return_value=prefs.model_copy())):
        effective = await character_preferences(db, uuid4(), "test")
    assert effective.response_language == expected
    assert effective.interface_language == "en"
    assert prefs.response_language == ("bn" if mode == "fixed" else "en")
    if mode in {"interface", "fixed"}:
        db.execute.assert_not_called()


@pytest.mark.parametrize("code,name", [("vi", "Minh"), ("bn", "অরুণ")])
def test_map_only_names_roundtrip(code, name):
    from heart.ss01_soul.character_catalog import display_name_from_spec
    draft = CharacterDraft(display_name={"localized": {code: name}}, locale=code, persona="An adult character with a detailed background.")
    spec = build_soul_spec_from_draft(draft, character_id="locale_test")
    assert spec.display_name.localized[code] == name
    assert display_name_from_spec(spec.model_dump(), "fallback") == name


@pytest.mark.parametrize("names", [{"vi": " "}, {"vi": "Minh", "localized": {"vi": "Other"}}, {"localized": {"bn": ""}}])
def test_invalid_names(names):
    with pytest.raises(ValidationError):
        CharacterDraft(display_name=names, persona="An adult character with a detailed background.")


@pytest.mark.asyncio
async def test_paused_values_retained_but_new_writes_rejected(monkeypatch):
    from heart.api.routes_profile import save_language_preferences
    from heart.core.auth import TokenData
    monkeypatch.setattr(settings, "international_localization", False)
    prior = LanguagePreferences(interface_language="bn", response_language="vi", response_mode="fixed")
    db = AsyncMock()
    with patch("heart.api.routes_profile.load_preferences", AsyncMock(return_value=prior)):
        saved = await save_language_preferences(prior, TokenData(user_id=str(uuid4())), db)
        assert saved.interface_language == "bn"
        with pytest.raises(HTTPException) as error:
            await save_language_preferences(prior.model_copy(update={"interface_language": "en"}), TokenData(user_id=str(uuid4())), db)
        assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_unsupported_voice_fails_before_provider(preview):
    from heart.api.routes_voice import synthesize, SynthesizeRequest
    from heart.core.auth import TokenData
    assert not voice_supported("vi") and not voice_supported("bn")
    prefs = LanguagePreferences(interface_language="bn")
    with patch("heart.i18n.character_preferences", AsyncMock(return_value=prefs)), patch("heart.api.routes_voice.get_voice_service") as provider:
        with pytest.raises(HTTPException) as error:
            await synthesize.__wrapped__(SimpleNamespace(), SynthesizeRequest(text="কেমন আছেন?", character_id="test"), TokenData(user_id=str(uuid4())), AsyncMock())
        assert error.value.detail == "voice_language_unavailable"
        provider.assert_not_called()


@pytest.mark.asyncio
async def test_proactive_fallback_keeps_target_language(preview, monkeypatch):
    from heart.ss06_inner_state.service import InnerStateService
    from heart.i18n import PROACTIVE_FALLBACKS
    monkeypatch.setattr(settings, "proactive_llm_enabled", False)
    service = InnerStateService()
    content = await service._resolve_proactive_content(character_id="test", trigger_type="idle", relationship_stage="FRIEND", intimacy=0.5, days_since_last_interaction=1, recent_context="", user_facts="", response_language="bn")
    assert content in PROACTIVE_FALLBACKS["bn"]
