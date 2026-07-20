"""Unit tests for B4: chat WS per-model billing + assert_model_allowed."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# _charge_llm_cost — idempotency key + skip-when-free
# ---------------------------------------------------------------------------


class TestChargeLlmCost:
    @pytest.mark.asyncio
    async def test_deepseek_returns_zero_no_deduction(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        cost, bal = await _charge_llm_cost(db, uuid.uuid4(), str(uuid.uuid4()), "deepseek")
        assert cost == 0
        assert bal == 0
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_grok_deducts_with_idempotency_key(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=5000)) as mock_deduct:
            cost, bal = await _charge_llm_cost(db, user_id, turn_id, "grok")

        assert cost == 300  # grok_cost_credits=3 → 300 fen
        assert bal == 5000
        mock_deduct.assert_called_once_with(db, user_id, 300, f"turn:{turn_id}:llm", "consume_llm")

    @pytest.mark.asyncio
    async def test_claude_deducts_1200_fen(self):
        from heart.api.routes_chat_ws import _charge_llm_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=3000)) as mock_deduct:
            cost, bal = await _charge_llm_cost(db, user_id, turn_id, "claude")

        assert cost == 1200  # claude_cost_credits=12 → 1200 fen
        assert bal == 3000
        mock_deduct.assert_called_once_with(db, user_id, 1200, f"turn:{turn_id}:llm", "consume_llm")

    @pytest.mark.asyncio
    async def test_idempotency_key_format(self):
        """Key must be 'turn:<turn_id>:llm' — downstream billing relies on this."""
        from heart.api.routes_chat_ws import _charge_llm_cost

        captured = {}

        async def fake_deduct(db, user_id, amount, idempotency_key, reason):
            captured["key"] = idempotency_key
            return 0

        db = AsyncMock()
        turn_id = "abc-123-def"
        with patch("heart.billing.deduct_credits", new=fake_deduct):
            await _charge_llm_cost(db, uuid.uuid4(), turn_id, "grok")

        assert captured["key"] == "turn:abc-123-def:llm"


# ---------------------------------------------------------------------------
# _precheck_billing — model_forbidden gate
# ---------------------------------------------------------------------------


class TestPrecheckBillingModelForbidden:
    @pytest.mark.asyncio
    async def test_grok_forbidden_for_free_user(self):
        """Free tier user requesting grok should receive model_forbidden event."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        user_id = uuid.uuid4()
        turn_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        # voice_enabled query → False
        voice_result = MagicMock()
        voice_result.scalar_one_or_none.return_value = False
        # balance query → high balance
        balance_result = MagicMock()
        balance_result.scalar_one_or_none.return_value = 100000

        mock_db.execute = AsyncMock(side_effect=[voice_result, balance_result])

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch(
                "sqlalchemy.ext.asyncio.AsyncSession",
                return_value=mock_db,
            ),
        ):
            _voice, can_proceed = await _precheck_billing(
                user_id, "char1", turn_id, ws, model="grok"
            )

        assert can_proceed is False
        ws.send_json.assert_called_once()
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "model_forbidden"
        assert sent["model"] == "grok"
        assert sent["tier"] == "free"
        assert sent["turn_id"] == turn_id

    @pytest.mark.asyncio
    async def test_deepseek_allowed_for_free_user(self):
        """Free tier user requesting deepseek should proceed."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        user_id = uuid.uuid4()
        turn_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)

        voice_result = MagicMock()
        voice_result.scalar_one_or_none.return_value = False
        balance_result = MagicMock()
        balance_result.scalar_one_or_none.return_value = 100000
        mock_db.execute = AsyncMock(side_effect=[voice_result, balance_result])

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
        ):
            _voice, can_proceed = await _precheck_billing(
                user_id, "char1", turn_id, ws, model="deepseek"
            )

        assert can_proceed is True
        # No model_forbidden event for deepseek
        for call in ws.send_json.call_args_list:
            assert call[0][0].get("type") != "model_forbidden"


# ---------------------------------------------------------------------------
# _precheck_billing — TTS provider tier gate (E): degrade voice→text, never block
# ---------------------------------------------------------------------------


_TIERS_CFG = (
    '{"free":{"models":["deepseek"],"tts":["mimo"],"clone":[],"monthly_grant":0},'
    '"plus":{"models":["deepseek","grok"],"tts":["mimo","fish"],"clone":["mimo","fish"],"monthly_grant":400}}'
)


def _precheck_mock_db():
    # resolve_effective_voice is patched per-test, so _precheck only issues two
    # db.execute calls itself: voice_enabled lookup + balance floor.
    mock_db = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)
    voice_result = MagicMock()
    voice_result.scalar_one_or_none.return_value = True  # voice enabled
    balance_result = MagicMock()
    balance_result.scalar_one_or_none.return_value = 100000  # ample balance
    mock_db.execute = AsyncMock(side_effect=[voice_result, balance_result])
    return mock_db


def _ev(provider: str):
    from heart.ss08_voice.voice_resolver import EffectiveVoice

    return EffectiveVoice(
        provider=provider, voice_type="clone", voice_id="v", reference_ref=None
    )


class TestPrecheckTtsGate:
    """The TTS gate now trusts resolve_effective_voice: it already tier-degrades
    Fish→MiMo for free users (still voice), so _precheck only degrades to TEXT
    when no tier-allowed ready voice exists (resolver returns None)."""

    @pytest.mark.asyncio
    async def test_no_usable_voice_degrades_to_text(self):
        """resolve_effective_voice → None → voice off, turn NOT blocked."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        turn_id = str(uuid.uuid4())
        mock_db = _precheck_mock_db()

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
            patch(
                "heart.ss08_voice.voice_resolver.resolve_effective_voice",
                new=AsyncMock(return_value=None),
            ),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
        ):
            effective_voice, can_proceed = await _precheck_billing(
                uuid.uuid4(), "char1", turn_id, ws, model="deepseek"
            )

        assert effective_voice is False  # degraded to text
        assert can_proceed is True  # never block the text turn
        for call in ws.send_json.call_args_list:
            assert call[0][0].get("type") not in ("model_forbidden", "error")

    @pytest.mark.asyncio
    async def test_free_user_effective_mimo_keeps_voice(self):
        """Free tier resolved to MiMo (e.g. Fish selection degraded) → voice kept."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        turn_id = str(uuid.uuid4())
        mock_db = _precheck_mock_db()

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
            patch(
                "heart.ss08_voice.voice_resolver.resolve_effective_voice",
                new=AsyncMock(return_value=_ev("mimo")),
            ),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
        ):
            effective_voice, can_proceed = await _precheck_billing(
                uuid.uuid4(), "char1", turn_id, ws, model="deepseek"
            )

        assert effective_voice is True
        assert can_proceed is True

    @pytest.mark.asyncio
    async def test_plus_user_effective_fish_keeps_voice(self):
        """Plus tier resolved to Fish → voice preserved."""
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        ws.send_json = AsyncMock()
        turn_id = str(uuid.uuid4())
        mock_db = _precheck_mock_db()

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="plus")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
            patch(
                "heart.ss08_voice.voice_resolver.resolve_effective_voice",
                new=AsyncMock(return_value=_ev("fish")),
            ),
            patch("heart.core.config.settings.membership_tiers_config", _TIERS_CFG),
        ):
            effective_voice, can_proceed = await _precheck_billing(
                uuid.uuid4(), "char1", turn_id, ws, model="deepseek"
            )

        assert effective_voice is True
        assert can_proceed is True


# ---------------------------------------------------------------------------
# TurnRequest carries model field
# ---------------------------------------------------------------------------


class TestTurnRequestModelField:
    def test_default_model_is_deepseek(self):
        from heart.ss07_orchestration.models import TurnRequest

        req = TurnRequest(
            user_id=uuid.uuid4(),
            character_id="rin",
            user_message="hi",
            history=[],
            trace_id=uuid.uuid4(),
        )
        assert req.model == "deepseek"

    def test_model_is_stored(self):
        from heart.ss07_orchestration.models import TurnRequest

        req = TurnRequest(
            user_id=uuid.uuid4(),
            character_id="rin",
            user_message="hi",
            history=[],
            trace_id=uuid.uuid4(),
            model="grok",
        )
        assert req.model == "grok"


# ---------------------------------------------------------------------------
# CompositionContext carries model + stream_meta
# ---------------------------------------------------------------------------


class TestCompositionContextModelFields:
    def test_default_model_is_deepseek(self):
        from heart.ss05_composer.service import CompositionContext

        ctx = CompositionContext(
            user_id=uuid.uuid4(),
            character_id="rin",
            turn_id=uuid.uuid4(),
        )
        assert ctx.model == "deepseek"
        assert ctx.stream_meta == {}

    def test_model_can_be_set(self):
        from heart.ss05_composer.service import CompositionContext

        ctx = CompositionContext(
            user_id=uuid.uuid4(),
            character_id="rin",
            turn_id=uuid.uuid4(),
            model="claude",
        )
        assert ctx.model == "claude"


# ---------------------------------------------------------------------------
# _upload_turn_audio helper
# ---------------------------------------------------------------------------


class TestUploadTurnAudio:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_audio(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        session = MagicMock()
        session.full_audio = b""
        url, dur = await _upload_turn_audio(session, uuid.uuid4(), "turn-1")
        assert url is None
        assert dur is None

    @pytest.mark.asyncio
    async def test_returns_none_when_session_is_none(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        url, dur = await _upload_turn_audio(None, uuid.uuid4(), "turn-1")
        assert url is None
        assert dur is None

    @pytest.mark.asyncio
    async def test_skips_when_s3_not_configured(self):
        from heart.api.routes_chat_ws import _upload_turn_audio

        session = MagicMock()
        session.full_audio = b"\x00" * 1000

        with patch("heart.infra.storage.is_s3_configured", return_value=False):
            url, dur = await _upload_turn_audio(session, uuid.uuid4(), "turn-1")

        assert url is None
        assert dur is None


# ---------------------------------------------------------------------------
# _charge_tts_cost
# ---------------------------------------------------------------------------


class TestChargeTtsCost:
    @pytest.mark.asyncio
    async def test_minimax_returns_zero_no_deduction(self):
        from heart.api.routes_chat_ws import _charge_tts_cost

        db = AsyncMock()
        cost, bal = await _charge_tts_cost(db, uuid.uuid4(), str(uuid.uuid4()), "minimax")
        assert cost == 0
        assert bal == 0
        db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_unknown_provider_returns_zero(self):
        from heart.api.routes_chat_ws import _charge_tts_cost

        db = AsyncMock()
        cost, bal = await _charge_tts_cost(db, uuid.uuid4(), str(uuid.uuid4()), "")
        assert cost == 0
        assert bal == 0

    @pytest.mark.asyncio
    async def test_mimo_deducts_with_consume_tts_type(self):
        from heart.api.routes_chat_ws import _charge_tts_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=9500)) as mock_deduct:
            cost, bal = await _charge_tts_cost(db, user_id, turn_id, "mimo")

        assert cost == 500  # mimo_tts_cost_credits=5 → 500 fen
        assert bal == 9500
        mock_deduct.assert_called_once_with(db, user_id, 500, f"turn:{turn_id}:tts", "consume_tts")

    @pytest.mark.asyncio
    async def test_fish_deducts_800_fen(self):
        from heart.api.routes_chat_ws import _charge_tts_cost

        db = AsyncMock()
        turn_id = str(uuid.uuid4())
        user_id = uuid.uuid4()

        with patch("heart.billing.deduct_credits", new=AsyncMock(return_value=8000)) as mock_deduct:
            cost, bal = await _charge_tts_cost(db, user_id, turn_id, "fish")

        assert cost == 800  # fish_tts_cost_credits=8 → 800 fen
        assert bal == 8000
        mock_deduct.assert_called_once_with(db, user_id, 800, f"turn:{turn_id}:tts", "consume_tts")

    @pytest.mark.asyncio
    async def test_idempotency_key_format(self):
        from heart.api.routes_chat_ws import _charge_tts_cost

        captured = {}

        async def fake_deduct(db, user_id, amount, idempotency_key, reason):
            captured["key"] = idempotency_key
            captured["reason"] = reason
            return 0

        db = AsyncMock()
        turn_id = "xyz-789"
        with patch("heart.billing.deduct_credits", new=fake_deduct):
            await _charge_tts_cost(db, uuid.uuid4(), turn_id, "mimo")

        assert captured["key"] == "turn:xyz-789:tts"
        assert captured["reason"] == "consume_tts"


# ---------------------------------------------------------------------------
# Cross-character routing: every server→client frame must carry character_id so
# the client can route it to the right character (regression: chat bleed bug).
# ---------------------------------------------------------------------------


class TestFramesCarryCharacterId:
    @pytest.mark.asyncio
    async def test_text_delta_frame_tags_character(self):
        from heart.api.routes_chat_ws import _send_text_delta

        ws = AsyncMock()
        await _send_text_delta(ws, "turn-1", "hello", "dorothy")
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "text_delta"
        assert sent["turn_id"] == "turn-1"
        assert sent["character_id"] == "dorothy"
        assert sent["delta"] == "hello"

    @pytest.mark.asyncio
    async def test_sentence_frame_tags_character(self):
        from heart.api.routes_chat_ws import _send_sentence

        ws = AsyncMock()
        await _send_sentence(ws, "turn-2", {"text": "hi"}, "rin")
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "sentence"
        assert sent["character_id"] == "rin"

    @pytest.mark.asyncio
    async def test_turn_end_frame_tags_character(self):
        from heart.api.routes_chat_ws import _send_turn_end

        ws = AsyncMock()
        await _send_turn_end(ws, "turn-3", "dorothy")
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "turn_end"
        assert sent["turn_id"] == "turn-3"
        assert sent["character_id"] == "dorothy"

    @pytest.mark.asyncio
    async def test_audio_chunk_frame_tags_character(self):
        """The StreamSession's send_audio closure must stamp character_id."""
        from heart.api.routes_chat_ws import _create_stream_session

        ws = AsyncMock()
        voice_service = MagicMock()  # truthy → session created

        # Grab the send_audio closure the session was built with.
        with patch("heart.ss08_voice.stream_session.StreamSession") as mock_session:
            _create_stream_session(voice_service, ws, character_id="dorothy")
            send_audio = mock_session.call_args[0][1]

        await send_audio("turn-4", 0, b"\x00\x01", True, "pcm16")
        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "audio_chunk"
        assert sent["character_id"] == "dorothy"
        assert sent["turn_id"] == "turn-4"

    @pytest.mark.asyncio
    async def test_model_forbidden_frame_tags_character(self):
        from heart.api.routes_chat_ws import _precheck_billing

        ws = AsyncMock()
        user_id = uuid.uuid4()
        turn_id = str(uuid.uuid4())

        mock_db = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=False)
        voice_result = MagicMock()
        voice_result.scalar_one_or_none.return_value = False
        mock_db.execute = AsyncMock(side_effect=[voice_result])

        with (
            patch("heart.membership.get_effective_tier", new=AsyncMock(return_value="free")),
            patch("heart.api.routes_chat_ws._get_engine"),
            patch("sqlalchemy.ext.asyncio.AsyncSession", return_value=mock_db),
        ):
            await _precheck_billing(user_id, "dorothy", turn_id, ws, model="grok")

        sent = ws.send_json.call_args[0][0]
        assert sent["type"] == "model_forbidden"
        assert sent["character_id"] == "dorothy"


