"""Voice Director — maps emotion/relationship state to TTS parameters."""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from heart.ss08_voice.types import TTSRequest
from heart.ss08_voice.voice_catalog import get_voice_id

# Temporary emotion keywords for text-based heuristic (until EmotionService integration)
_EMOTION_KEYWORDS = {
    "happy": r"(哈哈|开心|高兴|太好了|棒|喜欢|爱|😊|😄|😁|🎉)",
    "sad": r"(难过|伤心|失望|遗憾|可惜|😢|😭|💔)",
    "angry": r"(生气|愤怒|讨厌|烦|混蛋|😠|😡|💢)",
    "surprised": r"(哇|天啊|不会吧|真的吗|惊讶|😮|😲|😱)",
}


class VoiceDirector:
    """Maps emotion/relationship state to TTSRequest parameters."""

    def _detect_text_emotion(self, text: str) -> Optional[str]:
        """Detect emotion from text keywords (temporary heuristic).

        TODO: Replace with proper EmotionService.process_turn() integration.
        This is a fallback when VAD is default/neutral.
        """
        for emotion, pattern in _EMOTION_KEYWORDS.items():
            if re.search(pattern, text):
                return emotion
        return None

    EMOTION_MAP_RULES = [
        # (predicate, emotion, speed_delta, pitch_delta)
        # Order matters: first match wins
        (lambda v, a, d: v > 0.4 and a > 0.5, "happy", +0.05, +1),
        (lambda v, a, d: v < -0.3 and a > 0.6 and d > 0.5, "angry", +0.10, +2),
        (lambda v, a, d: v < -0.3 and a > 0.6 and d <= 0.3, "fearful", +0.15, +3),
        (lambda v, a, d: v < -0.3 and a < 0.3, "sad", -0.15, -2),
        (lambda v, a, d: abs(v) < 0.2 and a < 0.3, "neutral", 0.0, 0),
        (lambda v, a, d: True, "neutral", 0.0, 0),  # default
    ]

    def derive(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[str]] = None,
    ) -> TTSRequest:
        """Derive TTSRequest from emotion/relationship state.

        Args:
            text: Text to synthesize.
            character_id: Character ID (e.g., 'rin', 'dorothy').
            vad: VAD dict with valence, arousal, dominance (-1..1).
            intimacy: Intimacy level (0..1).
            active_emotions: List of active emotion names.
        """
        v = (vad or {}).get("valence", 0.0)
        a = (vad or {}).get("arousal", 0.3)
        d = (vad or {}).get("dominance", 0.5)

        # Default values
        emotion = "neutral"
        speed_delta = 0.0
        pitch_delta = 0

        # Find matching emotion rule
        for pred, emo, sp_d, pi_d in self.EMOTION_MAP_RULES:
            if pred(v, a, d):
                emotion, speed_delta, pitch_delta = emo, sp_d, pi_d
                break

        # Fallback: text-based emotion detection when VAD is default/neutral
        # (until EmotionService.process_turn() integration)
        if emotion == "neutral" and abs(v) < 0.1 and abs(a - 0.3) < 0.1:
            text_emotion = self._detect_text_emotion(text)
            if text_emotion:
                # Apply emotion-specific deltas
                emotion_deltas = {
                    "happy": (+0.05, +1),
                    "sad": (-0.15, -2),
                    "angry": (+0.10, +2),
                    "surprised": (+0.08, +2),
                }
                if text_emotion in emotion_deltas:
                    emotion = text_emotion
                    speed_delta, pitch_delta = emotion_deltas[text_emotion]

        # Intimacy adjustments: higher intimacy → slower, lower pitch
        intimacy_speed_mod = -0.05 * max(0.0, min(1.0, intimacy))
        intimacy_pitch_mod = -1 if intimacy > 0.6 else 0

        voice_id = get_voice_id(character_id)

        return TTSRequest(
            text=text,
            voice_id=voice_id,
            emotion=emotion,
            speed=max(0.7, min(1.3, 1.0 + speed_delta + intimacy_speed_mod)),
            pitch=max(-6, min(6, pitch_delta + intimacy_pitch_mod)),
            volume=1.0,
        )
