"""Voice Director — maps emotion/relationship state to TTS parameters.

优先级：
1. 句子文本本身推断的 delivery emotion（高 confidence 时直接采用）
2. SS03 角色 VAD 状态（fallback）
3. 默认 neutral

Intimacy 在第 1/2 之上做整体放慢 + 降 pitch 调整。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from heart.ss08_voice.text_emotion import infer_emotion_from_text
from heart.ss08_voice.types import TTSRequest
from heart.ss08_voice.voice_catalog import get_voice_id


class VoiceDirector:
    """Maps emotion/relationship/text state to TTSRequest parameters."""

    # vad fallback 规则。边界比原版宽松：a 阈值从 0.3 → 0.35，
    # 否则默认 vad (0, 0.3, 0.5) 会精准卡在边界外永远落到 neutral。
    EMOTION_MAP_RULES = [
        # (predicate, emotion, speed_delta, pitch_delta)
        (lambda v, a, d: v > 0.35 and a > 0.45, "happy", +0.07, +2),
        (lambda v, a, d: v < -0.3 and a > 0.55 and d > 0.45, "angry", +0.10, +2),
        (lambda v, a, d: v < -0.3 and a > 0.55 and d <= 0.35, "fearful", +0.15, +3),
        (lambda v, a, d: v < -0.2 and a < 0.4, "sad", -0.15, -2),
        (lambda v, a, d: v > 0.15, "happy", +0.04, +1),
        (lambda v, a, d: v < -0.1, "sad", -0.08, -1),
    ]

    # 高/低于此 confidence 时分别采用文本推断 / vad fallback
    TEXT_CONF_OVERRIDE = 0.7

    def derive(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[str]] = None,
    ) -> TTSRequest:
        """Derive TTSRequest. Text inference 主导，vad 兜底。"""
        inferred = infer_emotion_from_text(text or "")

        if inferred.confidence >= self.TEXT_CONF_OVERRIDE:
            emotion = inferred.emotion
            speed_delta = inferred.speed_delta
            pitch_delta = inferred.pitch_delta
        else:
            # 文本不确定 → 尝试 vad；vad 也不命中 → 用文本的低置信结果
            vad_emotion, vad_sp, vad_pi = self._from_vad(vad)
            if vad_emotion != "neutral":
                emotion, speed_delta, pitch_delta = vad_emotion, vad_sp, vad_pi
            elif inferred.confidence > 0:
                emotion, speed_delta, pitch_delta = (
                    inferred.emotion,
                    inferred.speed_delta,
                    inferred.pitch_delta,
                )
            else:
                emotion, speed_delta, pitch_delta = "neutral", 0.0, 0

        # Intimacy 调整：高亲密度 → 整体放慢、压一点 pitch（更温柔）
        clamped_intimacy = max(0.0, min(1.0, intimacy))
        intimacy_speed_mod = -0.05 * clamped_intimacy
        intimacy_pitch_mod = -1 if clamped_intimacy > 0.6 else 0

        return TTSRequest(
            text=text,
            voice_id=get_voice_id(character_id),
            emotion=emotion,
            speed=max(0.7, min(1.3, 1.0 + speed_delta + intimacy_speed_mod)),
            pitch=max(-6, min(6, pitch_delta + intimacy_pitch_mod)),
            volume=1.0,
        )

    @staticmethod
    def _from_vad(vad: Optional[Dict[str, float]]) -> tuple[str, float, int]:
        v = (vad or {}).get("valence", 0.0)
        a = (vad or {}).get("arousal", 0.3)
        d = (vad or {}).get("dominance", 0.5)
        for pred, emo, sp_d, pi_d in VoiceDirector.EMOTION_MAP_RULES:
            if pred(v, a, d):
                return emo, sp_d, pi_d
        return "neutral", 0.0, 0
