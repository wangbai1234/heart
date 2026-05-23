"""
Inner Loop Scheduler — SS06 Inner State & Behavior §3.2, §10.3

Background worker that drives the autonomous inner loop for every active
(user, character) pair.  Handles both scheduled (hourly) ticks and
event-driven triggers (user message, schedule expiry, emotion threshold,
anniversary upcoming).

Architecture:
  - Scheduled ticks: Redis ZSET keyed by next_inner_loop_at, polled every ~30s
  - Event-driven: Pub/sub or direct call from API triggers
  - Distributed lock (Redis SETNX) per (user_id, character_id) prevents
    concurrent execution of the same inner-loop iteration.
  - Each iteration calls the Initiative Decider and, when act=True,
    routes to the Proactive Message Generator → Proactive Scheduler.

Per-iteration flow (per spec §3.5, §10.3):
  Step 1: Load context (Soul + Emotion + Relationship + Memory)
  Step 2: Update Inner State (mood, activities, concerns, energy, cleanup)
  Step 3: Behavior Decision (Initiative Decider — 8 gates × 7 triggers)
  Step 4: If initiate → Generate Proactive Message (via Persona Composer)
  Step 5: Schedule delivery (Proactive Scheduler with jitter)
  Step 6: Persist + emit events

Key invariants:
  - INV-I-1: Cross-modal single point of truth
  - INV-I-2: scheduled_at ∉ user_quiet_hours ∧ gap ≥ MIN_PROACTIVE_GAP
  - INV-I-3: Update completes < 200ms (no main LLM calls)
  - No double-execution: distributed lock per (user_id, character_id)

Spec:   runtime_specs/06_inner_state_behavior_runtime.md §3.2, §3.5, §10.3
Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol
from uuid import UUID, uuid4

import structlog

logger = structlog.get_logger()


# ============================================================
# Trigger types
# ============================================================


class LoopTrigger(str, Enum):
    """What caused this inner-loop iteration to fire."""
    SCHEDULED = "scheduled"         # Hourly tick
    USER_MESSAGE = "user_message"   # New user turn completed
    EMOTION_THRESHOLD = "emotion_threshold"  # Longing > 0.7, etc.
    SPECIAL_STATE = "special_state"  # Cold war / drifting / reunion entered
    ANNIVERSARY_UPCOMING = "anniversary_upcoming"  # 24h before anniversary
    COLD_START = "cold_start"       # First session for this (user, character)


# ============================================================
# Inner Loop Result
# ============================================================


@dataclass
class InnerLoopResult:
    """Result of a single inner-loop iteration."""
    iteration_id: UUID
    user_id: UUID
    character_id: str
    trigger: LoopTrigger
    triggered_at: datetime

    # Decision
    initiative_acted: bool = False
    initiative_type: Optional[str] = None
    initiative_reason: str = ""

    # Generated message (if any)
    generated_message: Optional[str] = None
    scheduled_for: Optional[datetime] = None

    # Timing
    duration_ms: float = 0.0
    error: Optional[str] = None

    # Events emitted
    events: List[str] = field(default_factory=list)


# ============================================================
# Protocol for dependency injection
# ============================================================


class RedisClient(Protocol):
    """Minimal Redis client interface for scheduling + distributed locks."""

    def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> bool | None: ...
    def get(self, name: str) -> bytes | None: ...
    def delete(self, *names: str) -> int: ...
    def zadd(self, name: str, mapping: Dict[str, float]) -> int: ...
    def zrangebyscore(
        self, name: str, min: float, max: float, withscores: bool = False,
        start: int | None = None, num: int | None = None,
    ) -> list: ...
    def zrem(self, name: str, *values: str) -> int: ...
    def keys(self, pattern: str) -> list: ...


class InnerStateStore(Protocol):
    """Protocol for loading/storing inner state (testable without real DB)."""

    async def load(self, user_id: UUID, character_id: str) -> Optional[Any]: ...
    async def save(self, state: Any) -> None: ...


class ContextLoader(Protocol):
    """Protocol for loading context slices (Soul, Emotion, Relationship, Memory)."""

    async def load_context(self, user_id: UUID, character_id: str) -> Dict[str, Any]: ...


class InitiativeDeciderProto(Protocol):
    """Protocol for the Initiative Decider (pure function, no I/O)."""

    def evaluate(self, ctx: Any) -> Any: ...


class ProactiveGeneratorProto(Protocol):
    """Protocol for the Proactive Message Generator."""

    async def generate(self, user_id: UUID, character_id: str, initiative_type: str, context: dict) -> Any: ...


class ProactiveSchedulerProto(Protocol):
    """Protocol for the Proactive Scheduler."""

    async def schedule(self, initiative: Any) -> Any: ...


# ============================================================
# Constants
# ============================================================

# Hourly tick interval (per spec §3.2)
DEFAULT_TICK_INTERVAL_HOURS = 1

# Poll interval for due iterations (seconds)
POLL_INTERVAL_SECONDS = 30

# Distributed lock TTL (seconds) — long enough to run one iteration
LOCK_TTL_SECONDS = 60

# Maximum retries for a failed iteration before marking as dead
MAX_CONSECUTIVE_FAILURES = 3

# Redis key templates
SCHEDULE_KEY = "inner_loop:schedule"              # ZSET: score = next_inner_loop_at
LOCK_KEY = "inner_loop:lock:{user_id}:{character_id}"
FAILURE_COUNT_KEY = "inner_loop:failures:{user_id}:{character_id}"
ACTIVE_SET_KEY = "inner_loop:active"               # SET of active user_id:character_id


# ============================================================
# Inner Loop Scheduler
# ============================================================


class InnerLoopScheduler:
    """Background worker that drives autonomous inner-loop iterations.

    Manages scheduled (hourly) + event-driven triggers for all active
    (user, character) pairs.

    Usage (production)::

        redis = aioredis.from_url(...)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=my_loader,
            inner_state_store=my_store,
            initiative_decider=my_decider,
            proactive_generator=my_generator,
            proactive_scheduler=my_scheduler,
        )

        # Run as background task
        asyncio.create_task(scheduler.run())

    Usage (testing — no real Redis)::

        scheduler = InnerLoopScheduler(
            redis=InMemoryRedis(),
            context_loader=FakeLoader(),
            ...
        )
        result = await scheduler.run_iteration(user_id, character_id, trigger=LoopTrigger.SCHEDULED)
    """

    def __init__(
        self,
        redis: RedisClient,
        context_loader: ContextLoader,
        inner_state_store: InnerStateStore,
        initiative_decider: InitiativeDeciderProto,
        proactive_generator: Optional[ProactiveGeneratorProto] = None,
        proactive_scheduler: Optional[ProactiveSchedulerProto] = None,
        tick_interval_hours: int = DEFAULT_TICK_INTERVAL_HOURS,
        poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
    ):
        self._redis = redis
        self._context_loader = context_loader
        self._inner_state_store = inner_state_store
        self._initiative_decider = initiative_decider
        self._proactive_generator = proactive_generator
        self._proactive_scheduler = proactive_scheduler
        self._tick_interval = timedelta(hours=tick_interval_hours)
        self._poll_interval = poll_interval_seconds

        # Track active pairs for fast cold-start
        self._active_pairs: set[tuple[UUID, str]] = set()

    # ─── Public API ───

    async def run_iteration(
        self,
        user_id: UUID,
        character_id: str,
        trigger: LoopTrigger = LoopTrigger.SCHEDULED,
    ) -> InnerLoopResult:
        """Execute a single inner-loop iteration.

        Per spec §10.3: load context → update inner state → decide → generate → schedule → persist.

        This is idempotent: each invocation independently locks, loads, and decides.
        """
        iteration_id = uuid4()
        triggered_at = datetime.now(timezone.utc)
        t0 = time.monotonic()

        result = InnerLoopResult(
            iteration_id=iteration_id,
            user_id=user_id,
            character_id=character_id,
            trigger=trigger,
            triggered_at=triggered_at,
        )

        # Acquire distributed lock
        lock_key = LOCK_KEY.format(user_id=user_id, character_id=character_id)
        lock_value = str(iteration_id)
        acquired = self._acquire_lock(lock_key, lock_value)

        if not acquired:
            result.error = "lock_contention"
            result.duration_ms = (time.monotonic() - t0) * 1000
            logger.debug(
                "inner_loop.skipped",
                user_id=str(user_id),
                character_id=character_id,
                reason="lock_contention",
            )
            return result

        try:
            # Step 1: Load context
            ctx = await self._context_loader.load_context(user_id, character_id)

            # Step 2: Load inner state
            inner_state = await self._inner_state_store.load(user_id, character_id)

            # Step 3: Build decider context
            decider_ctx = self._build_decider_context(user_id, character_id, ctx, inner_state)

            # Step 4: Behavior decision
            decision = self._initiative_decider.evaluate(decider_ctx)

            if decision.act:
                result.initiative_acted = True
                result.initiative_type = getattr(decision, "type", None)
                result.initiative_reason = getattr(decision, "reason", "")

                # Step 5: Generate proactive message
                if self._proactive_generator:
                    try:
                        initiative_type = str(result.initiative_type) if result.initiative_type else ""
                        proactive_ctx = getattr(decision, "context", {}) or {}
                        message = await self._proactive_generator.generate(
                            user_id, character_id, initiative_type, proactive_ctx,
                        )
                        result.generated_message = getattr(message, "text", str(message))

                        # Step 6: Schedule delivery
                        if self._proactive_scheduler:
                            scheduled = await self._proactive_scheduler.schedule(message)
                            result.scheduled_for = getattr(scheduled, "scheduled_for", None)
                            result.events.append("proactive_scheduled")
                    except Exception as e:
                        logger.warning(
                            "inner_loop.proactive_failed",
                            user_id=str(user_id),
                            character_id=character_id,
                            error=str(e),
                        )

            # Step 7: Compute next iteration time and reschedule
            next_at = self._compute_next_iteration_time(triggered_at)
            self._schedule_next(user_id, character_id, next_at)

            # Step 8: Persist inner state
            if inner_state:
                await self._inner_state_store.save(inner_state)

            # Clear failure count on success
            self._clear_failure_count(user_id, character_id)

            result.events.append("iteration_complete")

        except Exception as e:
            logger.error(
                "inner_loop.error",
                user_id=str(user_id),
                character_id=character_id,
                error=str(e),
                exc_info=True,
            )
            result.error = str(e)
            self._increment_failure_count(user_id, character_id)

        finally:
            # Release lock
            self._release_lock(lock_key, lock_value)
            result.duration_ms = (time.monotonic() - t0) * 1000

        return result

    async def on_user_message(self, user_id: UUID, character_id: str) -> None:
        """Event-driven trigger: new user message completed.

        Fires an inner-loop iteration to update state after user interaction.
        """
        await self.run_iteration(user_id, character_id, trigger=LoopTrigger.USER_MESSAGE)

    async def on_emotion_threshold(self, user_id: UUID, character_id: str) -> None:
        """Event-driven trigger: emotion threshold crossed (e.g., longing > 0.7)."""
        await self.run_iteration(user_id, character_id, trigger=LoopTrigger.EMOTION_THRESHOLD)

    async def on_special_state(self, user_id: UUID, character_id: str) -> None:
        """Event-driven trigger: special state entered (cold_war, drifting, reunion)."""
        await self.run_iteration(user_id, character_id, trigger=LoopTrigger.SPECIAL_STATE)

    async def on_anniversary_upcoming(self, user_id: UUID, character_id: str) -> None:
        """Event-driven trigger: anniversary within 24h window."""
        await self.run_iteration(user_id, character_id, trigger=LoopTrigger.ANNIVERSARY_UPCOMING)

    async def cold_start(self, user_id: UUID, character_id: str) -> InnerLoopResult:
        """First-time initialization for a new (user, character) pair."""
        result = await self.run_iteration(user_id, character_id, trigger=LoopTrigger.COLD_START)
        self._active_pairs.add((user_id, character_id))
        return result

    # ─── Background runner ───

    async def run(self) -> None:
        """Run as a background worker: poll due iterations and execute them.

        Intended to be run via asyncio.create_task().
        """
        logger.info("inner_loop_scheduler.started", poll_interval_s=self._poll_interval)

        while True:
            try:
                due = self._poll_due()
                for user_id, character_id in due:
                    # Fire-and-forget (don't block the poll loop)
                    asyncio.create_task(
                        self.run_iteration(user_id, character_id, trigger=LoopTrigger.SCHEDULED)
                    )
            except Exception:
                logger.exception("inner_loop_scheduler.poll_error")

            await asyncio.sleep(self._poll_interval)

    # ─── Schedule management ───

    def _schedule_next(self, user_id: UUID, character_id: str, next_at: datetime) -> None:
        """Schedule the next inner-loop tick for this pair."""
        key = self._schedule_key(user_id, character_id)
        score = next_at.timestamp()
        self._redis.zadd(SCHEDULE_KEY, {key: score})

    def _poll_due(self) -> List[tuple[UUID, str]]:
        """Return all (user_id, character_id) pairs whose next tick is due."""
        now_ts = datetime.now(timezone.utc).timestamp()
        raw = self._redis.zrangebyscore(SCHEDULE_KEY, 0, now_ts)

        pairs: List[tuple[UUID, str]] = []
        for member in raw:
            member_str = member.decode() if isinstance(member, bytes) else member
            try:
                uid_str, cid = member_str.split(":", 1)
                pairs.append((UUID(uid_str), cid))
            except (ValueError, AttributeError):
                logger.warning("inner_loop_scheduler.bad_member", member=member_str)

        return pairs

    def _schedule_key(self, user_id: UUID, character_id: str) -> str:
        """Build the ZSET member key for a (user, character) pair."""
        return f"{user_id}:{character_id}"

    def _compute_next_iteration_time(self, from_time: datetime) -> datetime:
        """Compute the next scheduled tick: +1 hour from now."""
        return from_time + self._tick_interval

    # ─── Distributed locking ───

    def _acquire_lock(self, key: str, value: str) -> bool:
        """Acquire a Redis SETNX lock."""
        result = self._redis.set(key, value, ex=LOCK_TTL_SECONDS, nx=True)
        # redis-py returns True/None, fakeredis may return bool
        return result is True or result is not None

    def _release_lock(self, key: str, value: str) -> None:
        """Release the lock (only if we still own it)."""
        current = self._redis.get(key)
        if current:
            current_str = current.decode() if isinstance(current, bytes) else current
            if current_str == value:
                self._redis.delete(key)

    # ─── Failure tracking ───

    def _increment_failure_count(self, user_id: UUID, character_id: str) -> int:
        """Increment consecutive failures, return new count."""
        key = FAILURE_COUNT_KEY.format(user_id=user_id, character_id=character_id)
        current = self._redis.get(key)
        count = int(current.decode()) if current else 0
        count += 1
        self._redis.set(key, str(count))
        return count

    def _clear_failure_count(self, user_id: UUID, character_id: str) -> None:
        """Reset failure count on success."""
        key = FAILURE_COUNT_KEY.format(user_id=user_id, character_id=character_id)
        self._redis.delete(key)

    # ─── Context building ───

    def _build_decider_context(
        self,
        user_id: UUID,
        character_id: str,
        ctx: Dict[str, Any],
        inner_state: Any,
    ) -> Any:
        """Build an InnerLoopContext suitable for the Initiative Decider.

        In production, this maps the loaded context slices into the
        InnerLoopContext dataclass expected by InitiativeDecider.evaluate().
        """
        from heart.ss06_inner_state.initiative_decider import (
            BehavioralEnvelope,
            EmotionState,
            InnerLoopContext,
            InnerStateSlice,
            RelationshipState,
            SoulSpec,
            Stage,
        )

        # Map relationship state
        rel = ctx.get("relationship", {})
        relationship_state = RelationshipState(
            current_stage=Stage(rel.get("current_stage", "LOVER")),
            behavioral_envelope=BehavioralEnvelope(
                can_initiate_conversation=rel.get("can_initiate", True),
            ),
            active_special_states=rel.get("active_special_states", []),
        )

        # Map soul spec
        soul_data = ctx.get("soul", {})
        soul_spec = SoulSpec(
            soul_id=soul_data.get("soul_id", character_id),
            min_gap_hours=soul_data.get("min_gap_hours", 6.0),
            daily_quota_max=soul_data.get("daily_quota_max", {"LOVER": 2, "BONDED": 3}),
            daily_quota_avg=soul_data.get("daily_quota_avg", 0.5),
            longing_threshold=soul_data.get("longing_threshold", 0.7),
            spark_probability=soul_data.get("spark_probability", 0.1),
            expected_gap_days=soul_data.get("expected_gap_days", {"LOVER": 4.0}),
        )

        # Map emotion state
        emo = ctx.get("emotion", {})
        emotion_state = EmotionState(
            longing_intensity=emo.get("longing_intensity", 0.0),
        )

        # Map inner state slice
        if inner_state:
            inner_slice = InnerStateSlice(
                proactive_count_today=getattr(inner_state, "proactive_state", None) and
                    getattr(inner_state.proactive_state, "proactive_today_count", 0) or 0,
                morning_check_in_done=getattr(inner_state, "rituals", None) and
                    getattr(inner_state.rituals, "daily_check_in", None) and
                    getattr(inner_state.rituals.daily_check_in, "morning_done_today", False) or False,
                night_check_in_done=getattr(inner_state, "rituals", None) and
                    getattr(inner_state.rituals, "daily_check_in", None) and
                    getattr(inner_state.rituals.daily_check_in, "night_done_today", False) or False,
            )
        else:
            inner_slice = InnerStateSlice()

        local_time = datetime.now()  # TODO: use user's timezone

        return InnerLoopContext(
            user_id=str(user_id),
            character_id=character_id,
            relationship_state=relationship_state,
            soul_spec=soul_spec,
            emotion_state=emotion_state,
            inner_state=inner_slice,
            local_time=local_time,
        )
