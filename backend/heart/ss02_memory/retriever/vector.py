"""
Vector Retriever - SS02 §3.5

Semantic similarity search using pgvector (cosine distance).

Searches L2 (EpisodicMemory) + L3 (FactNode) by embedding similarity.

Author: 心屿团队
"""

from __future__ import annotations

from typing import List
from uuid import UUID

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import EpisodicMemory, FactNode
from heart.ss02_memory.retriever.base import (
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
)

logger = structlog.get_logger()


class VectorRetriever(RetrievalStrategy):
    """
    Vector similarity retriever using pgvector.

    Uses cosine similarity on embedding fields:
    - L2: EpisodicMemory.summary_embedding
    - L3: FactNode.literal_text_embedding

    Returns top-N by semantic match.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize vector retriever.

        Args:
            session: Database session with pgvector support
        """
        self.session = session

    @property
    def strategy_name(self) -> str:
        return "vector"

    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve memories by vector similarity.

        Args:
            query_context: Must have query_embedding
            top_n: Number of candidates per layer

        Returns:
            Scored memories with semantic score
        """
        if query_context.query_embedding is None:
            logger.warning("vector_retrieval_skipped_no_embedding")
            return []

        if query_context.user_id is None or query_context.character_id is None:
            logger.error("vector_retrieval_missing_filters")
            return []

        candidates = []

        # Search L2 (EpisodicMemory)
        l2_results = await self._search_l2(query_context, top_n)
        candidates.extend(l2_results)

        # Search L3 (FactNode)
        l3_results = await self._search_l3(query_context, top_n)
        candidates.extend(l3_results)

        logger.info(
            "vector_retrieval_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            l2_found=len(l2_results),
            l3_found=len(l3_results),
        )

        return candidates

    async def _search_l2(
        self,
        query_context: QueryContext,
        top_n: int,
    ) -> List[ScoredMemory]:
        """
        Search L2 episodic memories by vector similarity.

        Uses pgvector <=> operator (cosine distance).
        Lower distance = higher similarity.
        """
        embedding_str = f"[{','.join(map(str, query_context.query_embedding))}]"

        # pgvector cosine distance: <=>
        # Note: We need to use text() for raw SQL with pgvector operators
        from sqlalchemy import text

        stmt = select(
            EpisodicMemory,
            # Cosine distance (0 = identical, 2 = opposite)
            # Convert to similarity: 1 - distance/2 → [0, 1]
            func.cast(
                1.0 - (func.cast(
                    text(f"semantic_vector <=> '{embedding_str}'::vector"),
                    float
                ) / 2.0),
                float
            ).label("similarity"),
        ).where(
            EpisodicMemory.user_id == query_context.user_id,
            EpisodicMemory.character_id == query_context.character_id,
            EpisodicMemory.do_not_recall == False,
            EpisodicMemory.semantic_vector.isnot(None),
        ).order_by(
            text(f"semantic_vector <=> '{embedding_str}'::vector")
        ).limit(top_n)

        result = await self.session.execute(stmt)
        rows = result.all()

        scored = []
        for memory, similarity in rows:
            scored.append(
                ScoredMemory(
                    memory=memory,
                    memory_id=memory.id,
                    memory_type="L2",
                    score_breakdown={
                        "semantic": float(similarity),
                        "importance": memory.importance_score,
                        "confidence": 1.0,  # High confidence for vector match
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        return scored

    async def _search_l3(
        self,
        query_context: QueryContext,
        top_n: int,
    ) -> List[ScoredMemory]:
        """
        Search L3 facts by vector similarity.

        Uses semantic_vector field.
        """
        embedding_str = f"[{','.join(map(str, query_context.query_embedding))}]"

        from sqlalchemy import text

        stmt = select(
            FactNode,
            func.cast(
                1.0 - (func.cast(
                    text(f"semantic_vector <=> '{embedding_str}'::vector"),
                    float
                ) / 2.0),
                float
            ).label("similarity"),
        ).where(
            FactNode.user_id == query_context.user_id,
            FactNode.character_id == query_context.character_id,
            FactNode.do_not_recall == False,
            FactNode.promoted_to_l4_at.is_(None),  # Exclude L4-promoted facts
            FactNode.semantic_vector.isnot(None),
        ).order_by(
            text(f"semantic_vector <=> '{embedding_str}'::vector")
        ).limit(top_n)

        result = await self.session.execute(stmt)
        rows = result.all()

        scored = []
        for fact, similarity in rows:
            scored.append(
                ScoredMemory(
                    memory=fact,
                    memory_id=fact.id,
                    memory_type="L3",
                    score_breakdown={
                        "semantic": float(similarity),
                        "importance": fact.importance,
                        "confidence": fact.confidence,
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        return scored
