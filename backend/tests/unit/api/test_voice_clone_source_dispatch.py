"""Unit tests for voice-clone audio-source dispatch.

The clone endpoint now supports two audio-delivery paths:
- ``minimax_file://<file_id>`` — audio hosted at MiniMax (dev / no-S3 path)
- anything else — a public URL for MiniMax to fetch (S3-configured path)

Dispatch happens in ``_call_tts_clone_api``. These tests lock in the
routing so a future refactor doesn't silently regress into "always URL".

``_call_tts_clone_api`` and its inner helpers return ``tuple[voice_id, err_msg]``
where exactly one is non-None — success is ``(voice_id, None)``, failure
is ``(None, reason)``. The reason is written to ``character_voices.error_msg``
so the frontend toast can be actionable instead of "克隆失败，请重试".
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from heart.api import routes_voice


@pytest.mark.asyncio
async def test_local_scheme_is_rejected():
    """Legacy 'local://' placeholder must never succeed — that was the 假成功 bug."""
    voice_id, err = await routes_voice._call_tts_clone_api("local://tmp/x.wav", "abc")
    assert voice_id is None
    assert err and "local://" in err


@pytest.mark.asyncio
async def test_minimax_file_scheme_routes_to_file_id_path():
    """`minimax_file://123` should call the file_id clone helper, not URL."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value=("VOICE_OK", None)),
        ) as mock_file,
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(return_value=("WRONG", None)),
        ) as mock_url,
    ):
        voice_id, err = await routes_voice._call_tts_clone_api(
            "minimax_file://12345", "char_abc"
        )

    assert voice_id == "VOICE_OK"
    assert err is None
    mock_file.assert_awaited_once_with(12345, "char_abc")
    mock_url.assert_not_called()


@pytest.mark.asyncio
async def test_https_scheme_routes_to_url_path():
    """A regular https URL should call the file_url clone helper."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value=("WRONG", None)),
        ) as mock_file,
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(return_value=("VOICE_OK", None)),
        ) as mock_url,
    ):
        voice_id, err = await routes_voice._call_tts_clone_api(
            "https://cdn.example.com/sample.wav", "char_abc"
        )

    assert voice_id == "VOICE_OK"
    assert err is None
    mock_url.assert_awaited_once_with("https://cdn.example.com/sample.wav", "char_abc")
    mock_file.assert_not_called()


@pytest.mark.asyncio
async def test_dispatch_returns_none_on_missing_provider():
    with (
        patch.object(routes_voice.settings, "voice_provider", "unset"),
        patch.object(routes_voice.settings, "minimax_api_key", ""),
    ):
        voice_id, err = await routes_voice._call_tts_clone_api("minimax_file://1", "x")
    assert voice_id is None
    assert err and "MINIMAX_API_KEY" in err


@pytest.mark.asyncio
async def test_dispatch_allows_clone_when_primary_provider_is_mimo():
    """Clone must proceed as long as MiniMax key is set — the primary TTS
    provider being MiMo (voice_provider="mimo") is not a reason to refuse
    clone. Regression from 2026-07-12 real-device report."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "mimo"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_file_id",
            new=AsyncMock(return_value=("VOICE_OK", None)),
        ) as mock_file,
    ):
        voice_id, err = await routes_voice._call_tts_clone_api(
            "minimax_file://42", "char_abc"
        )

    assert voice_id == "VOICE_OK"
    assert err is None
    mock_file.assert_awaited_once_with(42, "char_abc")


@pytest.mark.asyncio
async def test_dispatch_swallows_exceptions():
    """A raised inner helper turns into ``(None, reason)`` — job marks failed
    with the exception text as the reason, no crash."""
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ),
    ):
        voice_id, err = await routes_voice._call_tts_clone_api("https://x/y.wav", "z")
    assert voice_id is None
    assert err and "boom" in err


