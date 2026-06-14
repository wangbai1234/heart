"""Tests for MiMo TTS Provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.mimo_provider import (
    MiMoCancellableStream,
    MiMoProvider,
    _extract_audio_from_chunk,
    _parse_mimo_response,
)
from heart.ss08_voice.types import TTSRequest


@pytest.fixture
def provider():
    return MiMoProvider(
        api_key="test-key",
        base_url="https://api.xiaomimimo.com/v1",
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


# ── Voice description tests ──


def test_voice_description_rin_in_build_body(provider, sample_request):
    """Test that rin's voice description is included in the request body."""
    body = provider._build_body(sample_request, "rin", stream=False)
    user_content = body["messages"][0]["content"]
    assert "25岁" in user_content
    assert "知性" in user_content or "温柔" in user_content
    assert "学姐" in user_content


def test_voice_description_dorothy_in_build_body(provider, sample_request):
    """Test that dorothy's voice description is included in the request body."""
    body = provider._build_body(sample_request, "dorothy", stream=False)
    user_content = body["messages"][0]["content"]
    assert "15岁" in user_content
    assert "活泼" in user_content
    assert "元气" in user_content


def test_unknown_character_falls_back_to_rin(provider, sample_request):
    """Test that unknown character_id falls back to rin."""
    body = provider._build_body(sample_request, "unknown", stream=False)
    user_content = body["messages"][0]["content"]
    assert "25岁" in user_content


# ── Emotion mapping tests ──


def test_emotion_directive_happy(provider, sample_request):
    body = provider._build_body(sample_request, "rin", stream=False)
    assert "欢快明亮" in body["messages"][0]["content"]
    assert body["messages"][1]["content"] == "(开心)你好，今天天气真好！"


def test_emotion_directive_sad(provider):
    req = TTSRequest(text="我有点累了", voice_id="rin", emotion="sad")
    body = provider._build_body(req, "rin", stream=False)
    assert "低沉温柔" in body["messages"][0]["content"]
    assert body["messages"][1]["content"] == "(悲伤)我有点累了"


def test_emotion_directive_neutral_no_tag(provider):
    req = TTSRequest(text="你好", voice_id="rin", emotion="neutral")
    body = provider._build_body(req, "rin", stream=False)
    assert "自然平和" in body["messages"][0]["content"]
    assert body["messages"][1]["content"] == "你好"


def test_invalid_emotion_falls_back_to_neutral(provider):
    req = TTSRequest(text="Hello", voice_id="rin", emotion="invalid_emotion")
    body = provider._build_body(req, "rin", stream=False)
    assert "自然平和" in body["messages"][0]["content"]


# ── Request body structure tests ──


def test_build_body_structure(provider, sample_request):
    body = provider._build_body(sample_request, "rin", stream=True)
    assert body["model"] == "mimo-v2.5-tts-voicedesign"
    assert body["stream"] is True
    assert len(body["messages"]) == 2
    assert body["messages"][0]["role"] == "user"
    assert body["messages"][1]["role"] == "assistant"
    assert body["audio"]["format"] == "pcm16"


def test_build_body_non_stream(provider, sample_request):
    body = provider._build_body(sample_request, "rin", stream=False)
    assert "stream" not in body


def test_build_body_includes_speed_pitch_volume(provider):
    req = TTSRequest(text="Test", voice_id="rin", speed=0.9, pitch=-2, volume=1.2)
    body = provider._build_body(req, "rin", stream=False)
    assert body["audio"]["speed"] == 0.9
    assert body["audio"]["pitch"] == -2
    assert body["audio"]["volume"] == 1.2


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
        assert result.format == "pcm16"
        assert result.duration_ms > 0
        assert result.request_id is not None


@pytest.mark.asyncio
async def test_synthesize_http_error(provider, sample_request):
    """Test HTTP error raises TTSProviderError."""
    import httpx

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(TTSProviderError):
            await provider.synthesize(sample_request, "rin")


@pytest.mark.asyncio
async def test_synthesize_missing_audio(provider, sample_request):
    """Test response without audio raises TTSProviderError."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"text": "no audio here"}}]}
    mock_response.raise_for_status = MagicMock()

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(TTSProviderError):
            await provider.synthesize(sample_request, "rin")


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


# ── MiMoCancellableStream tests ──


@pytest.mark.asyncio
async def test_stream_chunks_audio():
    """Test that MiMoCancellableStream chunks audio into 8KB pieces."""
    import base64
    import json

    # Create 20KB of audio (fake data)
    audio_bytes = b"\x00\x01" * 10240  # 20KB
    audio_b64 = base64.b64encode(audio_bytes).decode()
    response_data = json.dumps(
        {"choices": [{"message": {"audio": {"data": audio_b64}}}]}
    ).encode()

    mock_stream_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.aread = AsyncMock(return_value=response_data)
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_response.raise_for_status = MagicMock()

    stream = MiMoCancellableStream(mock_stream_ctx, "rin", "pcm16")

    chunks = []
    async for chunk in stream:
        chunks.append(chunk)

    assert len(chunks) >= 2
    assert chunks[0].format == "pcm16"
    assert chunks[0].seq == 0
    assert chunks[-1].is_last is True
    # Verify total audio size matches
    total = sum(len(c.data) for c in chunks)
    assert total == len(audio_bytes)


@pytest.mark.asyncio
async def test_stream_empty_response():
    """Test stream handles empty response gracefully."""
    mock_stream_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.aread = AsyncMock(return_value=b"")
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_response.raise_for_status = MagicMock()

    stream = MiMoCancellableStream(mock_stream_ctx, "rin", "pcm16")

    chunks = [c async for c in stream]
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert chunks[0].data == b""


@pytest.mark.asyncio
async def test_stream_cancel():
    """Test that cancelling stops iteration."""
    audio_bytes = b"\x00\x01" * 50_000  # Larger than one chunk
    import base64, json

    response_data = json.dumps(
        {"choices": [{"message": {"audio": {"data": base64.b64encode(audio_bytes).decode()}}}]}
    ).encode()

    mock_stream_ctx = MagicMock()
    mock_response = MagicMock()
    mock_response.aread = AsyncMock(return_value=response_data)
    mock_stream_ctx.__aenter__ = AsyncMock(return_value=mock_response)
    mock_stream_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_response.raise_for_status = MagicMock()

    stream = MiMoCancellableStream(mock_stream_ctx, "rin", "pcm16")

    count = 0
    async for chunk in stream:
        count += 1
        if count >= 2:
            stream._cancelled = True  # simulate cancel

    assert count <= 3  # Should stop early


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
def test_emotion_tags(provider, sample_request, emotion, expected_tag):
    req = TTSRequest(text="测试文本", voice_id="rin", emotion=emotion)
    body = provider._build_body(req, "rin", stream=False)
    assistant = body["messages"][1]["content"]
    if expected_tag:
        assert assistant.startswith(expected_tag)
    else:
        assert assistant == "测试文本"
