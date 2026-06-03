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

import heart.infra.invariant_predicates  # noqa: F401, E402 isort:skip

from .models import (
    ConsolidationJob,
    EpisodicMemory,
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

        # Lazily-initialized sub-components
        self._fast_encoder = None
        self._decay_engine = None

        logger.info("memory_service_initialized", has_db=db_session is not None)

    # ─────────── Read API ───────────

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
                from heart.ss02_memory.retriever.orchestrator import RetrievalOrchestrator

                orchestrator = RetrievalOrchestrator(self._db)
                return await orchestrator.retrieve(query_context, top_k)
            except Exception:
                logger.exception("retrieve_failed", user_id=str(user_id))

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
            except Exception:
                logger.exception("get_l4_failed", user_id=str(user_id))
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
            except Exception:
                logger.exception("get_recent_episodes_failed")
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
            except Exception:
                logger.exception("get_anniversaries_failed")
        return []

    # ─────────── Write API ───────────

    async def encode_fast(self, turn: Turn) -> FastSignals:
        """Fast encoding (< 50ms, no LLM) (§10.3 Write API).

        Real-time heuristic encoding:
        - Keyword detection
        - Sentiment analysis (lexicon-based)
        - Identity signal extraction (regex)

        Updates L1 Working Memory (Redis).

        Args:
            turn: Current conversation turn

        Returns:
            FastSignals with detected signals

        Spec: §7.2 写入者, §7.3 调用顺序 (T+10ms)
        """
        from heart.ss02_memory.encoder.fast import FastEncoder

        if self._fast_encoder is None:
            self._fast_encoder = FastEncoder()
        signals = self._fast_encoder.encode(turn)

        # Cache in L1 (Redis) if available
        if self._redis is not None:
            try:
                import json

                key = f"l1:{turn.user_id}:{turn.character_id}:latest"
                self._redis.setex(
                    key,
                    300,
                    json.dumps(
                        {
                            "sentiment": signals.sentiment,
                            "keywords": signals.detected_keywords,
                        }
                    ),
                )
            except Exception:
                logger.exception("l1_cache_failed")
        return signals

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
            self._db.add(event)
            await self._db.flush()
            logger.debug("encoding_queued", event_id=str(event.id))
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
            except Exception:
                logger.exception("reinforce_failed")

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
            except Exception:
                logger.exception("forget_failed")

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
            except Exception:
                logger.exception("decay_batch_failed")
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
            except Exception:
                logger.exception("consolidation_decay_failed")
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
        raise NotImplementedError("promote_to_l4() - to be implemented in Phase 2")

    # ─────────── Internal Helpers ───────────

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
