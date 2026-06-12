"""Tests for VoiceDirector."""

import pytest

from heart.ss08_voice.voice_director import VoiceDirector


@pytest.fixture
def director():
    return VoiceDirector()


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
    assert req.voice_id == "female-shaonv"


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
    assert req.voice_id == "female-shaonv"


def test_dorothy_voice_id(director):
    """Test dorothy gets correct voice_id."""
    req = director.derive(
        text="Hello.",
        character_id="dorothy",
        vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5},
    )
    assert req.voice_id == "female-yujie"