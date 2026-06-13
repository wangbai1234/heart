"""Voice catalog — character → voice_id mapping."""

from typing import Dict

# Character → variant → voice_id mapping
# Using new-generation "Chinese (Mandarin)_xxx" voices for natural-sounding TTS
VOICE_CATALOG: Dict[str, Dict[str, str]] = {
    "rin": {
        "default": "Chinese (Mandarin)_Gentle_Senior",  # 温柔学姐，新一代真人感
    },
    "dorothy": {
        "default": "Chinese (Mandarin)_Crisp_Girl",  # 清脆少女，新一代真人感
    },
}


def get_voice_id(character_id: str, variant: str = "default") -> str:
    """Get voice_id for a character and variant.

    Raises:
        KeyError: If character_id/variant combination is not found.
    """
    if character_id not in VOICE_CATALOG:
        raise KeyError(f"Unknown voice: {character_id}/{variant}")
    if variant not in VOICE_CATALOG[character_id]:
        raise KeyError(f"Unknown voice: {character_id}/{variant}")
    return VOICE_CATALOG[character_id][variant]


def register_voice(character_id: str, variant: str, voice_id: str) -> None:
    """Dynamically register a voice (for cloned voices)."""
    if character_id not in VOICE_CATALOG:
        VOICE_CATALOG[character_id] = {}
    VOICE_CATALOG[character_id][variant] = voice_id
