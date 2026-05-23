"""
Composer — SS05 Persona Composition Runtime §3.3 Step 6 (§3.6)

Assembles the final prompt for the main LLM from adapted, resolved layers.
This is the terminal deterministic step in the composition pipeline before
the LLM call.

Per runtime_specs/05_persona_composition_runtime.md:
- §6.2: PersonaComposer.compose() flow
- §6.3: Layer formatting convention
- §5.4: ComposedPrompt structure
- PC-1: Anchor Block always first segment
- PC-8: Composition output is immutable

Design contract:
- Deterministic (PC-12: no LLM calls)
- Sorts layers by priority + position_constraint
- Formats each layer per §6.3 convention
- Joins layers with double-newline separators
- Computes token estimate
- Builds CompositionTrace metadata
- < 10ms target latency (§3.3 Step 6)

Author: 心屿团队
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from heart.ss05_composer.layer_aggregator import PromptLayer
from heart.ss05_composer.modality_adapter import (
    LLMCallParams,
    Modality,
    ModalityAwareComposition,
    get_llm_params,
)


# ============================================================
# PromptBundle — Composer output, per §5.4 ComposedPrompt
# ============================================================


@dataclass
class LayerInclusion:
    """Metadata tracking a single layer's position in the assembled prompt."""

    layer_id: str
    source_subsystem: str
    start_offset: int  # character offset in prompt_text
    end_offset: int
    token_count: int


@dataclass
class CompositionTrace:
    """Audit trail for this composition — enables replay and debugging.

    Per §4.2 trace structure and C-PC-3 (every composition must be replayable).
    """

    trace_id: UUID
    turn_index: int
    character_id: str
    modality: Modality
    composed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_tokens: int = 0
    layer_count: int = 0
    layers_included: list[LayerInclusion] = field(default_factory=list)
    content_sha256: str = ""
    composition_ms: float = 0.0


@dataclass
class PromptBundle:
    """Final composed prompt ready for the main LLM call.

    Mirrors the §5.4 ComposedPrompt interface:
      trace_id, prompt_text, total_tokens, layers_included,
      llm_call_params, modality, modality_directives.

    This is an immutable value object (PC-8).
    """

    trace_id: UUID
    prompt_text: str
    total_tokens: int
    layers_included: list[LayerInclusion]

    # LLM call configuration
    llm_params: LLMCallParams

    # Modality metadata
    modality: Modality
    modality_directives: dict[str, Any] = field(default_factory=dict)

    # Composition trace (audit-only, never exposed to user per IMM-PC-4)
    composition_trace: CompositionTrace = field(default_factory=lambda: CompositionTrace(
        trace_id=uuid4(),
        turn_index=0,
        character_id="",
        modality="text-short",
    ))

    # Timestamp
    composed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================
# Token counting — reuse heuristic from token_budget.TokenCounter
# ============================================================


def _estimate_tokens(text: str) -> int:
    """Fast heuristic token estimation (CJK ~1.5/char, other ~0.3/char)."""
    if not text:
        return 0
    chinese = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    other = len(text) - chinese
    return max(0, int(chinese * 1.5 + other * 0.3))


# ============================================================
# Layer ordering — per §6.2 _order_layers
# ============================================================


def _order_layers(layers: list[PromptLayer]) -> list[PromptLayer]:
    """Sort layers by priority then position_constraint.

    Per §5.2 layer_priorities + §6.2 _compose:
    - "first" layers go to the front (among same priority, they lead)
    - "last" layers go to the end
    - Within same priority + constraint, preserve input order (stable sort)
    """
    def sort_key(layer: PromptLayer) -> tuple[int, int, int]:
        pos_order = {"first": 0, "anywhere": 1, "last": 2}
        return (
            layer.priority,
            pos_order.get(layer.position_constraint, 1),
            0,  # stable — we'll use a second pass below
        )

    # Use stable sorting: first tag with index, then sort
    tagged = [(sort_key(L), i, L) for i, L in enumerate(layers)]
    tagged.sort(key=lambda x: (x[0], x[1]))
    return [L for _, _, L in tagged]


# ============================================================
# Layer formatting — per §6.3 _format_layer
# ============================================================


