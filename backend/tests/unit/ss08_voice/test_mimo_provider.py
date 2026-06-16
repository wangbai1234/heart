"""Tests for MiMo TTS Provider (voiceclone)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.mimo_provider import (
    MiMoProvider,
    _extract_audio_from_chunk,
    _inject_breathing_tags,
    _parse_mimo_response,
)
from heart.ss08_voice.types import TTSRequest


@pytest.fixture
def provider():
    return MiMoProvider(
        api_key="test-key",
        base_url="https://api.xiaomimimo.com/v1",
        reference_audio_b64="data:audio/wav;base64,AAAA",
        model="mimo-v2.5-tts-voiceclone",
    )


@pytest.fixture
def sample_request():
    return TTSRequest(
        text="你好，今天天气真好！",
        voice_id="rin",
        emotion="happy",
        speed=1.0,
        pitch=0,
        volume=1.0,
    )


# ── Voiceclone structure tests ──


def test_build_body_voiceclone_structure(provider, sample_request):
    """Test that voiceclone request body has correct structure."""
    body = provider._build_body(sample_request, "rin")
    assert body["model"] == "mimo-v2.5-tts-voiceclone"
    assert "stream" not in body
    assert "speed" not in body["audio"]
    assert "pitch" not in body["audio"]
    assert "volume" not in body["audio"]
    assert body["audio"]["format"] == "wav"
    assert body["audio"]["voice"] == "data:audio/wav;base64,AAAA"


def test_build_body_director_mode(provider, sample_request):
    """Test that user content includes director mode dimensions."""
    body = provider._build_body(sample_request, "rin")
    user_content = body["messages"][0]["content"]
    assert "【角色】" in user_content
    assert "【场景】" in user_content
    assert "【指导】" in user_content
    assert "神无月凛" in user_content


def test_build_body_director_mode_rin_profile(provider, sample_request):
    """Test that rin character profile is used."""
    body = provider._build_body(sample_request, "rin")
    user_content = body["messages"][0]["content"]
    assert "20岁" in user_content
    assert "雷神" in user_content


def test_build_body_emotion_tags_happy(provider):
    """Test that happy emotion includes audio tag and emotion tag."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="happy")
    body = provider._build_body(req, "rin")
    assistant_content = body["messages"][1]["content"]
    assert assistant_content.startswith("[轻笑](开心)")


def test_build_body_emotion_tags_sad(provider):
    """Test that sad emotion includes audio tag and emotion tag."""
    req = TTSRequest(text="我有点累了", voice_id="rin", emotion="sad")
    body = provider._build_body(req, "rin")
    assistant_content = body["messages"][1]["content"]
    assert assistant_content.startswith("[叹气](悲伤)")


def test_build_body_emotion_tags_neutral(provider):
    """Test that neutral emotion has no prefix."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="neutral")
    body = provider._build_body(req, "rin")
    assistant_content = body["messages"][1]["content"]
    assert assistant_content == "你好"


def test_build_body_emotion_scene_happy(provider):
    """Test that happy emotion includes composite scene hints."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="happy")
    body = provider._build_body(req, "rin")
    user_content = body["messages"][0]["content"]
    assert "嘴角压不住的笑意" in user_content


def test_build_body_emotion_scene_angry(provider):
    """Test that angry emotion includes scene hints."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="angry")
    body = provider._build_body(req, "rin")
    user_content = body["messages"][0]["content"]
    assert "克制" in user_content


def test_build_body_emotion_direction_happy(provider):
    """Test that happy emotion includes naturalistic direction hints."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="happy")
    body = provider._build_body(req, "rin")
    user_content = body["messages"][0]["content"]
    assert "轻笑从鼻腔溢出" in user_content


def test_build_body_emotion_direction_angry(provider):
    """Test that angry emotion includes naturalistic direction hints."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="angry")
    body = provider._build_body(req, "rin")
    user_content = body["messages"][0]["content"]
    assert "咬得更清楚" in user_content


# ── Dorothy profile tests ──


def test_build_body_dorothy_profile(provider):
    """Test that dorothy character uses her own profile."""
    req = TTSRequest(text="你好呀", voice_id="dorothy", emotion="happy")
    body = provider._build_body(req, "dorothy")
    user_content = body["messages"][0]["content"]
    assert "桃桃" in user_content
    assert "活泼少女" in user_content


def test_build_body_dorothy_scene(provider):
    """Test that dorothy has her own scene default."""
    req = TTSRequest(text="你好呀", voice_id="dorothy", emotion="neutral")
    body = provider._build_body(req, "dorothy")
    user_content = body["messages"][0]["content"]
    assert "咖啡厅" in user_content


# ── Anti-pattern footer tests ──


def test_build_body_anti_pattern_footer(provider):
    """Test that anti-pattern footer is appended to direction."""
    req = TTSRequest(text="你好", voice_id="rin", emotion="neutral")
    body = provider._build_body(req, "rin")
    user_content = body["messages"][0]["content"]
    assert "参考音频" in user_content
    assert "播音腔" in user_content


def test_build_body_anti_pattern_footer_dorothy(provider):
    """Test that anti-pattern footer also applies to dorothy."""
    req = TTSRequest(text="你好呀", voice_id="dorothy", emotion="neutral")
    body = provider._build_body(req, "dorothy")
    user_content = body["messages"][0]["content"]
    assert "参考音频" in user_content


# ── synthesize tests ──


@pytest.mark.asyncio
async def test_synthesize_success(provider, sample_request):
    """Test successful synthesis returns TTSResult with audio."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [
            {
                "message": {
                    "audio": {"data": "SGVsbG8="},  # "Hello" in base64
                },
            },
        ],
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await provider.synthesize(sample_request, "rin")

        assert result.audio == b"Hello"
        assert result.format == "wav"
        assert result.duration_ms > 0
        assert result.request_id is not None


