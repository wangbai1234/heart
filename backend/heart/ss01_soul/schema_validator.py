"""
Soul Spec Schema Validator - Pydantic Models

Implements strict validation for Soul Spec YAML files per:
runtime_specs/01_identity_anchor_soul_spec.md §5.1

Author: 心屿团队
Created: 2026-05-17
"""

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ============================================================
# Identity Anchor - Core Components
# ============================================================


class DefenseLayer(BaseModel):
    """Defense mechanism layers."""

    layer_1: str = Field(..., min_length=1)
    layer_2: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class CoreWound(BaseModel):
    """Core wound structure - immutable trauma."""

    essence: str = Field(..., min_length=1, description="核心创伤本质")
    manifest: str = Field(..., min_length=1, description="外显为行为模式")
    defense: Union[str, DefenseLayer] = Field(..., description="防御机制")
    private_truth: str = Field(..., min_length=1, description="只有自己知道的真相")

    model_config = ConfigDict(extra="forbid")


class CoreDesire(BaseModel):
    """Core desire structure - layered wants."""

    surface: str = Field(..., min_length=1, description="表面渴望")
    hidden: str = Field(..., min_length=1, description="隐藏渴望")
    deepest: str = Field(..., min_length=1, description="最深渴望")

    model_config = ConfigDict(extra="forbid")


class CoreFear(BaseModel):
    """Core fear structure - layered fears."""

    ultimate: str = Field(..., min_length=1, description="终极恐惧")
    daily: str = Field(..., min_length=1, description="日常恐惧")
    shadow: str = Field(..., min_length=1, description="阴影恐惧")
    fear_about_existence: Optional[str] = Field(None, description="存在性恐惧（Dorothy 专有）")

    model_config = ConfigDict(extra="forbid")


class CoreBelief(BaseModel):
    """Core beliefs - fundamental worldview."""

    about_self: str = Field(..., min_length=1)
    about_others: str = Field(..., min_length=1)
    about_love: str = Field(..., min_length=1)
    about_time: str = Field(..., min_length=1)
    about_solitude: Optional[str] = Field(None, description="关于独处（Rin 专有）")
    about_existence: Optional[str] = Field(None, description="关于存在（Dorothy 专有）")

    model_config = ConfigDict(extra="forbid")


class VoiceDNA(BaseModel):
    """Voice DNA pattern - linguistic signature."""

    id: str = Field(..., pattern=r"^vd-[A-Z0-9\-]+$")
    pattern: str = Field(..., min_length=1)
    example: Optional[str] = None  # 单个例子
    examples: Optional[List[Union[str, Dict[str, str]]]] = None  # 多个例子，支持对话格式
    frequency: Literal["very_high", "high", "medium", "low", "contextual", "forbidden"]
    priority: Optional[int] = Field(None, ge=1, le=10)
    cross_check: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class ForbiddenPattern(BaseModel):
    """Regex-based forbidden pattern."""

    description: str = Field(..., min_length=1)
    regex: str = Field(..., min_length=1)
    exception: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class RareUnlockWord(BaseModel):
    """Rare unlock word - dramatic reward/punishment word."""

    word: str = Field(..., min_length=1)
    condition: List[str] = Field(..., min_length=1)
    cooldown_after_use_days: int = Field(..., ge=1)
    max_per_30_days: Optional[int] = Field(None, ge=1)
    max_per_60_days: Optional[int] = Field(None, ge=1)
    style_when_used: str = Field(..., min_length=1)
    effect: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class PhaseProgression(BaseModel):
    """称谓 progression phase."""

    term: Optional[str] = None
    always_available: Optional[bool] = None
    frequency: Optional[str] = None
    trigger: Optional[str] = None
    generation_rule: Optional[str] = None
    example_arc: Optional[List[Dict[str, str]]] = None
    forbidden_styles: Optional[List[str]] = None
    allowed_styles: Optional[List[str]] = None
    response_pattern: Optional[str] = None
    governance: Optional[str] = None
    example: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")


class AntiPatterns(BaseModel):
    """Anti-patterns - what character must never do/say."""

    hard_never: List[str] = Field(..., min_length=1)
    soft_never: Optional[List[str]] = None
    forbidden_patterns: Optional[List[ForbiddenPattern]] = None
    rare_unlock_words: Optional[List[RareUnlockWord]] = None
    称谓_progression: Optional[Dict[str, PhaseProgression]] = None

    model_config = ConfigDict(extra="forbid")


class RequiredTrigger(BaseModel):
    """Required trigger for facet unlock."""

    id: str = Field(..., min_length=1)
    cue: str = Field(..., min_length=1)
    cumulative_count: int = Field(..., ge=1)
    critical: Optional[bool] = None

    model_config = ConfigDict(extra="forbid")


