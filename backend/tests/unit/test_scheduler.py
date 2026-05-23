"""
Unit tests for Proactive Scheduler (SS06 §3.9, §10.1, §10.7).

Covers:
  - PendingInitiative JSON round-trip
  - Schedule: inserts into ZSET scored by scheduled_with_jitter
  - poll_due: returns only items where score ≤ now
  - poll_all_due: scans all user/character queue keys
  - Idempotency: mark_sent → is_already_sent guards double-fire
  - Cancel: single and bulk cancel
  - get_pending / count_pending queries
  - Dispatch lock acquire/release
  - ProactiveSender poll_and_dispatch with idempotency
  - Factory create_initiative with jitter
  - Edge cases: empty queue, JSON deserialization errors, concurrent locks
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from heart.ss06_inner_state.scheduler import (
    DEFAULT_JITTER_SECONDS,
    DISPATCH_LOCK_TTL,
    DispatchResult,
    PendingInitiative,
    ProactiveScheduler,
    ProactiveSender,
    ScheduleResult,
    _add_jitter,
    _to_timestamp,
    create_initiative,
)


# ============================================================
# In-memory Redis mock implementing RedisClient protocol
# ============================================================


class InMemoryRedis:
    """Fake Redis for testing — no external dependency needed.

    Implements the subset of RedisClient used by the scheduler:
    ZSET (zadd, zrangebyscore, zrem, zcard), SET (sadd, sismember, srem),
    STRING (set/get/delete), and key iteration (scan_iter, keys).
    """

    def __init__(self):
        self._data: dict[str, dict] = {}  # key → type-specific data
        self._zsets: dict[str, dict[str, float]] = {}  # name → {member: score}
        self._sets: dict[str, set[str]] = {}  # name → set of members
        self._strings: dict[str, str] = {}  # name → value
        self._expiry: dict[str, float] = {}  # name → expiry timestamp
        self._clock: float = 0.0

    def _now(self) -> float:
        import monotonic_time

        return self._clock if self._clock else 0.0

    # ─── ZSET ───

    def zadd(self, name: str, mapping: dict[str, float], nx: bool = False) -> int:
        if name not in self._zsets:
            self._zsets[name] = {}
        added = 0
        for member, score in mapping.items():
            if nx and member in self._zsets[name]:
                continue
            self._zsets[name][member] = score
            added += 1
        return added

    def zrangebyscore(
        self,
        name: str,
        min_val: float,
        max_val: float,
        withscores: bool = False,
        start: int | None = None,
        num: int | None = None,
    ) -> list:
        zset = self._zsets.get(name, {})
        # Collect members within score range
        scored: list[tuple[str, float]] = [
            (m, s) for m, s in zset.items() if min_val <= s <= max_val
        ]
        # Sort by score ascending
        scored.sort(key=lambda x: x[1])
        # Paginate
        if start is not None:
            scored = scored[start:]
        if num is not None:
            scored = scored[:num]
        if withscores:
            return scored
        return [m for m, _ in scored]

    def zrem(self, name: str, *values: str) -> int:
        zset = self._zsets.get(name, {})
        removed = 0
        for v in values:
            if v in zset:
                del zset[v]
                removed += 1
        return removed

    def zcard(self, name: str) -> int:
        return len(self._zsets.get(name, {}))

    # ─── SET ───

    def sadd(self, name: str, *values: str) -> int:
        if name not in self._sets:
            self._sets[name] = set()
        before = len(self._sets[name])
        for v in values:
            self._sets[name].add(v)
        after = len(self._sets[name])
        return after - before

    def sismember(self, name: str, value: str) -> bool:
        return value in self._sets.get(name, set())

    def srem(self, name: str, *values: str) -> int:
        s = self._sets.get(name, set())
        removed = 0
        for v in values:
            if v in s:
                s.discard(v)
                removed += 1
        return removed

    # ─── STRING ───

    def set(self, name: str, value: str, ex: int | None = None) -> bool:
        # SET NX: return False if key already exists
        if name in self._strings:
            return False
        self._strings[name] = value
        if ex is not None:
            # In a real test we don't enforce TTL on in-memory mock
            pass
        return True

    def get(self, name: str) -> bytes | None:
        v = self._strings.get(name)
        return v.encode() if v is not None else None

    def delete(self, *names: str) -> int:
        deleted = 0
        for n in names:
            if n in self._strings:
                del self._strings[n]
                deleted += 1
            if n in self._zsets:
                del self._zsets[n]
                deleted += 1
            if n in self._sets:
                del self._sets[n]
                deleted += 1
        return deleted

    # ─── Key iteration ───

    def scan_iter(
        self, match: str | None = None, count: int | None = None
    ) -> list:
        return self.keys(match or "*")

    def keys(self, pattern: str) -> list:
        import fnmatch

        all_keys = list(self._zsets.keys()) + list(self._sets.keys()) + list(self._strings.keys())
        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
def redis():
    """Fresh in-memory Redis instance."""
    return InMemoryRedis()


@pytest.fixture
def scheduler(redis):
    """Scheduler backed by in-memory Redis."""
    return ProactiveScheduler(redis)


@pytest.fixture
def user_id():
    return uuid4()


@pytest.fixture
def character_id():
    return "rin"


@pytest.fixture
def now():
    return datetime(2026, 5, 22, 14, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def initiative(user_id, character_id, now):
    """A sample pending initiative scheduled 30 min from 'now'."""
    return PendingInitiative(
        initiative_id=str(uuid4()),
        user_id=user_id,
        character_id=character_id,
        scheduled_at=now,
        scheduled_with_jitter=now + timedelta(minutes=30),
        initiative_type="longing_message",
        generated_message="……来都不来了。",
        status="ready",
    )


# ============================================================
# PendingInitiative JSON serialization
# ============================================================


class TestPendingInitiative:
    """JSON round-trip for ZSET member storage."""

    def test_round_trip(self, initiative):
        json_str = initiative.to_json()
        restored = PendingInitiative.from_json(json_str)
        assert restored.initiative_id == initiative.initiative_id
        assert restored.user_id == initiative.user_id
        assert restored.character_id == initiative.character_id
        assert restored.initiative_type == "longing_message"
        assert restored.generated_message == "……来都不来了。"
        assert restored.status == "ready"

    def test_round_trip_with_context(self, user_id, character_id):
        init = PendingInitiative(
            initiative_id=str(uuid4()),
            user_id=user_id,
            character_id=character_id,
            scheduled_at=datetime.now(timezone.utc),
            scheduled_with_jitter=datetime.now(timezone.utc),
            initiative_type="anniversary",
            generated_message="生日快乐。",
            context={"anniversary_name": "user_birthday", "hours_until": 0},
        )
        json_str = init.to_json()
        restored = PendingInitiative.from_json(json_str)
        assert restored.context["anniversary_name"] == "user_birthday"

    def test_from_json_handles_missing_fields(self):
        raw = '{"initiative_id": "abc", "user_id": "00000000-0000-0000-0000-000000000001", "character_id": "rin", "scheduled_at": "2026-05-22T14:30:00+00:00", "scheduled_with_jitter": "2026-05-22T14:35:00+00:00"}'
        restored = PendingInitiative.from_json(raw)
        assert restored.initiative_id == "abc"
        assert restored.generated_message == ""
        assert restored.status == "ready"


# ============================================================
# Schedule
# ============================================================


class TestSchedule:
    """Inserting initiatives into the ZSET."""

    def test_schedule_inserts_into_zset(self, scheduler, initiative):
        result = scheduler.schedule(initiative)
        assert result.success
        assert result.initiative_id == initiative.initiative_id

        # Should be in the queue
        assert scheduler.count_pending(initiative.user_id, initiative.character_id) == 1

    def test_schedule_multiple_ordered_by_score(
        self, scheduler, user_id, character_id, now
    ):
        # Insert 3 items with different scheduled times
        for offset_minutes in [60, 10, 30]:
            init = create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message=f"message at +{offset_minutes}m",
                scheduled_at=now + timedelta(minutes=offset_minutes),
                apply_jitter=False,
            )
            scheduler.schedule(init)

        assert scheduler.count_pending(user_id, character_id) == 3

        # poll_due with now = +20 min should only return the 10-min item
        due = scheduler.poll_due(
            user_id, character_id, now=now + timedelta(minutes=20)
        )
        assert len(due) == 1
        assert "at +10m" in due[0].generated_message

    def test_schedule_with_jitter_applied(self, scheduler, user_id, character_id, now):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="ritual_morning",
            generated_message="……早。",
            scheduled_at=now,
            apply_jitter=True,
        )
        # scheduled_with_jitter should be within ±5 min of base
        delta = abs(
            (init.scheduled_with_jitter - init.scheduled_at).total_seconds()
        )
        assert 0 <= delta <= 300  # ≤ 5 minutes

        result = scheduler.schedule(init)
        assert result.success


# ============================================================
# Poll due
# ============================================================


class TestPollDue:
    """Retrieving items whose scheduled_with_jitter has passed."""

    def test_returns_empty_when_no_due_items(
        self, scheduler, user_id, character_id, initiative, now
    ):
        scheduler.schedule(initiative)  # scheduled 30 min from now
        due = scheduler.poll_due(user_id, character_id, now=now)
        assert due == []

    def test_returns_item_when_due(self, scheduler, user_id, character_id, now):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="……还活着。",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        scheduler.schedule(init)
        due = scheduler.poll_due(user_id, character_id, now=now)
        assert len(due) == 1
        assert due[0].initiative_id == init.initiative_id

    def test_respects_limit(self, scheduler, user_id, character_id, now):
        for i in range(5):
            init = create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message=f"msg-{i}",
                scheduled_at=now - timedelta(minutes=10),
                apply_jitter=False,
            )
            scheduler.schedule(init)

        due = scheduler.poll_due(user_id, character_id, now=now, limit=3)
        assert len(due) == 3

    def test_poll_all_due_across_users(
        self, scheduler, now
    ):
        uid1 = uuid4()
        uid2 = uuid4()

        init1 = create_initiative(
            user_id=uid1,
            character_id="rin",
            initiative_type="check_in",
            generated_message="due-1",
            scheduled_at=now - timedelta(minutes=1),
            apply_jitter=False,
        )
        init2 = create_initiative(
            user_id=uid2,
            character_id="dorothy",
            initiative_type="longing_message",
            generated_message="due-2",
            scheduled_at=now - timedelta(minutes=2),
            apply_jitter=False,
        )
        scheduler.schedule(init1)
        scheduler.schedule(init2)

        all_due = scheduler.poll_all_due(now=now)
        assert len(all_due) == 2
        # Oldest first
        assert all_due[0].generated_message == "due-2"

    def test_poll_all_due_respects_limit(self, scheduler, now):
        for i in range(10):
            uid = uuid4()
            init = create_initiative(
                user_id=uid,
                character_id="rin",
                initiative_type="check_in",
                generated_message=f"due-{i}",
                scheduled_at=now - timedelta(minutes=i),
                apply_jitter=False,
            )
            scheduler.schedule(init)

        all_due = scheduler.poll_all_due(now=now, limit=5)
        assert len(all_due) == 5


# ============================================================
# Idempotency
# ============================================================


class TestIdempotency:
    """Never double-fire the same initiative."""

    def test_is_already_sent_false_before_marking(
        self, scheduler, initiative
    ):
        scheduler.schedule(initiative)
        assert not scheduler.is_already_sent(
            initiative.initiative_id, initiative.user_id, initiative.character_id
        )

    def test_mark_sent_makes_is_already_sent_true(
        self, scheduler, initiative
    ):
        scheduler.schedule(initiative)
        result = scheduler.mark_sent(initiative)
        assert result  # True = first time marking

        assert scheduler.is_already_sent(
            initiative.initiative_id, initiative.user_id, initiative.character_id
        )

    def test_mark_sent_removes_from_queue(
        self, scheduler, initiative
    ):
        scheduler.schedule(initiative)
        assert scheduler.count_pending(
            initiative.user_id, initiative.character_id
        ) == 1

        scheduler.mark_sent(initiative)
        assert scheduler.count_pending(
            initiative.user_id, initiative.character_id
        ) == 0

    def test_mark_sent_twice_returns_false(self, scheduler, initiative):
        scheduler.schedule(initiative)
        assert scheduler.mark_sent(initiative)  # first time
        assert not scheduler.mark_sent(initiative)  # second time (idempotent)

    def test_get_pending_returns_none_after_mark_sent(
        self, scheduler, user_id, character_id, now
    ):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="msg",
            scheduled_at=now,
            apply_jitter=False,
        )
        scheduler.schedule(init)
        assert scheduler.get_pending(user_id, character_id) is not None
        scheduler.mark_sent(init)
        assert scheduler.get_pending(user_id, character_id) is None


# ============================================================
# Cancel
# ============================================================


class TestCancel:
    """Cancelling pending initiatives."""

    def test_cancel_single(self, scheduler, user_id, character_id, now):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="msg",
            scheduled_at=now,
            apply_jitter=False,
        )
        scheduler.schedule(init)

        removed = scheduler.cancel(
            init.initiative_id, user_id, character_id
        )
        assert removed == 1
        assert scheduler.count_pending(user_id, character_id) == 0

    def test_cancel_nonexistent(self, scheduler, user_id, character_id):
        removed = scheduler.cancel("fake-id", user_id, character_id)
        assert removed == 0

    def test_cancel_all(self, scheduler, user_id, character_id, now):
        for _ in range(3):
            init = create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message="msg",
                scheduled_at=now,
                apply_jitter=False,
            )
            scheduler.schedule(init)

        assert scheduler.count_pending(user_id, character_id) == 3
        removed = scheduler.cancel_all(user_id, character_id)
        assert removed == 3
        assert scheduler.count_pending(user_id, character_id) == 0

    def test_cancel_all_empty_queue(self, scheduler, user_id, character_id):
        removed = scheduler.cancel_all(user_id, character_id)
        assert removed == 0


# ============================================================
# Queries
# ============================================================


class TestQueries:
    """get_pending and count_pending."""

    def test_get_pending_returns_next(self, scheduler, user_id, character_id, now):
        early = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="early",
            scheduled_at=now + timedelta(minutes=5),
            apply_jitter=False,
        )
        late = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="late",
            scheduled_at=now + timedelta(minutes=60),
            apply_jitter=False,
        )
        scheduler.schedule(early)
        scheduler.schedule(late)

        next_pending = scheduler.get_pending(user_id, character_id)
        assert next_pending is not None
        assert next_pending.generated_message == "early"

    def test_get_pending_empty(self, scheduler, user_id, character_id):
        assert scheduler.get_pending(user_id, character_id) is None

    def test_count_pending(self, scheduler, user_id, character_id, now):
        assert scheduler.count_pending(user_id, character_id) == 0
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="x",
            scheduled_at=now,
            apply_jitter=False,
        )
        scheduler.schedule(init)
        assert scheduler.count_pending(user_id, character_id) == 1


# ============================================================
# Dispatch lock
# ============================================================


class TestDispatchLock:
    """Concurrency mutex for worker dispatch."""

    def test_acquire_lock_succeeds(self, scheduler):
        iid = str(uuid4())
        acquired = scheduler.acquire_dispatch_lock(iid)
        assert acquired

    def test_second_acquire_fails(self, scheduler):
        iid = str(uuid4())
        assert scheduler.acquire_dispatch_lock(iid)
        assert not scheduler.acquire_dispatch_lock(iid)

    def test_release_and_reacquire(self, scheduler):
        iid = str(uuid4())
        assert scheduler.acquire_dispatch_lock(iid)
        scheduler.release_dispatch_lock(iid)
        assert scheduler.acquire_dispatch_lock(iid)


# ============================================================
# ProactiveSender — poll_and_dispatch
# ============================================================


class TestProactiveSender:
    """Background worker dispatch logic with idempotency."""

    @pytest.fixture
    def sender(self, scheduler):
        return ProactiveSender(scheduler)

    def test_dispatches_due_item(self, sender, scheduler, user_id, character_id, now):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="longing_message",
            generated_message="……还活着。",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        scheduler.schedule(init)

        results = sender.poll_and_dispatch(now=now)
        assert len(results) == 1
        assert results[0].dispatched
        assert results[0].initiative_id == init.initiative_id
        assert results[0].message == "……还活着。"

    def test_does_not_dispatch_future_items(
        self, sender, scheduler, user_id, character_id, now
    ):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="ritual_night",
            generated_message="……早点睡。",
            scheduled_at=now + timedelta(hours=2),
            apply_jitter=False,
        )
        scheduler.schedule(init)

        results = sender.poll_and_dispatch(now=now)
        assert len(results) == 0

    def test_idempotency_no_double_fire(
        self, sender, scheduler, user_id, character_id, now
    ):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="msg",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        scheduler.schedule(init)

        # First dispatch
        results1 = sender.poll_and_dispatch(now=now)
        assert results1[0].dispatched

        # Second dispatch on same items → should skip (already sent)
        results2 = sender.poll_and_dispatch(now=now)
        assert len(results2) == 0

    def test_dispatches_only_due_items_mixed(
        self, sender, scheduler, user_id, character_id, now
    ):
        # One due, two future
        due = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="due",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        future1 = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="ritual_morning",
            generated_message="future1",
            scheduled_at=now + timedelta(minutes=10),
            apply_jitter=False,
        )
        future2 = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="ritual_night",
            generated_message="future2",
            scheduled_at=now + timedelta(hours=3),
            apply_jitter=False,
        )
        scheduler.schedule(due)
        scheduler.schedule(future1)
        scheduler.schedule(future2)

        results = sender.poll_and_dispatch(now=now)
        assert len(results) == 1
        assert results[0].initiative_id == due.initiative_id

        # Future items still pending
        assert scheduler.count_pending(user_id, character_id) == 2

    def test_custom_dispatch_callback(
        self, scheduler, user_id, character_id, now
    ):
        """Inject a real dispatch callback and verify it's called."""
        dispatched_ids = []

        def collector(init: PendingInitiative) -> DispatchResult:
            dispatched_ids.append(init.initiative_id)
            return DispatchResult(
                initiative_id=init.initiative_id,
                dispatched=True,
                reason="collected",
                message=init.generated_message,
            )

        sender = ProactiveSender(scheduler, on_dispatch=collector)

        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="anniversary",
            generated_message="生日快乐。",
            scheduled_at=now - timedelta(minutes=1),
            apply_jitter=False,
        )
        scheduler.schedule(init)

        results = sender.poll_and_dispatch(now=now)
        assert len(dispatched_ids) == 1
        assert dispatched_ids[0] == init.initiative_id
        assert results[0].dispatched

    def test_callback_returns_not_dispatched_skips_mark_sent(
        self, scheduler, user_id, character_id, now
    ):
        def fail_dispatcher(init: PendingInitiative) -> DispatchResult:
            return DispatchResult(
                initiative_id=init.initiative_id,
                dispatched=False,
                reason="push_service_down",
            )

        sender = ProactiveSender(scheduler, on_dispatch=fail_dispatcher)

        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="msg",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        scheduler.schedule(init)

        results = sender.poll_and_dispatch(now=now)
        assert not results[0].dispatched

        # Should NOT be marked sent → still pending
        assert not scheduler.is_already_sent(
            init.initiative_id, user_id, character_id
        )
        assert scheduler.count_pending(user_id, character_id) == 1


