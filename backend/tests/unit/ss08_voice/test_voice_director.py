"""Tests for VoiceDirector."""

import time

import pytest

from heart.ss08_voice.voice_director import VoiceDirector


@pytest.fixture
def director():
    d = VoiceDirector()
    d._prior.clear()
    return d


def test_happy_emotion(director):
    req = director.derive(text="I'm so happy!", character_id="rin", vad={"valence": 0.6, "arousal": 0.7, "dominance": 0.5})
    assert req.emotion == "happy"
    assert req.speed > 1.0
    assert req.pitch >= 1
    assert req.voice_id == "Chinese (Mandarin)_Gentle_Senior"


def test_angry_emotion(director):
    req = director.derive(text="I'm furious!", character_id="rin", vad={"valence": -0.5, "arousal": 0.7, "dominance": 0.7})
    assert req.emotion == "angry"
    assert req.speed > 1.0
    assert req.pitch >= 2


def test_fearful_emotion(director):
    req = director.derive(text="I'm scared!", character_id="rin", vad={"valence": -0.5, "arousal": 0.8, "dominance": 0.1})
    assert req.emotion == "fearful"
    assert req.speed > 1.0
    assert req.pitch >= 3


def test_sad_emotion(director):
    req = director.derive(text="I'm feeling down.", character_id="rin", vad={"valence": -0.5, "arousal": 0.2, "dominance": 0.5})
    assert req.emotion == "sad"
    assert req.speed < 1.0
    assert req.pitch < 0


def test_neutral_emotion(director):
    req = director.derive(text="Hello.", character_id="rin", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5})
    assert req.emotion == "neutral"
    assert req.speed == 1.0
    assert req.pitch == 0


def test_high_intimacy_slower_speed(director):
    req_low = director.derive(text="Hello.", character_id="rin", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5}, intimacy=0.0)
    req_high = director.derive(text="Hello.", character_id="rin", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5}, intimacy=0.8)
    assert req_high.speed < req_low.speed
    assert req_low.speed - req_high.speed >= 0.04


def test_high_intimacy_lower_pitch(director):
    req_low = director.derive(text="Hello.", character_id="rin", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5}, intimacy=0.0)
    req_high = director.derive(text="Hello.", character_id="rin", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5}, intimacy=0.8)
    assert req_high.pitch < req_low.pitch
    assert req_low.pitch - req_high.pitch >= 1


def test_none_vad_does_not_raise(director):
    req = director.derive(text="Hello.", character_id="rin", vad=None)
    assert req.emotion == "neutral"
    assert req.voice_id == "Chinese (Mandarin)_Gentle_Senior"


def test_dorothy_voice_id(director):
    req = director.derive(text="Hello.", character_id="dorothy", vad={"valence": 0.0, "arousal": 0.2, "dominance": 0.5})
    assert req.voice_id == "Chinese (Mandarin)_Crisp_Girl"


def test_text_keyword_overrides_neutral_vad(director):
    req = director.derive(text="哈哈，今天太开心了", character_id="rin", vad={"valence": 0.0, "arousal": 0.3, "dominance": 0.5})
    assert req.emotion == "happy"
    assert req.speed > 1.0
    assert req.pitch >= 1


def test_text_sad_keyword_overrides_neutral_vad(director):
    req = director.derive(text="好累啊，想哭", character_id="rin", vad={"valence": 0.0, "arousal": 0.3, "dominance": 0.5})
    assert req.emotion == "sad"
    assert req.speed < 1.0
    assert req.pitch < 0


# ── Emotion smoothing tests ─────────────────────────────────────────


def test_emotion_neighbor_clamp(director):
    director.derive("哈哈太开心了", "rin", vad=None)
    req = director.derive("好累啊，想哭", "rin", vad=None)
    assert req.emotion == "neutral"


def test_emotion_neighbor_ok(director):
    director.derive("真的吗？没想到", "rin", vad=None)
    req = director.derive("哈哈太开心了", "rin", vad=None)
    assert req.emotion == "happy"


def test_speed_ema_smoothing(director):
    director.derive("哈哈太开心了", "rin", vad=None)
    req = director.derive("唉，好难过", "rin", vad=None)
    assert 0.90 < req.speed < 1.05


def test_prior_ttl_reset(director):
    director.derive("哈哈太开心了", "rin", vad=None)
    director._prior["rin"] = (*director._prior["rin"][:3], time.monotonic() - 200)
    req = director.derive("好累啊，想哭", "rin", vad=None)
    assert req.emotion == "sad"


# ── Turn-Locked Emotion tests ───────────────────────────────────────


def test_locked_emotion_two_sentences(director):
    """同 turn 两句锁定同一情绪，第二句不能被字面情绪改 emotion。"""
    r1 = director.derive("哈哈太开心了", "rin", vad=None, locked_emotion="happy", locked_speed_base=1.08, locked_pitch_base=2)
    r2 = director.derive("不过也有点累。", "rin", vad=None, locked_emotion="happy", locked_speed_base=1.08, locked_pitch_base=2)
    assert r1.emotion == "happy"
    assert r2.emotion == "happy"


def test_locked_emotion_micro_adjust(director):
    """locked 模式下 text_emotion 只影响 speed/pitch 30% 权重。"""
    r_neutral = director.derive("你好。", "rin", vad=None, locked_emotion="happy", locked_speed_base=1.0, locked_pitch_base=0)
    r_sad_text = director.derive("好累啊，想哭", "rin", vad=None, locked_emotion="happy", locked_speed_base=1.0, locked_pitch_base=0)
    assert r_neutral.emotion == "happy"
    assert r_sad_text.emotion == "happy"
    assert r_sad_text.speed < r_neutral.speed


# ── Short sentence attenuation tests ────────────────────────────────


def test_short_sentence_capped_confidence():
    from heart.ss08_voice.text_emotion import infer_emotion_from_text
    result = infer_emotion_from_text("嗯。")
    assert result.confidence <= 0.4


def test_short_sentence_halved_deltas():
    from heart.ss08_voice.text_emotion import infer_emotion_from_text
    result = infer_emotion_from_text("唉")
    assert result.confidence == 0.4
    assert abs(result.speed_delta) < 0.15
