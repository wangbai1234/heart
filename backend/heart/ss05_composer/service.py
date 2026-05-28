"""
SS05 Composer Service — Persona Composition Runtime core.

Per runtime_specs/05_persona_composition_runtime.md:
- Layer Aggregator: assembles context blocks from SS01-SS04, SS06
- Conflict Resolver: resolves competing subsystem directives
- Token Budget Allocator: prioritizes layers under budget constraint
- Anti-Pattern Filter: enforces hard_never patterns post-generation

Architecture:
    ComposerService
        └── compose(context_blocks, user_message) → response
            ├── build_system_prompt(soul, memory, emotion, relationship, inner_state)
            ├── ModelRouter.call_main() / stream_main()
            └── post_filter(response, anti_patterns) → validated response

DI: ComposerService(soul_registry, memory_service, emotion_service, model_router)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import UUID

import structlog
from heart.infra.invariants import invariant
import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip
from heart.observability.turn_profiler import TurnProfiler

from heart.ss01_soul.registry import SoulRegistry
from heart.ss01_soul.schema_validator import SoulSpec

logger = structlog.get_logger(__name__)


# ── Context Block Types ──────────────────────────────────────────


@dataclass
class AnchorContextBlock:
    """SS01 Soul Spec anchor block for prompt composition."""

    archetype: str = ""
    core_wound_essence: str = ""
    core_desire_surface: str = ""
    identity_anchor_text: str = ""
    voice_dna: List[Dict[str, str]] = field(default_factory=list)
    hard_never: List[str] = field(default_factory=list)
    anti_patterns: List[str] = field(default_factory=list)
    anchor_mode: str = "standard"


@dataclass
class MemoryContextBlock:
    """SS02 Memory context block for prompt composition."""

    retrieved_memories: List[Dict[str, Any]] = field(default_factory=list)
    recently_forgotten_hints: List[str] = field(default_factory=list)
    l4_included: bool = False


@dataclass
class EmotionContextBlock:
    """SS03 Emotion context block for prompt composition."""

    emotion_summary: str = ""
    vad_valence: float = 0.0
    vad_arousal: float = 0.3
    vad_dominance: float = 0.5
    active_emotions: List[Dict[str, Any]] = field(default_factory=list)
    mood_descriptor: str = "平静"
    energy_descriptor: str = "适中"
    pending_repairs_summary: Optional[str] = None
    expression_guidelines: Optional[List[str]] = None


@dataclass
class RelationshipContextBlock:
    """SS04 Relationship context block for prompt composition."""

    relationship_phase: str = "stranger"
    trust_level: float = 0.0
    attachment_style: str = ""
    behavioral_envelope: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InnerStateContextBlock:
    """SS06 Inner State context block for prompt composition."""

    internal_monologue: str = ""
    recent_reflections: List[str] = field(default_factory=list)
    current_need: str = ""


@dataclass
class CompositionContext:
    """Aggregated context from all subsystems for one turn."""

    user_id: UUID
    character_id: str
    turn_id: UUID
    session_id: Optional[UUID] = None
    anchor: AnchorContextBlock = field(default_factory=AnchorContextBlock)
    memory: MemoryContextBlock = field(default_factory=MemoryContextBlock)
    emotion: EmotionContextBlock = field(default_factory=EmotionContextBlock)
    relationship: RelationshipContextBlock = field(default_factory=RelationshipContextBlock)
    inner_state: InnerStateContextBlock = field(default_factory=InnerStateContextBlock)

    # Token budget
    max_tokens: int = 2000
    token_budget_allocations: Dict[str, int] = field(default_factory=dict)


@dataclass
class CompositionResult:
    """Result of one composition turn."""

    response: str
    character_id: str
    turn_id: UUID
    token_count: int = 0
    latency_ms: int = 0
    blocked_by_safety: bool = False
    anti_pattern_hits: List[str] = field(default_factory=list)
    composition_trace: Dict[str, Any] = field(default_factory=dict)


# ── Composer Service ─────────────────────────────────────────────


class ComposerService:
    """SS05 Persona Composer — assembles context blocks and generates response.

    Per spec §3 (Architecture), this is the system's main response path.
    All subsystem outputs converge here.

    DI pattern: all dependencies passed via constructor.

    Usage:
        composer = ComposerService(
            soul_registry=registry,
            memory_service=memory_svc,
            emotion_service=emotion_svc,
            model_router=router,
        )
        result = await composer.compose(context)
    """

    # Token budget allocation per layer (percentages)
    DEFAULT_BUDGET = {
        "soul_anchor": 0.20,
        "memory_context": 0.25,
        "emotion_context": 0.15,
        "relationship": 0.10,
        "inner_state": 0.10,
        "hard_rules": 0.05,
        "conversation": 0.15,
    }

    def __init__(
        self,
        *,
        soul_registry: SoulRegistry,
        memory_service: Optional[Any] = None,
        emotion_service: Optional[Any] = None,
        relationship_service: Optional[Any] = None,
        inner_state_service: Optional[Any] = None,
        model_router: Optional[Any] = None,
        replay_recorder: Optional[Any] = None,
        token_budget: int = 4000,
    ):
        """Initialize ComposerService with injected dependencies.

        Args:
            soul_registry: SoulRegistry for character specs
            memory_service: Optional MemoryService for memory context
            emotion_service: Optional EmotionService for emotion context
            relationship_service: Optional SS04 service
            inner_state_service: Optional SS06 service
            model_router: Optional ModelRouter for LLM calls
            replay_recorder: Optional ReplayRecorder for persisting prompt bundles
            token_budget: Total token budget for system prompt (default 4000)
        """
        self._soul_registry = soul_registry
        self._memory_service = memory_service
        self._emotion_service = emotion_service
        self._relationship_service = relationship_service
        self._inner_state_service = inner_state_service
        self._model_router = model_router
        self._replay_recorder = replay_recorder
        self._token_budget = token_budget

    @invariant("inv-c-1.no-hard-never-leak", severity="WARN", subsystem="ss05")
    async def compose(
        self,
        ctx: CompositionContext,
        *,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
    ) -> CompositionResult:
        """Compose and generate a response for one turn.

        Pipeline:
        1. Load Soul Spec and build Anchor context block
        2. Collect context blocks from memory, emotion, relationship, inner state
        3. Build system prompt with token budget allocation
        4. Call LLM via ModelRouter
        5. Post-filter response against anti-patterns

        Args:
            ctx: CompositionContext with user_id, character_id, turn_id
            user_message: Raw user message text
            conversation_history: Optional conversation history for context
            temperature: LLM temperature (default 0.7)

        Returns:
            CompositionResult with response text and metadata
        """
        import time as _time

        t_start = _time.monotonic()
        p = TurnProfiler.current()

        # 1. Load Soul Spec
        soul_spec = self._soul_registry.get_soul(ctx.character_id)
        anchor_block = self._build_anchor_block(soul_spec)

        # 2. Collect context from subsystems
        with p.span("retriever"):
            memory_block = await self._build_memory_block(ctx)
        emotion_block = await self._build_emotion_block(ctx)
        relationship_block = await self._build_relationship_block(ctx)
        inner_state_block = await self._build_inner_state_block(ctx)

        # 3. Build system prompt
        with p.span("composer"):
            system_prompt = self._build_system_prompt(
                anchor=anchor_block,
                memory=memory_block,
                emotion=emotion_block,
                relationship=relationship_block,
                inner_state=inner_state_block,
                soul_spec=soul_spec,
            )

            # Count layers and tokens built (for profiling)
            n_layers = 0
            if anchor_block.identity_anchor_text:
                n_layers += 1
            if memory_block.retrieved_memories:
                n_layers += 1
            if emotion_block.emotion_summary:
                n_layers += 1
            if (
                relationship_block.relationship_phase
                and relationship_block.relationship_phase != "stranger"
            ):
                n_layers += 1
            if inner_state_block.internal_monologue:
                n_layers += 1
            prompt_tokens = len(system_prompt.split())
            p.annotate(layers=n_layers, prompt_tokens_built=prompt_tokens)

        # 4. Call LLM
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        with p.span("model_router"):
            if self._model_router is None:
                response_text = self._fallback_response(ctx.character_id, user_message)
            else:
                response_text = await self._model_router.call_main(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=ctx.max_tokens,
                    agent_name=f"Composer.{ctx.character_id}",
                )

        # 5. Post-filter
        with p.span("anti_pattern"):
            anti_pattern_hits = self._post_filter(response_text, anchor_block)
            total_filters = len(anchor_block.hard_never) + len(anchor_block.anti_patterns)
            p.annotate(filters_applied=total_filters, hits=len(anti_pattern_hits))

        latency_ms = int((_time.monotonic() - t_start) * 1000)

        # 6. Record replay snapshot (best-effort, non-blocking)
        await self._record_replay_snapshot(
            ctx=ctx,
            user_message=user_message,
            system_prompt=system_prompt,
            messages=messages,
            anchor=anchor_block,
            memory=memory_block,
            emotion=emotion_block,
            relationship=relationship_block,
            inner_state=inner_state_block,
            raw_response=response_text,
            anti_pattern_hits=anti_pattern_hits,
            latency_ms=latency_ms,
        )

        return CompositionResult(
            response=response_text,
            character_id=ctx.character_id,
            turn_id=ctx.turn_id,
            token_count=len(response_text.split()),
            latency_ms=latency_ms,
            anti_pattern_hits=anti_pattern_hits,
            composition_trace={
                "anchor_mode": anchor_block.anchor_mode,
                "memory_count": len(memory_block.retrieved_memories),
                "emotion_summary": emotion_block.emotion_summary,
                "relationship_phase": relationship_block.relationship_phase,
            },
        )

    async def compose_stream(
        self,
        ctx: CompositionContext,
        *,
        user_message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.7,
    ) -> AsyncGenerator[str, None]:
        """Streaming variant of compose().

        Yields response text chunks as they arrive from the LLM.
        Post-filter is deferred until the full response is assembled.
        """
        soul_spec = self._soul_registry.get_soul(ctx.character_id)
        anchor_block = self._build_anchor_block(soul_spec)

        memory_block = await self._build_memory_block(ctx)
        emotion_block = await self._build_emotion_block(ctx)
        relationship_block = await self._build_relationship_block(ctx)
        inner_state_block = await self._build_inner_state_block(ctx)

        system_prompt = self._build_system_prompt(
            anchor=anchor_block,
            memory=memory_block,
            emotion=emotion_block,
            relationship=relationship_block,
            inner_state=inner_state_block,
            soul_spec=soul_spec,
        )

        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        if self._model_router is None:
            yield self._fallback_response(ctx.character_id, user_message)
            return

        full_response = ""
        async for chunk in self._model_router.stream_main(
            messages=messages,
            temperature=temperature,
            max_tokens=ctx.max_tokens,
            agent_name=f"Composer.{ctx.character_id}",
        ):
            full_response += chunk
            yield chunk

        # Post-filter: log anti-pattern hits (can't block streaming)
        hits = self._post_filter(full_response, anchor_block)
        if hits:
            logger.warning(
                "composer_anti_pattern_detected",
                character_id=ctx.character_id,
                turn_id=str(ctx.turn_id),
                hits=hits,
            )

    # ── Context Block Builders ────────────────────────────────

    def _build_anchor_block(self, soul_spec: SoulSpec) -> AnchorContextBlock:
        """Build anchor context block from SoulSpec."""
        anchor = soul_spec.identity_anchor
        voice_dna_raw = getattr(anchor, "voice_dna", [])
        voice_dna = [
            {"pattern": vd.pattern, "frequency": getattr(vd, "frequency", "medium")}
            if hasattr(vd, "pattern")
            else (vd if isinstance(vd, dict) else {"pattern": str(vd)})
            for vd in voice_dna_raw
        ]
        anti_pat = getattr(anchor, "anti_patterns", None)
        hard_never = getattr(anti_pat, "hard_never", []) if anti_pat else []
        anti_patterns = getattr(anti_pat, "soft_never", []) if anti_pat else []

        core_wound = getattr(anchor, "core_wound", None)
        core_desire = getattr(anchor, "core_desire", None)

        return AnchorContextBlock(
            archetype=getattr(anchor, "archetype", ""),
            core_wound_essence=getattr(core_wound, "essence", "") if core_wound else "",
            core_desire_surface=getattr(core_desire, "surface", "") if core_desire else "",
            identity_anchor_text=getattr(anchor, "identity_text", ""),
            voice_dna=voice_dna if isinstance(voice_dna, list) else [],
            hard_never=hard_never if isinstance(hard_never, list) else [],
            anti_patterns=anti_patterns if isinstance(anti_patterns, list) else [],
            anchor_mode="standard",
        )

    async def _build_memory_block(self, ctx: CompositionContext) -> MemoryContextBlock:
        """Build memory context block from MemoryService."""
        if self._memory_service is None:
            return MemoryContextBlock()
        try:
            from heart.ss02_memory.service import QueryContext

            qctx = QueryContext(
                current_message="",
                recent_turns=[],
                session_id=ctx.turn_id,
                user_id=ctx.user_id,
                character_id=ctx.character_id,
            )
            result = await self._memory_service.retrieve(
                user_id=ctx.user_id,
                character_id=ctx.character_id,
                query_context=qctx,
            )
            return MemoryContextBlock(
                retrieved_memories=[
                    {
                        "text": m.reconstructed_text,
                        "type": m.memory_type,
                        "score": m.score,
                        "uncertainty": m.uncertainty_level,
                    }
                    for m in result.memories
                ],
                recently_forgotten_hints=[h.hint_text for h in result.recently_forgotten_hints],
                l4_included=result.l4_included,
            )
        except Exception:
            logger.exception("composer_memory_block_failed")
            return MemoryContextBlock()

    async def _build_emotion_block(self, ctx: CompositionContext) -> EmotionContextBlock:
        """Build emotion context block from EmotionService."""
        if self._emotion_service is None:
            return EmotionContextBlock()
        try:
            ecb = self._emotion_service.get_context_block(
                user_id=ctx.user_id,
                character_id=ctx.character_id,
            )
            return EmotionContextBlock(
                emotion_summary=ecb.get("emotion_summary", ""),
                vad_valence=ecb.get("vad", {}).get("valence", 0.0),
                vad_arousal=ecb.get("vad", {}).get("arousal", 0.3),
                vad_dominance=ecb.get("vad", {}).get("dominance", 0.5),
                active_emotions=ecb.get("active_emotions", []),
                mood_descriptor=ecb.get("mood_descriptor", ""),
                energy_descriptor=ecb.get("energy_descriptor", ""),
                pending_repairs_summary=ecb.get("pending_repairs_summary"),
                expression_guidelines=ecb.get("expression_guidelines"),
            )
        except Exception:
            logger.exception("composer_emotion_block_failed")
            return EmotionContextBlock()

    async def _build_relationship_block(self, ctx: CompositionContext) -> RelationshipContextBlock:
        """Build relationship context block from SS04."""
        if self._relationship_service is None:
            return RelationshipContextBlock()
        try:
            phase_info = self._relationship_service.get_current_phase(
                user_id=ctx.user_id, character_id=ctx.character_id
            )
            return RelationshipContextBlock(
                relationship_phase=phase_info.get("phase", "stranger"),
                trust_level=phase_info.get("trust_level", 0.0),
                attachment_style=phase_info.get("attachment_style", ""),
                behavioral_envelope=phase_info.get("behavioral_envelope", {}),
            )
        except Exception:
            logger.exception("composer_relationship_block_failed")
            return RelationshipContextBlock()

    async def _build_inner_state_block(self, ctx: CompositionContext) -> InnerStateContextBlock:
        """Build inner state context block from SS06."""
        if self._inner_state_service is None:
            return InnerStateContextBlock()
        try:
            state = self._inner_state_service.get_inner_state(
                user_id=ctx.user_id, character_id=ctx.character_id
            )
            return InnerStateContextBlock(
                internal_monologue=state.get("internal_monologue", ""),
                recent_reflections=state.get("recent_reflections", []),
                current_need=state.get("current_need", ""),
            )
        except Exception:
            logger.exception("composer_inner_state_block_failed")
            return InnerStateContextBlock()

    # ── Prompt Builder ────────────────────────────────────────

    def _build_system_prompt(
        self,
        anchor: AnchorContextBlock,
        memory: MemoryContextBlock,
        emotion: EmotionContextBlock,
        relationship: RelationshipContextBlock,
        inner_state: InnerStateContextBlock,
        soul_spec: SoulSpec,
    ) -> str:
        """Build the system prompt from all context blocks.

        Layered structure prioritized by token budget:
        1. Identity Anchor (highest priority, always included)
        2. Hard Constraints (hard_never + anti_patterns)
        3. Emotion Context (current state)
        4. Memory Context (retrieved memories)
        5. Relationship Context (phase cues)
        6. Inner State (internal monologue)
        """
        # Use AnchorInjector's attribute-based access (Pydantic model, not dict)
        dn = soul_spec.display_name
        display_name = dn.zh or dn.ja or dn.en or soul_spec.character_id

        parts = []

        # Layer 1: Identity Anchor (always included)
        parts.append(f"你是 {display_name}。")
        if anchor.archetype:
            parts.append(f"角色原型：{anchor.archetype}")
        if anchor.core_wound_essence:
            parts.append(f"核心创伤：{anchor.core_wound_essence}")
        if anchor.core_desire_surface:
            parts.append(f"核心渴望：{anchor.core_desire_surface}")
        if anchor.identity_anchor_text:
            parts.append(anchor.identity_anchor_text)

        # Layer 2: Voice DNA
        if anchor.voice_dna:
            vd_lines = []
            for vd in anchor.voice_dna:
                pattern = vd.get("pattern", "") if isinstance(vd, dict) else str(vd)
                if pattern:
                    vd_lines.append(f"- {pattern}")
            if vd_lines:
                parts.append("\n表达风格：\n" + "\n".join(vd_lines))

        # Layer 3: Hard Constraints (hard_never rules)
        if anchor.hard_never:
            rules = "\n".join(f"- 绝对不：{rule}" for rule in anchor.hard_never)
            parts.append(f"\n必须遵守的规则：\n{rules}")

        # Layer 4: Anti-patterns (things to avoid)
        if anchor.anti_patterns:
            ap_lines = "\n".join(f"- 避免：{ap}" for ap in anchor.anti_patterns)
            parts.append(f"\n避免的行为：\n{ap_lines}")

        # Layer 5: Emotion Context
        if emotion and emotion.emotion_summary:
            parts.append(f"\n当前情绪状态：{emotion.emotion_summary}")
        if emotion.mood_descriptor and emotion.mood_descriptor != "平静":
            parts.append(f"心境：{emotion.mood_descriptor}")
        if emotion.expression_guidelines:
            parts.append("情感表达指南：" + "；".join(emotion.expression_guidelines))

        # Layer 6: Relationship Context
        if (
            relationship
            and relationship.relationship_phase
            and relationship.relationship_phase != "stranger"
        ):
            parts.append(f"与用户的关系阶段：{relationship.relationship_phase}")

        # Layer 7: Memory Context
        if memory.retrieved_memories:
            mem_lines = []
            for mem in memory.retrieved_memories[:3]:
                text = mem.get("text", "")
                if text:
                    mem_lines.append(f"- {text}")
            if mem_lines:
                parts.append("\n关于用户的记忆：\n" + "\n".join(mem_lines))

        if memory.recently_forgotten_hints:
            hints = "；".join(memory.recently_forgotten_hints[:2])
            parts.append(f"模糊的印象：{hints}")

        # Layer 8: Inner State (lowest priority)
        if inner_state.internal_monologue:
            parts.append(f"\n内心活动：{inner_state.internal_monologue}")

        # Layer 9: Response directive
        parts.append("\n请自然地回应用户。保持角色一致性。语气、词汇、情感表达应符合上述设定。")

        return "\n".join(parts)

    # ── Post-filter ────────────────────────────────────────────

    def _post_filter(self, response: str, anchor: AnchorContextBlock) -> List[str]:
        """Check response against anti-patterns and hard_never rules.

        Returns list of matched anti-patterns.
        """
        hits: List[str] = []

        for rule in anchor.hard_never:
            if rule.lower() in response.lower():
                hits.append(f"hard_never:{rule}")

        for pattern in anchor.anti_patterns:
            if pattern.lower() in response.lower():
                hits.append(f"anti_pattern:{pattern}")

        return hits

    def _fallback_response(self, character_id: str, user_message: str) -> str:
        """Fallback response when ModelRouter is unavailable."""
        logger.warning("composer_fallback_response", character_id=character_id)
        return f"[{character_id}] 收到你的消息了。我在这里。"

    # ── Replay snapshot recording ───────────────────────────────

    def _build_layers_dict(
        self,
        anchor: AnchorContextBlock,
        memory: MemoryContextBlock,
        emotion: EmotionContextBlock,
        relationship: RelationshipContextBlock,
        inner_state: InnerStateContextBlock,
    ) -> Dict[str, Any]:
        """Build a dict of composer layers for replay recording.

        Each entry mirrors what _build_system_prompt assembles but as
        structured LayerSnapshot data instead of a flat prompt string.
        """
        layers = {}

        # Soul (SS01)
        soul_parts = []
        if anchor.archetype:
            soul_parts.append(f"Archetype: {anchor.archetype}")
        if anchor.core_wound_essence:
            soul_parts.append(f"Core wound: {anchor.core_wound_essence}")
        if anchor.core_desire_surface:
            soul_parts.append(f"Core desire: {anchor.core_desire_surface}")
        if anchor.identity_anchor_text:
            soul_parts.append(anchor.identity_anchor_text)
        if anchor.voice_dna:
            for vd in anchor.voice_dna:
                pattern = vd.get("pattern", "") if isinstance(vd, dict) else str(vd)
                if pattern:
                    soul_parts.append(f"Voice: {pattern}")
        layers["soul"] = {
            "name": "Soul (SS01)",
            "content": "\n".join(soul_parts),
            "token_count": sum(len(p.split()) for p in soul_parts),
            "metadata": {
                "archetype": anchor.archetype,
                "anchor_mode": anchor.anchor_mode,
                "voice_dna_count": len(anchor.voice_dna),
            },
        }

        # Memory (SS02)
        mem_parts = []
        if memory.retrieved_memories:
            for mem in memory.retrieved_memories[:3]:
                text = mem.get("text", "")
                if text:
                    mem_parts.append(
                        f"[{mem.get('type', 'mem')} score={mem.get('score', 0):.2f}] {text}"
                    )
        if memory.recently_forgotten_hints:
            mem_parts.append("Fuzzy: " + "; ".join(memory.recently_forgotten_hints[:2]))
        layers["memory"] = {
            "name": "Memory (SS02)",
            "content": "\n".join(mem_parts),
            "token_count": sum(len(p.split()) for p in mem_parts),
            "metadata": {
                "retrieved_count": len(memory.retrieved_memories),
                "l4_included": memory.l4_included,
                "forgotten_hints": len(memory.recently_forgotten_hints),
            },
        }

        # Emotion (SS03)
        emo_parts = []
        if emotion.emotion_summary:
            emo_parts.append(f"Summary: {emotion.emotion_summary}")
        emo_parts.append(
            f"VAD: V={emotion.vad_valence:+.2f} A={emotion.vad_arousal:.2f} D={emotion.vad_dominance:.2f}"
        )
        if emotion.mood_descriptor:
            emo_parts.append(f"Mood: {emotion.mood_descriptor}")
        if emotion.expression_guidelines:
            emo_parts.append("Guidelines: " + "; ".join(emotion.expression_guidelines))
        layers["emotion"] = {
            "name": "Emotion (SS03)",
            "content": "\n".join(emo_parts),
            "token_count": sum(len(p.split()) for p in emo_parts),
            "metadata": {
                "vad_valence": emotion.vad_valence,
                "vad_arousal": emotion.vad_arousal,
                "vad_dominance": emotion.vad_dominance,
                "active_emotions_count": len(emotion.active_emotions),
            },
        }

        # Relationship (SS04)
        rel_parts = []
        if relationship.relationship_phase:
            rel_parts.append(f"Phase: {relationship.relationship_phase}")
        if relationship.trust_level:
            rel_parts.append(f"Trust: {relationship.trust_level:.2f}")
        if relationship.attachment_style:
            rel_parts.append(f"Attachment: {relationship.attachment_style}")
        if relationship.behavioral_envelope:
            rel_parts.append(f"Envelope: {relationship.behavioral_envelope}")
        layers["relationship"] = {
            "name": "Relationship (SS04)",
            "content": "\n".join(rel_parts),
            "token_count": sum(len(p.split()) for p in rel_parts),
            "metadata": {
                "phase": relationship.relationship_phase,
                "trust_level": relationship.trust_level,
                "attachment_style": relationship.attachment_style,
            },
        }

        # Inner State (SS06)
        is_parts = []
        if inner_state.internal_monologue:
            is_parts.append(f"Monologue: {inner_state.internal_monologue}")
        if inner_state.recent_reflections:
            for ref in inner_state.recent_reflections[:3]:
                is_parts.append(f"Reflection: {ref}")
        if inner_state.current_need:
            is_parts.append(f"Need: {inner_state.current_need}")
        layers["inner_state"] = {
            "name": "Inner State (SS06)",
            "content": "\n".join(is_parts),
            "token_count": sum(len(p.split()) for p in is_parts),
            "metadata": {
                "reflection_count": len(inner_state.recent_reflections),
                "has_monologue": bool(inner_state.internal_monologue),
            },
        }

        # Director / Hard Constraints
        dir_parts = []
        if anchor.hard_never:
            dir_parts.append("Hard Never:")
            for rule in anchor.hard_never:
                dir_parts.append(f"  - {rule}")
        if anchor.anti_patterns:
            dir_parts.append("Anti-Patterns:")
            for ap in anchor.anti_patterns:
                dir_parts.append(f"  - {ap}")
        layers["director"] = {
            "name": "Director / Hard Constraints",
            "content": "\n".join(dir_parts) if dir_parts else "(none)",
            "token_count": sum(len(p.split()) for p in dir_parts),
            "metadata": {
                "hard_never_count": len(anchor.hard_never),
                "anti_pattern_count": len(anchor.anti_patterns),
            },
        }

        return layers

    async def _record_replay_snapshot(
        self,
        ctx: CompositionContext,
        user_message: str,
        system_prompt: str,
        messages: List[Dict[str, str]],
        anchor: AnchorContextBlock,
        memory: MemoryContextBlock,
        emotion: EmotionContextBlock,
        relationship: RelationshipContextBlock,
        inner_state: InnerStateContextBlock,
        raw_response: str,
        anti_pattern_hits: List[str],
        latency_ms: int,
    ) -> None:
        """Record a replay snapshot if a ReplayRecorder is configured."""
        if self._replay_recorder is None:
            return

        try:
            from heart.replay.bundle_dump import LayerSnapshot, PromptBundle

            session_id = getattr(ctx, "session_id", None) or ctx.turn_id

            layers_dict = self._build_layers_dict(
                anchor, memory, emotion, relationship, inner_state
            )
            layers = {k: LayerSnapshot(**v) for k, v in layers_dict.items()}

            model_name = (
                getattr(
                    getattr(self._model_router, "config", None),
                    "get_main_model",
                    lambda: type("M", (), {"name": "deepseek-reasoner"})(),
                )().name
                if self._model_router
                else "fallback"
            )

            bundle = PromptBundle(
                turn_id=ctx.turn_id,
                session_id=session_id,
                user_id=str(ctx.user_id),
                character_id=ctx.character_id,
                system_prompt=system_prompt,
                messages=messages,
                layers=layers,
                raw_response=raw_response,
                final_response=raw_response,
                latency_ms=latency_ms,
                model_name=model_name,
                token_count=len(raw_response.split()),
                anti_pattern_hits=anti_pattern_hits,
                blocked=len(anti_pattern_hits) > 0,
            )
            await self._replay_recorder.record(bundle)
        except Exception as e:
            logger.warning("replay_snapshot_record_failed", error=str(e))

    # ── Support: context block assembly from raw data ──────────

    def build_context(
        self,
        *,
        user_id: UUID,
        character_id: str,
        turn_id: UUID,
        anchor: Optional[AnchorContextBlock] = None,
        memory: Optional[MemoryContextBlock] = None,
        emotion: Optional[EmotionContextBlock] = None,
        relationship: Optional[RelationshipContextBlock] = None,
        inner_state: Optional[InnerStateContextBlock] = None,
        max_tokens: int = 2000,
    ) -> CompositionContext:
        """Build a CompositionContext from individual blocks."""
        return CompositionContext(
            user_id=user_id,
            character_id=character_id,
            turn_id=turn_id,
            anchor=anchor or AnchorContextBlock(),
            memory=memory or MemoryContextBlock(),
            emotion=emotion or EmotionContextBlock(),
            relationship=relationship or RelationshipContextBlock(),
            inner_state=inner_state or InnerStateContextBlock(),
            max_tokens=max_tokens,
        )