@pytest.mark.asyncio
async def test_synthesize_api_error(provider, sample_request):
    """Test API error raises TTSProviderError."""
    import httpx

    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Unauthorized",
        request=MagicMock(),
        response=mock_response,
    )

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response

        with pytest.raises(TTSProviderError) as exc_info:
            await provider.synthesize(sample_request, "rin")
        assert "401" in str(exc_info.value)


@pytest.mark.asyncio
async def test_stream_synthesize_raises(provider, sample_request):
    """Test that stream_synthesize raises NotImplementedError."""
    with pytest.raises(NotImplementedError) as exc_info:
        await provider.stream_synthesize(sample_request, "rin")
    assert "voiceclone 不支持真流式" in str(exc_info.value)


# ── Provider metadata tests ──


def test_provider_name(provider):
    assert provider.name == "mimo"


def test_estimate_cost_cents(provider):
    cost = provider.estimate_cost_cents("你好世界")
    assert cost == len("你好世界") * 0.02


# ── All emotion types test ──


@pytest.mark.parametrize(
    "emotion,expected_tag",
    [
        ("happy", "(开心)"),
        ("sad", "(悲伤)"),
        ("angry", "(生气)"),
        ("fearful", "(害怕)"),
        ("disgusted", "(厌恶)"),
        ("surprised", "(惊讶)"),
        ("neutral", ""),
    ],
)
def test_emotion_tags(provider, emotion, expected_tag):
    req = TTSRequest(text="测试文本", voice_id="rin", emotion=emotion)
    body = provider._build_body(req, "rin")
    assistant = body["messages"][1]["content"]
    if expected_tag:
        assert expected_tag in assistant
    else:
        assert assistant == "测试文本"


# ── Response parsing tests ──


def test_extract_audio_from_choices_message():
    data = {
        "choices": [
            {"message": {"audio": {"data": "SGVsbG8="}}}
        ]
    }
    assert _extract_audio_from_chunk(data) == b"Hello"


def test_extract_audio_from_choices_delta():
    data = {
        "choices": [
            {"delta": {"audio": {"data": "V09STEQ="}}}
        ]
    }
    assert _extract_audio_from_chunk(data) == b"WORLD"


def test_extract_audio_from_flat_data():
    data = {"data": {"audio": "WUFZ"}}
    assert _extract_audio_from_chunk(data) == b"YAY"


def test_extract_audio_from_audio_obj():
    data = {"audio": {"data": "QUJD"}}
    assert _extract_audio_from_chunk(data) == b"ABC"


def test_extract_audio_empty():
    assert _extract_audio_from_chunk({}) == b""


def test_parse_mimo_response_single_json():
    raw = b'{"choices":[{"message":{"audio":{"data":"SGVsbG8="}}}]}'
    assert _parse_mimo_response(raw) == b"Hello"


def test_parse_mimo_response_sse_style():
    raw = b'data: {"choices":[{"message":{"audio":{"data":"WUFZ"}}}]}\n\ndata: [DONE]'
    assert _parse_mimo_response(raw) == b"YAY"


def test_parse_mimo_response_empty():
    assert _parse_mimo_response(b"") == b""


def test_parse_mimo_response_unparseable():
    assert _parse_mimo_response(b"not valid json or sse") == b""


# ── Breathing tag injection tests ──


def test_inject_breathing_tags_short_text_unchanged():
    """Text shorter than 20 chars should not be modified."""
    assert _inject_breathing_tags("你好，世界", "neutral") == "你好，世界"


def test_inject_breathing_tags_no_punctuation_unchanged():
    """Text without Chinese punctuation should not be modified."""
    text = "这是一段没有标点符号的很长的测试文本用来测试没有标点"
    assert _inject_breathing_tags(text, "neutral") == text


def test_inject_breathing_tags_inserts_at_punctuation():
    """Breathing tags should be inserted after punctuation marks."""
    text = "今天天气真好，我们出去走走吧，顺便买点东西，晚上一起做饭。"
    result = _inject_breathing_tags(text, "neutral")
    assert "[吸气]" in result
    assert result.count("[吸气]") <= 2


def test_inject_breathing_tags_emotion_specific():
    """Different emotions should use different breathing tags."""
    text = "我有点难过，不知道该怎么办，心里很不是滋味。"
    sad_result = _inject_breathing_tags(text, "sad")
    angry_result = _inject_breathing_tags(text, "angry")
    assert "[叹气]" in sad_result
    assert "[深呼吸]" in angry_result


def test_inject_breathing_tags_max_two():
    """Should insert at most 2 breathing tags."""
    text = "第一句话，第二句话，第三句话，第四句话，第五句话，第六句话。"
    result = _inject_breathing_tags(text, "neutral")
    assert result.count("[吸气]") <= 2


def test_inject_breathing_tags_in_build_body(provider):
    """Breathing tags should appear in assistant content for long text."""
    long_text = "今天天气真好，我们可以出去走走，顺便去公园看看花，你觉得怎么样。"
    req = TTSRequest(text=long_text, voice_id="rin", emotion="happy")
    body = provider._build_body(req, "rin")
    assistant = body["messages"][1]["content"]
    assert "[吸气]" in assistant or "[轻笑]" in assistant
