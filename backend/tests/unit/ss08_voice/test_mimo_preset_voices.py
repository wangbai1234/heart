"""Unit tests for MiMo preset voice profile lookup (P5)."""

from __future__ import annotations

import pytest

from heart.ss08_voice.mimo_provider import MiMoProvider, _VOICE_DESCRIPTIONS
from heart.ss08_voice.types import TTSRequest

_PRESET_FEMALE_IDS = [
    "mimo_female_gentle",
    "mimo_female_cool",
    "mimo_female_bright",
    "mimo_female_elegant",
    "mimo_female_shy",
]

_PRESET_MALE_IDS = [
    "mimo_male_gentle",
    "mimo_male_cool",
    "mimo_male_energetic",
    "mimo_male_mature",
    "mimo_male_sweet",
]


@pytest.fixture
def provider():
    return MiMoProvider(api_key="test-key")


def _req(voice_id: str) -> TTSRequest:
    return TTSRequest(
        text="你好",
        voice_id=voice_id,
        emotion="neutral",
        speed=1.0,
        pitch=0,
        volume=1.0,
    )


class TestPresetVoiceDescriptionsExist:
    @pytest.mark.parametrize("vid", _PRESET_FEMALE_IDS)
    def test_female_preset_in_voice_descriptions(self, vid):
        assert vid in _VOICE_DESCRIPTIONS, f"Missing: {vid}"

    @pytest.mark.parametrize("vid", _PRESET_MALE_IDS)
    def test_male_preset_in_voice_descriptions(self, vid):
        assert vid in _VOICE_DESCRIPTIONS, f"Missing: {vid}"

    def test_total_preset_count_is_ten(self):
        preset_ids = [k for k in _VOICE_DESCRIPTIONS if k.startswith("mimo_")]
        assert len(preset_ids) == 10


class TestPresetVoiceFallbackInBuildBody:
    def test_unknown_character_uses_voice_id_description(self, provider):
        """user-created character with preset voice_id gets preset description."""
        req = _req("mimo_female_gentle")
        body = provider._build_body(req, "char_abc123_user_created", stream=False)
        user_content = body["messages"][0]["content"]
        assert "22岁" in user_content
        assert "温柔" in user_content

    def test_preset_voice_id_overrides_rin_fallback(self, provider):
        """mimo_male_cool description should differ from rin's description."""
        req_preset = _req("mimo_male_cool")
        req_rin = _req("rin")
        body_preset = provider._build_body(req_preset, "unknown_char", stream=False)
        body_rin = provider._build_body(req_rin, "unknown_char", stream=False)
        assert body_preset["messages"][0]["content"] != body_rin["messages"][0]["content"]

    def test_character_id_takes_priority_over_voice_id(self, provider):
        """Built-in character_id (rin) must win over a preset voice_id."""
        req = _req("mimo_female_cool")
        body = provider._build_body(req, "rin", stream=False)
        user_content = body["messages"][0]["content"]
        assert "25岁" in user_content  # rin's description, not mimo_female_cool

    def test_unknown_char_unknown_voice_id_falls_back_to_rin(self, provider):
        req = _req("nonexistent_voice")
        body = provider._build_body(req, "totally_unknown", stream=False)
        user_content = body["messages"][0]["content"]
        assert "25岁" in user_content  # rin default

    @pytest.mark.parametrize("vid", _PRESET_FEMALE_IDS + _PRESET_MALE_IDS)
    def test_all_presets_produce_non_empty_description(self, provider, vid):
        req = _req(vid)
        body = provider._build_body(req, "user_char_xyz", stream=False)
        assert len(body["messages"][0]["content"]) > 20
