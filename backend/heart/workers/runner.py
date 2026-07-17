"""
Worker Runner — starts background workers at app startup.

Registers:
- MemoryEncoderWorker: polls memory_encoding_events for LLM fact extraction
- MemoryExtractorWorker: polls memory_extraction_queue for slow-path extraction
- MemoryConsolidatorWorker: daily consolidation (decay, clustering, L4 promotion)

Controlled by HEART_WORKERS_ENABLED=true (default: false to avoid test interference).
"""

from __future__ import annotations

import asyncio
import os
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)


_worker_tasks: list[asyncio.Task] = []
_worker_stop_events: list[asyncio.Event] = []


async def start_workers() -> None:  # noqa: C901 — pre-existing complexity, tracked in branch debt
    """Start all background workers if HEART_WORKERS_ENABLED=true."""
    if os.getenv("HEART_WORKERS_ENABLED", "false").lower() != "true":
        logger.info("workers_disabled", hint="Set HEART_WORKERS_ENABLED=true to enable")
        return

    logger.info("workers_starting")

    # Start memory encoder worker
    try:
        from heart.api.wiring import _get_session_factory
        from heart.workers.memory_encoder import MemoryEncoderWorker

        factory = _get_session_factory()
        encoder = MemoryEncoderWorker(db_session_factory=factory)
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)

        task = asyncio.create_task(
            _run_until_stopped(encoder.start, stop_event),
            name="memory_encoder_worker",
        )
        _worker_tasks.append(task)
        logger.info("memory_encoder_worker_started")
    except Exception as e:
        logger.error("memory_encoder_worker_start_failed", error=str(e))

    # Start memory extractor worker (slow-path LLM extraction → embedding)
    try:
        from heart.workers.memory_extractor_worker import MemoryExtractorWorker

        factory = _get_session_factory()
        extractor = MemoryExtractorWorker(db_session_factory=factory)
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)

        task = asyncio.create_task(
            _run_until_stopped(extractor.start, stop_event),
            name="memory_extractor_worker",
        )
        _worker_tasks.append(task)
        logger.info("memory_extractor_worker_started")
    except Exception as e:
        logger.error("memory_extractor_worker_start_failed", error=str(e))

    # Start consolidator worker (daily at 03:00 or configurable interval)
    try:
        consolidation_interval = int(os.getenv("HEART_CONSOLIDATION_INTERVAL_S", "86400"))
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)

        task = asyncio.create_task(
            _run_consolidator_loop(consolidation_interval, stop_event),
            name="memory_consolidator_worker",
        )
        _worker_tasks.append(task)
        logger.info(
            "memory_consolidator_worker_started",
            interval_seconds=consolidation_interval,
        )
    except Exception as e:
        logger.error("memory_consolidator_worker_start_failed", error=str(e))

    # Start memory promoter worker (L3 → L4 identity fact promotion)
    try:
        import redis.asyncio as aioredis

        from heart.api.wiring import _get_session_factory
        from heart.workers.memory_promoter_worker import MemoryPromoterWorker

        factory = _get_session_factory()
        redis_client = aioredis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        promoter = MemoryPromoterWorker(
            db_session_factory=factory,
            redis_client=redis_client,
        )
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)

        task = asyncio.create_task(
            _run_until_stopped(promoter.start, stop_event),
            name="memory_promoter_worker",
        )
        _worker_tasks.append(task)
        logger.info("memory_promoter_worker_started")
    except Exception as e:
        logger.error("memory_promoter_worker_start_failed", error=str(e))

    # Start inner loop worker (proactive messages)
    if os.getenv("HEART_INNER_LOOP_ENABLED", "false").lower() == "true":
        try:
            from heart.ss06_inner_state.inner_loop_worker import InnerLoopWorker
            from heart.ss06_inner_state.service import InnerStateService

            factory = _get_session_factory()
            inner_svc = InnerStateService()
            inner_loop = InnerLoopWorker(
                db_session_factory=factory,
                inner_state_service=inner_svc,
            )
            stop_event = asyncio.Event()
            _worker_stop_events.append(stop_event)

            task = asyncio.create_task(
                _run_until_stopped(inner_loop.start, stop_event),
                name="inner_loop_worker",
            )
            _worker_tasks.append(task)
            logger.info("inner_loop_worker_started")
        except Exception as e:
            logger.error("inner_loop_worker_start_failed", error=str(e))

    logger.info("workers_started", count=len(_worker_tasks))

    # Start replay snapshots cleanup (daily)
    try:
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)
        task = asyncio.create_task(
            _run_replay_cleanup_loop(stop_event),
            name="replay_snapshots_cleanup",
        )
        _worker_tasks.append(task)
        logger.info("replay_snapshots_cleanup_started")
    except Exception as e:
        logger.error("replay_snapshots_cleanup_start_failed", error=str(e))

    # Start account purge worker (deletes data after 30-day grace period)
    try:
        from heart.workers.account_purge_worker import run_account_purge_loop

        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)
        task = asyncio.create_task(
            run_account_purge_loop(stop_event),
            name="account_purge_worker",
        )
        _worker_tasks.append(task)
        logger.info("account_purge_worker_started")
    except Exception as e:
        logger.error("account_purge_worker_start_failed", error=str(e))

    # Start credit reconciliation worker
    try:
        from heart.workers.credit_reconciliation_worker import run_credit_reconciliation_loop

        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)
        task = asyncio.create_task(
            run_credit_reconciliation_loop(stop_event),
            name="credit_reconciliation_worker",
        )
        _worker_tasks.append(task)
        logger.info("credit_reconciliation_worker_started")
    except Exception as e:
        logger.error("credit_reconciliation_worker_start_failed", error=str(e))

    # Start OTP cleanup worker (delete expired codes)
    try:
        stop_event = asyncio.Event()
        _worker_stop_events.append(stop_event)
        task = asyncio.create_task(
            _run_otp_cleanup_loop(stop_event),
            name="otp_cleanup_worker",
        )
        _worker_tasks.append(task)
        logger.info("otp_cleanup_worker_started")
    except Exception as e:
        logger.error("otp_cleanup_worker_start_failed", error=str(e))


