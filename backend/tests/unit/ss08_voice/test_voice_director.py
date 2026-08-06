"""Tests for VoiceDirector."""

import pytest

from heart.core.config import settings
from heart.ss08_voice.voice_catalog import get_voice_id
from heart.ss08_voice.voice_director import VoiceDirector


@pytest.fixture(autouse=True)
def reset_voice_settings(monkeypatch):
    monkeypatch.setattr(settings, "voice_profiles", None)
    monkeypatch.setattr(settings, "minimax_rin_clone_voice_id", None)
    monkeypatch.setattr(settings, "minimax_dorothy_voice_id", None)


@pytest.fixture
def director():
    # Default production mode: S2 [中文指令] for the s21pro-flash family.
    return VoiceDirector(emotion_mode="s2")


@pytest.fixture
def off_director():
    return VoiceDirector(emotion_mode="off")


@pytest.fixture
def s1_director():
    # S1 (english-label) tags — only interpreted by modelId "fishaudio-s1".
    return VoiceDirector(emotion_mode="s1")


def test_happy_emotion(director):
    """Test happy emotion mapping (high valence, high arousal)."""
    req = director.derive(
        text="I'm so happy!",
        character_id="rin",
        vad={"valence": 0.6, "arousal": 0.7, "dominance": 0.5},
    )
    assert req.emotion == "happy"
    assert req.speed > 1.0
    assert req.pitch >= 1
    assert req.voice_id == get_voice_id("rin")


def test_angry_emotion(director):
    """Test angry emotion mapping (low valence, high arousal, high dominance)."""
    req = director.derive(
        text="I'm furious!",
        character_id="rin",
        vad={"valence": -0.5, "arousal": 0.7, "dominance": 0.7},
    )
    assert req.emotion == "angry"
    assert req.speed > 1.0
    assert req.pitch >= 2


def test_fearful_emotion(director):
    """Test fearful emotion mapping (low valence, high arousal, low dominance)."""
    req = director.derive(
        text="I'm scared!",
        character_id="rin",
        vad={"valence": -0.5, "arousal": 0.8, "dominance": 0.1},
    )
    assert req.emotion == "fearful"
    assert req.speed > 1.0
    assert req.pitch >= 3


