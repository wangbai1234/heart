"""
Layer Aggregator - SS05 Persona Composition Runtime §3.2 + §10.3

Parallel aggregation of upstream subsystem context blocks:
- SS01: Anchor Block (Soul Spec)
- SS02: Memory Context Block
- SS03: Emotion Context Block
- SS04: Relationship Context Block
- SS06: Inner State Block

Design:
- All 5 layers fetched in parallel via asyncio.gather
- Each upstream call has an independent timeout
- Partial-result tolerance: on timeout/failure, uses cached fallback
- End-to-end aggregation target: < 200ms (per INV-PC-8 COMPOSITION_BUDGET)

Per runtime_specs/05_persona_composition_runtime.md §10.3 and §3.2.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Optional, Protocol
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()

# ============================================================
# Constants
# ============================================================

# Per-layer independent timeouts (seconds), per §7.3 timing budget
DEFAULT_LAYER_TIMEOUTS: dict[str, float] = {
    "SS01": 0.050,  # anchor, cached (~5ms typical)
    "SS02": 0.250,  # memory retrieval, bottleneck (~200ms typical)
    "SS03": 0.050,  # emotion (~10ms typical)
    "SS04": 0.050,  # relationship (~10ms typical)
    "SS06": 0.030,  # inner state, cached (~5ms typical)
}

# Global aggregation timeout (safety net, per §10.3 LAYER_AGGREGATION_TIMEOUT)
LAYER_AGGREGATION_TIMEOUT = 0.300  # 300ms

# ============================================================
# PromptLayer — per §5.1
# ============================================================

LayerType = str  # "anchor_full" | "anchor_light" | "anchor_reinforce" | "safety" |
# "modality_adaptation" | "relationship_context" | "emotion_context" |
# "inner_state" | "memory_context" | "scene_context" |
# "conversation_history" | "user_message" | "response_directive"

SubsystemId = str  # "SS01" | "SS02" | "SS03" | "SS04" | "SS06" | "SS07"

PositionConstraint = str  # "first" | "anywhere" | "last"


@dataclass
class PromptLayer:
    """A single prompt layer, as defined in §5.1.

    Each layer carries content, priority, position constraint, and
    token metadata for downstream budget allocation and composition.
    """

    # ─── Identity ───
    layer_id: str
    source_subsystem: SubsystemId
    layer_type: LayerType

    # ─── Priority & Position ───
    priority: int  # 1 (highest) - 100 (lowest)
    position_constraint: PositionConstraint = "anywhere"

    # ─── Content ───
    content: str = ""

    # ─── Token Management ───
    token_count_estimate: int = 0
    min_token_count: int = 0
    is_compressible: bool = False

    # ─── Metadata ───
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cache_key: Optional[str] = None
    content_hash: str = ""

    # ─── Conflict Resolution Hints ───
    conflicts_with: list[dict[str, str]] = field(default_factory=list)

    # ─── Pre-rendered variants (for Conflict Resolver SWITCH_VARIANT) ───
    # Keyed by variant_id (e.g. "vulnerable_anger", "tenderness", "anger_intimate",
    # "interrupted_for_you", "care_path_voice"). Maps to alternate content text.
    variants: dict[str, str] = field(default_factory=dict)

    # ─── Subsystem-specific metadata (for Conflict Resolver inspection) ───
    # The resolver inspects this map to make deterministic decisions.
    # Conventional keys per source_subsystem:
    #   SS01 (anchor): hard_never, default_tone, cognitive_style_max,
    #                  care_path_voice, identity_archetype, voice_dna_markers
    #   SS02 (memory): episodes ([{id, min_stage, contradicted_by_l4, ...}])
    #   SS03 (emotion): emotion_name, intensity, stage_variants
    #                   (dict mapping stage_id → variant_id)
    #   SS04 (relationship): stage, behavioral_envelope (set of allowed emotion names)
    #   SS06 (inner_state): availability, sub_suggestions, intensity,
    #                       stage_variants, romantic
    #   SS07 (safety): level ("GREEN" | "YELLOW" | "ORANGE" | "PURPLE")
    #   Scene: scene ("office" | "home" | ...)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.content_hash and self.content:
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()

    @property
    def is_empty(self) -> bool:
        """Whether this layer is an empty fallback placeholder."""
        return not self.content


# ============================================================
# Layer priorities — per §5.2
# ============================================================

LAYER_PRIORITIES: dict[str, int] = {
    "anchor_full": 1,
    "anchor_light": 1,
    "anchor_reinforce": 1,
    "safety": 5,
    "modality_adaptation": 10,
    "relationship_context": 20,
    "emotion_context": 25,
    "inner_state": 30,
    "memory_context": 35,
    "scene_context": 40,
    "conversation_history": 50,
    "user_message": 90,
    "response_directive": 95,
}

LAYER_MIN_TOKENS: dict[str, int] = {
    "anchor_full": 400,
    "anchor_light": 80,
    "anchor_reinforce": 300,
    "relationship_context": 200,
    "emotion_context": 150,
    "inner_state": 100,
    "memory_context": 300,
    "user_message": 100,
    "response_directive": 50,
}


# ============================================================
# Upstream Subsystem Protocols
# ============================================================


class CompositionContext(Protocol):
    """Minimal protocol for the composition context passed through aggregation.

    Full definition per §4.1.  We only depend on the fields the aggregator reads.
    """

    trace_id: UUID
    user_id: UUID
    character_id: str
    turn_index: int


# ============================================================
# LayerAggregator
# ============================================================


class LayerAggregator:
    """Parallel layer aggregator per §3.2 and §10.3.

    Collects context blocks from all upstream subsystems concurrently,
    with independent per-layer timeouts and cached fallback on failure.

    Usage::

        aggregator = LayerAggregator(
            ss01=anchor_injector,
            ss02=memory_service,
            ss03=emotion_service,
            ss04=relationship_service,
            ss06=inner_state_service,
        )
        layers = await aggregator.aggregate(ctx, user_message)
    """

    def __init__(
        self,
        *,
        ss01: Optional[Any] = None,  # provides get_anchor_block(ctx) -> PromptLayer
        ss02: Optional[Any] = None,  # provides get_memory_context_block(ctx) -> PromptLayer
        ss03: Optional[Any] = None,  # provides get_emotion_context_block(ctx) -> PromptLayer
        ss04: Optional[Any] = None,  # provides get_relationship_context_block(ctx) -> PromptLayer
        ss06: Optional[Any] = None,  # provides get_inner_state_block(ctx) -> PromptLayer
        timeouts: Optional[dict[str, float]] = None,
    ):
        self._upstreams: dict[str, Any] = {
            "SS01": ss01,
            "SS02": ss02,
            "SS03": ss03,
            "SS04": ss04,
            "SS06": ss06,
        }
        self._timeouts = {**DEFAULT_LAYER_TIMEOUTS, **(timeouts or {})}

        # Per-layer result cache for fallback on timeout/failure
        # Keyed by (layer_name, user_id, character_id)
        self._result_cache: dict[str, PromptLayer] = {}

    # ─── Public API ──────────────────────────────────────────

    async def aggregate(
        self,
        ctx: CompositionContext,
        user_message: str,
    ) -> list[PromptLayer]:
        """Aggregate all upstream layers in parallel.

        Args:
            ctx: Composition context (user, character, turn, etc.).
            user_message: The current user message text.

        Returns:
            List of PromptLayer objects, one per upstream + user_message
            + response_directive.  Layers that failed are replaced with
            cached or empty fallback placeholders.

        Raises:
            asyncio.TimeoutError: If global aggregation timeout is exceeded.
        """
        start = time.monotonic()

        # Build per-layer tasks with independent timeouts
        tasks = [
            self._with_fallback("SS01", self._fetch_anchor(ctx)),
            self._with_fallback("SS02", self._fetch_memory(ctx)),
            self._with_fallback("SS03", self._fetch_emotion(ctx)),
            self._with_fallback("SS04", self._fetch_relationship(ctx)),
            self._with_fallback("SS06", self._fetch_inner_state(ctx)),
        ]

        # Parallel gather with global safety timeout
        results = await asyncio.wait_for(
            asyncio.gather(*tasks),
            timeout=self._timeouts.get("_global", LAYER_AGGREGATION_TIMEOUT),
        )

        layers: list[PromptLayer] = list(results)

        # Append user_message layer (always succeeds, no upstream call)
        layers.append(self._build_user_message_layer(user_message))

        # Append response directive layer
        layers.append(self._build_response_directive_layer(ctx.character_id))

        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "layer_aggregation_complete",
            trace_id=str(getattr(ctx, "trace_id", "N/A")),
            layer_count=len(layers),
            empty_layer_count=sum(1 for L in layers if L.is_empty),
            elapsed_ms=round(elapsed_ms, 2),
        )

        return layers

    # ─── Per-layer fetch helpers ──────────────────────────────

    async def _fetch_anchor(self, ctx: CompositionContext) -> PromptLayer:
        """Fetch anchor block from SS01."""
        upstream = self._upstreams["SS01"]
        if upstream is None or not hasattr(upstream, "get_anchor_block"):
            return self._empty_anchor()
        return await upstream.get_anchor_block(ctx)

    async def _fetch_memory(self, ctx: CompositionContext) -> PromptLayer:
        """Fetch memory context block from SS02."""
        upstream = self._upstreams["SS02"]
        if upstream is None or not hasattr(upstream, "get_memory_context_block"):
            return self._empty_memory()
        return await upstream.get_memory_context_block(ctx)

    async def _fetch_emotion(self, ctx: CompositionContext) -> PromptLayer:
        """Fetch emotion context block from SS03."""
        upstream = self._upstreams["SS03"]
        if upstream is None or not hasattr(upstream, "get_emotion_context_block"):
            return self._empty_emotion()
        return await upstream.get_emotion_context_block(ctx)

    async def _fetch_relationship(self, ctx: CompositionContext) -> PromptLayer:
        """Fetch relationship context block from SS04."""
        upstream = self._upstreams["SS04"]
        if upstream is None or not hasattr(upstream, "get_relationship_context_block"):
            return self._empty_relationship()
        return await upstream.get_relationship_context_block(ctx)

    async def _fetch_inner_state(self, ctx: CompositionContext) -> PromptLayer:
        """Fetch inner state block from SS06."""
        upstream = self._upstreams["SS06"]
        if upstream is None or not hasattr(upstream, "get_inner_state_block"):
            return self._empty_inner_state()
        return await upstream.get_inner_state_block(ctx)

    # ─── Timeout + Fallback wrapper ───────────────────────────

    async def _with_fallback(
        self,
        layer_name: str,
        coro: Coroutine[Any, Any, PromptLayer],
    ) -> PromptLayer:
        """Execute a layer fetch with independent timeout and cached fallback.

        Per §9.1 / §10.3: on timeout or exception, we first try the
        in-memory cache (last known good result), then an empty placeholder.

        Args:
            layer_name: Human-readable layer name for logging (e.g. "SS01").
            coro: The awaitable that produces a PromptLayer.

        Returns:
            The fetched PromptLayer, a cached fallback, or an empty placeholder.
        """
        timeout = self._timeouts.get(layer_name, 0.100)  # default 100ms

        try:
            layer = await asyncio.wait_for(coro, timeout=timeout)
            # Cache successful result for future fallback
            self._cache_put(layer_name, layer)
            return layer
        except asyncio.TimeoutError:
            logger.warning(
                "layer_fetch_timeout",
                layer=layer_name,
                timeout_ms=timeout * 1000,
            )
        except Exception:
            logger.exception("layer_fetch_failed", layer=layer_name)

        # Try cached fallback
        cached = self._cache_get(layer_name)
        if cached is not None:
            logger.info("layer_fallback_used", layer=layer_name, source="cache")
            return cached

        # Last resort: empty placeholder
        logger.warning("layer_fallback_used", layer=layer_name, source="empty")
        return self._empty_for(layer_name)

    # ─── Cache ────────────────────────────────────────────────

    def _cache_put(self, layer_name: str, layer: PromptLayer) -> None:
        """Store a successful layer result for future fallback."""
        self._result_cache[layer_name] = layer

    def _cache_get(self, layer_name: str) -> Optional[PromptLayer]:
        """Retrieve the last cached successful result for a layer."""
        return self._result_cache.get(layer_name)

    def invalidate_cache(self, layer_name: Optional[str] = None) -> None:
        """Invalidate cached results.

        Args:
            layer_name: If provided, invalidate only that layer.
                        Otherwise, invalidate all.
        """
        if layer_name:
            self._result_cache.pop(layer_name, None)
        else:
            self._result_cache.clear()

    # ─── Empty / Fallback Layer Factories ─────────────────────

    def _empty_anchor(self) -> PromptLayer:
        """Empty anchor placeholder (per §9.1)."""
        return PromptLayer(
            layer_id=f"anchor-empty-{uuid4().hex[:8]}",
            source_subsystem="SS01",
            layer_type="anchor_light",
            priority=LAYER_PRIORITIES["anchor_light"],
            position_constraint="first",
            content="",
            min_token_count=LAYER_MIN_TOKENS["anchor_light"],
            is_compressible=False,
        )

    def _empty_memory(self) -> PromptLayer:
        return PromptLayer(
            layer_id=f"memory-empty-{uuid4().hex[:8]}",
            source_subsystem="SS02",
            layer_type="memory_context",
            priority=LAYER_PRIORITIES["memory_context"],
            position_constraint="anywhere",
            content="",
            min_token_count=LAYER_MIN_TOKENS["memory_context"],
            is_compressible=True,
        )

    def _empty_emotion(self) -> PromptLayer:
        return PromptLayer(
            layer_id=f"emotion-empty-{uuid4().hex[:8]}",
            source_subsystem="SS03",
            layer_type="emotion_context",
            priority=LAYER_PRIORITIES["emotion_context"],
            position_constraint="anywhere",
            content="",
            min_token_count=LAYER_MIN_TOKENS["emotion_context"],
            is_compressible=True,
        )

    def _empty_relationship(self) -> PromptLayer:
        return PromptLayer(
            layer_id=f"rel-empty-{uuid4().hex[:8]}",
            source_subsystem="SS04",
            layer_type="relationship_context",
            priority=LAYER_PRIORITIES["relationship_context"],
            position_constraint="anywhere",
            content="",
            min_token_count=LAYER_MIN_TOKENS["relationship_context"],
            is_compressible=True,
        )

    def _empty_inner_state(self) -> PromptLayer:
        return PromptLayer(
            layer_id=f"inner-empty-{uuid4().hex[:8]}",
            source_subsystem="SS06",
            layer_type="inner_state",
            priority=LAYER_PRIORITIES["inner_state"],
            position_constraint="anywhere",
            content="",
            min_token_count=LAYER_MIN_TOKENS["inner_state"],
            is_compressible=True,
        )

    def _empty_for(self, layer_name: str) -> PromptLayer:
        """Return the appropriate empty placeholder for a layer name."""
        factories: dict[str, Callable[[], PromptLayer]] = {
            "SS01": self._empty_anchor,
            "SS02": self._empty_memory,
            "SS03": self._empty_emotion,
            "SS04": self._empty_relationship,
            "SS06": self._empty_inner_state,
        }
        factory = factories.get(layer_name)
        if factory:
            return factory()
        # Generic empty layer
        return PromptLayer(
            layer_id=f"empty-{layer_name}-{uuid4().hex[:8]}",
            source_subsystem=layer_name,
            layer_type="memory_context",
            priority=99,
        )

    # ─── User Message & Response Directive ────────────────────

    @staticmethod
    def _build_user_message_layer(user_message: str) -> PromptLayer:
        """Build the user_message layer (always present, no upstream call)."""
        return PromptLayer(
            layer_id=f"user-msg-{uuid4().hex[:8]}",
            source_subsystem="SS05",
            layer_type="user_message",
            priority=LAYER_PRIORITIES["user_message"],
            position_constraint="last",
            content=user_message,
            token_count_estimate=len(user_message),
            min_token_count=LAYER_MIN_TOKENS["user_message"],
            is_compressible=False,
        )

    @staticmethod
    def _build_response_directive_layer(character_id: str) -> PromptLayer:
        """Build the response directive layer."""
        return PromptLayer(
            layer_id=f"resp-dir-{uuid4().hex[:8]}",
            source_subsystem="SS05",
            layer_type="response_directive",
            priority=LAYER_PRIORITIES["response_directive"],
            position_constraint="last",
            content=f"{character_id}的回复:",
            token_count_estimate=5,
            min_token_count=LAYER_MIN_TOKENS["response_directive"],
            is_compressible=False,
        )
