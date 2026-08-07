"""Unit tests for the Fish realtime TTS path (no live key required).

Covers the msgpack framing + session state machine (FishRealtimeSession), the
incremental streaming session (RealtimeStreamSession), and the wiring/selection
+ fallback in routes_chat_ws._create_stream_session.
"""

from __future__ import annotations

import asyncio

import pytest

from heart.ss08_voice.errors import TTSProviderError
from heart.ss08_voice.fish_realtime_provider import (
    FishRealtimeSession,
    _pack,
    _unpack,
)


class _FakeClosed(Exception):
    """Stands in for websockets.ConnectionClosedOK (name matched by provider)."""

    def __init__(self) -> None:
        super().__init__("ConnectionClosedOK")

    def __str__(self) -> str:  # keep the class name in the type, message here
        return "closed"


# Rename so the provider's `"ConnectionClosed" in type(e).__name__` check trips.
_FakeClosed.__name__ = "ConnectionClosedOK"


class FakeWs:
    """In-memory WebSocket: replays a queue of frames on recv(), records sends."""

    def __init__(self, incoming: list[dict]) -> None:
        self.sent: list[dict] = []
        self._incoming = [_pack(d) for d in incoming]
        self._i = 0
        self.closed = False

    async def send(self, data: bytes) -> None:
        self.sent.append(_unpack(data))

    async def recv(self):
        if self._i >= len(self._incoming):
            raise _FakeClosed()
        frame = self._incoming[self._i]
        self._i += 1
        return frame

    async def close(self) -> None:
        self.closed = True


def _factory_for(ws: FakeWs):
    async def _factory(url: str, api_key: str):
        return ws

    return _factory


class TestMsgpackRoundtrip:
    def test_pack_unpack(self):
        obj = {"event": "start", "request": {"model_id": "v-uuid", "format": "mp3"}}
        assert _unpack(_pack(obj)) == obj

    def test_unpack_str_frame(self):
        # A str frame is encoded before unpacking (defensive).
        assert _unpack(_pack({"event": "flush"})) == {"event": "flush"}


