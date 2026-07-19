"""B5 unit tests: Fish Audio provider + wiring priority + clone cost dispatch."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from heart.ss08_voice.fish_provider import FishProvider
from heart.ss08_voice.types import TTSRequest


# ── FishProvider ──────────────────────────────────────────────────────────────


def test_fish_provider_name():
    p = FishProvider(api_key="test-key")
    assert p.name == "fish"


def test_fish_provider_init_defaults():
    p = FishProvider(api_key="key")
    # fishaudio.org open-API gateway contract (/speech/tts, /voices).
    assert p._base_url == "https://fishaudio.org/api/open/v1"
    assert p._model == "fishaudio-s21pro-flash"
    assert p._timeout == 60.0


def test_fish_provider_strips_trailing_slash():
    p = FishProvider(api_key="key", base_url="https://api.fish.audio/")
    assert not p._base_url.endswith("/")


@pytest.mark.asyncio
async def test_fish_provider_synthesize_success():
    fake_audio = b"fake_audio_data_mp3"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_audio

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("heart.ss08_voice.fish_provider.httpx.AsyncClient", return_value=mock_client):
        provider = FishProvider(api_key="test-key")
        req = TTSRequest(text="Hello world", voice_id="voice-123")
        result = await provider.synthesize(req)

    assert result.audio == fake_audio
    assert result.format == "mp3"
    assert result.duration_ms >= 1
    assert result.request_id  # non-empty UUID string


@pytest.mark.asyncio
async def test_fish_provider_synthesize_error_raises():
    import httpx

    from heart.ss08_voice.errors import TTSProviderError

    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "bad request"

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("heart.ss08_voice.fish_provider.httpx.AsyncClient", return_value=mock_client):
        provider = FishProvider(api_key="test-key")
        req = TTSRequest(text="Hello world", voice_id="v1")
        with pytest.raises(TTSProviderError, match="Fish Audio TTS error 400"):
            await provider.synthesize(req)


@pytest.mark.asyncio
async def test_fish_provider_stream_synthesize_yields_one_chunk():
    fake_audio = b"audio_bytes"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = fake_audio

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("heart.ss08_voice.fish_provider.httpx.AsyncClient", return_value=mock_client):
        provider = FishProvider(api_key="test-key")
        req = TTSRequest(text="stream test", voice_id="v1")
        chunks = []
        async for chunk in provider.stream_synthesize(req):
            chunks.append(chunk)

    assert len(chunks) == 1
    assert chunks[0].data == fake_audio
    assert chunks[0].is_last is True
    assert chunks[0].seq == 0


# ── _clone_cost_fen dispatch ──────────────────────────────────────────────────


def test_clone_cost_fen_mimo():
    from heart.api.routes_voice import _clone_cost_fen

    with patch("heart.billing.pricing.action_cost_fen", return_value=5000) as mock_fn:
        result = _clone_cost_fen("mimo")
    mock_fn.assert_called_once_with("clone_mimo")
    assert result == 5000


def test_clone_cost_fen_fish():
    from heart.api.routes_voice import _clone_cost_fen

    with patch("heart.billing.pricing.action_cost_fen", return_value=10000) as mock_fn:
        result = _clone_cost_fen("fish")
    mock_fn.assert_called_once_with("clone_fish")
    assert result == 10000


def test_clone_cost_fen_fallback_on_import_error():
    from heart.api.routes_voice import _CLONE_COST_FEN_FALLBACK, _clone_cost_fen

    with patch.dict("sys.modules", {"heart.billing.pricing": None}):
        result = _clone_cost_fen("mimo")
    assert result == _CLONE_COST_FEN_FALLBACK


def test_clone_cost_fen_fallback_on_zero_cost():
    from heart.api.routes_voice import _CLONE_COST_FEN_FALLBACK, _clone_cost_fen

    with patch("heart.billing.pricing.action_cost_fen", return_value=0):
        result = _clone_cost_fen("unknown_provider")
    assert result == _CLONE_COST_FEN_FALLBACK


# ── Wiring priority order ─────────────────────────────────────────────────────


def test_build_primary_voice_provider_mimo_first(monkeypatch):
    """When MIMO_API_KEY is set, primary provider should be MiMo."""
    from heart.api import wiring

    monkeypatch.setattr(wiring.settings, "mimo_api_key", "mimo-key")
    monkeypatch.setattr(wiring.settings, "fish_api_key", "fish-key")
    monkeypatch.setattr(wiring.settings, "minimax_api_key", "mm-key")

    mock_mimo = MagicMock()
    mock_mimo.name = "mimo"

    with patch("heart.ss08_voice.mimo_provider.MiMoProvider", return_value=mock_mimo):
        provider = wiring._build_primary_voice_provider()

    # MiMo should be returned first (highest priority)
    assert provider.name == "mimo"


def test_build_primary_voice_provider_fish_when_no_mimo(monkeypatch):
    """When only FISH_API_KEY is set (no MIMO), primary should be Fish."""
    from heart.api import wiring

    monkeypatch.setattr(wiring.settings, "mimo_api_key", None)
    monkeypatch.setattr(wiring.settings, "fish_api_key", "fish-key")
    monkeypatch.setattr(wiring.settings, "minimax_api_key", None)

    mock_fish = MagicMock()
    mock_fish.name = "fish"

    with patch("heart.ss08_voice.fish_provider.FishProvider", return_value=mock_fish):
        provider = wiring._build_primary_voice_provider()

    assert provider.name == "fish"


def test_build_fallback_mimo_primary_gets_fish_fallback(monkeypatch):
    """MiMo primary → Fish fallback when fish_api_key is set."""
    from heart.api import wiring

    monkeypatch.setattr(wiring.settings, "fish_api_key", "fish-key")
    monkeypatch.setattr(wiring.settings, "fish_base_url", "https://api.fish.audio")
    monkeypatch.setattr(wiring.settings, "fish_model", "speech-1.6")

    mock_primary = MagicMock()
    mock_primary.name = "mimo"
    mock_fish = MagicMock()
    mock_fish.name = "fish"

    with patch("heart.ss08_voice.fish_provider.FishProvider", return_value=mock_fish):
        fallback = wiring._build_fallback_voice_provider(mock_primary)

    assert fallback.name == "fish"


def test_build_fallback_fish_primary_gets_minimax(monkeypatch):
    """Fish primary → MiniMax fallback when minimax_api_key is set."""
    from heart.api import wiring

    monkeypatch.setattr(wiring.settings, "minimax_api_key", "mm-key")
    monkeypatch.setattr(wiring.settings, "minimax_group_id", "grp")
    monkeypatch.setattr(wiring.settings, "minimax_base_url", "https://api.minimax.io/v1")

    mock_primary = MagicMock()
    mock_primary.name = "fish"
    mock_mm = MagicMock()
    mock_mm.name = "minimax"

    with patch("heart.ss08_voice.minimax_provider.MiniMaxProvider", return_value=mock_mm):
        fallback = wiring._build_fallback_voice_provider(mock_primary)

    assert fallback.name == "minimax"
