"""
Identity Lookup - SS02 §3.5

Retrieves L4 sacred memories (Identity Memory).

L4 memories are always relevant if matched, and force-included in results.

Author: 心屿团队
"""

from __future__ import annotations

from typing import List

import structlog
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss02_memory.models import IdentityMemory
from heart.ss02_memory.retriever.base import (
    QueryContext,
    RetrievalStrategy,
    ScoredMemory,
)

logger = structlog.get_logger()


class IdentityLookup(RetrievalStrategy):
    """
    L4 identity memory lookup.

    L4 memories are sacred and never decay:
    - Foundational facts (name, birthday, core values)
    - Promises and commitments
    - First-time events
    - Anniversaries

    Always included in retrieval if relevant.
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize identity lookup.

        Args:
            session: Database session
        """
        self.session = session

    @property
    def strategy_name(self) -> str:
        return "identity"

    async def retrieve(
        self,
        query_context: QueryContext,
        top_n: int = 20,
    ) -> List[ScoredMemory]:
        """
        Retrieve L4 identity memories.

        Strategy:
        1. Keyword match (if keywords provided)
        2. Category match (if in query context)
        3. Vector match (if embedding provided)

        Args:
            query_context: Query cues
            top_n: Max candidates to return

        Returns:
            Scored L4 memories (always high score)
        """
        if query_context.user_id is None or query_context.character_id is None:
            logger.error("identity_lookup_missing_filters")
            return []

        # Build query
        stmt = select(IdentityMemory).where(
            IdentityMemory.user_id == query_context.user_id,
            IdentityMemory.character_id == query_context.character_id,
        )

        # Filter by keywords (if provided)
        if query_context.keywords:
            # Search in content field (JSON text contains any keyword)
            # Note: This is a simple implementation
            # In production, use full-text search or vector similarity
            keyword_filters = [
                IdentityMemory.content.cast(str).contains(kw) for kw in query_context.keywords
            ]
            stmt = stmt.where(or_(*keyword_filters))

        # Limit
        stmt = stmt.limit(top_n)

        result = await self.session.execute(stmt)
        memories = result.scalars().all()

        # Score L4 memories
        scored = []
        for memory in memories:
            # L4 always has high importance (never decays)
            # Confidence = 1.0 (sacred facts)
            scored.append(
                ScoredMemory(
                    memory=memory,
                    memory_id=memory.id,
                    memory_type="L4",
                    score_breakdown={
                        "importance": 1.0,  # L4 always important
                        "confidence": 1.0,
                        "semantic": 0.8,  # High relevance if retrieved
                    },
                    retrieved_by=[self.strategy_name],
                )
            )

        logger.info(
            "identity_lookup_completed",
            user_id=str(query_context.user_id),
            character_id=query_context.character_id,
            keywords=query_context.keywords,
            found=len(scored),
        )

        return scored

    async def get_by_category(
        self,
        user_id: str,
        character_id: str,
        category: str,
    ) -> List[IdentityMemory]:
        """
        Retrieve L4 memories by category.

        Categories (from schema):
        - foundational: Core facts (name, birthday)
        - promise: Commitments
        - first_event: First-time experiences
        - anniversary: Commemorative dates

        Args:
            user_id: User UUID
            character_id: Character ID
            category: Category filter

        Returns:
            List of L4 memories
        """
        stmt = select(IdentityMemory).where(
            IdentityMemory.user_id == user_id,
            IdentityMemory.character_id == character_id,
            IdentityMemory.category == category,
        )

        result = await self.session.execute(stmt)
        return result.scalars().all()