def test_sad_emotion(director):
    """Test sad emotion mapping (low valence, low arousal)."""
    req = director.derive(
        text="I'm feeling down.",
        character_id="rin",
        vad={"valence": -0.5, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.emotion == "sad"
    assert req.speed < 1.0
    assert req.pitch < 0


def test_neutral_emotion(director):
    """Test neutral emotion mapping (near-zero valence, low arousal)."""
    req = director.derive(
        text="Hello.",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.emotion == "neutral"
    assert req.speed == 1.0
    assert req.pitch == 0


def test_high_intimacy_slower_speed(director):
    """Test high intimacy results in slower speed."""
    req_low = director.derive(
        text="Hello.",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        intimacy=0.0,
    )
    req_high = director.derive(
        text="Hello.",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        intimacy=0.8,
    )
    assert req_high.speed < req_low.speed
    assert req_low.speed - req_high.speed >= 0.04


def test_high_intimacy_lower_pitch(director):
    """Test high intimacy results in lower pitch."""
    req_low = director.derive(
        text="Hello.",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        intimacy=0.0,
    )
    req_high = director.derive(
        text="Hello.",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        intimacy=0.8,
    )
    assert req_high.pitch < req_low.pitch
    assert req_low.pitch - req_high.pitch >= 1


def test_none_vad_does_not_raise(director):
    """Test that vad=None does not raise an error."""
    req = director.derive(
        text="Hello.",
        character_id="rin",
        vad=None,
    )
    assert req.emotion == "neutral"
    assert req.voice_id == get_voice_id("rin")


def test_dorothy_voice_id(director):
    """Test dorothy gets correct voice_id."""
    req = director.derive(
        text="Hello.",
        character_id="dorothy",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.voice_id == "female-yujie"


def test_off_mode_injects_nothing(off_director):
    # "off" mode ships clean prose (no markers of any kind).
    req = off_director.derive(
        text="今天真的有一点累。想先安静一下。",
        character_id="rin",
        vad={"valence": -0.4, "arousal": 0.2, "dominance": 0.4},
        intimacy=0.6,
    )
    assert "(" not in req.text and "[" not in req.text
    assert req.text == "今天真的有一点累。想先安静一下。"


def test_s2_never_uses_s1_parens(director):
    # S2 mode must NEVER emit S1 () tags — those get read aloud on s21pro-flash.
    req = director.derive(
        text="今天真的有一点累。想先安静一下。",
        character_id="rin",
        vad={"valence": -0.4, "arousal": 0.2, "dominance": 0.4},
        intimacy=0.6,
    )
    assert "(" not in req.text


def test_s2_sad_gets_chinese_instruction(director):
    # Sad VAD → a leading [中文指令] the S2.1 model interprets (not spoken).
    req = director.derive(
        text="今天真的有一点累。想先安静一下。",
        character_id="rin",
        vad={"valence": -0.4, "arousal": 0.2, "dominance": 0.4},
        active_emotions=[{"emotion": "aggrieved", "intensity": 0.8}],
    )
    assert req.emotion == "sad"
    assert req.text.startswith("[")
    assert req.text.endswith("想先安静一下。")


def test_s2_stacks_reaction_cue_before_emotion_tone(director):
    # Layer-2 fallback (LLM emitted no bracket): aggrieved → sighing cue +
    # sad tone should STACK as [叹了口气][声音低下去…], reaction first.
    req = director.derive(
        text="我在。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        active_emotions=[{"emotion": "aggrieved", "intensity": 0.8}],
    )
    assert req.text.startswith("[叹了口气]")
    assert "难过" in req.text  # emotion tone stacked after the cue
    # Every bracket is well-formed — no dangling '[' that TTS would speak.
    assert req.text.count("[") == req.text.count("]")


def test_s2_prefix_never_slices_a_bracket(director):
    # Even if many cues pile up, the length cap only drops WHOLE tokens.
    req = director.derive(
        text="嗯。",
        character_id="rin",
        vad={"valence": -0.5, "arousal": 0.2, "dominance": 0.4},
        active_emotions=[{"emotion": "aggrieved", "intensity": 0.9}],
        stage_directions=["哭", "叹气", "停顿", "惊", "低声"],
    )
    assert req.text.count("[") == req.text.count("]")
    assert "[" in req.text and not req.text.rstrip().endswith("[")


def test_s2_stage_direction_becomes_bracket_cue(director):
    req = director.derive(
        text="kaito。他们提过一次。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        stage_directions=["目光停顿片刻，嗓音带着雨后的凉意"],
    )
    assert "目光停顿" not in req.text
    assert req.text.startswith("[") and "(" not in req.text


def test_s2_preserves_existing_bracket_instruction(director):
    req = director.derive(
        text="[压低声音]别出声。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.text == "[压低声音]别出声。"


def test_sad_text_gets_pause_tag_when_s1_enabled(s1_director):
    req = s1_director.derive(
        text="今天真的有一点累。想先安静一下。",
        character_id="rin",
        vad={"valence": -0.4, "arousal": 0.2, "dominance": 0.4},
        intimacy=0.6,
    )
    assert req.text.startswith("(sighing)")
    assert "(break)" in req.text


def test_existing_expression_tags_are_preserved(s1_director):
    req = s1_director.derive(
        text="(break)别担心，我会陪着你。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.text == "(break)别担心，我会陪着你。"


def test_active_emotions_drive_director_cues(s1_director):
    req = s1_director.derive(
        text="我在。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        active_emotions=[{"emotion": "aggrieved", "intensity": 0.8}],
    )
    assert req.emotion == "sad"
    assert req.text.startswith("(sighing)")
    assert req.speed < 1.0


def test_stage_directions_become_nonspoken_cues(s1_director):
    req = s1_director.derive(
        text="kaito。他们提过一次。",
        character_id="rin",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
        stage_directions=["目光停顿片刻，嗓音带着雨后的凉意"],
    )
    assert "目光停顿" not in req.text
    assert req.text.startswith("(break)")
    assert req.pitch < 0


def test_clone_profile_stabilizes_strong_emotion(director, monkeypatch):
    monkeypatch.setattr(
        settings,
        "voice_profiles",
        '{"rin":{"voice_id":"RinClone_20260705","clone_stability":true}}',
    )

    req = director.derive(
        text="别靠近。",
        character_id="rin",
        vad={"valence": -0.8, "arousal": 0.9, "dominance": 0.8},
        active_emotions=[{"emotion": "anger", "intensity": 0.9}],
    )

    assert req.voice_id == "RinClone_20260705"
    assert req.emotion == "neutral"
    assert 0.98 <= req.speed <= 1.02
    assert -1 <= req.pitch <= 0


def test_voice_profiles_allow_new_character(director, monkeypatch):
    monkeypatch.setattr(
        settings,
        "voice_profiles",
        '{"luna":{"voice_id":"LunaClone_001","clone_stability":true}}',
    )

    req = director.derive(
        text="我在这里。",
        character_id="luna",
        vad={"valence": 0.5, "arousal": 0.8, "dominance": 0.5},
    )

    assert req.voice_id == "LunaClone_001"
    assert req.emotion == "neutral"


def test_clone_profile_does_not_add_emotion_tag_for_vad_only(director, monkeypatch):
    monkeypatch.setattr(
        settings,
        "voice_profiles",
        '{"rin":{"voice_id":"RinClone_20260705","clone_stability":true}}',
    )

    req = director.derive(
        text="今天好像还不错。",
        character_id="rin",
        vad={"valence": 0.7, "arousal": 0.8, "dominance": 0.5},
    )

    assert req.emotion == "neutral"
    assert not req.text.startswith("(chuckle)")
