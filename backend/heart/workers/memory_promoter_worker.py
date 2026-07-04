"""Memory Promoter Worker — Singleton L3→L4 promotion loop.

Runs every MEMORY_PROMOTER_INTERVAL_SECS with a Redis SETNX lock
to prevent double-run across replicas.

Follows the existing consolidator worker pattern per CLAUDE.md.

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import time

import structlog
from redis.asyncio import Redis

from heart.core.config import settings
from heart.ss02_memory.promoter import Promoter, load_config

logger = structlog.get_logger()

_LOCK_KEY = "heart:memory_promoter:lock"
_LOCK_TTL_SECS = 300  # 5 minutes — should finish well within this


class MemoryPromoterWorker:
    """Singleton background worker for L3→L4 promotion.

    Uses Redis SETNX for distributed lock to ensure only one replica
    runs the promoter at a time.
    """

    def __init__(self, db_session_factory, redis_client: Redis | None = None) -> None:
        self._db_factory = db_session_factory
        self._redis = redis_client
        self._should_stop = False
        self._interval = settings.memory_promoter_interval_secs
        self._config = load_config()

        logger.info(
            "memory_promoter_worker_initialized",
            interval_secs=self._interval,
            batch_size=self._config.batch_size,
        )

    async def start(self) -> None:
        """Start the promoter loop."""
        logger.info("memory_promoter_worker_started")

        while not self._should_stop:
            try:
                acquired = await self._acquire_lock()
                if not acquired:
                    logger.debug("promoter_lock_not_acquired")
                    await asyncio.sleep(self._interval)
                    continue

                try:
                    await self._run_once()
                finally:
                    await self._release_lock()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("promoter_worker_error", error=str(e), exc_info=True)

            await asyncio.sleep(self._interval)

        logger.info("memory_promoter_worker_stopped")

    async def stop(self) -> None:
        """Stop worker gracefully."""
        logger.info("memory_promoter_worker_stopping")
        self._should_stop = True

    async def _run_once(self) -> None:
        """Run one promoter batch."""
        start = time.monotonic()

        async with self._db_factory() as session:
            promoter = Promoter(session, self._config)
            result = await promoter.run_batch()
            await session.commit()

        elapsed_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "promoter_run_complete",
            promoted=len(result.promoted),
            demoted=len(result.demoted),
            candidates=result.candidates_found,
            reconciliation_fixed=result.reconciliation_fixed,
            errors=len(result.errors),
            elapsed_ms=elapsed_ms,
        )

        try:
            from prometheus_client import Histogram

            latency_histogram = Histogram(
                "heart_memory_promoter_latency_seconds",
                "Promoter batch latency",
                buckets=[1, 5, 10, 30, 60, 120],
            )
            latency_histogram.observe(elapsed_ms / 1000)
        except Exception:
            pass

    async def _acquire_lock(self) -> bool:
        """Acquire distributed lock via Redis SETNX.

        Returns True if lock acquired, False if another replica holds it.
        """
        if self._redis is None:
            # No Redis — single-instance mode, always acquire
            return True

        try:
            result = await self._redis.set(
                _LOCK_KEY,
                "1",
                nx=True,
                ex=_LOCK_TTL_SECS,
            )
            return result is not None
        except Exception as e:
            logger.warning("promoter_lock_acquire_error", error=str(e))
            # On Redis error, allow run (better to double-run than never run)
            return True

    async def _release_lock(self) -> None:
        """Release the distributed lock."""
        if self._redis is None:
            return

        try:
            await self._redis.delete(_LOCK_KEY)
        except Exception as e:
            logger.warning("promoter_lock_release_error", error=str(e))
