"""User-facing character creation draft model (C5a).

End-users cannot author a full SoulSpec (voice_dna regex ids, golden_dialogues,
meta.changelog, etc. are too complex).  Instead they fill a simplified
CharacterDraft; the server calls build_soul_spec_from_draft() to deterministically
expand it into a fully-valid SoulSpec.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Optional

from pydantic import BaseModel, Field, model_validator


class GreetingStyle(str, Enum):
    warm = "warm"
    cool = "cool"
    playful = "playful"
    reserved = "reserved"
    intense = "intense"


class DisplayNameDraft(BaseModel, extra="forbid"):
    zh: Optional[str] = Field(None, min_length=1, max_length=20)
    ja: Optional[str] = Field(None, min_length=1, max_length=20)
    en: Optional[str] = Field(None, min_length=1, max_length=40)

    @model_validator(mode="after")
    def at_least_one(self) -> "DisplayNameDraft":
        if not any([self.zh, self.ja, self.en]):
            raise ValueError("At least one of zh / ja / en is required")
        return self


class SliderSet(BaseModel, extra="forbid"):
    """Personality sliders; each value in [0.0, 1.0]."""

    warmth: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    talkativeness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    directness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    humor: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    playfulness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5
    steadiness: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5


class CharacterDraft(BaseModel, extra="forbid"):
    """Simplified character creation form — expanded into a full SoulSpec server-side.

    Fields:
        display_name:     At least one locale name.
        avatar_url:       Optional user-supplied avatar URL.
        persona:          Free-text description of who this character is (20–1500 chars).
        greeting_style:   One of 5 preset emotional register archetypes.
        speech_samples:   Up to 5 example lines that capture the character's voice.
        sliders:          Six float knobs (0-1) mapping onto SoulSpec numeric fields.
        locale:           Primary language for generated content (zh/ja/en).
    """

    display_name: DisplayNameDraft
    avatar_url: Optional[str] = Field(None, max_length=200000)
    persona: Annotated[str, Field(min_length=20, max_length=1500)]
    greeting_style: GreetingStyle = GreetingStyle.warm
    speech_samples: Annotated[list[str], Field(min_length=0, max_length=5)] = Field(
        default_factory=list
    )
    sliders: SliderSet = Field(default_factory=SliderSet)
    locale: str = "zh"