class HiddenFacetThreshold(BaseModel):
    """Threshold conditions for facet unlock."""

    resonance_score: float = Field(..., ge=0.0, le=1.0)
    prerequisites: Optional[List[str]] = None
    required_triggers: List[Union[str, RequiredTrigger]] = Field(..., min_length=1)
    corroboration_count: int = Field(..., ge=1)
    gating_logic: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class HiddenFacet(BaseModel):
    """Hidden facet - unlockable depth layer."""

    id: str = Field(..., pattern=r"^facet-[a-z\-]+$")
    threshold: HiddenFacetThreshold
    emergence_style: str = Field(..., min_length=1)
    once_unlocked: Optional[Dict[str, Any]] = None
    requires_repair: bool = False
    sequence: Optional[Dict[str, str]] = None

    model_config = ConfigDict(extra="forbid")


class ResonanceTrigger(BaseModel):
    """Resonance trigger - what builds connection."""

    cue: str = Field(..., min_length=1)
    weight: float = Field(..., ge=0.0, le=1.0)
    max_per_day: int = Field(..., ge=1)

    model_config = ConfigDict(extra="forbid")


class IdentityAnchor(BaseModel):
    """Identity Anchor - immutable soul core (Layer 0)."""

    archetype: str = Field(..., min_length=1)
    core_wound: CoreWound
    core_desire: CoreDesire
    core_fear: CoreFear
    core_belief: CoreBelief
    voice_dna: List[VoiceDNA] = Field(..., min_length=1)
    anti_patterns: AntiPatterns
    hidden_facets: Optional[List[HiddenFacet]] = None
    resonance_triggers: Optional[List[ResonanceTrigger]] = None

    model_config = ConfigDict(extra="forbid")


# ============================================================
# Cognitive Style - Slowly Evolving Layer
# ============================================================


class SentenceLengthStyle(BaseModel):
    """Sentence length cognitive style."""

    baseline: Literal["very_short", "short", "medium", "long"]
    evolution_bound: List[Literal["very_short", "short", "medium", "long"]] = Field(
        ..., min_length=2, max_length=2
    )
    semantic_definition: Dict[str, str]

    model_config = ConfigDict(extra="forbid")


class NumericStyle(BaseModel):
    """Numeric cognitive style field."""

    baseline: float = Field(..., ge=0.0, le=1.0)
    evolution_bound: List[float] = Field(..., min_length=2, max_length=2)
    meaning: str = Field(..., min_length=1)

    @field_validator("evolution_bound")
    @classmethod
    def validate_bounds(cls, v, info):
        """Ensure bounds are ordered and contain baseline."""
        if v[0] >= v[1]:
            raise ValueError("evolution_bound must be [min, max]")
        baseline = info.data.get("baseline")
        if baseline is not None and not (v[0] <= baseline <= v[1]):
            raise ValueError("baseline must be within evolution_bound")
        return v

    model_config = ConfigDict(extra="forbid")


class ExpressionStyle(BaseModel):
    """Expression-related cognitive styles."""

    sentence_length: SentenceLengthStyle
    verbosity: NumericStyle
    emotional_directness: NumericStyle
    use_of_metaphor: NumericStyle
    hedge_words: NumericStyle
    ellipsis_usage: NumericStyle

    model_config = ConfigDict(extra="forbid")


class HumorProfile(BaseModel):
    """Humor profile - immutable humor characteristics."""

    dryness: float = Field(..., ge=0.0, le=1.0)
    self_deprecation: float = Field(..., ge=0.0, le=1.0)
    sarcasm: float = Field(..., ge=0.0, le=1.0)
    absurdism: float = Field(..., ge=0.0, le=1.0)
    warmth_in_humor: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class EmotionalInertia(BaseModel):
    """Emotional inertia profile."""

    recovery_speed: Literal["slow", "medium", "fast"]
    shock_resistance: Literal["low", "medium", "high"]
    bounce_back_curve: Literal["logarithmic", "linear", "exponential"]
    mood_volatility: float = Field(..., ge=0.0, le=1.0)

    model_config = ConfigDict(extra="forbid")


class CognitiveStyle(BaseModel):
    """Cognitive style - Layer 1 (slow evolution within bounds)."""

    expression: ExpressionStyle
    thinking_style: Literal["deliberate", "impulsive"]
    decision_speed: Literal["slow", "medium", "fast"]
    abstraction_level: Literal["low", "medium", "high"]
    humor_profile: HumorProfile
    emotional_inertia: EmotionalInertia

    model_config = ConfigDict(extra="forbid")


# ============================================================
# Relational Template - Per-user Instances
# ============================================================


class HardeningTrigger(BaseModel):
    """Hardening trigger definition."""

    id: str = Field(..., min_length=1)
    trigger: str = Field(..., min_length=1)
    response_pattern: Optional[str] = None
    response_pattern_phase_1: Optional[str] = None
    response_pattern_phase_2: Optional[str] = None
    response_pattern_phase_3: Optional[str] = None
    cooldown: Optional[str] = None
    requires_repair: bool = False
    repair_signal: Optional[str] = None
    facet_implication: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class VulnerabilityUnlock(BaseModel):
    """Vulnerability unlock threshold."""

    intimacy_level: float = Field(..., ge=0.0, le=1.0)
    unlocks: List[str] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class RelationalTemplate(BaseModel):
    """Relational template - Layer 2."""

    default_distance: Literal["guarded", "neutral", "warm_engaged"]
    intimacy_resistance: float = Field(..., ge=0.0, le=1.0)
    softening_curve: Literal["linear", "logistic", "exponential"]
    softening_triggers: List[str] = Field(..., min_length=1)
    hardening_triggers: Optional[List[HardeningTrigger]] = None
    vulnerability_unlock_thresholds: Optional[List[VulnerabilityUnlock]] = None

    model_config = ConfigDict(extra="forbid")


