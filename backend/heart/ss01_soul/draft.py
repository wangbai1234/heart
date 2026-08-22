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

# Import new UGC creation models (batch 1)
from heart.ss01_soul.draft_new_models import (
    ChromeDraft,
    PremiseCardDraft,
    ProfileBlock,
    StarterConfig,
)


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


class SoulProfileDraft(BaseModel, extra="forbid"):
    """Character-specific inner life produced or authored during creation.

    The deterministic builder still owns SoulSpec shape and safety baselines;
    this model supplies the character-specific content that used to come from
    one of five generic greeting-style templates.
    """

    wound_essence: Annotated[str, Field(min_length=4, max_length=160)]
    wound_manifest: Annotated[str, Field(min_length=4, max_length=200)]
    wound_defense: Annotated[str, Field(min_length=4, max_length=160)]
    private_truth: Annotated[str, Field(min_length=4, max_length=160)]
    desire_surface: Annotated[str, Field(min_length=2, max_length=120)]
    desire_hidden: Annotated[str, Field(min_length=4, max_length=160)]
    desire_deepest: Annotated[str, Field(min_length=4, max_length=160)]
    fear_ultimate: Annotated[str, Field(min_length=4, max_length=160)]
    fear_daily: Annotated[str, Field(min_length=4, max_length=160)]
    fear_shadow: Annotated[str, Field(min_length=4, max_length=160)]
    belief_self: Annotated[str, Field(min_length=4, max_length=160)]
    belief_others: Annotated[str, Field(min_length=4, max_length=160)]
    belief_love: Annotated[str, Field(min_length=4, max_length=160)]
    belief_time: Annotated[str, Field(min_length=4, max_length=160)]
    softening_triggers: list[Annotated[str, Field(min_length=2, max_length=80)]] = Field(
        min_length=2, max_length=5
    )


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
    # A distinct story hook for the profile's 叙引 card. It must not merely
    # repeat tagline/intro; quick-prefill enforces that quality boundary.
    one_liner: Optional[Annotated[str, Field(max_length=120)]] = None
    # Short public identity label, e.g. "急诊科医生" or "流亡星舰领航员".
    archetype_label: Optional[Annotated[str, Field(max_length=40)]] = None
    # Character-specific psychological core. Older/manual drafts may omit it
    # and continue to use the greeting-style compatibility template.
    soul_profile: Optional[SoulProfileDraft] = None
    sliders: SliderSet = Field(default_factory=SliderSet)
    locale: str = "zh"
    # Intended visibility once the character is published.
    # public/unlisted → enters review pipeline; private → immediately live,
    # no review, no reward.
    visibility: Literal["public", "unlisted", "private"] = "private"

    # ── Batch 1: UGC Creation Redesign Fields ──
    # 创建模式: quick (快速创建) vs workshop (角色创作)
    creation_mode: Literal["quick", "workshop"] = "quick"
    # 主题配色 (14 槽位)
    ui_chrome: Optional[ChromeDraft] = None
    # 详情页区块 (最多 12 个)
    profile_blocks: list[ProfileBlock] = Field(default_factory=list, max_length=12)
    # 高级 HTML (50KB 上限)
    custom_html: Optional[Annotated[str, Field(max_length=51200)]] = None
    # 开场档案卡
    premise_card: Optional[PremiseCardDraft] = None
    # 聊天开场选项配置
    starter_config: Optional[StarterConfig] = None
    # 开场白格式: plain (纯文本) vs rich (带 <scene>/<plot>/<dialogue> 标签)
    opening_format: Literal["plain", "rich"] = "plain"

    @model_validator(mode="after")
    def quick_mode_limits(self) -> "CharacterDraft":
        """快速创建模式限制: 不得公开，不得使用角色创作专属字段。"""
        if self.creation_mode == "quick":
            if self.visibility == "public":
                raise ValueError("quick mode cannot be public")
            workshop_fields = [
                self.custom_html,
                self.profile_blocks,
                self.premise_card,
                self.starter_config,
            ]
            if any(workshop_fields):
                raise ValueError("quick mode cannot set workshop-only fields")
        return self
