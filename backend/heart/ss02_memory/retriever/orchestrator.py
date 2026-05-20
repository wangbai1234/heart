"""
Retrieval Orchestrator - SS02 §3.5 + §10.3

Coordinates multi-strategy retrieval with parallel execution.

Pipeline:
1. Run all strategies in parallel (asyncio.gather)
2. Merge candidates
3. Combine scores using weights (§10.4.2)
4. Select Top-K with L4 force-inclusion
5. Deduplicate

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time
from typing import Dict, List, Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.retriever.base import (
    MemoryRetrievalResult,
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
    combine_scores,
    select_top_k,
    DEFAULT_WEIGHTS,
)
from heart.ss02_memory.retriever.vector import VectorRetriever
from heart.ss02_memory.retriever.graph import GraphRetriever
from heart.ss02_memory.retriever.recency import RecencyRetriever
from heart.ss02_memory.retriever.emotional import EmotionalRetriever
from heart.ss02_memory.retriever.identity import IdentityLookup

logger = structlog.get_logger()


class RetrievalOrchestrator:
    """
    Orchestrates multi-strategy retrieval.

    Runs 5 strategies in parallel:
    - Vector: semantic similarity (pgvector)
    - Graph: spreading activation
    - Recency: time-based
    - Emotional: emotional resonance
    - Identity: L4 sacred memories

    Combines scores and selects Top-K.
    """

    def __init__(
        self,
        session: AsyncSession,
        weights: Optional[Dict[str, float]] = None,
        enable_vector: bool = True,
        enable_graph: bool = True,
        enable_recency: bool = True,
        enable_emotional: bool = True,
        enable_identity: bool = True,
    ):
        """
        Initialize retrieval orchestrator.

        Args:
            session: Database session
            weights: Score combination weights (defaults to §10.4.2)
            enable_*: Feature flags to disable specific strategies
        """
        self.session = session
        self.weights = weights or DEFAULT_WEIGHTS

        # Initialize strategies
        self.strategies: List[RetrievalStrategy] = []

        if enable_vector:
            self.strategies.append(VectorRetriever(session))

        if enable_graph:
            self.strategies.append(GraphRetriever(session))

        if enable_recency:
            self.strategies.append(RecencyRetriever(session))

        if enable_emotional:
            self.strategies.append(EmotionalRetriever(session))

        if enable_identity:
            self.strategies.append(IdentityLookup(session))

        logger.info(
            "retrieval_orchestrator_initialized",
            strategies=[s.strategy_name for s in self.strategies],
        )

    async def retrieve(
        self,
        query_context: QueryContext,
        top_k: int = 5,
    ) -> MemoryRetrievalResult:
        """
        Execute multi-strategy retrieval.

        Pipeline:
        1. Run all strategies in parallel
        2. Merge candidates (deduplicate by memory_id)
        3. Combine scores
        4. Select Top-K with L4 force-inclusion

        Args:
            query_context: Query cues and filters
            top_k: Number of memories to return (default 5)

        Returns:
            MemoryRetrievalResult with Top-K memories

        Raises:
            ValueError: If user_id or character_id missing (INV-M-13)
        """
        # Validate filters (INV-M-13)
        if query_context.user_id is None or query_context.character_id is None:
            raise ValueError("user_id and character_id are required (INV-M-13)")

        start_time = time.perf_counter()

        # Run all strategies in parallel
        logger.info(
            "retrieval_started",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            strategies=[s.strategy_name for s in self.strategies],
        )

        strategy_results = await self._run_strategies_parallel(query_context)

        # Merge candidates
        merged_candidates = self._merge_candidates(strategy_results)

        total_candidates = len(merged_candidates)

        logger.debug(
            "retrieval_candidates_merged",
            total=total_candidates,
            by_strategy={name: len(candidates) for name, candidates in strategy_results.items()},
        )

        # Combine scores
        combine_scores(merged_candidates, self.weights)

        # Select Top-K with L4 force-inclusion
        top_k_memories = select_top_k(
            merged_candidates,
            k=top_k,
            must_include_l4=True,
        )

        # Count L4 included
        l4_count = sum(1 for m in top_k_memories if m.memory_type == "L4")

        # Compute timing
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        logger.info(
            "retrieval_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            total_candidates=total_candidates,
            top_k=len(top_k_memories),
            l4_included=l4_count,
            elapsed_ms=round(elapsed_ms, 2),
        )

        return MemoryRetrievalResult(
            memories=top_k_memories,
            query_context=query_context,
            strategies_used=[s.strategy_name for s in self.strategies],
            total_candidates=total_candidates,
            l4_included=l4_count,
            retrieval_time_ms=elapsed_ms,
            strategy_times=self._extract_strategy_times(strategy_results),
        )

    async def _run_strategies_parallel(
        self,
        query_context: QueryContext,
    ) -> Dict[str, List[ScoredMemory]]:
        """
        Run all strategies in parallel using asyncio.gather.

        Args:
            query_context: Query cues

        Returns:
            Dict of {strategy_name: [ScoredMemory]}
        """
        # Create tasks for all strategies
        tasks = [self._run_strategy_timed(strategy, query_context) for strategy in self.strategies]

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result dict
        strategy_results = {}
        for strategy, result in zip(self.strategies, results):
            if isinstance(result, Exception):
                logger.error(
                    "strategy_failed",
                    strategy=strategy.strategy_name,
                    error=str(result),
                    exc_info=result,
                )
                strategy_results[strategy.strategy_name] = []
            else:
                strategy_results[strategy.strategy_name] = result

        return strategy_results

    async def _run_strategy_timed(
        self,
        strategy: RetrievalStrategy,
        query_context: QueryContext,
    ) -> List[ScoredMemory]:
        """
        Run a strategy and measure its execution time.

        Args:
            strategy: Strategy to run
            query_context: Query cues

        Returns:
            List of scored memories
        """
        start = time.perf_counter()
        try:
            candidates = await strategy.retrieve(query_context)
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            logger.debug(
                "strategy_completed",
                strategy=strategy.strategy_name,
                found=len(candidates),
                elapsed_ms=round(elapsed_ms, 2),
            )

            # Attach timing metadata
            for cand in candidates:
                cand.score_breakdown[f"_{strategy.strategy_name}_time_ms"] = elapsed_ms

            return candidates

        except Exception as e:
            logger.error(
                "strategy_error",
                strategy=strategy.strategy_name,
                error=str(e),
                exc_info=True,
            )
            raise

    def _merge_candidates(
        self,
        strategy_results: Dict[str, List[ScoredMemory]],
    ) -> List[ScoredMemory]:
        """
        Merge candidates from all strategies.

        Deduplicates by memory_id, combining score_breakdown.

        Args:
            strategy_results: Dict of {strategy_name: [ScoredMemory]}

        Returns:
            Merged list of ScoredMemory
        """
        # Deduplicate by memory_id
        merged: Dict[str, ScoredMemory] = {}

        for strategy_name, candidates in strategy_results.items():
            for cand in candidates:
                key = str(cand.memory_id)

                if key in merged:
                    # Merge score_breakdown
                    existing = merged[key]
                    for k, v in cand.score_breakdown.items():
                        if k not in existing.score_breakdown:
                            existing.score_breakdown[k] = v
                        else:
                            # Take max if same key from different strategies
                            existing.score_breakdown[k] = max(existing.score_breakdown[k], v)

                    # Merge retrieved_by
                    existing.retrieved_by.extend(cand.retrieved_by)
                    existing.retrieved_by = list(set(existing.retrieved_by))
                else:
                    merged[key] = cand

        return list(merged.values())

    def _extract_strategy_times(
        self,
        strategy_results: Dict[str, List[ScoredMemory]],
    ) -> Dict[str, float]:
        """
        Extract timing info from strategy results.

        Args:
            strategy_results: Dict of {strategy_name: [ScoredMemory]}

        Returns:
            Dict of {strategy_name: elapsed_ms}
        """
        times = {}
        for strategy_name, candidates in strategy_results.items():
            if candidates:
                # Extract timing from first candidate's metadata
                key = f"_{strategy_name}_time_ms"
                if key in candidates[0].score_breakdown:
                    times[strategy_name] = candidates[0].score_breakdown[key]
        return times
