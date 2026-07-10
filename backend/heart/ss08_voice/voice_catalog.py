"""Voice catalog — character → voice profile mapping."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict

from heart.core.config import settings


class VoiceNotConfigured(Exception):
    """Raised when a character has no voice configured (not in catalog or DB)."""

    def __init__(self, character_id: str) -> None:
        self.character_id = character_id
        super().__init__(f"No voice configured for character: {character_id}")


@dataclass(frozen=True)
class VoiceProfile:
    """Runtime voice profile for one character."""

    character_id: str
    voice_id: str
    fallback_voice_id: str
    clone_stability: bool = False
    allowed_emotions: tuple[str, ...] = (
        "happy",
        "sad",
        "angry",
        "fearful",
        "disgusted",
        "surprised",
        "neutral",
    )
    speed_range: tuple[float, float] = (0.7, 1.3)
    pitch_range: tuple[int, int] = (-6, 6)
    max_cues: int = 2


# Backward-compatible Character → variant → voice_id mapping.
VOICE_CATALOG: Dict[str, Dict[str, str]] = {
    "rin": {"default": "female-shaonv"},  # MiniMax built-in voice ID
    "dorothy": {"default": "female-yujie"},
}

_CLONE_STABLE_EMOTIONS = ("neutral",)


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _coerce_float_range(value: Any, default: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default
    try:
        low = float(value[0])
        high = float(value[1])
    except (TypeError, ValueError):
        return default
    return (min(low, high), max(low, high))


def _coerce_int_range(value: Any, default: tuple[int, int]) -> tuple[int, int]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        return default
    try:
        low = int(value[0])
        high = int(value[1])
    except (TypeError, ValueError):
        return default
    return (min(low, high), max(low, high))


def _load_configured_profiles() -> dict[str, dict[str, Any]]:
    raw = getattr(settings, "voice_profiles", None)
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _legacy_voice_id(character_id: str) -> str | None:
    if character_id == "rin" and settings.minimax_rin_clone_voice_id:
        return settings.minimax_rin_clone_voice_id
    if character_id == "dorothy" and settings.minimax_dorothy_voice_id:
        return settings.minimax_dorothy_voice_id
    return None


def _resolve_default_voice(character_id: str) -> str:
    return get_voice_profile(character_id).voice_id


def get_voice_profile(character_id: str) -> VoiceProfile:
    """Get the effective voice profile for a character.

    ``VOICE_PROFILES`` accepts JSON shaped like:
    {"rin":{"voice_id":"RinClone_20260705","clone_stability":true}}
    """
    configured = _load_configured_profiles()
    profile_data = configured.get(character_id, {})
    if not isinstance(profile_data, dict):
        profile_data = {}

    if character_id not in VOICE_CATALOG and not isinstance(profile_data, dict):
        raise VoiceNotConfigured(character_id)
    if character_id not in VOICE_CATALOG and not profile_data:
        raise VoiceNotConfigured(character_id)

    fallback = VOICE_CATALOG.get(character_id, {}).get("default", "")
    voice_id = str(profile_data.get("voice_id") or _legacy_voice_id(character_id) or fallback)
    if not voice_id:
        raise VoiceNotConfigured(character_id)

    clone_stability = _coerce_bool(
        profile_data.get("clone_stability"),
        default=bool(profile_data.get("voice_id") or _legacy_voice_id(character_id)),
    )
    allowed_emotions = profile_data.get("allowed_emotions")
    if isinstance(allowed_emotions, list) and all(
        isinstance(item, str) for item in allowed_emotions
    ):
        allowed = tuple(allowed_emotions)
    elif clone_stability:
        allowed = _CLONE_STABLE_EMOTIONS
    else:
        allowed = VoiceProfile(character_id, voice_id, fallback).allowed_emotions

    return VoiceProfile(
        character_id=character_id,
        voice_id=voice_id,
        fallback_voice_id=fallback or voice_id,
        clone_stability=clone_stability,
        allowed_emotions=allowed,
        speed_range=_coerce_float_range(
            profile_data.get("speed_range"),
            (0.98, 1.02) if clone_stability else (0.7, 1.3),
        ),
        pitch_range=_coerce_int_range(
            profile_data.get("pitch_range"),
            (-1, 0) if clone_stability else (-6, 6),
        ),
        max_cues=int(profile_data.get("max_cues", 1 if clone_stability else 2)),
    )


def get_voice_id(character_id: str, variant: str = "default") -> str:
    """Get voice_id for a character and variant.

    Raises:
        KeyError: If character_id/variant combination is not found.
    """
    if character_id not in VOICE_CATALOG and character_id not in _load_configured_profiles():
        raise VoiceNotConfigured(character_id)
    if variant == "default":
        return _resolve_default_voice(character_id)
    if variant not in VOICE_CATALOG[character_id]:
        raise VoiceNotConfigured(character_id)
    return VOICE_CATALOG[character_id][variant]


def register_voice(character_id: str, variant: str, voice_id: str) -> None:
    """Dynamically register a voice (for cloned voices)."""
    if character_id not in VOICE_CATALOG:
        VOICE_CATALOG[character_id] = {}
    VOICE_CATALOG[character_id][variant] = voice_id