# ============================================================
# Factory and helpers
# ============================================================


class TestCreateInitiative:
    """create_initiative factory."""

    def test_creates_with_defaults(self, user_id, character_id):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="thought_share",
            generated_message="刚才在看书。",
            apply_jitter=False,
        )
        assert init.initiative_id
        assert init.user_id == user_id
        assert init.character_id == character_id
        assert init.initiative_type == "thought_share"
        assert init.generated_message == "刚才在看书。"
        assert init.status == "ready"
        assert init.scheduled_at == init.scheduled_with_jitter  # jitter=False

    def test_jitter_applied(self, user_id, character_id):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="care_check",
            generated_message="……还没睡？",
            apply_jitter=True,
        )
        delta = abs(
            (init.scheduled_with_jitter - init.scheduled_at).total_seconds()
        )
        assert 0 <= delta <= DEFAULT_JITTER_SECONDS  # 300 seconds = 5 min

    def test_explicit_scheduled_at(self, user_id, character_id):
        target = datetime(2026, 5, 23, 8, 0, 0, tzinfo=timezone.utc)
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="ritual_morning",
            generated_message="早安。",
            scheduled_at=target,
            apply_jitter=False,
        )
        assert init.scheduled_at == target


class TestHelpers:
    """Timestamp and jitter helpers."""

    def test_to_timestamp_roundtrip(self):
        dt = datetime(2026, 5, 22, 14, 30, 0, tzinfo=timezone.utc)
        ts = _to_timestamp(dt)
        assert ts == dt.timestamp()

    def test_add_jitter_range(self):
        base = datetime(2026, 5, 22, 12, 0, 0, tzinfo=timezone.utc)
        import random

        rng = random.Random(42)
        for _ in range(100):
            jittered = _add_jitter(base, jitter_seconds=300, rng=rng)
            delta = abs((jittered - base).total_seconds())
            assert 0 <= delta <= 300