class TestFishRealtimeSession:
    @pytest.mark.asyncio
    async def test_open_sends_start_and_waits_ready(self):
        ws = FakeWs([{"event": "authenticated"}, {"event": "ready"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="voice-123", fmt="mp3",
            ws_factory=_factory_for(ws),
        )
        await sess.open()
        start = next(f for f in ws.sent if f.get("event") == "start")
        assert start["request"]["model_id"] == "voice-123"
        assert start["request"]["format"] == "mp3"

    @pytest.mark.asyncio
    async def test_open_raises_on_error_frame(self):
        ws = FakeWs([{"event": "error", "message": "bad model"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        with pytest.raises(TTSProviderError):
            await sess.open()
        assert ws.closed  # cleaned up on failure

    @pytest.mark.asyncio
    async def test_send_text_emits_text_then_flush(self):
        ws = FakeWs([{"event": "ready"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        await sess.open()
        await sess.send_text("你好")
        events = [f["event"] for f in ws.sent]
        assert events[-2:] == ["text", "flush"]
        assert any(f.get("text") == "你好" for f in ws.sent)

    @pytest.mark.asyncio
    async def test_audio_events_yields_then_finishes(self):
        ws = FakeWs(
            [
                {"event": "ready"},
                {"event": "audio", "data": b"AAA", "audio_sequence": 0},
                {"event": "audio", "data": b"BBB", "audio_sequence": 1},
                {"event": "finish", "reason": "stop"},
            ]
        )
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        await sess.open()
        chunks = [c async for c in sess.audio_events()]
        assert chunks == [b"AAA", b"BBB"]

    @pytest.mark.asyncio
    async def test_audio_events_raises_on_error(self):
        ws = FakeWs([{"event": "ready"}, {"event": "error", "message": "boom"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        await sess.open()
        with pytest.raises(TTSProviderError):
            _ = [c async for c in sess.audio_events()]

    @pytest.mark.asyncio
    async def test_audio_events_ends_cleanly_on_close(self):
        # No 'finish' frame — the connection just closes; iterator ends, no raise.
        ws = FakeWs([{"event": "ready"}, {"event": "audio", "data": b"AAA"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        await sess.open()
        chunks = [c async for c in sess.audio_events()]
        assert chunks == [b"AAA"]

    @pytest.mark.asyncio
    async def test_captures_sample_rate_from_ready(self):
        # pcm/wav: Fish reports the real rate on ready; the client must honour it.
        ws = FakeWs([{"event": "ready", "sample_rate": 44100}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", fmt="wav",
            ws_factory=_factory_for(ws),
        )
        await sess.open()
        assert sess.sample_rate == 44100

    @pytest.mark.asyncio
    async def test_captures_sample_rate_from_audio_frame(self):
        # If ready lacked it, the first audio frame carries it (docs say both do).
        ws = FakeWs(
            [
                {"event": "ready"},
                {"event": "audio", "data": b"AAA", "sample_rate": 24000},
                {"event": "finish"},
            ]
        )
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", fmt="wav",
            ws_factory=_factory_for(ws),
        )
        await sess.open()
        _ = [c async for c in sess.audio_events()]
        assert sess.sample_rate == 24000

    @pytest.mark.asyncio
    async def test_accepts_audio_payload_under_audio_key(self):
        # Docs list the binary key as `audio`; this build sends `data`. Accept both.
        ws = FakeWs(
            [
                {"event": "ready"},
                {"event": "audio", "audio": b"XYZ"},
                {"event": "finish"},
            ]
        )
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", ws_factory=_factory_for(ws)
        )
        await sess.open()
        chunks = [c async for c in sess.audio_events()]
        assert chunks == [b"XYZ"]

    @pytest.mark.asyncio
    async def test_mp3_has_no_sample_rate(self):
        ws = FakeWs([{"event": "ready"}])
        sess = FishRealtimeSession(
            api_key="k", url="wss://x", model_id="v", fmt="mp3",
            ws_factory=_factory_for(ws),
        )
        await sess.open()
        assert sess.sample_rate is None


class FakeRealtimeSession:
    """Fake FishRealtimeSession for RealtimeStreamSession tests."""

    def __init__(self, audio_chunks: list[bytes], sample_rate: int | None = None) -> None:
        self._audio = audio_chunks
        self.opened = False
        self.texts: list[str] = []
        self.finished = False
        self.closed = False
        self.sample_rate = sample_rate
        self._text_seen = asyncio.Event()

    async def open(self) -> None:
        self.opened = True

    async def send_text(self, text: str) -> None:
        self.texts.append(text)
        self._text_seen.set()

    async def audio_events(self):
        # Audio only after the first text (mirrors real ordering).
        await self._text_seen.wait()
        for c in self._audio:
            await asyncio.sleep(0)
            yield c

    async def finish(self) -> None:
        self.finished = True

    async def close(self) -> None:
        self.closed = True


class TestRealtimeStreamSession:
    @pytest.mark.asyncio
    async def test_streams_audio_incrementally(self, monkeypatch):
        from heart.ss08_voice import realtime_stream_session as rss

        monkeypatch.setattr(
            "heart.ss08_voice.voice_catalog.get_voice_id", lambda cid: "voice-xyz"
        )

        sent: list[tuple] = []

        async def send_audio(t_id, seq, data, is_last, fmt, sample_rate=None):
            sent.append((t_id, seq, data, fmt, sample_rate))

        fake = FakeRealtimeSession([b"one", b"two"])
        session = rss.RealtimeStreamSession(
            send_audio,
            api_key="k",
            url="wss://x",
            character_id="rin",
            fmt="mp3",
            session_factory=lambda model_id: fake,
        )
        await session.start()
        assert fake.opened
        await session.submit("turn-1", "第一句", None, 0.0, [], "rin")
        await session.finish()

        assert [s[2] for s in sent] == [b"one", b"two"]  # both chunks, in order
        assert [s[3] for s in sent] == ["mp3", "mp3"]
        assert [s[4] for s in sent] == [None, None]  # no sample_rate for mp3
        assert all(s[0] == "turn-1" for s in sent)
        assert [s[1] for s in sent] == [0, 1]  # incrementing seq
        assert session.full_audio == b"onetwo"
        assert session.audio_produced is True
        assert session.tts_provider_name == "fish"
        assert fake.finished and fake.closed

    @pytest.mark.asyncio
    async def test_speed_override_applied_for_known_voice(self, monkeypatch):
        # A voice_id present in _REALTIME_SPEED_OVERRIDES must lower the speed
        # passed to the Fish session (realtime otherwise renders every voice at
        # 1.0, which for this preset was faster than its REST preview).
        from heart.ss08_voice import realtime_stream_session as rss

        override_id = next(iter(rss._REALTIME_SPEED_OVERRIDES))
        expected = rss._REALTIME_SPEED_OVERRIDES[override_id]
        monkeypatch.setattr(
            "heart.ss08_voice.voice_catalog.get_voice_id", lambda cid: override_id
        )

        async def send_audio(t_id, seq, data, is_last, fmt, sample_rate=None):
            pass

        captured: dict[str, float] = {}

        def factory(mid: str) -> FakeRealtimeSession:
            captured["s"] = sess._speed  # speed at the moment the session is built
            return FakeRealtimeSession([b"a"])

        sess = rss.RealtimeStreamSession(
            send_audio,
            api_key="k",
            url="wss://x",
            character_id="rin",
            fmt="wav",
            session_factory=factory,
        )
        await sess.start()
        assert captured["s"] == expected
        assert sess._speed == expected

    @pytest.mark.asyncio
    async def test_speed_default_for_unknown_voice(self, monkeypatch):
        # A voice_id not in the override table keeps the default 1.0.
        from heart.ss08_voice import realtime_stream_session as rss

        monkeypatch.setattr(
            "heart.ss08_voice.voice_catalog.get_voice_id", lambda cid: "not-overridden"
        )

        async def send_audio(t_id, seq, data, is_last, fmt, sample_rate=None):
            pass

        sess = rss.RealtimeStreamSession(
            send_audio,
            api_key="k",
            url="wss://x",
            character_id="rin",
            fmt="wav",
            session_factory=lambda mid: FakeRealtimeSession([b"a"]),
        )
        await sess.start()
        assert sess._speed == 1.0

    @pytest.mark.asyncio
    async def test_forwards_sample_rate_from_session(self, monkeypatch):
        # wav/pcm call path: the session reports a sample_rate and it must reach
        # send_audio so the client builds AudioBuffers at the true rate.
        from heart.ss08_voice import realtime_stream_session as rss

        monkeypatch.setattr(
            "heart.ss08_voice.voice_catalog.get_voice_id", lambda cid: "v"
        )
        sent: list[tuple] = []

        async def send_audio(t_id, seq, data, is_last, fmt, sample_rate=None):
            sent.append((fmt, sample_rate))

        fake = FakeRealtimeSession([b"aa", b"bb"], sample_rate=44100)
        session = rss.RealtimeStreamSession(
            send_audio, api_key="k", url="wss://x", character_id="rin",
            fmt="wav", session_factory=lambda model_id: fake,
        )
        await session.start()
        await session.submit("turn-1", "第一句", None, 0.0, [], "rin")
        await session.finish()

        assert [s[0] for s in sent] == ["wav", "wav"]
        assert [s[1] for s in sent] == [44100, 44100]

    @pytest.mark.asyncio
    async def test_cancel_closes_session(self, monkeypatch):
        from heart.ss08_voice import realtime_stream_session as rss

        monkeypatch.setattr(
            "heart.ss08_voice.voice_catalog.get_voice_id", lambda cid: "v"
        )

        async def send_audio(*a):
            pass

        fake = FakeRealtimeSession([b"x"])
        session = rss.RealtimeStreamSession(
            send_audio, api_key="k", url="wss://x", character_id="rin",
            session_factory=lambda model_id: fake,
        )
        await session.start()
        session.cancel()
        assert session.is_cancelled
        await asyncio.sleep(0)  # let the scheduled close() run
        assert fake.closed


class TestCreateStreamSessionSelection:
    def _voice_service(self):
        from unittest.mock import MagicMock

        vs = MagicMock()
        return vs

    def _ws(self):
        from unittest.mock import AsyncMock

        return AsyncMock()

    def test_flag_off_returns_rest_stream_session(self, monkeypatch):
        from heart.api import routes_chat_ws as m
        from heart.core.config import settings
        from heart.ss08_voice.stream_session import StreamSession

        monkeypatch.setattr(settings, "fish_realtime_enabled", False)
        monkeypatch.setattr(settings, "fish_api_key", "k")
        sess = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="fish", character_id="rin",
        )
        assert isinstance(sess, StreamSession)

    def test_flag_on_fish_returns_realtime(self, monkeypatch):
        from heart.api import routes_chat_ws as m
        from heart.core.config import settings
        from heart.ss08_voice.realtime_stream_session import RealtimeStreamSession

        monkeypatch.setattr(settings, "fish_realtime_enabled", True)
        monkeypatch.setattr(settings, "fish_api_key", "k")
        monkeypatch.setattr(settings, "fish_realtime_url", "wss://x")
        sess = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="fish", character_id="rin",
        )
        assert isinstance(sess, RealtimeStreamSession)

    def test_flag_on_but_mimo_returns_rest(self, monkeypatch):
        from heart.api import routes_chat_ws as m
        from heart.core.config import settings
        from heart.ss08_voice.stream_session import StreamSession

        monkeypatch.setattr(settings, "fish_realtime_enabled", True)
        monkeypatch.setattr(settings, "fish_api_key", "k")
        sess = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="mimo", character_id="rin",
        )
        assert isinstance(sess, StreamSession)

    def test_call_channel_selects_wav_format(self, monkeypatch):
        from heart.api import routes_chat_ws as m
        from heart.core.config import settings

        monkeypatch.setattr(settings, "fish_realtime_enabled", True)
        monkeypatch.setattr(settings, "fish_api_key", "k")
        monkeypatch.setattr(settings, "fish_realtime_url", "wss://x")
        call = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="fish", character_id="rin", channel="call",
        )
        chat = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="fish", character_id="rin", channel="chat",
        )
        assert call._fmt == "wav"  # call needs per-frame decodable linear PCM
        assert chat._fmt == "mp3"  # chat concatenates + plays once at turn_end

    def test_allow_realtime_false_forces_rest(self, monkeypatch):
        from heart.api import routes_chat_ws as m
        from heart.core.config import settings
        from heart.ss08_voice.stream_session import StreamSession

        monkeypatch.setattr(settings, "fish_realtime_enabled", True)
        monkeypatch.setattr(settings, "fish_api_key", "k")
        monkeypatch.setattr(settings, "fish_realtime_url", "wss://x")
        sess = m._create_stream_session(
            self._voice_service(), self._ws(),
            preferred_provider_name="fish", character_id="rin",
            allow_realtime=False,
        )
        assert isinstance(sess, StreamSession)