class TestLockedWS:
    """_LockedWS serialises sends across concurrent turn tasks and forwards
    every other attribute to the real socket transparently."""

    @pytest.mark.asyncio
    async def test_send_json_forwards_under_lock(self):
        import asyncio

        from heart.api.routes_chat_ws import _LockedWS

        real = AsyncMock()
        locked = _LockedWS(real, asyncio.Lock())
        await locked.send_json({"type": "turn_end", "turn_id": "t1"})
        real.send_json.assert_awaited_once_with({"type": "turn_end", "turn_id": "t1"})

    @pytest.mark.asyncio
    async def test_concurrent_sends_do_not_interleave(self):
        """Two tasks sending concurrently must each complete a whole send while
        holding the lock — no partial interleaving on the shared socket."""
        import asyncio

        from heart.api.routes_chat_ws import _LockedWS

        order: list[str] = []

        class RecordingWS:
            async def send_json(self, data):
                order.append(f"start:{data['id']}")
                await asyncio.sleep(0)  # yield so a naive impl would interleave
                order.append(f"end:{data['id']}")

        locked = _LockedWS(RecordingWS(), asyncio.Lock())
        await asyncio.gather(
            locked.send_json({"id": "a"}),
            locked.send_json({"id": "b"}),
        )
        # Each send's start is immediately followed by its own end.
        assert order in (
            ["start:a", "end:a", "start:b", "end:b"],
            ["start:b", "end:b", "start:a", "end:a"],
        )

    def test_forwards_other_attributes(self):
        import asyncio

        from heart.api.routes_chat_ws import _LockedWS

        real = MagicMock()
        real.client_state = "CONNECTED"
        locked = _LockedWS(real, asyncio.Lock())
        assert locked.client_state == "CONNECTED"

    @pytest.mark.asyncio
    async def test_detach_makes_send_a_noop(self):
        """After detach, sends no-op so a departed client never aborts the turn —
        the turn keeps synthesising + persisting voice in the background."""
        import asyncio

        from heart.api.routes_chat_ws import _LockedWS

        real = AsyncMock()
        locked = _LockedWS(real, asyncio.Lock())
        locked.detach()
        await locked.send_json({"type": "turn_end", "turn_id": "t1"})
        real.send_json.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_failure_auto_detaches_and_swallows(self):
        """A send that raises (peer gone before WebSocketDisconnect surfaced) is
        swallowed and flips the proxy to detached, so the turn completes instead
        of crashing on the first failed send."""
        import asyncio

        from heart.api.routes_chat_ws import _LockedWS

        real = AsyncMock()
        real.send_json.side_effect = RuntimeError("connection closed")
        locked = _LockedWS(real, asyncio.Lock())
        # Must not raise despite the underlying socket erroring.
        await locked.send_json({"type": "text_delta", "turn_id": "t1"})
        assert locked._detached is True
        # Subsequent sends are no-ops (already detached).
        real.send_json.reset_mock()
        await locked.send_json({"type": "turn_end", "turn_id": "t1"})
        real.send_json.assert_not_awaited()


