"""
Token Budget Allocator — SS05 Persona Composition Runtime §3.3 Step 4 + §10.5 + §10.6

Allocates token budget across prompt layers by priority:
- Anchor (SS01) and Care Path (safety level=PURPLE) are NON-compressible (§3.3 Step 4)
- Compressible layers use truncation / summarization / drop strategies (§10.6)
- Low-priority layers are compressed or dropped first (§6 _allocate_budget)

Core invariants:
  INV-PC-2: for all composed_prompt P, sum P.layer_tokens <= token_budget
  PC-3:     Token budget must be strictly enforced; overflow triggers compression

Token counting per §10.5: heuristic estimate (CJK ~1.5 tokens/char, others ~0.3/char),
+-15% accuracy, <5ms per call.

Compression strategies per §10.6:
  - memory_context: keep L4 identity -> compress episodes -> drop forgetting hints
  - conversation_history: keep first turn + last N turns -> truncate middle
  - relationship_context: truncation (V1), smarter signal compression (V2)
  - default: simple truncation

Per runtime_specs/05_persona_composition_runtime.md §3.3, §5.3, §10.5, §10.6.

Author: 心屿团队
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from heart.ss05_composer.layer_aggregator import PromptLayer

# ============================================================
# Non-compressible layer types
# ============================================================

# Anchor layers are always non-compressible.
# PC-1: Anchor Block is always the first segment.  It must never be
# truncated, summarized, or dropped -- doing so would fatally degrade
# character identity coherence.
NON_COMPRESSIBLE_ANCHOR_TYPES: frozenset[str] = frozenset(
    {
        "anchor_full",
        "anchor_light",
        "anchor_reinforce",
    }
)

# Care Path: safety layer with level "PURPLE" is also non-compressible.
# When a user is in crisis, the safety guardrails must remain intact at
# full fidelity -- no truncation, no summarization, no drop.


# ============================================================
# TokenCounter — §10.5
# ============================================================


class TokenCounter:
    """Fast heuristic + exact token counting per §10.5.

    ``estimate()`` uses the CJK × 1.5 / non-CJK × 0.3 heuristic from
    anchor_injector.HeuristicTokenEstimator.  Accurate to ±15% vs real
    tokenizers, runs well under 5 ms.

    ``exact()`` currently falls back to ``estimate()``.  Production (V2)
    should plug in a model-specific tokenizer (tiktoken / DeepSeek tokenizer).

    Usage::

        counter = TokenCounter()
        tokens = counter.estimate("你好世界")
    """

    def estimate(self, text: str) -> int:
        """Fast heuristic token estimation for budget allocation.

        CJK Unified Ideographs (U+4E00-U+9FFF) ≈ 1.5 tokens/char.
        Everything else (ASCII, punctuation, emoji, etc.) ≈ 0.3 tokens/char.
        """
        if not text:
            return 0
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        non_chinese = len(text) - chinese_chars
        return max(0, int(chinese_chars * 1.5 + non_chinese * 0.3))

    def exact(self, text: str) -> int:
        """Exact token count (V1 falls back to estimate; V2 -> tiktoken)."""
        # TODO(heart-V2): plug in tiktoken / DeepSeek tokenizer per model. # TODO(#issue-69)
        return self.estimate(text)


# ============================================================
# Compression Strategy — §10.6
# ============================================================


class LayerCompressor:
    """Per-layer-type compression strategies.

    Different prompt layers carry different semantic structures, so a
    one-size-fits-all truncation would destroy critical information.
    The compressor dispatches by ``layer_type`` to a strategy that
    respects the internal structure of that layer.

    Strategies (per §10.6):
        memory_context     -- keep L4 identity, drop oldest episodes, remove hints
        conversation_history -- keep first turn + recent N, truncate middle
        relationship_context -- truncation (V1), signal-aware compression (V2)
        default              -- simple char-level truncation
    """

    def __init__(self, token_counter: Optional[TokenCounter] = None):
        self._counter = token_counter or TokenCounter()

    # -- public entry --------------------------------------------------

    def compress(self, layer: PromptLayer, target_tokens: int) -> PromptLayer:
        """Compress *layer* to <= *target_tokens*.

        Returns a **new** ``PromptLayer`` with updated content and token
        estimate.  The original layer is never mutated.
        """
        current = self._counter.estimate(layer.content)
        if current <= target_tokens:
            return layer

        strategy = self._dispatch(layer.layer_type)
        return strategy(layer, target_tokens)

    # -- strategy dispatch ---------------------------------------------

    def _dispatch(self, layer_type: str):
        _strategies = {
            "memory_context": self._compress_memory,
            "conversation_history": self._compress_history,
            "relationship_context": self._compress_relationship,
        }
        return _strategies.get(layer_type, self._compress_truncation)

    # -- default: truncation -------------------------------------------

    def _compress_truncation(self, layer: PromptLayer, target: int) -> PromptLayer:
        """Plain character-level truncation.  Binary-search for cutoff point."""
        content = layer.content
        truncated = self._truncate_to_tokens(content, target)
        return self._rebuild(layer, truncated)

    # -- memory_context ------------------------------------------------

    def _compress_memory(self, layer: PromptLayer, target: int) -> PromptLayer:
        """Memory compression: preserve L4 identity, drop oldest episodes.

        Strategy (§10.6):
        1. Extract [L4_IDENTITY] block -- never compress.
        2. Split remaining content into episodes.
        3. Keep most-recent episodes until budget is exhausted.
        4. Drop forgetting hints (lowest priority).
        """
        content = layer.content
        current = self._counter.estimate(content)
        if current <= target:
            return layer

        # 1. Extract L4 identity block
        l4_pattern = re.compile(r"\[L4_IDENTITY\](.*?)\[/L4_IDENTITY\]", re.DOTALL)
        l4_match = l4_pattern.search(content)
        l4_block = l4_match.group(0) if l4_match else ""
        l4_tokens = self._counter.estimate(l4_block)

        remaining_budget = target - l4_tokens
        if remaining_budget <= 0:
            # Even L4 alone exceeds target -- reluctantly truncate L4
            return self._rebuild(layer, self._truncate_to_tokens(l4_block, target))

        # 2. Remove L4 block; process remaining as episodes
        body = l4_pattern.sub("", content) if l4_match else content

        # 3. Split into episodes
        episodes = re.split(r"\n(?=Episode \d+:|\[EPISODE\])", body.strip())

        # 4. Keep most-recent episodes
        kept: list[str] = []
        used = 0
        for ep in reversed(episodes):
            ep_tokens = self._counter.estimate(ep)
            if used + ep_tokens <= remaining_budget:
                kept.insert(0, ep)
                used += ep_tokens
            else:
                break

        result = l4_block
        if kept:
            result = l4_block + "\n\n" + "\n".join(kept)
        return self._rebuild(layer, result.strip())

    # -- conversation_history ------------------------------------------

    def _compress_history(self, layer: PromptLayer, target: int) -> PromptLayer:
        """Conversation history compression: keep first turn + last N turns.

        Strategy (§10.6):
        1. Always keep the first turn (setup / character introduction).
        2. Keep as many most-recent turns as budget allows.
        3. Middle turns are silently dropped.
        """
        content = layer.content
        current = self._counter.estimate(content)
        if current <= target:
            return layer

        # Split into turns
        turns = re.split(r"\n(?=(?:用户|助手|User|Assistant)\s*[:：])", content)

        if len(turns) <= 2:
            return self._rebuild(layer, self._truncate_to_tokens(content, target))

        first_turn = turns[0]
        first_tokens = self._counter.estimate(first_turn)

        remaining = target - first_tokens
        if remaining <= 0:
            return self._rebuild(layer, self._truncate_to_tokens(content, target))

        # Keep last turns from the end
        kept_last: list[str] = []
        used = 0
        for turn in reversed(turns[1:]):
            t = self._counter.estimate(turn)
            if used + t <= remaining:
                kept_last.insert(0, turn)
                used += t
            else:
                break

        result = first_turn
        if kept_last:
            result = first_turn + "\n" + "\n".join(kept_last)
        return self._rebuild(layer, result.strip())

    # -- relationship_context ------------------------------------------

    def _compress_relationship(self, layer: PromptLayer, target: int) -> PromptLayer:
        """Relationship context compression (V1: truncation)."""
        return self._compress_truncation(layer, target)

    # -- helpers -------------------------------------------------------

    def _truncate_to_tokens(self, text: str, target: int) -> str:
        """Binary-search for the longest prefix whose token estimate <= target."""
        if not text:
            return ""
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._counter.estimate(text[:mid]) <= target:
                lo = mid + 1
            else:
                hi = mid
        return text[: lo - 1] if lo > 0 else ""

    def _rebuild(self, original: PromptLayer, new_content: str) -> PromptLayer:
        """Create a new PromptLayer with compressed content.

        The original layer is not mutated; this returns a shallow copy with
        updated content, token estimate, and content hash.
        """
        return PromptLayer(
            layer_id=original.layer_id,
            source_subsystem=original.source_subsystem,
            layer_type=original.layer_type,
            priority=original.priority,
            position_constraint=original.position_constraint,
            content=new_content,
            token_count_estimate=self._counter.estimate(new_content),
            min_token_count=original.min_token_count,
            is_compressible=True,
            metadata=dict(original.metadata),
            variants=dict(original.variants),
            conflicts_with=list(original.conflicts_with),
        )


# ============================================================
# AllocatedLayers — output data structure
# ============================================================


@dataclass
class AllocatedLayer:
    """Per-layer allocation metadata for Composition Trace (§4.2).

    Attributes:
        layer_id: unique layer identifier within the composition.
        layer_type: type from prompt layer taxonomy (§5.1).
        priority: layer priority (1 = highest, 100 = lowest, §5.2).
        original_tokens: token estimate before allocation.
        allocated_tokens: token estimate after allocation / compression.
        compression_applied: strategy applied, or ``None`` if untouched.
            Values: ``"truncation"``, ``"summarization"``, ``"drop"``, ``None``.
    """

    layer_id: str
    layer_type: str
    priority: int
    original_tokens: int
    allocated_tokens: int
    compression_applied: Optional[str] = None


@dataclass
class AllocatedLayers:
    """Result of token budget allocation.

    Attributes:
        layers: budget-respecting layer list.  Dropped layers are absent
            from this list; compressed layers carry updated content.
        total_tokens: sum of token estimates across ``layers``.
        budget: target budget that was enforced.
        compression_applied: ``True`` if any layer was compressed or dropped.
        allocations: per-layer metadata records (one per *input* layer,
            including dropped layers to provide a complete audit trail).
    """

    layers: list[PromptLayer]
    total_tokens: int
    budget: int
    compression_applied: bool
    allocations: list[AllocatedLayer] = field(default_factory=list)

    @property
    def dropped_layer_ids(self) -> list[str]:
        """Layer IDs that were dropped during allocation."""
        return [a.layer_id for a in self.allocations if a.compression_applied == "drop"]

    @property
    def compressed_layer_ids(self) -> list[str]:
        """Layer IDs that were compressed (but not dropped)."""
        return [
            a.layer_id
            for a in self.allocations
            if a.compression_applied and a.compression_applied != "drop"
        ]


# ============================================================
# Non-compressibility check
# ============================================================


def _is_non_compressible(layer: PromptLayer) -> bool:
    """Return ``True`` if *layer* must never be compressed or dropped.

    Non-compressible categories:
    - Anchor layers (``anchor_full``, ``anchor_light``, ``anchor_reinforce``)
      -- per §3.3 Step 4, anchors are always preserved at full fidelity.
    - Care Path: ``safety`` layer with ``metadata["level"] == "PURPLE"``
      -- when a user is in crisis, safety guardrails must remain intact.
    """
    if layer.layer_type in NON_COMPRESSIBLE_ANCHOR_TYPES:
        return True
    if layer.layer_type == "safety":
        level = layer.metadata.get("level", "")
        if level == "PURPLE":
            return True
    return False


# ============================================================
# Budget allocator — §3.3 Step 4 + §6 _allocate_budget
# ============================================================


def allocate(layers: list[PromptLayer], total_budget: int) -> AllocatedLayers:
    """Allocate token budget across layers by priority.

    **Algorithm** (per §6 ``_allocate_budget`` and §3.3 Step 4):

    1. Separate non-compressible layers (anchor + care path) from
       compressible layers.
    2. Non-compressible layers always keep their full content.
    3. Remaining budget is distributed to compressible layers, from
       **highest priority to lowest priority** -- i.e. low-priority
       layers are compressed or dropped first.
    4. Each compressible layer is checked in priority order:
       a. Fits as-is -> kept in full.
       b. Can be compressed to its ``min_token_count`` or above -> compressed.
       c. Cannot meet ``min_token_count`` -> **dropped** (removed from output).
    5. If even non-compressible layers exceed the budget (should not happen
       in practice), all compressible layers are dropped.

    **Performance target**: < 10 ms per §3.3 Step 4.

    Args:
        layers: Prompt layers from conflict resolver (Step 2).
        total_budget: Total token budget for the composed prompt.

    Returns:
        ``AllocatedLayers`` with budget-respecting layer list and per-layer
        allocation metadata for the Composition Trace.
    """
    counter = TokenCounter()
    compressor = LayerCompressor(counter)

    # -- 1. Separate non-compressible / compressible -------------------

    non_compressible: list[PromptLayer] = []
    compressible: list[PromptLayer] = []

    for L in layers:  # noqa: N806 — math convention: L = layer  # noqa: N806 — math convention: L = layer, per Composer spec §3.2
        if _is_non_compressible(L):
            non_compressible.append(L)
        else:
            compressible.append(L)

    # -- 2. Sort compressible by priority (hi -> lo) -------------------

    compressible.sort(key=lambda L: L.priority)  # noqa: N803 — math convention: L = layer

    # -- 3. Calculate non-compressible token cost ----------------------

    nc_tokens = sum(counter.estimate(L.content) for L in non_compressible)  # noqa: N806

    # -- 4. Extreme case: non-compressible already over budget ---------

    if nc_tokens > total_budget:
        allocations = [
            AllocatedLayer(
                layer_id=L.layer_id,
                layer_type=L.layer_type,
                priority=L.priority,
                original_tokens=counter.estimate(L.content),
                allocated_tokens=counter.estimate(L.content),
                compression_applied=None,
            )
            for L in non_compressible  # noqa: N806
        ]
        for L in compressible:  # noqa: N806
            allocations.append(
                AllocatedLayer(
                    layer_id=L.layer_id,
                    layer_type=L.layer_type,
                    priority=L.priority,
                    original_tokens=counter.estimate(L.content),
                    allocated_tokens=0,
                    compression_applied="drop",
                )
            )
        return AllocatedLayers(
            layers=list(non_compressible),
            total_tokens=nc_tokens,
            budget=total_budget,
            compression_applied=True,
            allocations=allocations,
        )

    # -- 5. Budget for compressible layers -----------------------------

    budget_for_compressible = total_budget - nc_tokens

    # Check if everything fits without compression
    total_compressible_est = sum(
        counter.estimate(L.content)
        for L in compressible  # noqa: N806
    )

    if nc_tokens + total_compressible_est <= total_budget:
        # No compression needed
        all_allocations = _build_noop_allocations(non_compressible + compressible, counter)
        return AllocatedLayers(
            layers=non_compressible + compressible,
            total_tokens=nc_tokens + total_compressible_est,
            budget=total_budget,
            compression_applied=False,
            allocations=all_allocations,
        )

    # -- 6. Allocate compressible layers — process hi-pri -> lo-pri ----

    kept_compressible: list[PromptLayer] = []
    allocations: list[AllocatedLayer] = []
    any_compression = False

    # Record non-compressible allocations (always pass through)
    for L in non_compressible:  # noqa: N806
        allocations.append(
            AllocatedLayer(
                layer_id=L.layer_id,
                layer_type=L.layer_type,
                priority=L.priority,
                original_tokens=counter.estimate(L.content),
                allocated_tokens=counter.estimate(L.content),
                compression_applied=None,
            )
        )

    # Walk compressible layers highest-priority first.
    # Each layer gets a chance to claim budget before lower-priority layers.
    remaining = budget_for_compressible

    for L in compressible:  # noqa: N806
        est = counter.estimate(L.content)

        if remaining >= est:
            # Fits in full
            kept_compressible.append(L)
            remaining -= est
            allocations.append(
                AllocatedLayer(
                    layer_id=L.layer_id,
                    layer_type=L.layer_type,
                    priority=L.priority,
                    original_tokens=est,
                    allocated_tokens=est,
                    compression_applied=None,
                )
            )
        elif remaining >= L.min_token_count:
            # Needs compression; can meet min_token_count
            compressed = compressor.compress(L, remaining)
            comp_est = counter.estimate(compressed.content)
            kept_compressible.append(compressed)
            remaining -= comp_est
            any_compression = True
            allocations.append(
                AllocatedLayer(
                    layer_id=L.layer_id,
                    layer_type=L.layer_type,
                    priority=L.priority,
                    original_tokens=est,
                    allocated_tokens=comp_est,
                    compression_applied="truncation",
                )
            )
        else:
            # Cannot meet min_token_count -> drop
            any_compression = True
            allocations.append(
                AllocatedLayer(
                    layer_id=L.layer_id,
                    layer_type=L.layer_type,
                    priority=L.priority,
                    original_tokens=est,
                    allocated_tokens=0,
                    compression_applied="drop",
                )
            )

    # -- 7. Assemble result --------------------------------------------

    result_layers = non_compressible + kept_compressible
    total_allocated = sum(
        counter.estimate(L.content)
        for L in result_layers  # noqa: N806
    )

    return AllocatedLayers(
        layers=result_layers,
        total_tokens=total_allocated,
        budget=total_budget,
        compression_applied=any_compression,
        allocations=allocations,
    )


def _build_noop_allocations(
    layers: list[PromptLayer], counter: TokenCounter
) -> list[AllocatedLayer]:
    """Build allocation records for the no-compression-needed case."""
    return [
        AllocatedLayer(
            layer_id=L.layer_id,
            layer_type=L.layer_type,
            priority=L.priority,
            original_tokens=counter.estimate(L.content),
            allocated_tokens=counter.estimate(L.content),
            compression_applied=None,
        )
        for L in layers  # noqa: N806
    ]
