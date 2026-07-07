"""
Base Retrieval Strategy - SS02 §3.5 + §10.3

Defines abstract interface and data structures for multi-strategy retrieval.

Author: 心屿团队
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from heart.ss02_memory.models import EpisodicMemory, FactNode, IdentityMemory

# ============================================================
# Query Context
# ============================================================


@dataclass
class QueryContext:
    """
    Retrieval cues extracted from user message and context.

    Used by retrieval strategies to find relevant memories.
    """

    # Text-based cues
    query_text: str
    query_embedding: Optional[List[float]] = None  # 1024-dim from BAAI/bge-m3
    keywords: List[str] = field(default_factory=list)

    # Emotional cues
    current_emotion: Optional[Dict[str, float]] = None  # {valence, arousal}
    emotional_label: Optional[str] = None  # e.g., "joy", "sadness"

    # Temporal cues
    current_time: datetime = field(default_factory=lambda: datetime.utcnow())
    scene_context: Optional[str] = None  # e.g., "morning greeting", "deep conversation"

    # Graph entry points (for graph retriever)
    entry_nodes: List[str] = field(default_factory=list)  # Predicates to start from

    # Filters
    user_id: UUID = None  # REQUIRED (INV-M-13)
    character_id: str = None  # REQUIRED


# ============================================================
# Scored Memory
# ============================================================


@dataclass
class ScoredMemory:
    """
    A memory with retrieval scores from various strategies.

    Combines scores using weighted sum per §10.4.2.
    """

    # Memory data
    memory: Union[EpisodicMemory, FactNode, IdentityMemory]
    memory_id: UUID
    memory_type: Literal["L2", "L3", "L4"]

    # Score breakdown (each strategy contributes)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    # Keys: "semantic", "importance", "emotional", "recency", "associative", "confidence"

    # Combined score (computed by score combiner)
    score: float = 0.0

    # Metadata
    retrieved_by: List[str] = field(default_factory=list)  # Strategy names
    retrieved_at: datetime = field(default_factory=lambda: datetime.utcnow())


# ============================================================
# Retrieval Result
# ============================================================


@dataclass
class MemoryRetrievalResult:
    """
    Result of multi-strategy retrieval.

    Returned by RetrievalOrchestrator.retrieve().
    """

    # Top-K memories
    memories: List[ScoredMemory]

    # Metadata
    query_context: QueryContext
    strategies_used: List[str]
    total_candidates: int
    l4_included: int

    # Performance
    retrieval_time_ms: float
    strategy_times: Dict[str, float] = field(default_factory=dict)

    # Forgetting affect hints
    recently_forgotten_hints: List[Any] = field(default_factory=list)


# ============================================================
# Abstract Retrieval Strategy
# ============================================================


class RetrievalStrategy(ABC):
    """
    Abstract base class for retrieval strategies.

    Each strategy implements a different retrieval method:
    - Vector: semantic similarity (pgvector)
    - Graph: spreading activation (recursive CTE)
    - Recency: time-based (last 72h)
    - Emotional: emotional resonance
    - Identity: L4 sacred memories
    """

    @abstractmethod
    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve memories using this strategy.

        Args:
            query_context: Query cues and filters
            top_n: Number of candidates to return (before score combination)

        Returns:
            List of scored memories (may be empty)

        Note:
            - MUST filter by user_id and character_id (INV-M-13)
            - MUST filter by do_not_recall=false
            - Score breakdown should include at least one relevant key
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def strategy_name(self) -> str:
        """
        Name of this strategy (e.g., "vector", "graph", "recency").

        Used for logging and score_breakdown keys.
        """
        raise NotImplementedError


# ============================================================
# Score Combination Utilities
# ============================================================


DEFAULT_WEIGHTS = {
    "semantic": 0.30,
    "importance": 0.20,
    "emotional": 0.15,
    "recency": 0.15,
    "associative": 0.10,
    "confidence": 0.10,
}


def combine_scores(
    candidates: List[ScoredMemory],
    weights: Optional[Dict[str, float]] = None,
) -> List[ScoredMemory]:
    """
    Combine score breakdown into final score using weighted sum.

    Formula (§10.4.2):
        score = 0.30×semantic + 0.20×importance + 0.15×emotional
              + 0.15×recency + 0.10×associative + 0.10×confidence

    Args:
        candidates: Scored memories with score_breakdown
        weights: Custom weights (defaults to DEFAULT_WEIGHTS)

    Returns:
        Same list with .score computed
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    for cand in candidates:
        s = cand.score_breakdown
        cand.score = sum(weights.get(k, 0.0) * s.get(k, 0.0) for k in weights)

    return candidates


