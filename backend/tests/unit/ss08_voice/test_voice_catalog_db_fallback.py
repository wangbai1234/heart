"""Unit tests for VoiceNotConfigured exception and register_voice behavior.

Covers:
- get_voice_profile raises VoiceNotConfigured for unknown character (not KeyError)
- register_voice pre-populates VOICE_CATALOG so get_voice_profile succeeds
- VoiceNotConfigured carries character_id
"""

from __future__ import annotations

import pytest

from heart.ss08_voice.voice_catalog import (
    VOICE_CATALOG,
    VoiceNotConfigured,
    get_voice_profile,
    register_voice,
)


def test_known_builtin_profiles_succeed():
    """rin and dorothy must always return a profile."""
    profile = get_voice_profile("rin")
    assert profile.character_id == "rin"
    assert profile.voice_id  # non-empty


def test_unknown_character_raises_voice_not_configured():
    """An unknown UGC character should raise VoiceNotConfigured, not KeyError."""
    with pytest.raises(VoiceNotConfigured) as exc_info:
        get_voice_profile("ugc_character_no_voice_xyz")
    assert exc_info.value.character_id == "ugc_character_no_voice_xyz"


def test_voice_not_configured_is_not_key_error():
    """VoiceNotConfigured must not be a KeyError (different exception hierarchy)."""
    with pytest.raises(VoiceNotConfigured):
        get_voice_profile("ugc_no_voice_abc")
    # verify it does NOT accidentally also satisfy KeyError
    try:
        get_voice_profile("ugc_no_voice_abc")
    except KeyError:
        pytest.fail("Should not raise KeyError — must be VoiceNotConfigured")
    except VoiceNotConfigured:
        pass  # expected


def test_register_voice_then_get_profile_succeeds():
    """After register_voice, get_voice_profile must succeed for that character."""
    cid = "ugc_test_register_123"
    voice_id = "mock_voice_id_xyz"

    # Clean up first (in case leftover from previous run)
    VOICE_CATALOG.pop(cid, None)

    register_voice(cid, "default", voice_id)
    try:
        profile = get_voice_profile(cid)
        assert profile.character_id == cid
        assert profile.voice_id == voice_id
    finally:
        VOICE_CATALOG.pop(cid, None)  # cleanup


def test_voice_not_configured_str():
    """VoiceNotConfigured.__str__ should mention the character_id."""
    exc = VoiceNotConfigured("my_char")
    assert "my_char" in str(exc)
