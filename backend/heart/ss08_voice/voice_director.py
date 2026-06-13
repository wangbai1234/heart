"""Voice Director — maps emotion/relationship state to TTS parameters.

优先级：
1. locked_emotion（turn 级锁定，同 turn 所有句子共享同一情绪基调）
2. 句子文本本身推断的 delivery emotion（高 confidence 时直接采用）
3. SS03 角色 VAD 状态（fallback）
4. 默认 neutral

Intimacy 在第 1/2 之上做整体放慢 + 降 pitch 调整。

平滑：per-character_id prior emotion 记忆 + EMA 平滑，避免相邻轮次情绪过山车。
Turn-Locked Emotion：一个 turn 锁定一个情绪基调，per-sentence 只允许微幅 speed/pitch 调整。
"""

from __future__ import annotations

import time
from threading import Lock
from typing import Dict, List, Optional

from heart.ss08_voice.text_emotion import infer_emotion_from_text
from heart.ss08_voice.types import TTSRequest
from heart.ss08_voice.voice_catalog import get_voice_id


class VoiceDirector:
    """Maps emotion/relationship/text state to TTSRequest parameters.

    Includes per-character prior emotion memory + EMA smoothing to prevent
    jarring emotion transitions between consecutive sentences.
    Supports turn-locked emotion: when locked_emotion is provided, all
    sentences in the turn share the same emotion基调 with only micro
    speed/pitch adjustments from per-sentence text_emotion.
    """

    EMOTION_MAP_RULES = [
        (lambda v, a, d: v > 0.35 and a > 0.45, "happy", +0.07, +2),
        (lambda v, a, d: v < -0.3 and a > 0.55 and d > 0.45, "angry", +0.10, +2),
        (lambda v, a, d: v < -0.3 and a > 0.55 and d <= 0.35, "fearful", +0.15, +3),
        (lambda v, a, d: v < -0.2 and a < 0.4, "sad", -0.15, -2),
        (lambda v, a, d: v > 0.15, "happy", +0.04, +1),
        (lambda v, a, d: v < -0.1, "sad", -0.08, -1),
    ]

    TEXT_CONF_OVERRIDE = 0.7
    INERTIA_ALPHA = 0.7
    PRIOR_TTL_SECONDS = 120

    EMO_NEIGHBOR: dict[str, set[str]] = {
        "neutral": {"happy", "sad", "surprised", "fearful", "angry"},
        "happy": {"neutral", "surprised"},
        "sad": {"neutral", "fearful"},
        "angry": {"neutral", "surprised"},
        "fearful": {"neutral", "sad", "surprised"},
        "surprised": {"neutral", "happy", "angry", "fearful"},
        "disgusted": {"neutral", "angry"},
    }

    _prior: dict[str, tuple[str, float, int, float]] = {}
    _lock = Lock()

    def derive(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[str]] = None,
        locked_emotion: Optional[str] = None,
        locked_speed_base: Optional[float] = None,
        locked_pitch_base: Optional[int] = None,
    ) -> TTSRequest:
        """Derive TTSRequest. locked_emotion > text inference > vad.带 EMA 平滑。"""
        if locked_emotion is not None:
            tgt_emo = locked_emotion
            tgt_sp = locked_speed_base if locked_speed_base is not None else 1.0
            tgt_pi = locked_pitch_base if locked_pitch_base is not None else 0
            per = infer_emotion_from_text(text or "")
            if per.confidence > 0:
                tgt_sp += per.speed_delta * 0.3
                tgt_pi = round(tgt_pi + per.pitch_delta * 0.3)
        else:
            inferred = infer_emotion_from_text(text or "")

            if inferred.confidence >= self.TEXT_CONF_OVERRIDE:
                tgt_emo = inferred.emotion
                tgt_sp = 1.0 + inferred.speed_delta
                tgt_pi = inferred.pitch_delta
            else:
                v = (vad or {}).get("valence", 0.0)
                a = (vad or {}).get("arousal", 0.3)
                d = (vad or {}).get("dominance", 0.5)
                vad_hit = self._from_vad(v, a, d)
                if vad_hit is not None:
                    tgt_emo, sp_d, pi_d = vad_hit
                    tgt_sp = 1.0 + sp_d
                    tgt_pi = pi_d
                elif inferred.confidence > 0:
                    tgt_emo = inferred.emotion
                    tgt_sp = 1.0 + inferred.speed_delta
                    tgt_pi = inferred.pitch_delta
                else:
                    tgt_emo, tgt_sp, tgt_pi = "neutral", 1.0, 0

        now = time.monotonic()
        with self._lock:
            prior = self._prior.get(character_id)
            if prior and (now - prior[3]) <= self.PRIOR_TTL_SECONDS:
                prev_emo, prev_sp, prev_pi, _ = prior
                if tgt_emo != prev_emo and tgt_emo not in self.EMO_NEIGHBOR.get(prev_emo, set()):
                    tgt_emo = "neutral"
                alpha = self.INERTIA_ALPHA
                tgt_sp = alpha * tgt_sp + (1 - alpha) * prev_sp
                tgt_pi = round(alpha * tgt_pi + (1 - alpha) * prev_pi)

            tgt_sp = tgt_sp - 0.05 * max(0.0, min(1.0, intimacy))
            if intimacy > 0.6:
                tgt_pi -= 1
            tgt_sp = max(0.7, min(1.3, tgt_sp))
            tgt_pi = max(-6, min(6, tgt_pi))
            self._prior[character_id] = (tgt_emo, tgt_sp, tgt_pi, now)

        return TTSRequest(
            text=text,
            voice_id=get_voice_id(character_id),
            emotion=tgt_emo,
            speed=tgt_sp,
            pitch=tgt_pi,
            volume=1.0,
        )

    @staticmethod
    def _from_vad(v: float, a: float, d: float) -> tuple[str, float, int] | None:
        for pred, emo, sp_d, pi_d in VoiceDirector.EMOTION_MAP_RULES:
            if pred(v, a, d):
                return emo, sp_d, pi_d
        return None
