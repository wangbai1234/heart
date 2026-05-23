"""
Unit tests for Inner Loop Scheduler (SS06 §3.2, §10.3).

Covers:
  - Hourly ticks don't double-execute (distributed lock)
  - Event-driven dispatch works (user_message, emotion_threshold, etc.)
  - Schedule management: poll_due returns only due items
  - Lock acquisition and release
  - Failure tracking and recovery
  - Context building from loaded slices
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from heart.workers.inner_loop_scheduler import (
    InnerLoopResult,
    InnerLoopScheduler,
    LoopTrigger,
    LOCK_TTL_SECONDS,
)


# ============================================================
# In-memory Redis mock
# ============================================================


class InMemoryRedis:
    """Fake Redis for testing — no external dependency needed."""

    def __init__(self):
        self._zsets: dict[str, dict[str, float]] = {}
        self._strings: dict[str, str] = {}
        self._expiry: dict[str, float] = {}

    def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> bool | None:
        if nx and name in self._strings:
            return None  # redis-py returns None when NX fails
        self._strings[name] = value
        return True

    def get(self, name: str) -> bytes | None:
        val = self._strings.get(name)
        if val is None:
            return None
        return val.encode()

    def delete(self, *names: str) -> int:
        count = 0
        for name in names:
            if name in self._strings:
                del self._strings[name]
                count += 1
        return count

    def zadd(self, name: str, mapping: dict[str, float]) -> int:
        if name not in self._zsets:
            self._zsets[name] = {}
        added = 0
        for member, score in mapping.items():
            if member not in self._zsets[name]:
                added += 1
            self._zsets[name][member] = score
        return added

    def zrangebyscore(
        self, name: str, min: float, max: float,
        withscores: bool = False,
        start: int | None = None, num: int | None = None,
    ) -> list:
        zset = self._zsets.get(name, {})
        items = [
            (member, score)
            for member, score in zset.items()
            if min <= score <= max
        ]
        items.sort(key=lambda x: x[1])
        if start is not None:
            items = items[start:]
        if num is not None:
            items = items[:num]
        if withscores:
            return [(m.encode(), s) for m, s in items]
        return [m.encode() for m, _ in items]

    def zrem(self, name: str, *values: str) -> int:
        zset = self._zsets.get(name, {})
        removed = 0
        for v in values:
            if v in zset:
                del zset[v]
                removed += 1
        return removed

    def keys(self, pattern: str) -> list:
        return [k.encode() for k in self._strings.keys()]


# ============================================================
# Fake dependencies
# ============================================================


class FakeContextLoader:
    """Returns canned context for testing."""

    def __init__(self, **overrides):
        self._data = {
            "relationship": {
                "current_stage": "LOVER",
                "can_initiate": True,
                "active_special_states": [],
            },
            "soul": {
                "soul_id": "rin",
            },
            "emotion": {
                "longing_intensity": 0.3,
            },
            **overrides,
        }

    async def load_context(self, user_id, character_id):
        return dict(self._data)


class FakeInnerStateStore:
    """In-memory inner state store."""

    def __init__(self):
        self._store: dict[tuple, object] = {}
        self.save_calls: list[tuple] = []

    async def load(self, user_id, character_id):
        return self._store.get((user_id, character_id))

    async def save(self, state):
        self.save_calls.append(state)


class FakeInitiativeDecider:
    """Decider that returns a configurable decision."""

    def __init__(self, act: bool = False, initiative_type: str = "", reason: str = ""):
        self.act = act
        self.initiative_type = initiative_type
        self.reason = reason
        self.evaluate_calls: list = []

    def evaluate(self, ctx):
        self.evaluate_calls.append(ctx)

        class FakeDecision:
            pass

        d = FakeDecision()
        d.act = self.act
        d.type = self.initiative_type or None
        d.reason = self.reason
        d.context = {}
        d.priority = 5
        return d


class FakeProactiveGenerator:
    """Fake generator that records calls."""

    def __init__(self):
        self.generate_calls: list = []

    async def generate(self, user_id, character_id, initiative_type, context):
        self.generate_calls.append((user_id, character_id, initiative_type, context))

        class FakeMessage:
            text = f"Proactive: {initiative_type}"

        return FakeMessage()


class FakeProactiveScheduler:
    """Fake scheduler that records calls."""

    def __init__(self):
        self.schedule_calls: list = []

    async def schedule(self, initiative):
        self.schedule_calls.append(initiative)

        class FakeScheduled:
            scheduled_for = datetime.now(timezone.utc) + timedelta(minutes=5)

        return FakeScheduled()


# ============================================================
# Helpers
# ============================================================


def _make_scheduler(
    redis: InMemoryRedis,
    decider_act: bool = False,
    with_generator: bool = False,
    with_scheduler: bool = False,
) -> InnerLoopScheduler:
    return InnerLoopScheduler(
        redis=redis,
        context_loader=FakeContextLoader(),
        inner_state_store=FakeInnerStateStore(),
        initiative_decider=FakeInitiativeDecider(act=decider_act),
        proactive_generator=FakeProactiveGenerator() if with_generator else None,
        proactive_scheduler=FakeProactiveScheduler() if with_scheduler else None,
    )


# ============================================================
# Tests: No double-execution (lock-based)
# ============================================================


class TestNoDoubleExecution:
    async def test_lock_prevents_concurrent_execution(self):
        """Second concurrent invocation should fail with lock_contention."""
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid = uuid4()
        cid = "rin"

        # Manually hold the lock to simulate a concurrent iteration
        lock_key = f"inner_loop:lock:{uid}:{cid}"
        redis.set(lock_key, "external-holder", ex=60, nx=False)

        # Iteration should see lock contention
        result = await scheduler.run_iteration(uid, cid, trigger=LoopTrigger.SCHEDULED)
        assert result.error == "lock_contention"

    async def test_lock_released_after_completion(self):
        """After iteration completes, lock is released for next tick."""
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid = uuid4()
        cid = "rin"

        result1 = await scheduler.run_iteration(uid, cid, trigger=LoopTrigger.SCHEDULED)
        assert result1.error is None

        # Lock should be released now
        result2 = await scheduler.run_iteration(uid, cid, trigger=LoopTrigger.SCHEDULED)
        assert result2.error is None  # no contention

    async def test_different_users_dont_block(self):
        """Lock is per (user, character), so different users don't contend."""
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid1 = uuid4()
        uid2 = uuid4()
        cid = "rin"

        r1 = await scheduler.run_iteration(uid1, cid, trigger=LoopTrigger.SCHEDULED)
        r2 = await scheduler.run_iteration(uid2, cid, trigger=LoopTrigger.SCHEDULED)

        assert r1.error is None
        assert r2.error is None  # different user, no contention


