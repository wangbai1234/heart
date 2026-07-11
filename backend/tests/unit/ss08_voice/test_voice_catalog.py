"""Tests for voice catalog."""

import pytest

from heart.core.config import settings
from heart.ss08_voice.voice_catalog import (
    VOICE_CATALOG,
    get_voice_id,
    get_voice_profile,
    register_voice,
)


@pytest.fixture(autouse=True)
def reset_voice_settings(monkeypatch):
    monkeypatch.setattr(settings, "voice_profiles", None)
    monkeypatch.setattr(settings, "minimax_rin_clone_voice_id", None)
    monkeypatch.setattr(settings, "minimax_dorothy_voice_id", None)


def test_get_voice_id_rin():
    """Test getting voice ID for rin."""
    voice_id = get_voice_id("rin")
    assert voice_id == "female-shaonv"


def test_get_voice_id_dorothy():
    """Test getting voice ID for dorothy."""
    voice_id = get_voice_id("dorothy")
    assert voice_id == "female-yujie"


def test_get_voice_id_unknown_raises():
    """Test getting voice ID for unknown character raises VoiceNotConfigured."""
    from heart.ss08_voice.voice_catalog import VoiceNotConfigured
    with pytest.raises(VoiceNotConfigured):
        get_voice_id("unknown_character")


def test_register_voice():
    """Test dynamic voice registration."""
    # Register a new voice
    register_voice("rin", "cloned_v1", "cloned-voice-abc")

    # Verify it was registered
    voice_id = get_voice_id("rin", "cloned_v1")
    assert voice_id == "cloned-voice-abc"

    # Clean up
    del VOICE_CATALOG["rin"]["cloned_v1"]


def test_voice_profiles_support_new_character(monkeypatch):
    monkeypatch.setattr(
        settings,
        "voice_profiles",
        '{"luna":{"voice_id":"LunaClone_001","clone_stability":true}}',
    )

    profile = get_voice_profile("luna")

    assert profile.voice_id == "LunaClone_001"
    assert profile.clone_stability is True
    assert profile.allowed_emotions == ("neutral",)
    assert get_voice_id("luna") == "LunaClone_001"


def test_legacy_rin_clone_becomes_stable_profile(monkeypatch):
    monkeypatch.setattr(settings, "minimax_rin_clone_voice_id", "RinClone_20260705")

    profile = get_voice_profile("rin")

    assert profile.voice_id == "RinClone_20260705"
    assert profile.clone_stability is True
    assert profile.speed_range == (0.98, 1.02)
