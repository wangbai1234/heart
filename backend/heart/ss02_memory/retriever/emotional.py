"""
Emotional Retriever - SS02 §3.5

Retrieves L2 memories by emotional resonance (valence/arousal similarity).

Author: 心屿团队
"""

from __future__ import annotations

import math
from typing import List

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import EpisodicMemory
from heart.ss02_memory.retriever.base import (
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
)

logger = structlog.get_logger()


class EmotionalRetriever(RetrievalStrategy):
    """
    Emotional resonance retriever for L2 episodic memories.

    Matches memories by emotional vector similarity:
    - Valence distance (positive/negative axis)
    - Arousal distance (intensity axis)

    Scoring:
        emotional_score = 1 / (1 + euclidean_distance)
        where distance = sqrt((v1-v2)^2 + (a1-a2)^2)
    """

    def __init__(
        self,
        session: AsyncSession,
        min_arousal: float = 0.3,
    ):
        """
        Initialize emotional retriever.

        Args:
            session: Database session
            min_arousal: Minimum arousal to consider (default 0.3)
                         Filters out neutral/low-arousal memories
        """
        self.session = session
        self.min_arousal = min_arousal

    @property
    def strategy_name(self) -> str:
        return "emotional"

    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve emotionally similar L2 memories.

        Args:
            query_context: Must have current_emotion {valence, arousal}
            top_n: Number of candidates to return

        Returns:
            Scored memories with emotional score
        """
        if query_context.user_id is None or query_context.character_id is None:
            logger.error("emotional_retrieval_missing_filters")
            return []

        if query_context.current_emotion is None:
            logger.warning("emotional_retrieval_skipped_no_emotion")
            return []

        query_valence = query_context.current_emotion.get("valence", 0.0)
        query_arousal = query_context.current_emotion.get("arousal", 0.0)

        # Skip if query is too neutral (low arousal)
        if query_arousal < self.min_arousal:
            logger.debug(
                "emotional_retrieval_skipped_low_arousal",
                arousal=query_arousal,
            )
            return []

        # Query L2 memories with non-null emotional_peak
        stmt = select(EpisodicMemory).where(
            EpisodicMemory.user_id == query_context.user_id,
            EpisodicMemory.character_id == query_context.character_id,
            ~EpisodicMemory.do_not_recall,
            EpisodicMemory.emotional_peak.isnot(None),
        )

        result = await self.session.execute(stmt)
        memories = result.scalars().all()

        # Compute emotional similarity
        scored = []
        for memory in memories:
            emotional_peak = memory.emotional_peak or {}
            mem_valence = emotional_peak.get("valence", 0.0)
            mem_arousal = emotional_peak.get("arousal", 0.0)

            # Filter low-arousal memories
            if mem_arousal < self.min_arousal:
                continue

            # Euclidean distance in 2D emotional space
            distance = math.sqrt(
                (query_valence - mem_valence) ** 2 + (query_arousal - mem_arousal) ** 2
            )

            # Convert to similarity score [0, 1]
            # Lower distance = higher similarity
            emotional_score = 1.0 / (1.0 + distance)

            scored.append(
                ScoredMemory(
                    memory=memory,
                    memory_id=memory.id,
                    memory_type="L2",
                    score_breakdown={
                        "emotional": emotional_score,
                        "importance": memory.importance_score,
                        "confidence": 1.0,
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        # Sort by emotional score and take top-N
        scored.sort(key=lambda x: x.score_breakdown["emotional"], reverse=True)
        scored = scored[:top_n]

        logger.info(
            "emotional_retrieval_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            query_emotion=query_context.current_emotion,
            found=len(scored),
        )

        return scored