async def stop_workers() -> None:
    """Stop all background workers gracefully."""
    logger.info("workers_stopping", count=len(_worker_stop_events))

    for event in _worker_stop_events:
        event.set()

    # Wait for tasks to complete with timeout
    if _worker_tasks:
        done, pending = await asyncio.wait(_worker_tasks, timeout=5.0)
        for task in pending:
            task.cancel()
            logger.warning("worker_task_cancelled", task_name=task.get_name())

    _worker_tasks.clear()
    _worker_stop_events.clear()
    logger.info("workers_stopped")


async def _run_until_stopped(coroutine_fn, stop_event: asyncio.Event) -> None:
    """Run a coroutine function until stop_event is set."""
    task = asyncio.current_task()
    task_name = task.get_name() if task else "unknown"
    try:
        await coroutine_fn()
    except asyncio.CancelledError:
        pass
    except Exception as e:
        # Use logger.error instead of logger.exception to avoid rich traceback bug
        logger.error("worker_unexpected_error", task_name=task_name, error=str(e))


async def _run_consolidator_loop(interval_s: int, stop_event: asyncio.Event) -> None:
    """Run consolidation worker until stopped.

    The ConsolidationWorker has its own internal loop that polls for
    pending consolidation jobs. We just run it until stop_event is set.
    """
    from heart.api.wiring import _get_session_factory
    from heart.workers.memory_consolidator import ConsolidationWorker

    factory = _get_session_factory()
    consolidator = ConsolidationWorker(db_session_factory=factory)

    try:
        await consolidator.start()
    except asyncio.CancelledError:
        await consolidator.stop()
    except Exception as e:
        logger.error("consolidator_unexpected_error", error=str(e))


async def _run_replay_cleanup_loop(stop_event: asyncio.Event) -> None:
    """Delete replay_snapshots older than 7 days. Runs once per day."""
    import os

    from sqlalchemy import text

    from heart.api.wiring import _get_session_factory

    interval_s = int(os.getenv("HEART_REPLAY_CLEANUP_INTERVAL_S", "86400"))
    retention_days = int(os.getenv("HEART_REPLAY_RETENTION_DAYS", "7"))

    factory = _get_session_factory()
    logger.info("replay_cleanup_started", retention_days=retention_days, interval_s=interval_s)

    while not stop_event.is_set():
        try:
            async with factory() as session:
                result = await session.execute(
                    text(
                        "DELETE FROM replay_snapshots WHERE created_at < NOW() - INTERVAL ':days days'"
                    ),
                    {"days": retention_days},
                )
                deleted = result.rowcount
                await session.commit()
                if deleted > 0:
                    logger.info(
                        "replay_snapshots_cleaned", deleted=deleted, retention_days=retention_days
                    )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("replay_cleanup_failed", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
            break  # stop_event was set
        except asyncio.TimeoutError:
            continue  # timeout reached, run cleanup again


async def _run_otp_cleanup_loop(stop_event: asyncio.Event) -> None:
    """Delete expired OTP codes older than 1 day. Runs every 6 hours."""
    from sqlalchemy import text

    from heart.api.wiring import _get_session_factory

    interval_s = int(os.getenv("HEART_OTP_CLEANUP_INTERVAL_S", "21600"))  # 6 hours
    factory = _get_session_factory()
    logger.info("otp_cleanup_started", interval_s=interval_s)

    while not stop_event.is_set():
        try:
            async with factory() as session:
                result = await session.execute(
                    text("DELETE FROM email_otp_codes WHERE expires_at < NOW() - INTERVAL '1 day'")
                )
                deleted = result.rowcount
                await session.commit()
                if deleted > 0:
                    logger.info("otp_codes_cleaned", deleted=deleted)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("otp_cleanup_failed", error=str(e))

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_s)
            break
        except asyncio.TimeoutError:
            continue
