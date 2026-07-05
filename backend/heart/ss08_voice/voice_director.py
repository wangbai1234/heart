"""Voice Director — maps emotion/relationship state to TTS parameters."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from heart.ss08_voice.types import TTSRequest
from heart.ss08_voice.voice_catalog import VoiceProfile, get_voice_profile


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

    _TAG_BY_EMOTION = {
        "happy": "(chuckle)",
        "sad": "(sighs)",
        "fearful": "(breath)",
        "surprised": "(gasps)",
    }

    _EMOTION_ALIASES = {
        "joy": "happy",
        "excitement": "happy",
        "relief": "happy",
        "sadness": "sad",
        "aggrieved": "sad",
        "longing": "sad",
        "weariness": "sad",
        "anger": "angry",
        "fear": "fearful",
        "worry": "fearful",
        "surprise": "surprised",
        "disgust": "disgusted",
        "trust": "neutral",
        "attachment": "neutral",
        "tenderness": "neutral",
        "coldness": "neutral",
    }

    _EMOTION_MODIFIERS = {
        "happy": (+0.05, +1),
        "sad": (-0.15, -2),
        "angry": (+0.10, +2),
        "fearful": (+0.15, +3),
        "surprised": (+0.08, +1),
        "disgusted": (+0.02, 0),
        "neutral": (0.0, 0),
    }

    _ACTIVE_EMOTION_CUES = {
        "longing": ["(breath)"],
        "aggrieved": ["(sighs)"],
        "weariness": ["(sighs)"],
        "worry": ["(breath)"],
        "fear": ["(breath)"],
        "surprise": ["(gasps)"],
        "joy": ["(chuckle)"],
        "excitement": ["(chuckle)"],
    }

    _STAGE_CUE_RULES = [
        (re.compile(r"笑|轻笑|chuckle|laugh", re.IGNORECASE), "(chuckle)", +0.02, 0),
        (re.compile(r"叹|叹息|无奈|疲惫|累|倦|sigh", re.IGNORECASE), "(sighs)", -0.06, -1),
        (re.compile(r"停顿|片刻|沉默|顿了|迟疑|犹豫|pause", re.IGNORECASE), "(breath)", -0.04, 0),
        (re.compile(r"惊|怔|愣|错愕|gasps|surprise", re.IGNORECASE), "(gasps)", +0.05, +1),
        (re.compile(r"哭|哽咽|泪|cry", re.IGNORECASE), "(crying)", -0.08, -1),
        (
            re.compile(r"低声|压低|轻声|克制|凉意|雨后|冷|淡淡", re.IGNORECASE),
            "(breath)",
            -0.05,
            -1,
        ),
        (re.compile(r"急|快|慌|兴奋|激动", re.IGNORECASE), "(breath)", +0.06, +1),
    ]

    _TAG_PATTERN = re.compile(
        r"\((laughs|chuckle|coughs|clear-throat|groans|breath|pant|inhale|exhale|gasps|sniffs|sighs|snorts|burps|lip-smacking|humming|hissing|emm|whistles|sneezes|crying|applause)\)",
        re.IGNORECASE,
    )

    _CLONE_STABLE_EMOTION_FALLBACK = {
        "angry": "neutral",
        "fearful": "neutral",
        "disgusted": "neutral",
        "surprised": "neutral",
    }

    def _normalize_active_emotions(
        self, active_emotions: Optional[List[Any]]
    ) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for item in active_emotions or []:
            if isinstance(item, str):
                normalized.append({"emotion": item, "intensity": 1.0})
            elif isinstance(item, dict) and item.get("emotion"):
                normalized.append(
                    {
                        "emotion": str(item["emotion"]),
                        "intensity": float(item.get("intensity", 1.0) or 0.0),
                    }
                )
        normalized.sort(key=lambda entry: entry["intensity"], reverse=True)
        return normalized[:3]

    def _emotion_from_active_stack(self, active_stack: list[dict[str, Any]]) -> str | None:
        for item in active_stack:
            if item["intensity"] < 0.2:
                continue
            mapped = self._EMOTION_ALIASES.get(item["emotion"])
            if mapped:
                return mapped
        return None

    def _derive_director_cues(
        self,
        active_stack: list[dict[str, Any]],
        stage_directions: Optional[List[str]],
    ) -> tuple[list[str], float, int]:
        cues: list[str] = []
        speed_delta = 0.0
        pitch_delta = 0

        for item in active_stack:
            if item["intensity"] < 0.2:
                continue
            for cue in self._ACTIVE_EMOTION_CUES.get(item["emotion"], []):
                cues.append(cue)

        stage_text = " ".join(stage_directions or [])
        for pattern, cue, sp_delta, pi_delta in self._STAGE_CUE_RULES:
            if pattern.search(stage_text):
                cues.append(cue)
                speed_delta += sp_delta
                pitch_delta += pi_delta

        deduped: list[str] = []
        for cue in cues:
            if cue not in deduped:
                deduped.append(cue)
        return deduped[:2], max(-0.15, min(0.12, speed_delta)), max(-2, min(2, pitch_delta))

    def _decorate_text(
        self,
        text: str,
        emotion: str,
        intimacy: float,
        cues: list[str],
        emotion_prefix_enabled: bool = True,
    ) -> str:
        cleaned = " ".join(text.split())
        if not cleaned:
            return cleaned

        if self._TAG_PATTERN.search(cleaned):
            return cleaned

        prefix = "".join(cues)
        if not prefix and emotion_prefix_enabled:
            prefix = self._TAG_BY_EMOTION.get(emotion)
        if prefix:
            cleaned = f"{prefix}{cleaned}"
        elif intimacy >= 0.72:
            cleaned = f"(breath){cleaned}"

        if len(cleaned) > 18:
            cleaned = re.sub(r"([。！？!?])(?=[^。！？!?])", r"\1(breath)", cleaned, count=1)
            cleaned = re.sub(r"([，、；：,;:])(?=[^，、；：,;:])", r"\1 ", cleaned)

        return cleaned

    def _stabilize_for_profile(
        self,
        profile: VoiceProfile,
        emotion: str,
        speed: float,
        pitch: int,
        cues: list[str],
    ) -> tuple[str, float, int, list[str]]:
        if emotion not in profile.allowed_emotions:
            emotion = self._CLONE_STABLE_EMOTION_FALLBACK.get(emotion, "neutral")
        if emotion not in profile.allowed_emotions:
            emotion = "neutral"

        low_speed, high_speed = profile.speed_range
        low_pitch, high_pitch = profile.pitch_range
        speed = max(low_speed, min(high_speed, speed))
        pitch = max(low_pitch, min(high_pitch, pitch))

        if profile.clone_stability:
            # Cloned voices keep identity better when strong emotions are carried
            # by light pause/breath cues instead of large model-level shifts.
            cues = [cue for cue in cues if cue in {"(breath)", "(sighs)", "(chuckle)"}]
        return emotion, speed, pitch, cues[: max(0, profile.max_cues)]

    def derive(
        self,
        text: str,
        character_id: str,
        vad: Optional[Dict[str, float]] = None,
        intimacy: float = 0.0,
        active_emotions: Optional[List[Any]] = None,
        stage_directions: Optional[List[str]] = None,
    ) -> TTSRequest:
        """Derive TTSRequest from emotion/relationship state.

        Args:
            text: Text to synthesize.
            character_id: Character ID (e.g., 'rin', 'dorothy').
            vad: VAD dict with valence, arousal, dominance (-1..1).
            intimacy: Intimacy level (0..1).
            active_emotions: List of active emotion names or emotion stack entries.
            stage_directions: Parenthetical stage directions stripped from visible speech.
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

        active_stack = self._normalize_active_emotions(active_emotions)
        active_emotion = self._emotion_from_active_stack(active_stack)
        if active_emotion:
            emotion = active_emotion
            speed_delta, pitch_delta = self._EMOTION_MODIFIERS.get(
                active_emotion, (speed_delta, pitch_delta)
            )

        director_cues, director_speed_delta, director_pitch_delta = self._derive_director_cues(
            active_stack, stage_directions
        )

        # Intimacy adjustments: higher intimacy → slower, lower pitch
        intimacy_speed_mod = -0.05 * max(0.0, min(1.0, intimacy))
        intimacy_pitch_mod = -1 if intimacy > 0.6 else 0

        profile = get_voice_profile(character_id)
        raw_speed = 1.0 + speed_delta + intimacy_speed_mod + director_speed_delta
        raw_pitch = pitch_delta + intimacy_pitch_mod + director_pitch_delta
        emotion, speed, pitch, director_cues = self._stabilize_for_profile(
            profile=profile,
            emotion=emotion,
            speed=raw_speed,
            pitch=raw_pitch,
            cues=director_cues,
        )

        return TTSRequest(
            text=self._decorate_text(
                text,
                emotion,
                intimacy,
                director_cues,
                emotion_prefix_enabled=not profile.clone_stability,
            ),
            voice_id=profile.voice_id,
            emotion=emotion,
            speed=speed,
            pitch=pitch,
            volume=1.0,
        )
