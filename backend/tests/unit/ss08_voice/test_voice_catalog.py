"""Tests for voice catalog."""

import pytest

from heart.ss08_voice.voice_catalog import VOICE_CATALOG, get_voice_id, register_voice


def test_get_voice_id_rin():
    """Test getting voice ID for rin."""
    voice_id = get_voice_id("rin")
    assert voice_id == "Chinese (Mandarin)_Gentle_Senior"


def test_get_voice_id_dorothy():
    """Test getting voice ID for dorothy."""
    voice_id = get_voice_id("dorothy")
    assert voice_id == "Chinese (Mandarin)_Crisp_Girl"


def test_get_voice_id_unknown_raises():
    """Test getting voice ID for unknown character raises KeyError."""
    with pytest.raises(KeyError, match="Unknown voice"):
        get_voice_id("unknown_character")


def test_register_voice():
    """Test dynamic voice registration."""
    register_voice("rin", "cloned_v1", "cloned-voice-abc")
    voice_id = get_voice_id("rin", "cloned_v1")
    assert voice_id == "cloned-voice-abc"
    del VOICE_CATALOG["rin"]["cloned_v1"]