# ============================================================
# Edge cases
# ============================================================


class TestEdgeCases:
    """Boundary conditions and error handling."""

    def test_poll_due_empty_queue(self, scheduler, user_id, character_id, now):
        due = scheduler.poll_due(user_id, character_id, now=now)
        assert due == []

    def test_poll_all_due_no_queues(self, scheduler, now):
        assert scheduler.poll_all_due(now=now) == []

    def test_schedule_then_cancel_all_then_poll(self, scheduler, user_id, character_id, now):
        init = create_initiative(
            user_id=user_id,
            character_id=character_id,
            initiative_type="check_in",
            generated_message="msg",
            scheduled_at=now - timedelta(minutes=5),
            apply_jitter=False,
        )
        scheduler.schedule(init)
        scheduler.cancel_all(user_id, character_id)

        due = scheduler.poll_due(user_id, character_id, now=now)
        assert due == []

    def test_multiple_schedules_same_score(self, scheduler, user_id, character_id, now):
        """Multiple items with identical scores are all stored."""
        for i in range(3):
            init = create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message=f"msg-{i}",
                scheduled_at=now,
                apply_jitter=False,
            )
            scheduler.schedule(init)

        assert scheduler.count_pending(user_id, character_id) == 3

    def test_schedule_result_position(self, scheduler, user_id, character_id, now):
        """ScheduleResult.position reflects queue size after insertion."""
        result1 = scheduler.schedule(
            create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message="first",
                scheduled_at=now,
                apply_jitter=False,
            )
        )
        assert result1.position >= 1

        result2 = scheduler.schedule(
            create_initiative(
                user_id=user_id,
                character_id=character_id,
                initiative_type="check_in",
                generated_message="second",
                scheduled_at=now,
                apply_jitter=False,
            )
        )
        assert result2.position >= 2
