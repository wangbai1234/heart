"""Tests for Qwen ASR provider (DashScope realtime WS), with a fake socket."""

import asyncio
import json

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.qwen_asr_provider import (
    QwenAsrProvider,
    QwenAsrSession,
    _extract_transcript_text,
    _wav_to_pcm16,
)


def _wav(pcm: bytes, rate: int = 16000) -> bytes:
    import struct

    data_len = len(pcm)
    header = b"RIFF" + struct.pack("<I", 36 + data_len) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", data_len)
    return header + pcm


class FakeWS:
    """In-memory WS: canned server frames + captured client sends."""

    def __init__(self, server_frames: list[dict]):
        self._server = list(server_frames)
        self.sent: list[dict] = []
        self.closed = False

    async def send(self, payload):
        self.sent.append(json.loads(payload))

    async def recv(self):
        if not self._server:
            # Emulate a closed connection ending the iterator.
            raise ConnectionClosedError()
        return json.dumps(self._server.pop(0))

    async def close(self):
        self.closed = True


class ConnectionClosedError(Exception):
    pass


def _factory(frames: list[dict]):
    async def make(url: str, api_key: str):
        make.ws = FakeWS(frames)  # type: ignore[attr-defined]
        return make.ws  # type: ignore[attr-defined]

    return make


# ── WAV → PCM ────────────────────────────────────────────────────────────────


def test_wav_to_pcm16_extracts_data_chunk():
    pcm = bytes(range(0, 32))
    assert _wav_to_pcm16(_wav(pcm)) == pcm


def test_wav_to_pcm16_passthrough_when_not_wav():
    raw = b"\x01\x02\x03\x04"
    assert _wav_to_pcm16(raw) == raw


# ── transcript extraction shape tolerance ────────────────────────────────────


@pytest.mark.parametrize(
    "evt,expected",
    [
        ({"text": "你好"}, "你好"),
        ({"transcript": "hi"}, "hi"),
        ({"transcription": {"text": "nested"}}, "nested"),
        ({"transcription": "flat"}, "flat"),
        ({"nothing": 1}, ""),
    ],
)
def test_extract_transcript_text(evt, expected):
    assert _extract_transcript_text(evt) == expected


# ── session handshake + one-shot transcribe ──────────────────────────────────


@pytest.mark.asyncio
async def test_open_waits_for_session_created_and_sends_config():
    frames = [{"type": "session.created"}]
    fac = _factory(frames)
    sess = QwenAsrSession("k", "wss://x/realtime", "qwen3-asr-flash-realtime", ws_factory=fac)
    await sess.open()
    # session.update must be sent with manual turn_detection=None + pcm/16k.
    upd = next(s for s in fac.ws.sent if s["type"] == "session.update")  # type: ignore[attr-defined]
    assert upd["session"]["turn_detection"] is None
    assert upd["session"]["input_audio_format"] == "pcm"
    assert upd["session"]["sample_rate"] == 16000


@pytest.mark.asyncio
async def test_open_raises_on_error_frame():
    fac = _factory([{"type": "error", "error": {"message": "bad key"}}])
    sess = QwenAsrSession("k", "wss://x/realtime", "m", ws_factory=fac)
    with pytest.raises(TTSProviderError):
        await sess.open()


@pytest.mark.asyncio
async def test_transcribe_bytes_returns_final():
    frames = [
        {"type": "session.created"},
        {"type": "conversation.item.input_audio_transcription.text", "text": "你"},
        {"type": "conversation.item.input_audio_transcription.completed", "text": "你好世界"},
        {"type": "session.finished"},
    ]
    fac = _factory(frames)
    sess = QwenAsrSession("k", "wss://x/realtime", "m", ws_factory=fac)
    await sess.open()
    out = await sess.transcribe_bytes(b"\x00\x01" * 100)
    assert out == "你好世界"
    # audio was appended + committed
    assert any(s["type"] == "input_audio_buffer.append" for s in fac.ws.sent)  # type: ignore[attr-defined]
    assert any(s["type"] == "input_audio_buffer.commit" for s in fac.ws.sent)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_transcribe_bytes_falls_back_to_latest_partial_on_close():
    # No 'completed' frame — socket closes after a partial. We keep the partial.
    frames = [
        {"type": "session.created"},
        {"type": "conversation.item.input_audio_transcription.text", "text": "半句"},
    ]
    fac = _factory(frames)
    sess = QwenAsrSession("k", "wss://x/realtime", "m", ws_factory=fac)
    await sess.open()
    out = await sess.transcribe_bytes(b"\x00\x01" * 100)
    assert out == "半句"


@pytest.mark.asyncio
async def test_provider_transcribe_end_to_end():
    frames = [
        {"type": "session.created"},
        {"type": "conversation.item.input_audio_transcription.completed", "text": "完整转写"},
        {"type": "session.finished"},
    ]
    prov = QwenAsrProvider(
        api_key="k",
        ws_url="wss://x/realtime",
        realtime_model="qwen3-asr-flash-realtime",
        ws_factory=_factory(frames),
    )
    out = await prov.transcribe(_wav(b"\x00\x01" * 200), mime="audio/wav")
    assert out == "完整转写"
    assert prov.name == "qwen_asr"


@pytest.mark.asyncio
async def test_provider_transcribe_empty_on_no_pcm():
    prov = QwenAsrProvider(api_key="k", ws_url="wss://x/realtime", ws_factory=_factory([]))
    # A WAV with an empty data chunk → no PCM → empty transcript, no WS opened.
    assert await prov.transcribe(_wav(b""), mime="audio/wav") == ""
