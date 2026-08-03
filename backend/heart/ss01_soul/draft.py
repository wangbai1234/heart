"""User-facing character creation draft model (C5a).

End-users cannot author a full SoulSpec (voice_dna regex ids, golden_dialogues,
meta.changelog, etc. are too complex).  Instead they fill a simplified
CharacterDraft; the server calls build_soul_spec_from_draft() to deterministically
expand it into a fully-valid SoulSpec.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Optional

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
        display_name:       At least one locale name.
        avatar_url:         Optional user-supplied avatar URL.
        persona:            Free-text description of who this character is (20–1500 chars).
        backstory:          Optional background history (0–1500 chars).
        catchphrases:       Up to 5 signature phrases (each ≤50 chars).
        hard_never_user:    Up to 10 extra hard-never rules from the creator.
        greeting_style:     One of 5 preset emotional register archetypes.
        speech_samples:     Up to 5 example lines that capture the character's voice.
        opening:            Authored first-encounter scene, played back verbatim (no LLM).
        intro:              Public profile blurb (display-only, not fed to the model).
        sliders:            Six float knobs (0-1) mapping onto SoulSpec numeric fields.
        locale:             Primary language for generated content (zh/ja/en).
    """

    display_name: DisplayNameDraft
    avatar_url: Optional[str] = Field(None, max_length=200000)
    # Portrait cover for the discovery grid + chat background. This is a *short*
    # S3 proxy URL (/api/profile/cover-file/...), never a base64 data URL — hence
    # a tight cap, unlike avatar_url which still tolerates legacy inline data.
    cover_url: Optional[str] = Field(None, max_length=500)
    # Style/category tags used by the discovery filter chips.
    tags: list[Annotated[str, Field(max_length=20)]] = Field(default_factory=list, max_length=10)
    persona: Annotated[str, Field(min_length=20, max_length=1500)]
    backstory: Optional[str] = Field(None, max_length=1500)
    catchphrases: list[Annotated[str, Field(max_length=50)]] = Field(
        default_factory=list, max_length=5
    )
    hard_never_user: list[Annotated[str, Field(max_length=200)]] = Field(
        default_factory=list, max_length=10
    )
    greeting_style: GreetingStyle = GreetingStyle.warm
    speech_samples: Annotated[list[str], Field(min_length=0, max_length=5)] = Field(
        default_factory=list
    )
    gender: Optional[Literal["male", "female"]] = None
    # Age bracket the creator picks in the UGC form (e.g. "18-24"). Free-text
    # short label — a public presentation field, kept out of the internal persona.
    age_range: Optional[Annotated[str, Field(max_length=16)]] = None
    # Authored first-encounter opening (the "作品" played back verbatim on first
    # chat entry — NEVER a runtime LLM call). Read by ss10_opening.generator via
    # spec._draft.opening. Presentation/playback field: build_soul_spec_from_draft
    # does not consume it.
    opening: Optional[Annotated[str, Field(max_length=2000)]] = None
    # Public display blurb for the character profile page (shown to users, NOT
    # fed to the model). Read by routes_characters._derive_profile_presentation.
    # Falls back to persona when omitted.
    intro: Optional[Annotated[str, Field(max_length=500)]] = None
    # One-line public tagline shown under the name on the profile page (display
    # -only, not fed to the model). Falls back to persona's first line when
    # omitted. Read by routes_characters._derive_profile_presentation.
    tagline: Optional[Annotated[str, Field(max_length=60)]] = None
    sliders: SliderSet = Field(default_factory=SliderSet)
    locale: str = "zh"
    # Intended visibility once the character is published.
    # public/unlisted → enters review pipeline; private → immediately live,
    # no review, no reward.
    visibility: Literal["public", "unlisted", "private"] = "private"
