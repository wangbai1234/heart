"""
Recency Retriever - SS02 §3.5

Time-based retrieval of recent episodic memories.

Default window: last 72 hours.

Author: 心屿团队
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
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


class RecencyRetriever(RetrievalStrategy):
    """
    Recency-based retriever for L2 episodic memories.

    Retrieves memories from last N hours (default 72h).

    Scoring:
        recency_score = exp(-hours_ago / tau)
        where tau = 24h (decay constant)
    """

    def __init__(
        self,
        session: AsyncSession,
        window_hours: int = 72,
        tau_hours: float = 24.0,
    ):
        """
        Initialize recency retriever.

        Args:
            session: Database session
            window_hours: Time window (default 72h)
            tau_hours: Decay constant for recency score (default 24h)
        """
        self.session = session
        self.window_hours = window_hours
        self.tau_hours = tau_hours

    @property
    def strategy_name(self) -> str:
        return "recency"

    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve recent L2 episodic memories.

        Args:
            query_context: Must have current_time
            top_n: Number of candidates to return

        Returns:
            Scored memories with recency score
        """
        if query_context.user_id is None or query_context.character_id is None:
            logger.error("recency_retrieval_missing_filters")
            return []

        now = query_context.current_time or datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=self.window_hours)

        # Query L2 memories within time window
        stmt = (
            select(EpisodicMemory)
            .where(
                EpisodicMemory.user_id == query_context.user_id,
                EpisodicMemory.character_id == query_context.character_id,
                EpisodicMemory.do_not_recall == False,
                EpisodicMemory.created_at >= cutoff,
            )
            .order_by(EpisodicMemory.created_at.desc())
            .limit(top_n)
        )

        result = await self.session.execute(stmt)
        memories = result.scalars().all()

        # Compute recency scores
        scored = []
        for memory in memories:
            hours_ago = (now - memory.created_at).total_seconds() / 3600.0
            recency_score = math.exp(-hours_ago / self.tau_hours)

            scored.append(
                ScoredMemory(
                    memory=memory,
                    memory_id=memory.id,
                    memory_type="L2",
                    score_breakdown={
                        "recency": recency_score,
                        "importance": memory.importance_score,
                        "confidence": 1.0,
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        logger.info(
            "recency_retrieval_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            window_hours=self.window_hours,
            found=len(scored),
        )

        return scored