# High-confidence L3 facts (explicit stored facts like "has_pet 年糕") must not be
# out-ranked out of the injected window by episodic chatter, which caused the recall
# bug where a confidence=1 fact was answered wrong. We force-include them like L4.
L3_CONFIDENCE_FLOOR = 0.9
MAX_FORCED_L3 = 2


def _fact_rank(m: ScoredMemory) -> tuple[float, float]:
    """Rank key for choosing which duplicate L3 fact to keep: confidence, then score."""
    return (float(getattr(m.memory, "confidence", 0.0) or 0.0), m.score)


def select_top_k(
    candidates: List[ScoredMemory],
    k: int = 5,
    must_include_l4: bool = True,
    dedup_threshold: float = 0.9,
) -> List[ScoredMemory]:
    """
    Select top-K memories with L4 + high-confidence-L3 force-inclusion and dedup.

    Rules (§10.4.2 + §3.5):
    - L4 memories with score > 0.1 are force-included (max 2)
    - High-confidence L3 facts (confidence >= L3_CONFIDENCE_FLOOR, score > 0.1) are
      force-included (max MAX_FORCED_L3) so explicit facts beat episodic chatter
    - Duplicate L3 facts (same subject+predicate) are collapsed, keeping the
      highest-confidence one
    - Top-K includes at least 1 L4 if relevant

    Args:
        candidates: Scored memories (must have .score computed)
        k: Top-K limit (default 5, per INV-M-9)
        must_include_l4: Force include L4 if relevant
        dedup_threshold: Reserved for future semantic dedup

    Returns:
        Top-K scored memories (ordered: L4, forced L3, then by score)
    """
    # Sort by score descending
    candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

    # Extract L4 and others
    l4_candidates = [c for c in candidates if c.memory_type == "L4" and c.score > 0.1]
    others = [c for c in candidates if c.memory_type != "L4"]

    # Deduplicate (collapses duplicate L3 fact triples)
    others = deduplicate_memories(others, threshold=dedup_threshold)

    # High-confidence L3 facts to force-include (already dedup'd, still score-sorted).
    forced_l3 = [
        c
        for c in others
        if c.memory_type == "L3"
        and float(getattr(c.memory, "confidence", 0.0) or 0.0) >= L3_CONFIDENCE_FLOOR
        and c.score > 0.1
    ][:MAX_FORCED_L3]

    final: List[ScoredMemory] = []
    chosen_ids: set[str] = set()

    def _add(mem: ScoredMemory) -> None:
        mid = str(mem.memory_id)
        if mid not in chosen_ids:
            final.append(mem)
            chosen_ids.add(mid)

    # Force include up to 2 L4
    if must_include_l4:
        for c in l4_candidates[:2]:
            _add(c)

    # Force include high-confidence L3 facts
    for c in forced_l3:
        _add(c)

    # Fill remaining slots with the rest (score order), skipping already-included
    for c in others:
        if len(final) >= k:
            break
        _add(c)

    return final[:k]


def deduplicate_memories(
    memories: List[ScoredMemory],
    threshold: float = 0.9,
) -> List[ScoredMemory]:
    """
    Collapse duplicate L3 fact triples (same subject+predicate), keeping the
    highest-confidence variant. Competing/duplicate facts about the same subject
    otherwise dilute the injected window and let a stale/low-confidence value win.

    Non-L3 memories (and L3 facts lacking subject/predicate) pass through unchanged.
    `threshold` is reserved for future semantic (embedding-cosine) dedup.
    """
    seen_facts: Dict[tuple, int] = {}  # (subject, predicate) -> index in result
    result: List[ScoredMemory] = []

    for m in memories:
        if m.memory_type == "L3":
            subject = getattr(m.memory, "subject", None)
            predicate = getattr(m.memory, "predicate", None)
            if subject is not None and predicate is not None:
                key = (subject, predicate)
                if key in seen_facts:
                    idx = seen_facts[key]
                    if _fact_rank(m) > _fact_rank(result[idx]):
                        result[idx] = m  # keep the higher-confidence duplicate
                    continue
                seen_facts[key] = len(result)
        result.append(m)

    return result
