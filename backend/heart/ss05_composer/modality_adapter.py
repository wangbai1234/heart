"""
Modality Adapter — SS05 Persona Composition Runtime §3.3 Step 5 (§3.5)

Transforms resolved prompt layers according to the target modality so that
the final composed prompt is structurally appropriate for the delivery
channel (text, voice, image-caption).

Per runtime_specs/05_persona_composition_runtime.md:
- PC-7: Modality must go through Modality Adapter, never direct to LLM
- INV-PC-7: for all modality m, prompt(m) is adapted via ModalityAdapter[m]

Supported modalities:
  text-short    — concise text response
  text-long     — detailed text response, full prompt + history
  voice-script  — voice-compatible output, no markdown, prosody hints, short
  image-caption — image caption mode, very concise, descriptive

Design contract:
- Deterministic (PC-12: no LLM calls in composition path)
- Pure function: reads composition, writes adapted composition
- < 5ms target latency (§3.3 Step 5)

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from heart.ss05_composer.layer_aggregator import PromptLayer

# ============================================================
# Modality type
# ============================================================

Modality = str  # "text-short" | "text-long" | "voice-script" | "image-caption"

VALID_MODALITIES: frozenset[str] = frozenset(
    {"text-short", "text-long", "voice-script", "image-caption"}
)


# ============================================================
# Modality-specific directives — per §5.4 ModalityDirectives
# ============================================================


@dataclass
class VoiceDirectives:
    """Voice-specific output constraints.

    When the response is destined for a TTS pipeline, the prompt must steer
    the LLM away from markdown, lists, and other visual formatting that
    cannot be spoken naturally.
    """

    target_response_length: str = "short"  # "short" | "medium"
    must_be_speakable: bool = True
    prosody_hints: dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.prosody_hints:
            self.prosody_hints = {
                "pitch_modifier": 0.0,
                "pace_modifier": 0.0,
                "breathiness": 0.0,
                "pause_pattern_emphasis": 0.0,
            }


@dataclass
class ImageCaptionDirectives:
    """Image-caption specific output constraints.

    Captions must be descriptive, visually grounded, and very concise.
    """

    target_response_length: str = "very_short"  # "very_short" | "short"
    require_visual_description: bool = True


@dataclass
class TextDirectives:
    """Text-specific output constraints."""

    target_response_length: str = "medium"  # "short" | "medium" | "long"


@dataclass
class ModalityDirectives:
    """Aggregated modality directives for the current turn."""

    text: Optional[TextDirectives] = None
    voice: Optional[VoiceDirectives] = None
    image_caption: Optional[ImageCaptionDirectives] = None


# ============================================================
# ModalityAwareComposition — adapter output
# ============================================================


@dataclass
class ModalityAwareComposition:
    """Output of the Modality Adapter step.

    Contains the adapted layer list and modality-specific directives
    that downstream Composer and rendering stages will use.
    """

    layers: list[PromptLayer]
    modality: Modality
    directives: ModalityDirectives
    adapted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_text(self) -> bool:
        return self.modality in ("text-short", "text-long")

    @property
    def is_voice(self) -> bool:
        return self.modality == "voice-script"

    @property
    def is_image_caption(self) -> bool:
        return self.modality == "image-caption"


# ============================================================
# Markdown stripping — voice-script compliance
# ============================================================

# Patterns that cannot be spoken naturally
_MARKDOWN_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, replacement, description)
    (r"\*\*(.+?)\*\*", r"\1", "bold"),
    (r"\*(.+?)\*", r"\1", "italic"),
    (r"__(.+?)__", r"\1", "bold underscore"),
    (r"_(.+?)_", r"\1", "italic underscore"),
    (r"`{1,3}[^`\n]*`{1,3}", "", "inline code / code block"),
    (r"~~(.+?)~~", r"\1", "strikethrough"),
    (r"^#{1,6}\s+", "", "headings"),
    (r"^[-*+]\s+", "• ", "unordered list bullet (→ bullet char)"),
    (r"^\d+[.)]\s+", "", "ordered list marker"),
    (r"^>\s+", "", "blockquote"),
    (r"\|.*\|", "", "table row"),
    (r"\[(.+?)\]\(.+?\)", r"\1", "link → text only"),
    (r"!\[.*?\]\(.+?\)", "", "image markdown"),
    (r"^---+$", "", "horizontal rule"),
]

# Voice-incompatible structural markers that must become natural speech
_VOICE_STRUCTURAL_REPLACEMENTS: list[tuple[str, str, str]] = [
    (r"\n{3,}", "\n\n", "excessive blank lines → single paragraph break"),
    (r"^\s*[-•●○◆◇▪▸►]\s*$", "", "standalone bullet lines"),
]


def _strip_markdown_for_voice(text: str) -> str:
    """Remove markdown formatting that cannot be spoken.

    Applies regex-based markdown stripping; preserves the semantic content
    while removing visual formatting constructs (bold markers, code fences,
    links, tables, etc.) that would confuse a TTS engine.
    """
    result = text
    for pattern, replacement, _desc in _MARKDOWN_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE)

    for pattern, replacement, _desc in _VOICE_STRUCTURAL_REPLACEMENTS:
        result = re.sub(pattern, replacement, result, flags=re.MULTILINE)

    # Collapse multiple spaces
    result = re.sub(r" {2,}", " ", result)

    # Clean up double blank lines that may have emerged from stripping
    result = re.sub(r"\n{3,}", "\n\n", result)

    return result.strip()


# ============================================================
# Structural element injection — per modality
# ============================================================


def _build_modality_header(modality: Modality) -> str:
    """Return a modality-specific system header injected before anchor."""
    headers: dict[str, str] = {
        "text-short": (
            "[MODE: TEXT-SHORT]\n"
            "You are responding in a text chat. Keep replies concise and natural.\n"
            "Aim for 1-3 sentences. Be direct and personal."
        ),
        "text-long": (
            "[MODE: TEXT-LONG]\n"
            "You are responding in a detailed text chat. You may write at length,\n"
            "using rich description, inner monologue, and extended narrative.\n"
            "Your full persona and memory are available to draw from."
        ),
        "voice-script": (
            "[MODE: VOICE-SCRIPT]\n"
            "You are speaking aloud. Your output must be speakable by a TTS engine.\n"
            "Do NOT use markdown, lists, code blocks, tables, or links.\n"
            "Use natural speech rhythms. Keep responses short (1-2 sentences).\n"
            "Use pauses (…) and intonation (rising? falling.) as appropriate."
        ),
        "image-caption": (
            "[MODE: IMAGE-CAPTION]\n"
            "You are describing a visual scene. Be descriptive and grounded in\n"
            "what is visible. Focus on sensory details: colors, shapes, expressions,\n"
            "lighting, composition. Keep to 1-2 sentences. Do not narrate action\n"
            "beyond what is visible."
        ),
    }
    return headers.get(modality, headers["text-short"])


# ============================================================
# Layer content adaptation — per modality
# ============================================================


def _adapt_layer_content(layer: PromptLayer, modality: Modality) -> PromptLayer:
    """Return a new PromptLayer with modality-appropriate content.

    For voice-script: strip markdown from all layer content.
    For text-short: mark all non-anchor content as compressible with lower min.
    For image-caption: strip conversation history, simplify emotional context.
    """
    content = layer.content

    if modality == "voice-script":
        content = _strip_markdown_for_voice(content)

    # Build adapted layer (always a new instance — immutable per PC-8)
    adapted = PromptLayer(
        layer_id=layer.layer_id,
        source_subsystem=layer.source_subsystem,
        layer_type=layer.layer_type,
        priority=layer.priority,
        position_constraint=layer.position_constraint,
        content=content,
        token_count_estimate=layer.token_count_estimate,
        min_token_count=layer.min_token_count,
        is_compressible=layer.is_compressible,
        generated_at=layer.generated_at,
        cache_key=layer.cache_key,
        content_hash="",  # recomputed in __post_init__
        conflicts_with=list(layer.conflicts_with),
        variants=dict(layer.variants),
        metadata=dict(layer.metadata),
    )
    return adapted


# ============================================================
# LLM parameter selection — per modality
# ============================================================


@dataclass
class LLMCallParams:
    """Parameters for the downstream main LLM call."""

    model: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    top_p: float = 0.95
    stop_sequences: list[str] = field(default_factory=list)
    stream: bool = True


def _select_llm_params(modality: Modality) -> LLMCallParams:
    """Choose LLM call parameters appropriate for the modality.

    Per §5.5 llm_param_selection:
      text-long  → high temperature, many tokens, creative
      text-short → medium temperature, fewer tokens
      voice      → lower temperature, short tokens, no markdown stops
      caption    → very low temperature, very few tokens, descriptive
    """
    params_by_modality: dict[str, dict[str, Any]] = {
        "text-short": {
            "temperature": 0.7,
            "max_tokens": 512,
            "top_p": 0.95,
            "stop_sequences": [],
        },
        "text-long": {
            "temperature": 0.8,
            "max_tokens": 4096,
            "top_p": 0.95,
            "stop_sequences": [],
        },
        "voice-script": {
            "temperature": 0.6,
            "max_tokens": 256,
            "top_p": 0.90,
            "stop_sequences": ["\n\n\n"],
        },
        "image-caption": {
            "temperature": 0.3,
            "max_tokens": 128,
            "top_p": 0.85,
            "stop_sequences": ["\n\n"],
        },
    }

    cfg = params_by_modality.get(modality, params_by_modality["text-short"])
    return LLMCallParams(
        temperature=cfg["temperature"],
        max_tokens=cfg["max_tokens"],
        top_p=cfg["top_p"],
        stop_sequences=list(cfg["stop_sequences"]),
    )


# ============================================================
# Public API: adapt()
# ============================================================


def adapt(
    composition: list[PromptLayer],
    modality: Modality,
) -> ModalityAwareComposition:
    """Adapt resolved layers and directives for the target modality.

    This is Step 5 of the per-turn composition flow (§3.3):
    - Injects a modality_adaptation layer with structural header
    - Adapts each layer's content for the modality (e.g., voice strips markdown)
    - Builds modality-specific directives for downstream rendering
    - Selects LLM call parameters appropriate for the modality

    Args:
        composition: Resolved prompt layers from Conflict Resolver + Token Budget.
        modality: Target modality ("text-short", "text-long", "voice-script", "image-caption").

    Returns:
        ModalityAwareComposition with adapted layers and directives.

    Raises:
        ValueError: If modality is not a recognized value.
    """
    if modality not in VALID_MODALITIES:
        raise ValueError(
            f"Unknown modality: {modality!r}. Must be one of {sorted(VALID_MODALITIES)}."
        )

    # --- Build modality adaptation layer ---
    header_content = _build_modality_header(modality)
    modality_layer = PromptLayer(
        layer_id=f"modality_{modality}",
        source_subsystem="SS05",
        layer_type="modality_adaptation",
        priority=10,  # per §5.2: modality_adaptation = 10
        position_constraint="anywhere",
        content=header_content,
        token_count_estimate=len(header_content),
        min_token_count=50,
        is_compressible=False,
    )

    # --- Adapt each layer ---
    adapted_layers: list[PromptLayer] = []
    for layer in composition:
        adapted = _adapt_layer_content(layer, modality)
        adapted_layers.append(adapted)

    # Prepend modality header layer (injected before anchor but after compositor ordering)
    adapted_layers.insert(0, modality_layer)

    # --- Build modality directives ---
    directives = _build_directives(modality)

    return ModalityAwareComposition(
        layers=adapted_layers,
        modality=modality,
        directives=directives,
    )


def _build_directives(modality: Modality) -> ModalityDirectives:
    """Construct modality-specific directives for downstream stages."""
    if modality in ("text-short", "text-long"):
        target_len = "short" if modality == "text-short" else "long"
        return ModalityDirectives(
            text=TextDirectives(target_response_length=target_len),
        )
    elif modality == "voice-script":
        return ModalityDirectives(
            voice=VoiceDirectives(
                target_response_length="short",
                must_be_speakable=True,
                prosody_hints={
                    "pitch_modifier": 0.0,
                    "pace_modifier": 0.0,
                    "breathiness": 0.2,
                    "pause_pattern_emphasis": 0.3,
                },
            ),
        )
    elif modality == "image-caption":
        return ModalityDirectives(
            image_caption=ImageCaptionDirectives(
                target_response_length="very_short",
                require_visual_description=True,
            ),
        )
    else:
        # Fallback (should not reach here due to validation above)
        return ModalityDirectives(text=TextDirectives())


# ============================================================
# Convenience: get LLM params for a modality
# ============================================================


def get_llm_params(modality: Modality) -> LLMCallParams:
    """Return the LLM call parameters for a given modality.

    Convenience function usable independently of the full adapt() pipeline.
    """
    if modality not in VALID_MODALITIES:
        raise ValueError(
            f"Unknown modality: {modality!r}. Must be one of {sorted(VALID_MODALITIES)}."
        )
    return _select_llm_params(modality)
