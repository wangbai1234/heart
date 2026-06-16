"""VoiceMessageSession 单元测试。"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from heart.ss08_voice.voice_message_session import (
    VoiceMessageSession,
    strip_stage_directions,
)
from heart.ss08_voice.types import TTSResult


@pytest.fixture
def mock_voice_service():
    return MagicMock()


@pytest.fixture
def mock_ws_send():
    return AsyncMock()


@pytest.fixture
def session(mock_voice_service, mock_ws_send):
    return VoiceMessageSession(mock_voice_service, mock_ws_send)


# ── strip_stage_directions tests ──


class TestStripStageDirections:
    def test_removes_parenthetical_action(self):
        text = "（手指在茶杯边缘停顿了一瞬）……这么突然。"
        assert strip_stage_directions(text) == "……这么突然。"

    def test_removes_multiple_parentheticals(self):
        text = "（微笑）你好啊。（叹气）算了吧。"
        assert strip_stage_directions(text) == "你好啊。算了吧。"

    def test_removes_mid_sentence_parenthetical(self):
        text = "237天没见了，（低头）偏偏选在要下雨的时候说这种话。"
        assert strip_stage_directions(text) == "237天没见了，偏偏选在要下雨的时候说这种话。"

    def test_preserves_text_without_parentheticals(self):
        text = "你好，今天天气真好。"
        assert strip_stage_directions(text) == "你好，今天天气真好。"

    def test_empty_text(self):
        assert strip_stage_directions("") == ""

    def test_only_parenthetical(self):
        assert strip_stage_directions("（沉默）") == ""

    def test_preserves_english_parentheses(self):
        text = "这是(test)文本"
        assert strip_stage_directions(text) == "这是(test)文本"

    def test_long_parenthetical_preserved(self):
        """Parentheticals over 50 chars are likely real content, not stage directions."""
        long_content = "这" * 51
        text = f"（{long_content}）你好"
        assert f"（{long_content}）" in strip_stage_directions(text)


# ── VoiceMessageSession tests ──


class TestVoiceMessageSession:
    """测试 VoiceMessageSession 类。"""

    @pytest.mark.asyncio
    async def test_submit_accumulates_sentences(self, session):
        await session.submit("你好", None, 0.0)
        await session.submit("今天天气真好", None, 0.0)

        assert len(session._sentences) == 2
        assert session._sentences[0] == "你好"
        assert session._sentences[1] == "今天天气真好"

    @pytest.mark.asyncio
    async def test_submit_retains_vad(self, session):
        vad = {"valence": 0.7, "arousal": 0.6, "dominance": 0.5}
        await session.submit("开心", vad, 0.5)

        assert session._last_vad == vad
        assert session._last_intimacy == 0.5

    @pytest.mark.asyncio
    async def test_submit_retains_latest_vad(self, session):
        vad1 = {"valence": 0.1, "arousal": 0.2, "dominance": 0.3}
        vad2 = {"valence": 0.8, "arousal": 0.9, "dominance": 0.5}
        await session.submit("第一句", vad1, 0.2)
        await session.submit("第二句", vad2, 0.7)

        assert session._last_vad == vad2
        assert session._last_intimacy == 0.7

    @pytest.mark.asyncio
    async def test_submit_none_vad_does_not_overwrite(self, session):
        vad = {"valence": 0.5, "arousal": 0.5, "dominance": 0.5}
        await session.submit("有情绪", vad, 0.5)
        await session.submit("无情绪", None, 0.3)

        assert session._last_vad == vad
        assert session._last_intimacy == 0.3

    @pytest.mark.asyncio
    async def test_finish_calls_synthesize_with_state(
        self, session, mock_voice_service, mock_ws_send
    ):
        vad = {"valence": 0.6, "arousal": 0.7, "dominance": 0.5}
        await session.submit("你好", vad, 0.4)
        await session.submit("今天天气真好", None, 0.4)

        mock_result = TTSResult(
            audio=b"audio_data",
            format="wav",
            duration_ms=1000,
            request_id="test-id",
        )
        mock_voice_service.synthesize_with_state = AsyncMock(return_value=mock_result)

        await session.finish("turn-123", "rin")

        mock_voice_service.synthesize_with_state.assert_called_once_with(
            text="你好今天天气真好",
            character_id="rin",
            vad=vad,
            intimacy=0.4,
        )
        mock_ws_send.assert_called_once_with("turn-123", mock_result)

    @pytest.mark.asyncio
    async def test_finish_strips_stage_directions(
        self, session, mock_voice_service, mock_ws_send
    ):
        await session.submit("（微笑）你好啊。", None, 0.0)

        mock_result = TTSResult(
            audio=b"audio_data",
            format="wav",
            duration_ms=500,
            request_id="test-id",
        )
        mock_voice_service.synthesize_with_state = AsyncMock(return_value=mock_result)

        await session.finish("turn-123", "rin")

        call_kwargs = mock_voice_service.synthesize_with_state.call_args.kwargs
        assert "（微笑）" not in call_kwargs["text"]
        assert call_kwargs["text"] == "你好啊。"

    @pytest.mark.asyncio
    async def test_finish_only_stage_direction_is_noop(
        self, session, mock_voice_service, mock_ws_send
    ):
        """If text is only stage directions, finish should be a no-op."""
        await session.submit("（沉默）", None, 0.0)

        await session.finish("turn-123", "rin")

        mock_ws_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_finish_after_cancel_is_noop(self, session, mock_voice_service, mock_ws_send):
        await session.submit("你好", None, 0.0)
        session.cancel()

        await session.finish("turn-123", "rin")

        mock_ws_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_finish_with_no_sentences_is_noop(self, session, mock_voice_service, mock_ws_send):
        await session.finish("turn-123", "rin")

        mock_ws_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_finish_synthesis_error_logged(self, session, mock_voice_service, mock_ws_send):
        await session.submit("你好", None, 0.0)

        mock_voice_service.synthesize_with_state = AsyncMock(
            side_effect=Exception("Synthesis failed")
        )

        await session.finish("turn-123", "rin")

        mock_ws_send.assert_not_called()

    def test_cancel_sets_is_cancelled(self, session):
        assert not session.is_cancelled
        session.cancel()
        assert session.is_cancelled

    @pytest.mark.asyncio
    async def test_submit_after_cancel_is_noop(self, session):
        session.cancel()
        await session.submit("你好", None, 0.0)

        assert len(session._sentences) == 0
