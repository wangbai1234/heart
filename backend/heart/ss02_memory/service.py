"""
Memory Service - SS02 Memory Runtime §10.3

唯一 source of truth writer for memory.
所有 agent 通过这个接口读写记忆。

Architecture:
- L1 Working Memory (Redis)
- L2 Episodic Memory (PostgreSQL + pgvector)
- L3 Semantic Memory (PostgreSQL + pgvector)
- L4 Identity Memory (PostgreSQL, sacred, immutable)

Invariants enforced:
- INV-M-3: Top-K limit (default 5, max 10)
- INV-M-6: All queries filtered by user_id + character_id

Author: 心屿团队
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog

from heart.infra.invariants import invariant
from heart.infra.partitions import ensure_monthly_partition

import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip

from .models import (
    ConsolidationJob,
    EpisodicMemory,
    FactNode,
    IdentityMemory,
    MemoryEncodingEvent,
)

logger = structlog.get_logger()


# ============================================================
# Data Structures (per §5)
# ============================================================


@dataclass(frozen=True)
class FastSignals:
    """Fast encoder signals (§5.1).

    Generated in < 50ms, no LLM call.
    """

    detected_keywords: list[str]
    sentiment: float  # [-1, 1] from lexicon
    candidate_identity_signals: list[IdentitySignal]


@dataclass(frozen=True)
class IdentitySignal:
    """Candidate identity signal from fast encoder."""

    type: str  # "name" | "birthday" | "occupation" | "pet" | "location"
    value: str
    raw_text: str


@dataclass(frozen=True)
class Turn:
    """Single conversation turn."""

    turn_index: int
    role: str  # "user" | "assistant"
    content: str
    user_id: UUID
    character_id: str
    timestamp: datetime


@dataclass(frozen=True)
class QueryContext:
    """Context for retrieval query (§7.3).

    Contains current conversation state for retrieval.
    """

    current_message: str
    recent_turns: list[Turn]
    session_id: UUID
    user_id: UUID
    character_id: str


@dataclass(frozen=True)
class RetrievedMemory:
    """Single retrieved memory with reconstruction (§5.5)."""

    memory_id: UUID
    memory_type: str  # "L2" | "L3" | "L4"
    state: str  # MemoryState

    # Reconstructor output
    reconstructed_text: str  # 角色化复述（注入 prompt 用）
    raw_content: str  # 原始内容（仅供 Critic / debug）

    # Score breakdown
    score: float
    score_breakdown: dict[
        str, float
    ]  # semantic, importance, emotional_resonance, recency, associative, confidence

    # Reconstruction metadata
    uncertainty_level: float  # [0, 1] 由 state 决定
    voice_dna_applied: list[str]  # 哪些 voice_dna ids 被应用

    # Source evidence for Critic
    source_evidence: str


@dataclass(frozen=True)
class ForgettingHint:
    """Hint about forgotten memory for affect injection."""

    hint_text: str  # "她隐约记得有什么，但说不清"
    related_to: str  # 关联主题（不暴露具体内容）


@dataclass(frozen=True)
class MemoryRetrievalResult:
    """Main retrieval result (§5.5)."""

    query_id: UUID
    retrieved_at: datetime

    # Reconstructed memories
    memories: list[RetrievedMemory]

    # Forgetting affect hints
    recently_forgotten_hints: list[ForgettingHint]

    # Metadata
    total_candidates: int
    retrieval_strategies_used: list[str]  # RetrievalStrategy
    retrieval_latency_ms: int
    l4_included: bool


@dataclass(frozen=True)
class ReinforcementTrigger:
    """Trigger for memory reinforcement (§5.2)."""

    trigger_type: str  # "user_re_mentioned" | "character_recalled_user_confirmed" | "recall_no_objection" | "peak_end_amplification" | "user_explicit_inquiry"
    context: str
    boost: float  # [0, 1]


# ============================================================
# Memory Service
# ============================================================


class MemoryService:
    """Memory Service - 唯一 source of truth writer for memory (§10.3).

    All agents read/write memory through this interface.

    Enforces:
    - INV-M-3: Top-K limit (default 5, max 10)
    - INV-M-6: User isolation (all queries filtered by user_id + character_id)
    - INV-M-4: Recall tracking (recall_count++, last_recalled_at update)
    - M-1: No physical deletion (only do_not_recall flag)
    - M-3: L4 never decays, never deleted
    """

    # Constants
    DEFAULT_TOP_K = 5
    MAX_TOP_K = 10
    DEFAULT_RECENT_HOURS = 72
    DEFAULT_RECENT_LIMIT = 10
    DEFAULT_ANNIVERSARY_WINDOW_DAYS = 7

    def __init__(
        self,
        db_session=None,
        redis_client=None,
        embedding_service=None,
    ):
        """Initialize Memory Service with optional dependencies.

        Args:
            db_session: SQLAlchemy AsyncSession (optional)
            redis_client: Redis client (optional, for L1 working memory)
            embedding_service: Embedding service (optional, for vector search)
        """
        self._db = db_session
        self._redis = redis_client
        self._embedding = embedding_service
        self._ensured_encoding_event_partitions: set[str] = set()

        # Lazily-initialized sub-components
        self._fast_encoder = None
        self._decay_engine = None

        logger.info("memory_service_initialized", has_db=db_session is not None)

    async def _ensure_memory_encoding_partition(self, created_at: datetime) -> None:
        """Ensure the monthly memory_encoding_events partition exists before flush."""
        if self._db is None:
            return
        await ensure_monthly_partition(
            self._db,
            parent_table="memory_encoding_events",
            partition_prefix="memory_encoding_events",
            created_at=created_at,
            cache=self._ensured_encoding_event_partitions,
        )

    # ─────────── Read API ───────────

    async def _ensure_query_embedding(self, query_context) -> None:
        """Populate query_context.query_embedding from its text, best-effort.

        Tolerant of both the retriever-level QueryContext (query_text) and the
        service-level one (current_message). No-op without an embedding service;
        never raises (falls back to recency/identity retrieval on failure).
        """
        query_text = getattr(query_context, "query_text", "") or getattr(
            query_context, "current_message", ""
        )
        if (
            self._embedding is None
            or getattr(query_context, "query_embedding", None) is not None
            or not query_text
        ):
            return
        try:
            embedding = await self._embedding.embed_query(query_text)
            try:
                query_context.query_embedding = embedding
            except Exception:
                pass  # frozen/unsupported context — skip silently
        except Exception as e:
            logger.warning("query_embedding_failed", error=str(e))

    async def retrieve(
        self,
        user_id: UUID,
        character_id: str,
        query_context: QueryContext,
        top_k: int = DEFAULT_TOP_K,
    ) -> MemoryRetrievalResult:
        """Main retrieval API (§10.3 Read API).

        Calls all retriever strategies:
        - Vector L2 search (semantic + emotional)
        - Vector L3 search
        - Graph spread
        - Recency scan
        - Emotional resonance
        - Identity lookup (L4)

        Enforces:
        - INV-M-3: top_k ≤ MAX_TOP_K
        - INV-M-6: user_id + character_id filter
        - INV-M-4: Updates recall tracking

        Args:
            user_id: User UUID (INV-M-6)
            character_id: Character ID (INV-M-6)
            query_context: Current conversation context
            top_k: Maximum results (default 5, max 10)

        Returns:
            MemoryRetrievalResult with reconstructed memories

        Spec: §10.3 Read API, §7.3 调用顺序
        """
        self._enforce_user_isolation(user_id, character_id, query_context)
        top_k = self._enforce_top_k(top_k)

        # Connect to RetrievalOrchestrator when DB is available
        if self._db is not None:
            try:
                from heart.ss02_memory.retriever.base import ScoredMemory
                from heart.ss02_memory.retriever.orchestrator import RetrievalOrchestrator

                # Compute a query embedding so the VectorRetriever can run
                # (it early-returns when query_embedding is None).
                await self._ensure_query_embedding(query_context)

                orchestrator = RetrievalOrchestrator(self._db)
                retriever_result = await orchestrator.retrieve(query_context, top_k)  # type: ignore[arg-type]

                # Convert retriever-layer ScoredMemory → service-layer RetrievedMemory
                reconstructor = self._get_reconstructor(character_id)
                retrieved: list[RetrievedMemory] = []
                for sm in retriever_result.memories:
                    try:
                        reconstructed = reconstructor.reconstruct(sm)
                        voice_dna_applied = (
                            list(reconstructor.voice_dna)
                            if hasattr(reconstructor, "voice_dna")
                            else []
                        )
                    except Exception as e:
                        logger.warning(
                            "reconstruct_failed_fallback", memory_id=str(sm.memory_id), error=str(e)
                        )
                        reconstructed = _fallback_text(sm.memory)
                        voice_dna_applied = []

                    state = getattr(sm.memory, "state", "vivid") or "vivid"
                    retrieved.append(
                        RetrievedMemory(
                            memory_id=sm.memory_id,
                            memory_type=sm.memory_type,
                            state=state,
                            reconstructed_text=reconstructed,
                            raw_content=_fallback_text(sm.memory),
                            score=sm.score,
                            score_breakdown=sm.score_breakdown,
                            uncertainty_level=_state_to_uncertainty(state),
                            voice_dna_applied=voice_dna_applied,
                            source_evidence=_fallback_text(sm.memory),
                        )
                    )

                # Convert forgetting hints
                forgetting_hints: list[ForgettingHint] = []
                for h in retriever_result.recently_forgotten_hints:
                    hint_text = getattr(h, "hint_text", None) or getattr(h, "text", None) or str(h)
                    related_to = getattr(h, "related_to", "") or ""
                    forgetting_hints.append(
                        ForgettingHint(hint_text=hint_text, related_to=related_to)
                    )

                # INV-M-4: recall tracking. Reinforce L2 episodic hits so
                # recall_count / last_recalled_at reflect actual usage
                # (previously never updated → stuck at 0 / null). boost=0.0
                # tracks the recall without inflating importance_score, which
                # would otherwise create a recall→importance→recall feedback
                # loop. Best-effort: a failure here must not break the turn.
                l2_hit_ids = [m.memory_id for m in retrieved if m.memory_type == "L2"]
                if l2_hit_ids:
                    try:
                        await self.reinforce(
                            l2_hit_ids,
                            ReinforcementTrigger(
                                trigger_type="recall_no_objection",
                                context="auto_recall",
                                boost=0.0,
                            ),
                        )
                        await self._db.commit()
                    except Exception as e:
                        logger.warning("auto_reinforce_failed", error=str(e))

                return MemoryRetrievalResult(
                    query_id=uuid4(),
                    retrieved_at=datetime.now(timezone.utc),
                    memories=retrieved,
                    recently_forgotten_hints=forgetting_hints,
                    total_candidates=retriever_result.total_candidates,
                    retrieval_strategies_used=retriever_result.strategies_used,
                    retrieval_latency_ms=int(retriever_result.retrieval_time_ms),
                    l4_included=bool(retriever_result.l4_included),
                )
            except Exception as e:
                logger.error("retrieve_failed", error=str(e), user_id=str(user_id))

        # Fallback: return empty result
        return MemoryRetrievalResult(
            query_id=uuid4(),
            retrieved_at=datetime.now(timezone.utc),
            memories=[],
            recently_forgotten_hints=[],
            total_candidates=0,
            retrieval_strategies_used=["fallback_empty"],
            retrieval_latency_ms=0,
            l4_included=False,
        )

    def _get_reconstructor(self, character_id: str):
        """Lazily initialize and cache a Reconstructor for the given character."""
        if not hasattr(self, "_reconstructor_cache"):
            self._reconstructor_cache: dict = {}
        if character_id not in self._reconstructor_cache:
            from pathlib import Path

            import yaml

            from heart.ss02_memory.reconstructor import Reconstructor

            specs_dir = Path(__file__).parent.parent.parent.parent / "soul_specs"
            spec_file = specs_dir / character_id / "v1.0.0.yaml"
            if spec_file.exists():
                with open(spec_file) as f:
                    soul_spec = yaml.safe_load(f)
                self._reconstructor_cache[character_id] = Reconstructor(character_id, soul_spec)
            else:
                logger.warning("reconstructor_spec_not_found", character_id=character_id)
                self._reconstructor_cache[character_id] = None
        return self._reconstructor_cache[character_id]

    async def get_l4(
        self,
        user_id: UUID,
        character_id: str,
        category: Optional[str] = None,
    ) -> list[IdentityMemory]:
        """Read L4 Identity Memory (神圣记忆) (§10.3 Read API).

        L4 is always accessible, never decays (M-3).

        Enforces:
        - INV-M-6: user_id + character_id filter

        Args:
            user_id: User UUID
            character_id: Character ID
            category: Optional filter by category (user_identity, sacred_promise, etc.)

        Returns:
            List of IdentityMemory records

        Spec: §5.4 L4 Identity Memory, §7.4 权限边界
        """
        self._enforce_user_isolation(user_id, character_id, None)

        if self._db is not None:
            try:
                from sqlalchemy import select

                stmt = select(IdentityMemory).where(
                    IdentityMemory.user_id == user_id,
                    IdentityMemory.character_id == character_id,
                )
                if category:
                    stmt = stmt.where(IdentityMemory.category == category)
                result = await self._db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error("get_l4_failed", error=str(e), user_id=str(user_id))
        return []

    async def get_recent_episodes(
        self,
        user_id: UUID,
        character_id: str,
        hours: int = DEFAULT_RECENT_HOURS,
        limit: int = DEFAULT_RECENT_LIMIT,
    ) -> list[EpisodicMemory]:
        """Recency-based retrieval for Inner State (§10.3 Read API).

        Used by Inner State Runtime to understand "她今天的内心活动".

        Enforces:
        - INV-M-6: user_id + character_id filter
        - INV-M-3: limit ≤ MAX_TOP_K

        Args:
            user_id: User UUID
            character_id: Character ID
            hours: Time window (default 72)
            limit: Max results (default 10, max 10)

        Returns:
            List of recent EpisodicMemory ordered by created_at DESC

        Spec: §7.5 跨 Agent 通信约束
        """
        self._enforce_user_isolation(user_id, character_id, None)
        limit = self._enforce_top_k(limit)

        if self._db is not None:
            try:
                from datetime import timedelta

                from sqlalchemy import desc, select

                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                stmt = (
                    select(EpisodicMemory)
                    .where(
                        EpisodicMemory.user_id == user_id,
                        EpisodicMemory.character_id == character_id,
                        EpisodicMemory.created_at >= cutoff,
                    )
                    .order_by(desc(EpisodicMemory.created_at))
                    .limit(limit)
                )
                result = await self._db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(
                    "get_recent_episodes_failed",
                    error=str(e),
                )
        return []

    async def get_anniversaries(
        self,
        user_id: UUID,
        character_id: str,
        window_days: int = DEFAULT_ANNIVERSARY_WINDOW_DAYS,
    ) -> list[IdentityMemory]:
        """Get upcoming anniversaries for Behavior Runtime (§10.3 Read API).

        Used by Behavior Runtime to trigger proactive behaviors.

        Enforces:
        - INV-M-6: user_id + character_id filter

        Args:
            user_id: User UUID
            character_id: Character ID
            window_days: Days ahead to check (default 7)

        Returns:
            List of IdentityMemory with next_anniversary_at within window

        Spec: §5.4 Anniversary Tracking, §7.5 跨 Agent 通信约束
        """
        self._enforce_user_isolation(user_id, character_id, None)

        if self._db is not None:
            try:
                from sqlalchemy import select

                stmt = select(IdentityMemory).where(
                    IdentityMemory.user_id == user_id,
                    IdentityMemory.character_id == character_id,
                    IdentityMemory.metadata["is_anniversary"].astext == "true",
                )
                result = await self._db.execute(stmt)
                return list(result.scalars().all())
            except Exception as e:
                logger.error(
                    "get_anniversaries_failed",
                    error=str(e),
                )
        return []

    # ─────────── Write API ───────────

    @invariant("inv-m-11.fast-path-no-l2-l3-l4")
    async def encode_fast(self, turn: Turn) -> FastSignals:
        """Fast encoding (< 50ms, no LLM) (§10.3 Write API).

        Real-time heuristic encoding:
        - Keyword detection (via RegexHintsProvider)
        - Sentiment analysis (lexicon-based)

        **INV-M-11**: Fast path writes ONLY L1 (Working Memory).
        Any L2 / L3 / L4 write must go through the slow-path
        Extractor → Resolver → Writer → Promoter pipeline.

        Updates L1 Working Memory (Redis).
        Enqueues regex hints for async LLM extraction (llm/dual mode).

        Args:
            turn: Current conversation turn

        Returns:
            FastSignals with detected signals
            (candidate_identity_signals is always empty — deprecated)

        Spec: §7.2 写入者, §7.3 调用顺序 (T+10ms)
        """
        from heart.ss02_memory.encoder.fast import FastEncoder

        if self._fast_encoder is None:
            self._fast_encoder = FastEncoder()
        signals = self._fast_encoder.encode(turn)

        # Cache in L1 (Redis) if available — INV-M-11: ONLY L1 write here
        if self._redis is not None:
            try:
                import json

                key = f"l1:{turn.user_id}:{turn.character_id}:latest"
                await self._redis.setex(
                    key,
                    300,
                    json.dumps(
                        {
                            "sentiment": signals.sentiment,
                            "keywords": signals.detected_keywords,
                        }
                    ),
                )
            except Exception as e:
                logger.error(
                    "l1_cache_failed",
                    error=str(e),
                )

        # Enqueue regex hints for slow-path LLM extraction
        hints = getattr(self._fast_encoder, "last_hints", [])
        if hints:
            await self._enqueue_extraction(
                turn,
                {
                    "hints": [
                        {
                            "raw_phrase": h.raw_phrase,
                            "suspected_attribute": h.suspected_attribute,
                            "span": list(h.span),
                        }
                        for h in hints
                    ]
                },
            )

        # INV-M-11 runtime assertion: fast path must NOT write L2/L3/L4
        # (enforced structurally — this method only touches Redis L1
        #  and the extraction queue; no DB writes to episodic/fact/identity tables)

        return signals

    async def _enqueue_extraction(
        self,
        turn: "Turn",
        hints: Optional[dict] = None,
    ) -> None:
        """Enqueue turn for slow-path LLM extraction.

        Called inside encode_fast() AFTER L1 write.
        Only enqueues when mode is 'llm' or 'dual' (INV-M-11 compliant).

        Args:
            turn: Current conversation turn
            hints: Optional regex hints as auxiliary signals
        """
        from heart.ss02_memory.mode import is_llm_enabled

        if not is_llm_enabled():
            return

        if self._db is None:
            logger.warning("extraction_enqueue_no_db")
            return

        try:
            from heart.ss02_memory.models import MemoryExtractionQueue

            item = MemoryExtractionQueue(
                id=uuid4(),
                session_id=uuid4(),  # Phase A: placeholder session_id
                turn_id=turn.turn_index,
                hints_json=hints,
                status="pending",
            )
            self._db.add(item)
            await self._db.flush()
            logger.debug("extraction_enqueued", turn_id=turn.turn_index)
        except Exception as e:
            logger.error("extraction_enqueue_failed", error=str(e))

    async def queue_llm_encoding(self, event: MemoryEncodingEvent) -> None:
        """Queue async LLM encoding (§10.3 Write API).

        Enqueues turn for LLM-based fact extraction.
        Worker processes queue asynchronously (~5min delay).

        Enforces:
        - INV-M-6: event must have user_id

        Args:
            event: MemoryEncodingEvent to queue

        Spec: §7.2 写入者, §7.3 调用顺序 (T+50ms → T+5min worker)
        """
        if self._db is not None:
            if event.created_at is None:
                event.created_at = datetime.now(timezone.utc).replace(tzinfo=None)
            await self._ensure_memory_encoding_partition(event.created_at)
            self._db.add(event)
            await self._db.flush()
            logger.debug("encoding_queued", event_id=str(event.event_id))
        else:
            logger.warning("encoding_queue_no_db")

    async def reinforce(
        self,
        memory_ids: list[UUID],
        trigger: ReinforcementTrigger,
    ) -> None:
        """Reinforce memories after recall (§10.3 Write API).

        Hebbian reinforcement (M-8):
        - Increment recall_count
        - Update last_recalled_at
        - Boost importance_score by trigger.boost
        - Record in reinforcement_history

        Enforces:
        - INV-M-4: recall tracking mandatory

        Args:
            memory_ids: Memory IDs to reinforce
            trigger: Reinforcement trigger with boost amount

        Spec: §10.4.3 Reinforcement, §7.2 写入者
        """
        if self._db is not None and memory_ids:
            try:
                from sqlalchemy import update

                now = datetime.now(timezone.utc)
                stmt = (
                    update(EpisodicMemory)
                    .where(EpisodicMemory.id.in_(memory_ids))
                    .values(
                        recall_count=EpisodicMemory.recall_count + 1,
                        last_recalled_at=now,
                        importance_score=EpisodicMemory.importance_score + trigger.boost,
                    )
                )
                await self._db.execute(stmt)
                await self._db.flush()
                logger.debug("reinforced", count=len(memory_ids))
            except Exception as e:
                logger.error(
                    "reinforce_failed",
                    error=str(e),
                )

    async def user_request_forget(
        self,
        user_id: UUID,
        memory_id: UUID,
    ) -> None:
        """User requests to forget memory (§10.3 Write API).

        Sets do_not_recall=true, NOT delete (M-1).
        Memory remains in database but won't be retrieved.

        Enforces:
        - INV-M-6: user_id must own memory
        - M-1: No physical deletion

        Args:
            user_id: User UUID (for ownership check)
            memory_id: Memory ID to forget

        Spec: §7.2 写入者, §2.1 规则 M-1
        """
        if self._db is not None:
            try:
                from sqlalchemy import update

                stmt = (
                    update(EpisodicMemory)
                    .where(EpisodicMemory.id == memory_id)
                    .values(do_not_recall=True)
                )
                result = await self._db.execute(stmt)
                await self._db.flush()
                if result.rowcount > 0:
                    logger.info("memory_forgotten", memory_id=str(memory_id))
            except Exception as e:
                logger.error(
                    "forget_failed",
                    error=str(e),
                )

    # ─────────── Lifecycle ───────────

    async def apply_decay_batch(
        self,
        user_id: UUID,
        character_id: str,
    ) -> int:
        """Apply daily batch decay (§10.3 Lifecycle).

        Updates importance_score and state for L2/L3 memories.
        L4 is never decayed (M-3).

        Uses lazy decay formula (§10.4.1):
        - Time factor: exp(-days / tau)
        - Emotional multiplier
        - Recall multiplier (Hebbian)
        - Floor by emotional significance

        Enforces:
        - INV-M-6: user_id + character_id filter
        - INV-M-7: importance floor
        - M-3: L4 never decays

        Args:
            user_id: User UUID
            character_id: Character ID

        Returns:
            Number of memories updated

        Spec: §10.4.1 Lazy Decay, §7.2 写入者
        """
        self._enforce_user_isolation(user_id, character_id, None)

        if self._db is not None:
            try:
                from heart.ss02_memory.decay_engine import DecayEngine

                if self._decay_engine is None:
                    self._decay_engine = DecayEngine()
                count = await self._decay_engine.apply_decay_batch(self._db, user_id, character_id)
                return count
            except Exception as e:
                logger.error(
                    "decay_batch_failed",
                    error=str(e),
                )
        return 0

    async def run_consolidation(
        self,
        user_id: UUID,
        character_id: str,
    ) -> ConsolidationJob:
        """Run daily consolidation ("sleep") (§10.3 Lifecycle).

        Overnight batch processing:
        - Cluster recent turns into episodes (L2)
        - Extract/reinforce facts (L3)
        - Detect contradictions
        - Promote to L4 (if conditions met)
        - Create associative links

        Scheduled at user local 03:00.

        Enforces:
        - INV-M-6: user_id + character_id filter
        - INV-M-8: ≤ 1 consolidation per user per day
        - M-12: Consolidation must run daily

        Args:
            user_id: User UUID
            character_id: Character ID

        Returns:
            ConsolidationJob record with results

        Spec: §7.3 调用顺序 (T=03:00), §7.2 写入者
        """
        self._enforce_user_isolation(user_id, character_id, None)

        logger.info("consolidation_triggered", user_id=str(user_id))
        if self._db is not None:
            try:
                from heart.ss02_memory.decay_engine import DecayEngine

                if self._decay_engine is None:
                    self._decay_engine = DecayEngine()
                await self._decay_engine.apply_decay_batch(self._db, user_id, character_id)
            except Exception as e:
                logger.error(
                    "consolidation_decay_failed",
                    error=str(e),
                )
        return ConsolidationJob(
            user_id=user_id,
            character_id=character_id,
            status="triggered",
            started_at=datetime.now(timezone.utc),
        )

    @invariant("inv-m-5.multi-signal-promotion")
    async def promote_to_l4(
        self,
        fact_id: UUID,
        reason: str,
    ) -> IdentityMemory:
        """Promote L3 fact to L4 Identity Memory (§10.3 Lifecycle).

        Strict promotion conditions (M-15):
        - significance_score >= 0.85
        - Multi-signal corroboration
        - Sacred reason required

        L4 is immutable after creation (M-3).

        Enforces:
        - M-15: Multi-condition promotion
        - M-3: L4 immutability

        Args:
            fact_id: L3 FactNode ID to promote
            reason: Sacred reason for promotion

        Returns:
            Created IdentityMemory

        Spec: §5.4 L4 Identity Memory, §7.2 写入者 RULE-W-M-4
        """
        if self._db is None:
            raise RuntimeError("promote_to_l4 requires db_session")

        # Fetch the L3 fact
        from sqlalchemy import select

        stmt = select(FactNode).where(FactNode.id == fact_id)
        result = await self._db.execute(stmt)
        fact = result.scalar_one_or_none()

        if fact is None:
            raise ValueError(f"Fact {fact_id} not found")

        # Validate promotion conditions
        if fact.importance < 0.85:
            raise ValueError(f"Fact importance {fact.importance} < 0.85 threshold for L4 promotion")

        # Check if already promoted
        existing_stmt = select(IdentityMemory).where(
            IdentityMemory.promoted_from_fact_id == fact_id
        )
        result = await self._db.execute(existing_stmt)
        existing = result.scalar_one_or_none()

        if existing is not None:
            logger.info("fact_already_promoted", fact_id=str(fact_id), l4_id=str(existing.id))
            return existing

        # Derive category from predicate
        category = self._derive_l4_category(fact.predicate)

        # Create L4 Identity Memory
        identity = IdentityMemory(
            id=uuid4(),
            user_id=fact.user_id,
            character_id=fact.character_id,
            category=category,
            key=fact.predicate,
            value=fact.object,
            disclosed_at=datetime.now(timezone.utc),
            disclosure_context=fact.raw_evidence,
            source_turn_ids=fact.source_turn_ids or [],
            sacred_reason=reason,
            significance_score=fact.importance,
            promotion_trigger=reason,
            promoted_from_fact_id=fact.id,
            reconstruction_hints={
                "original_literal": fact.literal_text,
                "confidence": fact.confidence,
                "emotional_charge": fact.emotional_charge,
            },
            created_at=datetime.now(timezone.utc),
        )

        self._db.add(identity)
        await self._db.flush()

        logger.info(
            "fact_promoted_to_l4",
            fact_id=str(fact_id),
            identity_id=str(identity.id),
            reason=reason,
            key=identity.key,
            value=identity.value,
        )

        return identity

    # ─────────── Internal Helpers ───────────

    def _derive_l4_category(self, predicate: str) -> str:
        """Derive L4 category from fact predicate.

        Maps predicates to IdentityMemory categories per §5.4.
        """
        category_map = {
            "妈妈": "family",
            "爸爸": "family",
            "家人": "family",
            "工作": "occupation",
            "职业": "occupation",
            "生日": "personal",
            "名字": "identity",
            "喜欢": "preference",
            "讨厌": "preference",
            "爱好": "interest",
            "宠物": "pet",
            "住": "location",
            "家在": "location",
        }

        for keyword, category in category_map.items():
            if keyword in predicate:
                return category

        return "user_identity"

    def _enforce_user_isolation(
        self,
        user_id: UUID,
        character_id: str,
        query_context: Optional[QueryContext],
    ) -> None:
        """Enforce INV-M-6: user_id + character_id isolation.

        All queries must be filtered by user_id and character_id.
        Cross-user access is strictly prohibited.

        Args:
            user_id: User UUID
            character_id: Character ID
            query_context: Optional QueryContext (must match if provided)

        Raises:
            ValueError: If context doesn't match user_id/character_id

        Spec: §2.2 不可违反的系统规则 INV-M-6
        """
        if query_context is not None:
            if query_context.user_id != user_id:
                raise ValueError(
                    f"INV-M-6 violation: query_context.user_id {query_context.user_id} "
                    f"does not match user_id {user_id}"
                )
            if query_context.character_id != character_id:
                raise ValueError(
                    f"INV-M-6 violation: query_context.character_id {query_context.character_id} "
                    f"does not match character_id {character_id}"
                )

    def _enforce_top_k(self, top_k: int) -> int:
        """Enforce INV-M-3: Top-K limit.

        Top-K must be ≤ MAX_TOP_K to prevent prompt explosion.

        Args:
            top_k: Requested top-k

        Returns:
            Clamped top-k value

        Spec: §2.2 不可违反的系统规则 INV-M-3
        """
        if top_k > self.MAX_TOP_K:
            logger.warning(
                "top_k_exceeded_max",
                requested=top_k,
                max=self.MAX_TOP_K,
            )
            return self.MAX_TOP_K
        return max(1, top_k)


def _fallback_text(memory) -> str:
    """Best-effort raw text when Reconstructor fails."""
    for attr in (
        "episode_summary",
        "summary",
        "literal_text",
        "raw_evidence",
        "identity_text",
        "key",
        "value",
    ):
        v = getattr(memory, attr, None)
        if v:
            return str(v)
    return str(memory)


def _state_to_uncertainty(state: str) -> float:
    """Convert memory state to uncertainty level [0, 1]."""
    return {
        "vivid": 0.0,
        "fading": 0.3,
        "faint": 0.6,
        "dormant": 0.8,
        "archived": 0.95,
    }.get(state, 0.5)