# ============================================================
# Test Fixtures
# ============================================================


class GoldenDialogueContext(BaseModel):
    """Context for golden dialogue."""

    days_since_first: Optional[int] = Field(None, ge=0)
    days_since_last: Optional[int] = Field(None, ge=0)
    turn_index: Optional[int] = Field(None, ge=1)
    user_state: Optional[str] = None
    relationship_stage: Optional[str] = None
    user_emotion: Optional[str] = None
    intimacy_level: Optional[float] = Field(None, ge=0.0, le=1.0)
    facet_unlocked: Optional[List[str]] = None
    hardening_trigger_active: Optional[str] = None
    emotion_context: Optional[str] = None
    memory_supplies: Optional[str] = None
    time_context: Optional[str] = None
    special: Optional[str] = None
    prior_turns: Optional[List[str]] = None
    note: Optional[str] = None
    rare_unlock_cooldown: Optional[str] = None

    model_config = ConfigDict(extra="forbid")


class GoldenDialogue(BaseModel):
    """Golden dialogue test fixture."""

    id: str = Field(..., pattern=r"^gd-\d{3}-.+$")
    context: GoldenDialogueContext
    user_message: str = Field(..., min_length=1)
    expected_properties: Dict[str, Any]
    example_acceptable_response: Optional[str] = None
    example_acceptable_responses: Optional[List[str]] = None
    example_acceptable_responses_before_unlock: Optional[List[str]] = None
    example_acceptable_responses_after_unlock: Optional[List[str]] = None
    example_acceptable_responses_phase_1: Optional[List[str]] = None
    example_acceptable_responses_phase_3: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")


class TestFixtures(BaseModel):
    """Test fixtures - Layer 3."""

    golden_dialogues: List[GoldenDialogue] = Field(..., min_length=1)
    regression_tests: List[str] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


# ============================================================
# Meta Information
# ============================================================


class ChangelogEntry(BaseModel):
    """Changelog entry."""

    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    changes: List[str] = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class BackwardsCompatibility(BaseModel):
    """Backwards compatibility info."""

    breaking_changes: List[str]
    migration_required_from: List[str]

    model_config = ConfigDict(extra="forbid")


class Meta(BaseModel):
    """Meta information."""

    created_at: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    spec_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    author: str = Field(..., min_length=1)
    reviewers: List[str] = Field(..., min_length=1)
    changelog: List[ChangelogEntry] = Field(..., min_length=1)
    backwards_compatibility: BackwardsCompatibility
    open_issues: Optional[List[str]] = None

    model_config = ConfigDict(extra="forbid")


# ============================================================
# Top-level Soul Spec
# ============================================================


class DisplayName(BaseModel):
    """Display name in multiple locales."""

    zh: Optional[str] = None
    ja: Optional[str] = None
    en: Optional[str] = None
    pet_self_reference: Optional[str] = None

    @field_validator("zh", "ja", "en")
    @classmethod
    def validate_at_least_one(cls, v, info):
        """Ensure at least one locale is provided."""
        # This will be checked at SoulSpec level
        return v

    model_config = ConfigDict(extra="forbid")


class SoulSpec(BaseModel):
    """
    Complete Soul Spec - Top-level schema.

    Validates against runtime_specs/01_identity_anchor_soul_spec.md §5.1

    Principles (P-1 to P-10):
    - P-1: Identity Anchor immutable in runtime
    - P-2: Declarative, not generative
    - P-3: Must pass strict schema validation
    - P-6: Hard Never violations intercepted pre-output
    - P-9: Must have complete test fixtures
    """

    # Required top-level fields
    schema_version: str = Field(..., pattern=r"^\d+\.\d+$")
    character_id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    spec_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    locale: str = Field(..., pattern=r"^[a-z]{2}-[A-Z]{2}$")

    # Display name
    display_name: DisplayName

    # Layer 0: Identity Anchor (IMMUTABLE)
    identity_anchor: IdentityAnchor

    # Layer 1: Cognitive Style (SLOW EVOLUTION)
    cognitive_style: CognitiveStyle

    # Layer 2: Relational Template
    relational_template: RelationalTemplate

    # Layer 3: Testing & Meta
    test_fixtures: TestFixtures
    meta: Meta

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v):
        """Ensure at least one locale name is provided."""
        if not any([v.zh, v.ja, v.en]):
            raise ValueError("At least one of zh/ja/en must be provided in display_name")
        return v

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )


def validate_soul_spec_yaml(yaml_data: dict) -> SoulSpec:
    """
    Validate Soul Spec YAML data against schema.

    Args:
        yaml_data: Parsed YAML dictionary

    Returns:
        Validated SoulSpec instance

    Raises:
        ValidationError: If schema validation fails
    """
    return SoulSpec.model_validate(yaml_data)