def _format_layer(layer: PromptLayer) -> str:
    """Format a single PromptLayer into its prompt-text representation.

    Per §6.3 Layer Formatting Convention:
      - anchor_full / anchor_light / anchor_reinforce: content as-is (has own ═══ box)
      - user_message: prefix with "用户："
      - response_directive: content as-is
      - modality_adaptation: content as-is
      - default: content as-is
    """
    layer_type = layer.layer_type

    # Anchor layers — already formatted with ═══ box, inject as-is
    if layer_type in ("anchor_full", "anchor_light", "anchor_reinforce"):
        return layer.content

    # User message — prefix
    if layer_type == "user_message":
        return f"用户：{layer.content}"

    # Response directive — pass through (e.g. "凛的回复:")
    if layer_type == "response_directive":
        return layer.content

    # Modality adaptation — pass through
    if layer_type == "modality_adaptation":
        return layer.content

    # Default — plain pass-through
    return layer.content


# ============================================================
# Composer class
# ============================================================


class Composer:
    """Assembles the final prompt from adapted layers.

    This is Step 6 of the per-turn composition flow (§3.3).

    Usage::

        composer = Composer()
        bundle = composer.compose(
            adapted.layers,
            adapted.modality,
            soul_hard_never=["拒绝", "再见"],
        )
    """

    def compose(
        self,
        resolved_layers: list[PromptLayer],
        modality: Modality,
        soul: Optional[dict[str, Any]] = None,
    ) -> PromptBundle:
        """Assemble the final prompt bundle for the main LLM call.

        Step-by-step per §6.2 _compose:
        1. Order layers by priority + position_constraint
        2. Format each layer per §6.3 convention
        3. Join with double-newline separators
        4. Compute token estimate
        5. Track layer inclusion offsets
        6. Select LLM call parameters per modality
        7. Build CompositionTrace
        8. Return immutable PromptBundle

        Args:
            resolved_layers: Post-adapter prompt layers, ready for assembly.
            modality: Target modality (drives LLM param selection).
            soul: Optional Soul Spec dict; used for anti-pattern extraction
                  and identity metadata in the trace.

        Returns:
            PromptBundle ready for the main LLM call.
        """
        trace_id = uuid4()
        start = time.perf_counter()

        # --- 1. Order layers ---
        ordered = _order_layers(resolved_layers)

        # --- 2. Format each layer ---
        formatted_parts: list[str] = []
        for layer in ordered:
            formatted = _format_layer(layer)
            if formatted:  # skip empty content
                formatted_parts.append(formatted)

        # --- 3. Join with separator ---
        prompt_text = "\n\n".join(formatted_parts)

        # --- 4. Token estimate ---
        total_tokens = _estimate_tokens(prompt_text)

        # --- 5. Track layer inclusion offsets ---
        layers_included: list[LayerInclusion] = []
        offset = 0
        for i, part in enumerate(formatted_parts):
            part_end = offset + len(part) + (2 if i < len(formatted_parts) - 1 else 0)  # \n\n
            layers_included.append(
                LayerInclusion(
                    layer_id=ordered[i].layer_id,
                    source_subsystem=ordered[i].source_subsystem,
                    start_offset=offset,
                    end_offset=part_end,
                    token_count=_estimate_tokens(part),
                )
            )
            offset = part_end

        # --- 6. Select LLM params ---
        llm_params = get_llm_params(modality)

        # --- 7. Build trace ---
        character_id = ""
        turn_index = 0
        if soul:
            character_id = soul.get("character_id", "")
        composition_ms = (time.perf_counter() - start) * 1000

        trace = CompositionTrace(
            trace_id=trace_id,
            turn_index=turn_index,
            character_id=character_id,
            modality=modality,
            total_tokens=total_tokens,
            layer_count=len(ordered),
            layers_included=list(layers_included),
            content_sha256=hashlib.sha256(prompt_text.encode()).hexdigest(),
            composition_ms=composition_ms,
        )

        # --- 8. Return PromptBundle (immutable per PC-8) ---
        return PromptBundle(
            trace_id=trace_id,
            prompt_text=prompt_text,
            total_tokens=total_tokens,
            layers_included=layers_included,
            llm_params=llm_params,
            modality=modality,
            modality_directives={},
            composition_trace=trace,
        )


# ============================================================
# Module-level convenience: compose from ModalityAwareComposition
# ============================================================


def assemble(
    adapted: ModalityAwareComposition,
    soul: Optional[dict[str, Any]] = None,
) -> PromptBundle:
    """Convenience: compose directly from a ModalityAwareComposition.

    This is the terminal composition step that follows modality adaptation.
    """
    composer = Composer()
    return composer.compose(
        resolved_layers=adapted.layers,
        modality=adapted.modality,
        soul=soul,
    )
