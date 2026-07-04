"""Slow Path Memory Extractor Worker — Phase B.

Polls memory_extraction_queue for pending extraction jobs.
Processes batches through Extractor → Resolver → Writer pipeline.

Pipeline:
  1. LLMExtractor.run(batch) → ExtractionEnvelope
  2. Resolver.resolve(envelope) → list[ResolverDecision]
  3. Writer.commit(decisions, envelope) → None

Idempotency: same extractor_run_id → reject second commit
  (Writer checks audit_log for existing entries).

Controlled by HEART_WORKERS_ENABLED=true and MEMORY_EXTRACTOR_MODE.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from heart.core.config import settings
from heart.ss02_memory.mode import get_mode
from heart.ss02_memory.models import MemoryExtractionQueue

logger = structlog.get_logger()

# ── Configuration ──

POLL_INTERVAL_SECONDS = 5
EMPTY_POLL_SLEEP = 5
BATCH_SIZE = 10
MAX_RETRIES = 3


# ── Worker ──


class MemoryExtractorWorker:
    """Async worker for slow-path memory extraction.

    Polls memory_extraction_queue for pending jobs, processes them
    through Extractor → Resolver → Writer pipeline.

    Usage:
        worker = MemoryExtractorWorker(
            db_session_factory=factory,
            extractor=LLMExtractor(router),
            user_id_provider=get_user_for_session,
        )
        await worker.start()
    """

    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        extractor: object | None = None,
        user_id_provider: object | None = None,
    ) -> None:
        self.db_session_factory = db_session_factory
        self._extractor = extractor
        self._user_id_provider = user_id_provider
        self._should_stop = False

    async def start(self) -> None:
        """Start worker loop."""
        logger.info("memory_extractor_worker_started", mode=get_mode())

        while not self._should_stop:
            try:
                async with self.db_session_factory() as session:
                    items = await self._fetch_pending(session)

                if not items:
                    await asyncio.sleep(EMPTY_POLL_SLEEP)
                    continue

                logger.info("extractor_batch_received", count=len(items))
                await self._process_batch(items)

            except Exception as e:
                logger.error("extractor_worker_loop_error", error=str(e))
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        logger.info("memory_extractor_worker_stopped")

    async def stop(self) -> None:
        """Stop worker gracefully."""
        logger.info("memory_extractor_worker_stopping")
        self._should_stop = True

    async def _fetch_pending(self, session: AsyncSession) -> list[dict]:
        """Fetch pending queue items."""
        stmt = (
            select(MemoryExtractionQueue)
            .where(MemoryExtractionQueue.status == "pending")
            .order_by(MemoryExtractionQueue.enqueued_at)
            .limit(BATCH_SIZE)
        )
        result = await session.execute(stmt)
        rows = result.scalars().all()

        return [
            {
                "id": row.id,
                "session_id": row.session_id,
                "turn_id": row.turn_id,
                "hints_json": row.hints_json,
            }
            for row in rows
        ]

    async def _process_batch(self, items: list[dict]) -> None:
        """Process a batch through Extractor → Resolver → Writer.

        Each item is processed individually (one envelope per item).
        """
        for item in items:
            await self._process_one(item)

    async def _process_one(self, item: dict) -> None:
        """Process a single queue item through the full pipeline."""
        run_id = uuid4()
        start = time.monotonic()

        try:
            # Mark as processing
            async with self.db_session_factory() as session:
                await self._mark_status(session, [item], "processing", run_id)

            # Resolve user_id for this item
            user_id = await self._resolve_user_id(item["session_id"])

            # Build QueueItem for the extractor
            from heart.ss02_memory.extractor.types import QueueItem as ExtractorQueueItem

            # ── Fetch turns for the extraction window ──
            turns = await self._fetch_turns(item)

            queue_item = ExtractorQueueItem(
                extractor_run_id=run_id,
                session_id=item["session_id"],
                window=turns,
                model=getattr(settings, "memory_extractor_llm_model", "deepseek-v4-flash"),
            )

            # ── Step 1: Extract ──
            if self._extractor is None:
                logger.warning("no_extractor_configured", run_id=str(run_id))
                async with self.db_session_factory() as session:
                    await self._mark_status(session, [item], "skipped")
                return

            results = await self._extractor.run([queue_item])  # type: ignore[union-attr,attr-defined]
            result = results[0] if results else None

            if result is None or result.failed:
                logger.error(
                    "extraction_failed",
                    run_id=str(run_id),
                    error=result.error if result else "no result",
                )
                async with self.db_session_factory() as session:
                    await self._mark_status(
                        session,
                        [item],
                        "failed",
                        error_message=result.error if result else "no result",
                    )
                return

            envelope = result.envelope

            # ── Step 2: Resolve ──
            from heart.ss02_memory.extractor.resolver import Resolver

            async with self.db_session_factory() as session:
                resolver = Resolver(session, user_id)
                decisions = await resolver.resolve(envelope)

            # ── Step 3: Write ──
            from heart.ss02_memory.extractor.writer import Writer

            async with self.db_session_factory() as session:
                writer = Writer(session, user_id, item["session_id"])
                await writer.commit(decisions, envelope)

            elapsed = time.monotonic() - start
            logger.info(
                "extractor_pipeline_done",
                run_id=str(run_id),
                candidates=len(envelope.candidates),
                decisions=len(decisions),
                latency_ms=int(elapsed * 1000),
            )

        except Exception as e:
            elapsed = time.monotonic() - start
            logger.error(
                "extractor_pipeline_failed",
                run_id=str(run_id),
                error=str(e),
                latency_ms=int(elapsed * 1000),
            )
            async with self.db_session_factory() as session:
                await self._mark_status(session, [item], "failed", error_message=str(e))

    async def _resolve_user_id(self, session_id: UUID) -> UUID:
        """Resolve user_id from session_id.

        Uses the provider if configured, otherwise returns a placeholder.
        In production, this should query the sessions table.
        """
        if self._user_id_provider is not None:
            return await self._user_id_provider(session_id)  # type: ignore[union-attr]

        # Fallback: query memory_encoding_events for user_id
        from heart.ss02_memory.models import MemoryEncodingEvent

        async with self.db_session_factory() as session:
            stmt = (
                select(MemoryEncodingEvent.user_id)
                .where(MemoryEncodingEvent.source_turn_id.isnot(None))
                .limit(1)
            )
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is not None:
                return row

        # Last resort placeholder
        return UUID(int=0)

    async def _fetch_turns(self, item: dict) -> list:
        """Fetch turns for an extraction window from memory_encoding_events.

        Returns a list of TurnInput objects ready for the extractor.
        """
        from heart.ss02_memory.extractor.types import TurnInput
        from heart.ss02_memory.models import MemoryEncodingEvent

        user_id = await self._resolve_user_id(item["session_id"])
        turns: list[TurnInput] = []

        try:
            async with self.db_session_factory() as session:
                stmt = (
                    select(MemoryEncodingEvent)
                    .where(
                        MemoryEncodingEvent.user_id == user_id,
                        MemoryEncodingEvent.source_user_text.isnot(None),
                    )
                    .order_by(MemoryEncodingEvent.created_at.desc())
                    .limit(20)
                )
                result = await session.execute(stmt)
                events = result.scalars().all()

                for i, event in enumerate(reversed(events)):
                    if event.source_user_text:
                        turns.append(
                            TurnInput(
                                turn_id=i + 1,
                                speaker="user",
                                ts=event.created_at.isoformat() if event.created_at else "",
                                text=event.source_user_text,
                            )
                        )
        except Exception as e:
            logger.warning("fetch_turns_failed", error=str(e))

        return turns

    async def _mark_status(
        self,
        session: AsyncSession,
        items: list[dict],
        status: str,
        run_id: Optional[UUID] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update status for a list of queue items."""
        now = datetime.now(timezone.utc)
        for item in items:
            stmt = select(MemoryExtractionQueue).where(MemoryExtractionQueue.id == item["id"])
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if row is None:
                continue

            row.status = status
            if status == "processing":
                row.started_at = now
                row.extractor_run_id = run_id
            elif status in ("done", "failed"):
                row.finished_at = now
                if error_message:
                    row.error_message = error_message[:1000]
                if status == "failed":
                    row.retry_count = (row.retry_count or 0) + 1

        await session.commit()