class TestByTurnAudioRoute:
    def test_by_turn_route_registered_before_message_id(self):
        """The by-turn route must be declared before the /{message_id} catch-all
        so `by-turn` is never captured as a message_id."""
        from heart.api import routes_chat_ws as m

        audio_paths = [
            r.path for r in m.router.routes if "/api/chat/audio" in getattr(r, "path", "")
        ]
        assert "/api/chat/audio/by-turn/{turn_id}" in audio_paths
        assert "/api/chat/audio/{message_id}" in audio_paths
        assert audio_paths.index("/api/chat/audio/by-turn/{turn_id}") < audio_paths.index(
            "/api/chat/audio/{message_id}"
        )


# ---------------------------------------------------------------------------
# _upload_turn_audio — persist in the provider's real format so replay decodes
# ---------------------------------------------------------------------------


class _FakeSession:
    def __init__(self, audio: bytes, audio_format: str):
        self.full_audio = audio
        self.audio_format = audio_format


class TestUploadTurnAudio:
    """Regression for replayed voice failing with '语音没能播放': MiMo emits
    headerless PCM16, which must be WAV-wrapped before upload; mp3 must stay
    mp3 (not relabelled audio/wav)."""

    @pytest.mark.asyncio
    async def test_pcm16_is_wrapped_as_wav(self):
        from heart.api import routes_chat_ws

        captured: dict = {}

        async def fake_upload(data, key, content_type):
            captured["data"] = data
            captured["key"] = key
            captured["content_type"] = content_type
            return f"s3://bucket/{key}"

        uid = uuid.uuid4()
        session = _FakeSession(b"\x01\x02" * 24000, "pcm16")
        with (
            patch("heart.infra.storage.is_s3_configured", return_value=True),
            patch("heart.infra.storage.upload_file", new=fake_upload),
        ):
            url, dur = await routes_chat_ws._upload_turn_audio(session, uid, "turn-1")

        assert captured["content_type"] == "audio/wav"
        assert captured["key"].endswith(".wav")
        assert captured["data"].startswith(b"RIFF")  # WAV header added
        assert url is not None
        assert dur == 1000  # 48000 bytes PCM @ 24kHz/16-bit mono = 1s

    @pytest.mark.asyncio
    async def test_mp3_kept_as_mpeg(self):
        from heart.api import routes_chat_ws

        captured: dict = {}

        async def fake_upload(data, key, content_type):
            captured["key"] = key
            captured["content_type"] = content_type
            return f"s3://bucket/{key}"

        uid = uuid.uuid4()
        session = _FakeSession(b"ID3\x03\x00fake-mp3-bytes", "mp3")
        with (
            patch("heart.infra.storage.is_s3_configured", return_value=True),
            patch("heart.infra.storage.upload_file", new=fake_upload),
        ):
            url, dur = await routes_chat_ws._upload_turn_audio(session, uid, "turn-2")

        assert captured["content_type"] == "audio/mpeg"
        assert captured["key"].endswith(".mp3")
        assert url is not None

    @pytest.mark.asyncio
    async def test_already_wav_not_double_wrapped(self):
        from heart.api import routes_chat_ws
        from heart.api.routes_voice import _pcm16_to_wav

        captured: dict = {}

        async def fake_upload(data, key, content_type):
            captured["data"] = data
            captured["content_type"] = content_type
            return "s3://bucket/x.wav"

        uid = uuid.uuid4()
        wav = _pcm16_to_wav(b"\x00\x00" * 100)
        session = _FakeSession(wav, "wav")
        with (
            patch("heart.infra.storage.is_s3_configured", return_value=True),
            patch("heart.infra.storage.upload_file", new=fake_upload),
        ):
            await routes_chat_ws._upload_turn_audio(session, uid, "turn-3")

        # RIFF bytes passed through untouched (no second header prepended)
        assert captured["data"] == wav

    @pytest.mark.asyncio
    async def test_no_audio_returns_none(self):
        from heart.api import routes_chat_ws

        session = _FakeSession(b"", "pcm16")
        url, dur = await routes_chat_ws._upload_turn_audio(session, uuid.uuid4(), "t")
        assert url is None and dur is None