@pytest.mark.asyncio
async def test_dispatch_flags_missing_group_id_on_mainland_endpoint():
    """Mainland-China ``api.minimaxi.*`` domains require ``?GroupId=`` on
    /voice_clone. When it's empty the call is doomed to fail with a fast
    4xx and the user sees "克隆失败" ~4s later with no clue. The dispatcher
    now fails early with an actionable ``error_msg`` instead.
    """
    with (
        patch.object(routes_voice.settings, "voice_provider", "minimax"),
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", ""),
        patch.object(
            routes_voice.settings, "minimax_base_url", "https://api.minimaxi.com/v1"
        ),
    ):
        voice_id, err = await routes_voice._call_tts_clone_api("minimax_file://7", "x")
    assert voice_id is None
    assert err and "MINIMAX_GROUP_ID" in err


def test_minimax_endpoint_appends_group_id_when_set():
    with (
        patch.object(routes_voice.settings, "minimax_group_id", "grp-123"),
        patch.object(
            routes_voice.settings, "minimax_base_url", "https://api.minimaxi.com/v1"
        ),
    ):
        url = routes_voice._minimax_endpoint("/voice_clone")
    assert url == "https://api.minimaxi.com/v1/voice_clone?GroupId=grp-123"


def test_minimax_endpoint_omits_group_id_when_unset():
    """International endpoint uses Bearer-only auth — no GroupId query."""
    with (
        patch.object(routes_voice.settings, "minimax_group_id", ""),
        patch.object(routes_voice.settings, "minimax_base_url", "https://api.minimax.io/v1"),
    ):
        url = routes_voice._minimax_endpoint("/files/upload")
    assert url == "https://api.minimax.io/v1/files/upload"


def test_extract_minimax_base_resp_error_handles_success():
    assert routes_voice._extract_minimax_base_resp_error({"base_resp": {"status_code": 0}}) is None
    assert routes_voice._extract_minimax_base_resp_error({}) is None
    assert routes_voice._extract_minimax_base_resp_error({"base_resp": None}) is None


def test_extract_minimax_base_resp_error_returns_reason_on_failure():
    body = {
        "base_resp": {"status_code": 1002, "status_msg": "invalid params: file_url"},
        # Note: MiniMax often returns HTTP 200 even for logical failures,
        # so this branch must be honoured or we'd mark a doomed clone as
        # ready and stall in chat later (2026-07-11 regression).
    }
    got = routes_voice._extract_minimax_base_resp_error(body)
    assert got is not None
    assert "1002" in got
    assert "invalid params: file_url" in got


@pytest.mark.asyncio
async def test_voice_clone_request_uses_httpx_client(monkeypatch):
    """Guard against a silent revert to ``aiohttp`` — Python.org 3.11 macOS
    installs ship an empty default trust store, so ``aiohttp`` fails TLS
    against ``*.minimaxi.com`` (WoTrus DV) while ``httpx`` uses certifi and
    works. If a future refactor swaps the client back, this test breaks.
    """
    import httpx

    captured: dict = {}

    class _StubResp:
        status_code = 200
        text = ""

        def json(self):
            return {"base_resp": {"status_code": 0, "status_msg": "success"}}

    class _StubClient:
        def __init__(self, *a, **kw):
            captured["client_kwargs"] = kw

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            captured["url"] = url
            captured["post_kwargs"] = kw
            return _StubResp()

    monkeypatch.setattr(httpx, "AsyncClient", _StubClient)
    with (
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice.settings, "minimax_base_url", "https://api.minimaxi.com/v1"
        ),
    ):
        voice_id, err = await routes_voice._minimax_voice_clone_request(
            {"file_id": 42, "voice_id": "UGC_x_deadbeef"}
        )
    assert err is None
    assert voice_id == "UGC_x_deadbeef"
    assert captured["url"] == "https://api.minimaxi.com/v1/voice_clone?GroupId=grp-1"
    assert captured["post_kwargs"]["json"]["file_id"] == 42
    assert captured["post_kwargs"]["headers"]["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_files_upload_uses_httpx_multipart(monkeypatch):
    """Same guard for ``_upload_audio_to_minimax`` — multipart form data must
    reach MiniMax with ``purpose=voice_clone`` and the ``file`` part, over
    httpx (certifi-backed TLS)."""
    import httpx

    captured: dict = {}

    class _StubResp:
        status_code = 200
        text = ""

        def json(self):
            return {
                "file": {"file_id": 987654321},
                "base_resp": {"status_code": 0, "status_msg": "success"},
            }

    class _StubClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kw):
            captured["url"] = url
            captured["files"] = kw.get("files")
            captured["data"] = kw.get("data")
            return _StubResp()

    monkeypatch.setattr(httpx, "AsyncClient", _StubClient)
    with (
        patch.object(routes_voice.settings, "minimax_api_key", "test-key"),
        patch.object(routes_voice.settings, "minimax_group_id", "grp-1"),
        patch.object(
            routes_voice.settings, "minimax_base_url", "https://api.minimaxi.com/v1"
        ),
    ):
        got = await routes_voice._upload_audio_to_minimax(
            data=b"\x00" * 1024, filename="rin.mp3", mime="audio/mpeg"
        )
    assert got == 987654321
    assert captured["url"] == "https://api.minimaxi.com/v1/files/upload?GroupId=grp-1"
    assert captured["data"] == {"purpose": "voice_clone"}
    # httpx multipart contract: files["file"] = (filename, bytes, mime)
    assert captured["files"]["file"][0] == "rin.mp3"
    assert captured["files"]["file"][2] == "audio/mpeg"


