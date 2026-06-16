"""非流式 TTS Session — 累积句子文本，在 turn 结束时合成完整音频并发送语音消息。"""

from __future__ import annotations

import re
from typing import Any, Callable

import structlog

logger = structlog.get_logger(__name__)

# Strip parenthetical stage directions before TTS: （动作描写）
_STAGE_DIRECTION_RE = re.compile(r"（[^）]{0,50}）")
# Strip leftover whitespace after removal
_MULTI_SPACE_RE = re.compile(r" {2,}")


def strip_stage_directions(text: str) -> str:
    """Remove Chinese parenthetical action descriptions from text.

    Examples removed: （手指在茶杯边缘停顿了一瞬）, （微笑）, （叹气）
    Keeps text like （略） which is a content placeholder.
    """
    cleaned = _STAGE_DIRECTION_RE.sub("", text)
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


class VoiceMessageSession:
    """非流式 TTS Session — 累积句子文本，在 turn 结束时合成完整音频并发送语音消息。"""

    def __init__(self, voice_service: Any, ws_send_voice_message: Callable):
        """
        Args:
            voice_service: VoiceService 实例
            ws_send_voice_message: async callable(turn_id: str, result: TTSResult)
        """
        self._voice_service = voice_service
        self._ws_send_voice_message = ws_send_voice_message
        self._sentences: list[str] = []
        self._cancelled = False
        self._last_vad: dict[str, float] | None = None
        self._last_intimacy: float = 0.0

    def cancel(self) -> None:
        """取消当前 session。"""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        """返回是否已取消。"""
        return self._cancelled

    async def submit(self, sentence: str, vad: dict | None, intimacy: float) -> None:
        """累积句子文本，保留最新的 VAD 和 intimacy 用于合成。

        Args:
            sentence: 句子文本
            vad: VAD dict with valence, arousal, dominance (-1..1)
            intimacy: 亲密度 (0..1)
        """
        if not self._cancelled:
            self._sentences.append(sentence)
            if vad is not None:
                self._last_vad = vad
            self._last_intimacy = intimacy

    async def finish(self, turn_id: str, character_id: str) -> None:
        """将所有句子拼接为完整文本，清洗后调用 voice_service 合成并发送。

        Uses synthesize_with_state() to pass VAD/intimacy through VoiceDirector
        for emotion-aware TTS. Falls back to synthesize_for_character() if
        VoiceDirector is not available.

        Args:
            turn_id: turn ID
            character_id: character ID (e.g., 'rin', 'dorothy')
        """
        if self._cancelled or not self._sentences:
            return

        try:
            full_text = strip_stage_directions("".join(self._sentences))
            if not full_text:
                return

            result = await self._voice_service.synthesize_with_state(
                text=full_text,
                character_id=character_id,
                vad=self._last_vad,
                intimacy=self._last_intimacy,
            )
            await self._ws_send_voice_message(turn_id, result)
        except Exception as e:
            logger.error(
                "voice_message_synthesis_failed",
                turn_id=turn_id,
                character_id=character_id,
                error=str(e),
            )
