"""Tests for MiniMax TTS Provider."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.minimax_provider import MiniMaxProvider
from heart.ss08_voice.types import TTSRequest


@pytest.fixture
def provider():
    return MiniMaxProvider(
        api_key="test-key",
        group_id="test-group",
        base_url="https://api.minimax.io/v1",
    )


@pytest.fixture
def sample_request():
    return TTSRequest(
        text="Hello, how are you?",
        voice_id="female-shaonv",
        emotion="happy",
        speed=1.0,
        pitch=0,
        volume=1.0,
        format="mp3",
        sample_rate=24000,
    )


@pytest.mark.asyncio
async def test_synthesize_success(provider, sample_request):
    """Test successful synthesis returns TTSResult with non-empty audio."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "audio": "48656c6c6f",  # "Hello" in hex
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        result = await provider.synthesize(sample_request)

        assert result.audio == b"Hello"
        assert result.format == "mp3"
        assert result.duration_ms > 0
        assert result.request_id is not None


@pytest.mark.asyncio
async def test_synthesize_http_error(provider, sample_request):
    """Test HTTP error raises TTSProviderError."""
    import httpx

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.RequestError("Connection failed")

        with pytest.raises(TTSProviderError):
            await provider.synthesize(sample_request)


@pytest.mark.asyncio
async def test_synthesize_invalid_emotion_falls_back_to_neutral(provider):
    """Test invalid emotion falls back to neutral."""
    request = TTSRequest(
        text="Test",
        voice_id="female-shaonv",
        emotion="invalid_emotion",
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": {
            "audio": "48656c6c6f",
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(provider._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await provider.synthesize(request)

        # Verify the request body had emotion="neutral"
        call_args = mock_post.call_args
        body = call_args[1]["json"] if "json" in call_args[1] else call_args[0][1]
        assert body["voice_setting"]["emotion"] == "neutral"


def test_endpoint_appends_group_id_when_set():
    """Mainland MiniMax (`api.minimaxi.com`) resolves cloned UGC voice_ids via
    GroupId. Without it, /t2a_v2 silently returns an unusable body and the
    caller shows "偏离轨道". Guard against a silent revert to the plain URL."""
    p = MiniMaxProvider(api_key="k", group_id="grp-123", base_url="https://api.minimaxi.com/v1")
    assert p._endpoint("/t2a_v2") == "https://api.minimaxi.com/v1/t2a_v2?GroupId=grp-123"


def test_endpoint_omits_group_id_when_unset():
    """International endpoint uses Bearer-only auth — no GroupId query."""
    p = MiniMaxProvider(api_key="k", group_id="", base_url="https://api.minimax.io/v1")
    assert p._endpoint("/t2a_v2") == "https://api.minimax.io/v1/t2a_v2"


@pytest.mark.asyncio
async def test_synthesize_uses_group_id_url(sample_request):
    """The high-level ``synthesize`` call must hit the ?GroupId= URL — otherwise
    cloned UGC voice_ids fail on mainland MiniMax with an opaque error."""
    p = MiniMaxProvider(api_key="k", group_id="grp-1", base_url="https://api.minimaxi.com/v1")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"data": {"audio": "48656c6c6f"}}
    mock_response.raise_for_status = MagicMock()

    with patch.object(p._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        await p.synthesize(sample_request)

    call_args = mock_post.call_args
    url = call_args[0][0] if call_args[0] else call_args[1].get("url")
    assert url == "https://api.minimaxi.com/v1/t2a_v2?GroupId=grp-1"


@pytest.mark.asyncio
async def test_synthesize_raises_on_base_resp_error(sample_request):
    """MiniMax returns HTTP 200 with a non-zero ``base_resp.status_code`` for
    logical failures. Those must surface as ``TTSProviderError`` so the caller
    can log the actual reason (e.g. GroupId mismatch) instead of showing
    "Invalid MiniMax response: {...}"."""
    p = MiniMaxProvider(api_key="k", group_id="grp-1", base_url="https://api.minimaxi.com/v1")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "base_resp": {"status_code": 1002, "status_msg": "voice_id not found"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(p._client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        with pytest.raises(TTSProviderError) as excinfo:
            await p.synthesize(sample_request)

    msg = str(excinfo.value)
    assert "1002" in msg
    assert "voice_id not found" in msg