def test_clone_voice_id_for_starts_with_letter_and_contains_char_id():
    """MiniMax voice_id needs to be a stable-ish identifier — sanity-check shape."""
    got = routes_voice._clone_voice_id_for("char_abc123")
    assert got.startswith("UGC_")
    assert "char" in got or "abc" in got  # segment survived alnum filter
    assert len(got) <= 64


def test_clone_voice_id_for_handles_ugly_ids():
    """Even a pure-symbol character_id shouldn't produce an empty middle segment."""
    got = routes_voice._clone_voice_id_for("---")
    assert got.startswith("UGC_clone_")


# ---------------------------------------------------------------------------
# Fish provider routing — clone by direct bytes upload (fixes the 403)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fish_provider_routes_to_fish_clone_from_bytes():
    """provider='fish' must clone from the raw bytes, never MiniMax, never a re-download."""
    with (
        patch.object(
            routes_voice,
            "_fish_clone_from_bytes",
            new=AsyncMock(return_value=("fish-voice-id", None)),
        ) as mock_fish,
        patch.object(
            routes_voice,
            "_minimax_clone_by_url",
            new=AsyncMock(return_value=("WRONG", None)),
        ) as mock_mm,
    ):
        voice_id, err = await routes_voice._call_tts_clone_api(
            "upload://sample.wav",
            "char_xyz",
            provider="fish",
            audio_bytes=b"RIFFxxxx",
            mime="audio/wav",
        )

    assert voice_id == "fish-voice-id"
    assert err is None
    # Cloned from the bytes we passed — no URL download step.
    mock_fish.assert_awaited_once_with(b"RIFFxxxx", "audio/wav", "char_xyz")
    mock_mm.assert_not_called()


@pytest.mark.asyncio
async def test_fish_clone_no_api_key_returns_error():
    with patch.object(routes_voice.settings, "fish_api_key", ""):
        voice_id, err = await routes_voice._fish_clone_from_bytes(b"audio", "audio/wav", "ch")
    assert voice_id is None
    assert err and "FISH_API_KEY" in err


@pytest.mark.asyncio
async def test_fish_clone_missing_bytes_returns_error():
    with patch.object(routes_voice.settings, "fish_api_key", "sk-fish"):
        voice_id, err = await routes_voice._fish_clone_from_bytes(None, "audio/wav", "ch")
    assert voice_id is None
    assert err and "bytes" in err


