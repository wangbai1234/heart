"""
Graph Retriever - SS02 §3.5

Spreading activation on L3 fact graph using recursive CTE.

V1: PostgreSQL recursive CTE
V2 (future): Neo4j for advanced graph operations

Author: 心屿团队
"""

from __future__ import annotations

import math
from typing import List
from uuid import UUID

import structlog
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import FactNode
from heart.ss02_memory.retriever.base import (
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
)

logger = structlog.get_logger()


class GraphRetriever(RetrievalStrategy):
    """
    Graph-based retriever using spreading activation.

    Algorithm:
    1. Find entry nodes (facts matching keywords)
    2. Traverse related_facts edges (BFS)
    3. Score by distance from entry nodes (activation decay)

    Scoring:
        associative_score = exp(-distance / tau)
        where tau = 1.5 (decay constant)
    """

    def __init__(
        self,
        session: AsyncSession,
        max_depth: int = 2,
        tau: float = 1.5,
    ):
        """
        Initialize graph retriever.

        Args:
            session: Database session
            max_depth: Maximum traversal depth (default 2)
            tau: Activation decay constant (default 1.5)
        """
        self.session = session
        self.max_depth = max_depth
        self.tau = tau

    @property
    def strategy_name(self) -> str:
        return "graph"

    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve facts via spreading activation.

        Args:
            query_context: Must have keywords or entry_nodes
            top_n: Number of candidates to return

        Returns:
            Scored facts with associative score
        """
        if query_context.user_id is None or query_context.character_id is None:
            logger.error("graph_retrieval_missing_filters")
            return []

        # Get entry nodes
        entry_nodes = await self._find_entry_nodes(query_context)

        if not entry_nodes:
            logger.debug("graph_retrieval_no_entry_nodes")
            return []

        # Spread activation
        activated_facts = await self._spread_activation(
            query_context,
            entry_nodes,
        )

        # Score by distance
        scored = []
        for fact_id, distance in activated_facts.items():
            # Fetch fact
            fact = await self._get_fact(fact_id)
            if fact is None:
                continue

            # Compute associative score
            associative_score = math.exp(-distance / self.tau)

            scored.append(
                ScoredMemory(
                    memory=fact,
                    memory_id=fact.id,
                    memory_type="L3",
                    score_breakdown={
                        "associative": associative_score,
                        "importance": fact.importance,
                        "confidence": fact.confidence,
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        # Sort by associative score and take top-N
        scored.sort(key=lambda x: x.score_breakdown["associative"], reverse=True)
        scored = scored[:top_n]

        logger.info(
            "graph_retrieval_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            entry_nodes=len(entry_nodes),
            activated=len(activated_facts),
            found=len(scored),
        )

        return scored

    async def _find_entry_nodes(
        self,
        query_context: QueryContext,
    ) -> List[UUID]:
        """
        Find entry nodes for spreading activation.

        Strategy:
        1. Use explicit entry_nodes if provided
        2. Otherwise, find facts matching keywords (predicate or object)

        Returns:
            List of fact IDs
        """
        # Explicit entry nodes
        if query_context.entry_nodes:
            # Convert predicate names to fact IDs
            stmt = select(FactNode.id).where(
                FactNode.user_id == query_context.user_id,
                FactNode.character_id == query_context.character_id,
                FactNode.do_not_recall == False,
                FactNode.promoted_to_l4_at.is_(None),
                FactNode.predicate.in_(query_context.entry_nodes),
            )
            result = await self.session.execute(stmt)
            return [row[0] for row in result.all()]

        # Keyword-based search
        if query_context.keywords:
            # Search predicate, object, or literal_text
            # Note: Simple LIKE search for V1
            # V2 should use full-text search or vector similarity
            from sqlalchemy import or_

            keyword_filters = []
            for kw in query_context.keywords:
                keyword_filters.append(FactNode.predicate.contains(kw))
                keyword_filters.append(FactNode.object.contains(kw))
                keyword_filters.append(FactNode.literal_text.contains(kw))

            stmt = (
                select(FactNode.id)
                .where(
                    FactNode.user_id == query_context.user_id,
                    FactNode.character_id == query_context.character_id,
                    FactNode.do_not_recall == False,
                    FactNode.promoted_to_l4_at.is_(None),
                    or_(*keyword_filters),
                )
                .limit(10)
            )

            result = await self.session.execute(stmt)
            return [row[0] for row in result.all()]

        return []

    async def _spread_activation(
        self,
        query_context: QueryContext,
        entry_nodes: List[UUID],
    ) -> dict[UUID, int]:
        """
        Spread activation from entry nodes via BFS.

        Uses recursive CTE to traverse related_facts edges.

        Returns:
            Dict of {fact_id: distance}
        """
        if not entry_nodes:
            return {}

        # Convert UUIDs to strings for SQL
        entry_ids = [str(fid) for fid in entry_nodes]

        # Recursive CTE query
        # Note: This is V1 implementation using related_facts array
        # V2 will use Neo4j for better graph traversal
        query = text(f"""
            WITH RECURSIVE activated AS (
                -- Base case: entry nodes (distance = 0)
                SELECT
                    id,
                    0 AS distance
                FROM fact_nodes
                WHERE id = ANY(:entry_ids::uuid[])
                  AND user_id = :user_id
                  AND character_id = :character_id
                  AND do_not_recall = false
                  AND promoted_to_l4_at IS NULL

                UNION

                -- Recursive case: follow related_facts
                SELECT
                    fn.id,
                    a.distance + 1
                FROM fact_nodes fn
                INNER JOIN activated a ON fn.id = ANY(
                    SELECT unnest(fn2.related_facts)
                    FROM fact_nodes fn2
                    WHERE fn2.id = a.id
                )
                WHERE a.distance < :max_depth
                  AND fn.user_id = :user_id
                  AND fn.character_id = :character_id
                  AND fn.do_not_recall = false
                  AND fn.promoted_to_l4_at IS NULL
            )
            SELECT DISTINCT ON (id) id, distance
            FROM activated
            ORDER BY id, distance
        """)

        result = await self.session.execute(
            query,
            {
                "entry_ids": entry_ids,
                "user_id": str(query_context.user_id),
                "character_id": query_context.character_id,
                "max_depth": self.max_depth,
            },
        )

        # Build distance map
        activated = {}
        for row in result.all():
            fact_id = UUID(str(row[0]))
            distance = int(row[1])
            activated[fact_id] = distance

        return activated

    async def _get_fact(self, fact_id: UUID) -> FactNode | None:
        """
        Fetch a fact by ID.

        Args:
            fact_id: Fact UUID

        Returns:
            FactNode or None
        """
        stmt = select(FactNode).where(FactNode.id == fact_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
