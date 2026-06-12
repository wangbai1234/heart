"""Voice Director — maps emotion/relationship state to TTS parameters."""

from __future__ import annotations

from typing import Dict, List, Optional

from heart.ss08_voice.types import TTSRequest
from heart.ss08_voice.voice_catalog import get_voice_id


class VoiceDirector:
    """Maps emotion/relationship state to TTSRequest parameters."""

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