@pytest.mark.asyncio
async def test_fish_clone_success_uses_clone_from_bytes():
    """Happy path: FishProvider.clone_from_bytes voiceId is returned; the bytes we
    were handed are what get uploaded (no anonymous URL fetch → no HTTP 403)."""
    from heart.ss08_voice.fish_provider import FishProvider

    with (
        patch.object(routes_voice.settings, "fish_api_key", "sk-fish"),
        patch.object(
            FishProvider,
            "clone_from_bytes",
            new=AsyncMock(return_value="fish-voice-xyz"),
        ) as mock_clone,
    ):
        voice_id, err = await routes_voice._fish_clone_from_bytes(
            b"audio-bytes", "audio/mpeg", "char_abc123"
        )
    assert voice_id == "fish-voice-xyz"
    assert err is None
    args, _kwargs = mock_clone.await_args
    assert args[0] == b"audio-bytes"


@pytest.mark.asyncio
async def test_fish_clone_provider_error_returns_reason():
    from heart.ss08_voice.errors import TTSProviderError
    from heart.ss08_voice.fish_provider import FishProvider

    with (
        patch.object(routes_voice.settings, "fish_api_key", "sk-fish"),
        patch.object(
            FishProvider,
            "clone_from_bytes",
            new=AsyncMock(side_effect=TTSProviderError("Fish clone error 400: invalid audio")),
        ),
    ):
        voice_id, err = await routes_voice._fish_clone_from_bytes(
            b"audio", "audio/wav", "char_abc123"
        )
    assert voice_id is None
    assert err and "400" in err


# ---------------------------------------------------------------------------
# Tier gate: assert_clone_allowed must reject free users (P4 — defect E)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assert_clone_allowed_rejects_free_tier():
    from heart.membership import CloneForbiddenError, assert_clone_allowed

    with pytest.raises(CloneForbiddenError) as exc_info:
        assert_clone_allowed("free", "fish")
    assert exc_info.value.provider == "fish"
    assert exc_info.value.tier == "free"


@pytest.mark.asyncio
async def test_assert_clone_allowed_rejects_free_mimo():
    from heart.membership import CloneForbiddenError, assert_clone_allowed

    with pytest.raises(CloneForbiddenError):
        assert_clone_allowed("free", "mimo")


@pytest.mark.asyncio
async def test_assert_clone_allowed_permits_plus_fish():
    from heart.membership import assert_clone_allowed

    assert_clone_allowed("plus", "fish")  # must not raise


@pytest.mark.asyncio
async def test_assert_clone_allowed_permits_immersive_fish():
    from heart.membership import assert_clone_allowed

    assert_clone_allowed("immersive", "fish")  # must not raise


# ---------------------------------------------------------------------------
# Clone provider availability gate — MiMo is zero-shot, gated by MIMO_API_KEY
# (NOT MINIMAX_API_KEY): that mis-gate was the "音色克隆服务未配置" seen by
# plus/immersive users uploading a MiMo clone.
# ---------------------------------------------------------------------------


def test_mimo_gate_uses_mimo_api_key_not_minimax():
    """MiMo clone available when MIMO_API_KEY is set, even with no MiniMax key."""
    with (
        patch.object(routes_voice.settings, "mimo_api_key", "tp-xxx"),
        patch.object(routes_voice.settings, "minimax_api_key", ""),
    ):
        routes_voice._check_clone_provider_available("mimo")  # must not raise


def test_mimo_gate_blocks_when_mimo_key_missing():
    from fastapi import HTTPException

    with (
        patch.object(routes_voice.settings, "mimo_api_key", ""),
        patch.object(routes_voice.settings, "minimax_api_key", "mm-key"),
    ):
        with pytest.raises(HTTPException) as exc:
            routes_voice._check_clone_provider_available("mimo")
    assert exc.value.status_code == 503


def test_fish_gate_uses_fish_api_key():
    from fastapi import HTTPException

    with patch.object(routes_voice.settings, "fish_api_key", ""):
        with pytest.raises(HTTPException) as exc:
            routes_voice._check_clone_provider_available("fish")
    assert exc.value.status_code == 503
    with patch.object(routes_voice.settings, "fish_api_key", "sk-fish"):
        routes_voice._check_clone_provider_available("fish")  # must not raise