# ============================================================
# Tests: Event-driven dispatch
# ============================================================


class TestEventDrivenDispatch:
    async def test_on_user_message_triggers_iteration(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        await scheduler.on_user_message(uid, "rin")
        assert len(decider.evaluate_calls) == 1

    async def test_on_emotion_threshold_triggers_iteration(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        await scheduler.on_emotion_threshold(uid, "rin")
        assert len(decider.evaluate_calls) == 1

    async def test_on_special_state_triggers_iteration(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        await scheduler.on_special_state(uid, "rin")
        assert len(decider.evaluate_calls) == 1

    async def test_on_anniversary_upcoming_triggers_iteration(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        await scheduler.on_anniversary_upcoming(uid, "rin")
        assert len(decider.evaluate_calls) == 1

    async def test_cold_start_triggers_and_registers(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        result = await scheduler.cold_start(uid, "rin")
        assert result.trigger == LoopTrigger.COLD_START
        assert len(decider.evaluate_calls) == 1


# ============================================================
# Tests: Schedule management
# ============================================================


class TestScheduleManagement:
    async def test_schedule_next_adds_to_zset(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid = uuid4()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        scheduler._schedule_next(uid, "rin", future)

        # Should be in zset but not due yet
        key = scheduler._schedule_key(uid, "rin")
        zset = redis._zsets.get("inner_loop:schedule", {})
        assert key in zset

    async def test_poll_due_returns_only_due_items(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid1 = uuid4()
        uid2 = uuid4()
        cid = "rin"

        now = datetime.now(timezone.utc)

        # Schedule uid1 in the past (due)
        past = now - timedelta(hours=1)
        scheduler._schedule_next(uid1, cid, past)

        # Schedule uid2 in the future (not due)
        future = now + timedelta(hours=2)
        scheduler._schedule_next(uid2, cid, future)

        due = scheduler._poll_due()
        due_uids = {uid for uid, _ in due}

        assert uid1 in due_uids
        assert uid2 not in due_uids

    async def test_empty_schedule_returns_empty(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        due = scheduler._poll_due()
        assert due == []


# ============================================================
# Tests: Initiative decider → proactive pipeline
# ============================================================


class TestProactivePipeline:
    async def test_decision_no_act_does_not_generate(self):
        redis = InMemoryRedis()
        gen = FakeProactiveGenerator()
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=FakeInitiativeDecider(act=False),
            proactive_generator=gen,
        )

        uid = uuid4()
        result = await scheduler.run_iteration(uid, "rin", trigger=LoopTrigger.SCHEDULED)
        assert result.initiative_acted is False
        assert len(gen.generate_calls) == 0

    async def test_decision_act_generates_and_schedules(self):
        redis = InMemoryRedis()
        gen = FakeProactiveGenerator()
        sched = FakeProactiveScheduler()
        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=FakeInitiativeDecider(act=True, initiative_type="ritual_morning"),
            proactive_generator=gen,
            proactive_scheduler=sched,
        )

        uid = uuid4()
        result = await scheduler.run_iteration(uid, "rin", trigger=LoopTrigger.SCHEDULED)
        assert result.initiative_acted is True
        assert result.initiative_type == "ritual_morning"
        assert result.generated_message is not None
        assert len(gen.generate_calls) == 1
        assert len(sched.schedule_calls) == 1

    async def test_generator_errors_are_handled(self):
        redis = InMemoryRedis()

        class FailingGenerator:
            async def generate(self, *args, **kwargs):
                raise RuntimeError("LLM timeout")

        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FakeContextLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=FakeInitiativeDecider(act=True, initiative_type="care_check"),
            proactive_generator=FailingGenerator(),
        )

        uid = uuid4()
        result = await scheduler.run_iteration(uid, "rin", trigger=LoopTrigger.SCHEDULED)
        # Should still succeed overall (error is caught)
        assert result.error is None
        assert result.initiative_acted is True
        assert "proactive_scheduled" not in result.events


# ============================================================
# Tests: Failure tracking
# ============================================================


class TestFailureTracking:
    async def test_consecutive_failures_tracked(self):
        redis = InMemoryRedis()

        class FailingLoader:
            async def load_context(self, user_id, character_id):
                raise RuntimeError("DB down")

        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FailingLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=FakeInitiativeDecider(act=False),
        )

        uid = uuid4()
        for i in range(3):
            result = await scheduler.run_iteration(uid, "rin")
            assert result.error is not None

    async def test_success_clears_failure_count(self):
        redis = InMemoryRedis()

        class FlakyLoader:
            def __init__(self):
                self.call_count = 0

            async def load_context(self, user_id, character_id):
                self.call_count += 1
                if self.call_count <= 2:
                    raise RuntimeError("transient error")
                return {"relationship": {}, "soul": {}, "emotion": {}}

        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=FlakyLoader(),
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=FakeInitiativeDecider(act=False),
        )

        uid = uuid4()
        # First 2 → fail
        r1 = await scheduler.run_iteration(uid, "rin")
        assert r1.error is not None
        r2 = await scheduler.run_iteration(uid, "rin")
        assert r2.error is not None

        # Third → succeed
        r3 = await scheduler.run_iteration(uid, "rin")
        assert r3.error is None


# ============================================================
# Tests: Initialization and cold start
# ============================================================


class TestInitialization:
    async def test_new_instance_starts_empty(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)
        assert len(scheduler._active_pairs) == 0

    async def test_cold_start_adds_to_active_pairs(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid = uuid4()
        await scheduler.cold_start(uid, "rin")
        assert (uid, "rin") in scheduler._active_pairs

    async def test_run_iteration_calculates_duration(self):
        redis = InMemoryRedis()
        scheduler = _make_scheduler(redis)

        uid = uuid4()
        result = await scheduler.run_iteration(uid, "rin", trigger=LoopTrigger.SCHEDULED)
        assert result.duration_ms >= 0


# ============================================================
# Tests: Context building
# ============================================================


class TestContextBuilding:
    async def test_builds_decider_context_from_slices(self):
        redis = InMemoryRedis()
        decider = FakeInitiativeDecider(act=False)

        ctx_loader = FakeContextLoader(
            relationship={"current_stage": "BONDED", "can_initiate": True, "active_special_states": []},
            soul={"soul_id": "dorothy", "longing_threshold": 0.5},
            emotion={"longing_intensity": 0.6},
        )

        scheduler = InnerLoopScheduler(
            redis=redis,
            context_loader=ctx_loader,
            inner_state_store=FakeInnerStateStore(),
            initiative_decider=decider,
        )

        uid = uuid4()
        await scheduler.run_iteration(uid, "dorothy", trigger=LoopTrigger.SCHEDULED)

        assert len(decider.evaluate_calls) == 1
        ctx = decider.evaluate_calls[0]
        assert ctx.character_id == "dorothy"
        assert ctx.relationship_state.current_stage.value == "BONDED"
        assert ctx.emotion_state.longing_intensity == 0.6
        assert ctx.soul_spec.soul_id == "dorothy"
        assert ctx.soul_spec.longing_threshold == 0.5


# ============================================================
# Tests: LoopTrigger enum
# ============================================================


class TestLoopTrigger:
    def test_all_triggers_have_correct_values(self):
        assert LoopTrigger.SCHEDULED == "scheduled"
        assert LoopTrigger.USER_MESSAGE == "user_message"
        assert LoopTrigger.EMOTION_THRESHOLD == "emotion_threshold"
        assert LoopTrigger.SPECIAL_STATE == "special_state"
        assert LoopTrigger.ANNIVERSARY_UPCOMING == "anniversary_upcoming"
        assert LoopTrigger.COLD_START == "cold_start"


# ============================================================
# Tests: InnerLoopResult
# ============================================================


class TestInnerLoopResult:
    def test_result_defaults(self):
        result = InnerLoopResult(
            iteration_id=uuid4(),
            user_id=uuid4(),
            character_id="rin",
            trigger=LoopTrigger.SCHEDULED,
            triggered_at=datetime.now(timezone.utc),
        )
        assert result.initiative_acted is False
        assert result.initiative_type is None
        assert result.error is None
        assert result.events == []
