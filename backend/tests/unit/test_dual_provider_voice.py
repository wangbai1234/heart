"""Unit tests for issue 3: dual mimo+fish clones + per-user provider selection.

Covers the resolver branching (resolve_effective_voice), the MiMo voiceclone
request body, and the Fish backbone model header.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from heart.ss08_voice import voice_resolver as vr
from heart.ss08_voice.types import TTSRequest

_TIERS_CFG = (
    '{"free":{"models":["deepseek"],"tts":["mimo"],"clone":[],"monthly_grant":0},'
    '"plus":{"models":["deepseek","grok"],"tts":["mimo","fish"],"clone":["mimo","fish"],"monthly_grant":400}}'
)


# ── _tts_allowed ────────────────────────────────────────────────────────────


class TestTtsAllowed:
    def test_free_allows_mimo_not_fish(self):
        with patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG):
            assert vr._tts_allowed("free", "mimo") is True
            assert vr._tts_allowed("free", "fish") is False

    def test_plus_allows_fish(self):
        with patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG):
            assert vr._tts_allowed("plus", "fish") is True


# ── _row_to_effective ───────────────────────────────────────────────────────


class TestRowToEffective:
    def test_mimo_clone_carries_reference_not_voice_id(self):
        row = {
            "voice_provider": "mimo",
            "voice_type": "clone",
            "clone_voice_id": None,
            "clone_audio_url": "/refs/rin.wav",
            "preset_voice_id": None,
        }
        ev = vr._row_to_effective(row)
        assert ev.provider == "mimo"
        assert ev.reference_ref == "/refs/rin.wav"
        assert ev.voice_id is None

    def test_fish_clone_carries_voice_id_not_reference(self):
        row = {
            "voice_provider": "fish",
            "voice_type": "clone",
            "clone_voice_id": "fish-model-123",
            "clone_audio_url": "/refs/rin.wav",
            "preset_voice_id": None,
        }
        ev = vr._row_to_effective(row)
        assert ev.provider == "fish"
        assert ev.voice_id == "fish-model-123"
        assert ev.reference_ref is None

    def test_preset_row_uses_preset_voice_id(self):
        row = {
            "voice_provider": "mimo",
            "voice_type": "preset",
            "clone_voice_id": None,
            "clone_audio_url": None,
            "preset_voice_id": "mimo_female_gentle",
        }
        ev = vr._row_to_effective(row)
        assert ev.voice_id == "mimo_female_gentle"
        assert ev.reference_ref is None


# ── resolve_effective_voice (branching, helpers patched) ─────────────────────


def _mimo_row():
    return {
        "voice_provider": "mimo",
        "voice_type": "clone",
        "clone_voice_id": None,
        "clone_audio_url": "/refs/rin.wav",
        "preset_voice_id": None,
    }


def _fish_row():
    return {
        "voice_provider": "fish",
        "voice_type": "clone",
        "clone_voice_id": "fish-123",
        "clone_audio_url": "/refs/rin.wav",
        "preset_voice_id": None,
    }


class TestResolveEffectiveVoice:
    @pytest.mark.asyncio
    async def test_free_user_fish_selection_degrades_to_mimo(self):
        """Free user who selected fish → resolved to the mimo row (still voice)."""
        db = AsyncMock()
        with (
            patch.object(vr, "get_selected_voice_provider", new=AsyncMock(return_value="fish")),
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
            patch.object(
                vr,
                "_ready_row",
                new=AsyncMock(
                    side_effect=lambda cid, d, prov: _mimo_row() if prov == "mimo" else None
                ),
            ),
        ):
            ev = await vr.resolve_effective_voice("rin", uuid.uuid4(), db)
        assert ev is not None
        assert ev.provider == "mimo"

    @pytest.mark.asyncio
    async def test_plus_user_fish_selection_keeps_fish(self):
        db = AsyncMock()
        with (
            patch.object(vr, "get_selected_voice_provider", new=AsyncMock(return_value="fish")),
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="plus")),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
            patch.object(
                vr,
                "_ready_row",
                new=AsyncMock(
                    side_effect=lambda cid, d, prov: _fish_row() if prov == "fish" else None
                ),
            ),
        ):
            ev = await vr.resolve_effective_voice("rin", uuid.uuid4(), db)
        assert ev is not None
        assert ev.provider == "fish"
        assert ev.voice_id == "fish-123"

    @pytest.mark.asyncio
    async def test_free_user_only_fish_available_returns_none(self):
        """Free user, selected mimo but only a fish row is ready → no tier-allowed
        voice → None (caller keeps the turn text-only)."""
        db = AsyncMock()
        with (
            patch.object(vr, "get_selected_voice_provider", new=AsyncMock(return_value="mimo")),
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
            patch.object(vr, "_ready_row", new=AsyncMock(return_value=None)),
            patch.object(vr, "_all_ready_rows", new=AsyncMock(return_value=[_fish_row()])),
        ):
            ev = await vr.resolve_effective_voice("rin", uuid.uuid4(), db)
        assert ev is None

    @pytest.mark.asyncio
    async def test_fallback_to_any_allowed_ready_row(self):
        """Selected provider missing → fall back to an allowed ready row (mimo)."""
        db = AsyncMock()
        with (
            patch.object(vr, "get_selected_voice_provider", new=AsyncMock(return_value="mimo")),
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
            patch.object(vr, "_ready_row", new=AsyncMock(return_value=None)),
            patch.object(vr, "_all_ready_rows", new=AsyncMock(return_value=[_mimo_row()])),
        ):
            ev = await vr.resolve_effective_voice("rin", uuid.uuid4(), db)
        assert ev is not None
        assert ev.provider == "mimo"


# ── MiMo voiceclone request body ─────────────────────────────────────────────


class TestMiMoVoicecloneBody:
    def test_reference_uses_voiceclone_model_and_voice_field(self):
        from heart.ss08_voice.mimo_provider import MiMoProvider

        p = MiMoProvider(api_key="k")
        req = TTSRequest(text="你好世界", voice_id="rin", emotion="neutral")
        data_uri = "data:audio/wav;base64,QUJD"
        body = p._build_body(req, "rin", reference_data_uri=data_uri)

        assert body["model"] == "mimo-v2.5-tts-voiceclone"
        assert body["audio"]["voice"] == data_uri
        # optimize_text_preview is voicedesign-only — MiMo 400s if sent to voiceclone.
        assert "optimize_text_preview" not in body["audio"]
        # user message empty, assistant carries the text to speak
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][0]["content"] == ""
        assert body["messages"][1]["role"] == "assistant"
        assert body["messages"][1]["content"].endswith("你好世界")

    def test_no_reference_uses_voicedesign_model(self):
        from heart.ss08_voice.mimo_provider import MiMoProvider

        p = MiMoProvider(api_key="k")
        req = TTSRequest(text="你好", voice_id="rin")
        body = p._build_body(req, "rin")
        assert body["model"] == "mimo-v2.5-tts-voicedesign"
        assert "voice" not in body["audio"]
        assert body["audio"]["optimize_text_preview"] is False


# ── Fish backbone model header ───────────────────────────────────────────────


class TestFishModelHeader:
    @pytest.mark.asyncio
    async def test_synthesize_sends_model_header(self):
        from heart.ss08_voice import fish_provider

        captured: dict = {}

        class _FakeResp:
            status_code = 200
            content = b"\x00\x01audio"

        class _FakeClient:
            def __init__(self, *a, **k):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, json=None, headers=None):
                captured["url"] = url
                captured["headers"] = headers
                captured["json"] = json
                return _FakeResp()

        p = fish_provider.FishProvider(
            api_key="k", base_url="https://api.fish.audio", model="fishaudio-s21pro-flash"
        )
        with patch.object(fish_provider.httpx, "AsyncClient", _FakeClient):
            await p.synthesize(TTSRequest(text="hi", voice_id="fish-123"))

        assert captured["headers"]["model"] == "fishaudio-s21pro-flash"
        assert captured["json"]["reference_id"] == "fish-123"
