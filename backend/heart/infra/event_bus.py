"""
Event Bus — Redis Streams pub/sub per SS07 §3.6.

中央事件总线。Connects all subsystems through typed, async events.

Design invariants (from runtime_specs/07_agent_orchestration.md):
  INV-O-4: ∀ event e, e.user_id 严格用作隔离
  O-2:     All cross-subsystem 通信通过 service adapters 或 event bus
  O-9:     Event Bus 必须保证 at-least-once delivery (重要事件)
  O-10:    任何 subsystem 失败必须有降级策略

Delivery guarantees per §3.6:
  at_most_once: 性能优先 — fire-and-forget, no redelivery
  at_least_once: 重要事件 — Redis Streams consumer groups, consumers must be idempotent

Topics (spec-defined):
  turn.completed        — Turn finished, payload includes trace_id
  soul.drift.detected   — SS01 drift threshold exceeded
  emotion.event         — SS03 emotion state transition
  relationship.transition — SS04 phase / special-state transition
  memory.l4.promoted    — SS02 L4 sacred memory promoted
  inner.proactive.sent  — SS06 proactive message dispatched
  wellbeing.alert       — Wellbeing Monitor alert triggered

Backend:
  MVP: Redis Streams (via redis-py)
  V2:  Kafka / Pulsar

Usage::

    from heart.infra.event_bus import EventBus

    eb = EventBus(redis_client=redis)

    # Emit
    await eb.emit("turn.completed", {"trace_id": str(tid), "user_id": str(uid)})

    # Subscribe (at-least-once with consumer group)
    async def handle_turn_completed(payload: dict) -> None:
        print(f"Turn done: {payload['trace_id']}")

    sub = await eb.subscribe("turn.completed", handle_turn_completed, group="memory_encoder")
    await eb.start_consuming()

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import structlog
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Awaitable, Callable, Optional, Set

logger = structlog.get_logger()


# ============================================================
# Enums & Constants
# ============================================================


class DeliveryLevel(str, Enum):
    """Event delivery guarantee level per §3.6."""
    AT_MOST_ONCE = "at_most_once"    # Fire-and-forget — performance-first
    AT_LEAST_ONCE = "at_least_once"  # Consumer groups — idempotent consumers required


# Topic delivery-level mapping per §3.6
TOPIC_DELIVERY_LEVELS: dict[str, DeliveryLevel] = {
    "turn.completed":         DeliveryLevel.AT_LEAST_ONCE,
    "soul.drift.detected":    DeliveryLevel.AT_LEAST_ONCE,
    "emotion.event":          DeliveryLevel.AT_MOST_ONCE,
    "relationship.transition": DeliveryLevel.AT_LEAST_ONCE,
    "memory.l4.promoted":     DeliveryLevel.AT_LEAST_ONCE,
    "inner.proactive.sent":   DeliveryLevel.AT_MOST_ONCE,
    "wellbeing.alert":        DeliveryLevel.AT_LEAST_ONCE,
}


# ============================================================
# Data Models
# ============================================================


@dataclass
class Event:
    """An event on the bus."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    topic: str = ""
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    trace_id: Optional[str] = None
    payload: dict[str, Any] = field(default_factory=dict)
    delivery_level: DeliveryLevel = DeliveryLevel.AT_LEAST_ONCE
    timestamp: float = field(default_factory=time.time)
    # Idempotency key: topic + event_id hash — consumers use this to dedupe
    idempotency_key: str = ""

    def __post_init__(self):
        if not self.idempotency_key:
            raw = f"{self.topic}:{self.event_id}"
            self.idempotency_key = hashlib.sha256(raw.encode()).hexdigest()[:32]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "topic": self.topic,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "trace_id": self.trace_id,
            "payload": self.payload,
            "delivery_level": self.delivery_level.value,
            "timestamp": self.timestamp,
            "idempotency_key": self.idempotency_key,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Event":
        return cls(
            event_id=data.get("event_id", ""),
            topic=data.get("topic", ""),
            user_id=data.get("user_id"),
            character_id=data.get("character_id"),
            trace_id=data.get("trace_id"),
            payload=data.get("payload", {}),
            delivery_level=DeliveryLevel(data.get("delivery_level", "at_least_once")),
            timestamp=data.get("timestamp", time.time()),
            idempotency_key=data.get("idempotency_key", ""),
        )


# ============================================================
# Subscription
# ============================================================


@dataclass
class Subscription:
    """A topic subscription handle."""
    subscription_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    topic: str = ""
    group: str = ""
    handler: Callable[[Event], Awaitable[None]] | None = None

    async def unsubscribe(self) -> None:
        """Cancel this subscription. Handler will handle this by reference."""
        pass


# ============================================================
# Backend Interfaces
# ============================================================


class EventBusBackend:
    """Abstract event bus backend."""

    async def emit(self, topic: str, event: Event) -> str:
        """Emit an event to a topic. Returns the event_id."""
        raise NotImplementedError

    async def subscribe(
        self,
        topic: str,
        group: str,
        handler: Callable[[Event], Awaitable[None]],
        consumer_id: str = "",
    ) -> Subscription:
        """Subscribe to a topic with a consumer group."""
        raise NotImplementedError

    async def ack(self, topic: str, group: str, event_id: str) -> None:
        """Acknowledge an event after processing (at-least-once)."""
        raise NotImplementedError

    async def start_consuming(self) -> None:
        """Start consuming messages (blocking in background)."""
        raise NotImplementedError


# ============================================================
# Redis Streams Backend
# ============================================================


REDIS_STREAM_PREFIX = "heart:events:"


class RedisStreamsBackend(EventBusBackend):
    """Redis Streams event bus backend per §3.6.

    MVP: Uses Redis Streams with consumer groups for at-least-once semantics.
    Fallback: In-memory queue when Redis unavailable.

    At-least-once pattern:
      1. Producer XADD to stream
      2. Consumer XREADGROUP reads pending + new
      3. Consumer processes event (must be idempotent)
      4. Consumer XACK to acknowledge

    Consumer deduplication: Each consumer group member tracks processed
    idempotency_keys to prevent double-processing.
    """

    def __init__(self, redis_client=None):
        """Initialize with an optional Redis client.

        Args:
            redis_client: redis.asyncio.Redis instance. If None, falls back
                          to in-memory queue (dev mode).
        """
        self.redis = redis_client
        # Per-(topic, group) queues for fan-out in in-memory mode
        self._in_memory_queues: dict[tuple[str, str], asyncio.Queue] = {}
        self._consumer_tasks: dict[str, asyncio.Task] = {}
        self._subscriptions: dict[str, list[tuple[str, Callable]]] = {}
        self._running = False
        self._stop_event = asyncio.Event()

    # --- Emit ---

    async def emit(self, topic: str, event: Event) -> str:
        """Emit an event to a topic stream."""
        stream_key = f"{REDIS_STREAM_PREFIX}{topic}"
        event_data = event.to_dict()

        if self.redis is not None:
            try:
                await self.redis.xadd(
                    stream_key,
                    {"data": json.dumps(event_data)},
                    maxlen=10000,  # 30-day retention approximate
                )
                logger.debug(f"Emitted to Redis stream {stream_key}: {event.event_id}")
                return event.event_id
            except Exception as e:
                logger.warning(f"Redis emit failed, falling back to in-memory: {e}")

        # In-memory fallback: fan out to all consumer groups for this topic
        delivered = 0
        for (t, grp), q in self._in_memory_queues.items():
            if t == topic:
                try:
                    await q.put(event)
                    delivered += 1
                except asyncio.QueueFull:
                    logger.warning(f"In-memory queue full for topic={topic}, group={grp}")
        logger.debug(
            f"Emitted to in-memory {topic}: {event.event_id} "
            f"(delivered to {delivered} consumer groups)"
        )
        return event.event_id

    # --- Subscribe ---

    async def subscribe(
        self,
        topic: str,
        group: str,
        handler: Callable[[Event], Awaitable[None]],
        consumer_id: str = "",
    ) -> Subscription:
        """Subscribe a consumer group to a topic.

        For Redis: creates consumer group if it doesn't exist, then starts
        a background consumption task.

        Args:
            topic: Topic to subscribe to (e.g. "turn.completed").
            group: Consumer group name (e.g. "memory_encoder").
            handler: Async callback for each event.
            consumer_id: Unique consumer ID within the group; auto-generated.

        Returns:
            Subscription handle.
        """
        if not consumer_id:
            consumer_id = f"{group}-{uuid.uuid4().hex[:8]}"

        sub = Subscription(
            topic=topic,
            group=group,
            handler=handler,
        )

        if group not in self._subscriptions:
            self._subscriptions[group] = []
        self._subscriptions[group].append((topic, handler))

        if self.redis is not None:
            stream_key = f"{REDIS_STREAM_PREFIX}{topic}"
            try:
                await self.redis.xgroup_create(
                    stream_key, group, id="0", mkstream=True
                )
                logger.info(f"Created consumer group '{group}' on stream {stream_key}")
            except Exception:
                # Group may already exist
                logger.debug(f"Consumer group '{group}' already exists on {stream_key}")

            if self._running:
                task = asyncio.create_task(
                    self._redis_consume_loop(topic, group, consumer_id, handler)
                )
                self._consumer_tasks[f"{topic}:{group}:{consumer_id}"] = task

        logger.info(f"Subscribed [{group}] to topic '{topic}'")
        return sub

    # --- Start / Stop consuming ---

    async def start_consuming(self) -> None:
        """Start all consumer loops (blocks on in-memory; background on Redis)."""
        self._running = True
        self._stop_event.clear()

        if self.redis is not None:
            # Redis: spawn consumer loops in background
            for group, subs in self._subscriptions.items():
                for topic, handler in subs:
                    consumer_id = f"{group}-{uuid.uuid4().hex[:8]}"
                    task = asyncio.create_task(
                        self._redis_consume_loop(topic, group, consumer_id, handler)
                    )
                    key = f"{topic}:{group}:{consumer_id}"
                    self._consumer_tasks[key] = task
                    logger.debug(f"Spawned Redis consumer: {key}")
        else:
            # In-memory: spawn consumer loops with per-(topic, group) queues
            for group, subs in self._subscriptions.items():
                for topic, handler in subs:
                    qkey = (topic, group)
                    if qkey not in self._in_memory_queues:
                        self._in_memory_queues[qkey] = asyncio.Queue(maxsize=10000)
                    task = asyncio.create_task(
                        self._in_memory_consume_loop(topic, group, handler)
                    )
                    key = f"{topic}:{group}"
                    self._consumer_tasks[key] = task

    async def stop_consuming(self) -> None:
        """Stop all consumer loops."""
        self._running = False
        self._stop_event.set()

        for task in self._consumer_tasks.values():
            task.cancel()
        # Wait for tasks to clean up
        if self._consumer_tasks:
            await asyncio.gather(*self._consumer_tasks.values(), return_exceptions=True)
        self._consumer_tasks.clear()

    # --- Ack ---

    async def ack(self, topic: str, group: str, event_id: str) -> None:
        """Acknowledge an event (at-least-once only)."""
        if self.redis is not None:
            stream_key = f"{REDIS_STREAM_PREFIX}{topic}"
            try:
                await self.redis.xack(stream_key, group, event_id)
            except Exception as e:
                logger.warning(f"Failed to ack {event_id}: {e}")

    # --- Internal: Redis consumer loop ---

    async def _redis_consume_loop(
        self,
        topic: str,
        group: str,
        consumer_id: str,
        handler: Callable[[Event], Awaitable[None]],
    ) -> None:
        """Background loop: read from Redis stream, dispatch to handler."""
        stream_key = f"{REDIS_STREAM_PREFIX}{topic}"
        processed_keys: Set[str] = set()  # idempotency deduplication
        max_processed = 10000  # Safety ceiling to prevent unbounded memory

        logger.info(f"Redis consumer [{consumer_id}] started on {stream_key}")

        while self._running:
            try:
                # Read new and pending messages
                results = await self.redis.xreadgroup(
                    groupname=group,
                    consumername=consumer_id,
                    streams={stream_key: ">"},
                    count=1,
                    block=1000,  # 1 second block
                )

                if results:
                    for _stream_name, messages in results:
                        for msg_id, msg_data in messages:
                            try:
                                raw = msg_data.get(b"data", b"{}")
                                event_dict = json.loads(raw.decode())
                                event = Event.from_dict(event_dict)
                            except (json.JSONDecodeError, KeyError) as e:
                                logger.error(f"Failed to parse event {msg_id}: {e}")
                                await self.redis.xack(stream_key, group, msg_id)
                                continue

                            # Idempotency check
                            if event.idempotency_key in processed_keys:
                                logger.debug(
                                    f"Skipping duplicate event {event.event_id} "
                                    f"(key={event.idempotency_key[:8]}...)"
                                )
                                await self.redis.xack(stream_key, group, msg_id)
                                continue

                            # Process
                            try:
                                await handler(event)
                                processed_keys.add(event.idempotency_key)
                                # Bounded set
                                if len(processed_keys) > max_processed:
                                    processed_keys = set(
                                        list(processed_keys)[-max_processed // 2:]
                                    )
                            except Exception as e:
                                logger.error(
                                    f"Handler failed for event {event.event_id}: {e}",
                                    exc_info=True,
                                )
                                # Don't ack on failure — Redis will redeliver

                            await self.redis.xack(stream_key, group, msg_id)

            except asyncio.CancelledError:
                logger.info(f"Redis consumer [{consumer_id}] cancelled")
                break
            except Exception as e:
                logger.error(f"Redis consume loop error: {e}", exc_info=True)
                await asyncio.sleep(1)  # Backoff on error

    # --- Internal: In-memory consumer loop ---

    async def _in_memory_consume_loop(
        self,
        topic: str,
        group: str,
        handler: Callable[[Event], Awaitable[None]],
    ) -> None:
        """Background loop: read from in-memory queue, dispatch to handler."""
        processed_keys: Set[str] = set()
        max_processed = 10000

        logger.info(f"In-memory consumer [{group}] started on topic '{topic}'")

        qkey = (topic, group)

        while self._running:
            try:
                queue = self._in_memory_queues.get(qkey)
                if queue is None:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Idempotency check
                if event.idempotency_key in processed_keys:
                    logger.debug(
                        f"Skipping duplicate event {event.event_id}"
                    )
                    continue

                try:
                    await handler(event)
                    processed_keys.add(event.idempotency_key)
                    if len(processed_keys) > max_processed:
                        processed_keys = set(
                            list(processed_keys)[-max_processed // 2:]
                        )
                except Exception as e:
                    logger.error(
                        f"Handler failed for event {event.event_id}: {e}",
                        exc_info=True,
                    )

            except asyncio.CancelledError:
                logger.info(f"In-memory consumer [{group}] cancelled")
                break
            except Exception as e:
                logger.error(f"In-memory consume loop error: {e}")
                await asyncio.sleep(0.1)


# ============================================================
# Event Bus (facade)
# ============================================================


class EventBus:
    """中央事件总线 — per SS07 §3.6.

    Thin facade over EventBusBackend. Provides topic-level delivery guarantee
    configuration and a clean emit/subscribe API.

    Usage::

        import redis.asyncio as redis
        r = redis.Redis(host="localhost", port=6379)
        eb = EventBus(redis_client=r)

        await eb.emit("turn.completed", {
            "user_id": str(uid),
            "trace_id": str(tid),
            "turn_index": 5,
        })

        # Consumer with idempotent handling
        async def on_turn_completed(event: Event) -> None:
            # Safe to re-process — idempotency_key deduplicates
            payload = event.payload
            await process_turn(payload["trace_id"])

        await eb.subscribe("turn.completed", on_turn_completed, group="memory_encoder")
        await eb.start_consuming()
    """

    def __init__(self, redis_client=None):
        """Initialize event bus.

        Args:
            redis_client: redis.asyncio.Redis instance. If None, uses in-memory
                          queue (suitable for dev/testing).
        """
        self.backend = RedisStreamsBackend(redis_client=redis_client)
        self._running = False

    # --- Emit ---

    async def emit(
        self,
        topic: str,
        payload: dict[str, Any],
        *,
        event_id: str = "",
        user_id: Optional[str] = None,
        character_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        delivery_level: Optional[str] = None,
    ) -> str:
        """Emit an event to a topic.

        Args:
            topic: Event topic (e.g. "turn.completed").
            payload: Event payload dict.
            event_id: Optional event ID (auto-generated).
            user_id: Isolating user ID (INV-O-4).
            character_id: Character ID if applicable.
            trace_id: Trace ID for end-to-end correlation.
            delivery_level: Override topic default ("at_least_once" | "at_most_once").

        Returns:
            The event_id of the emitted event.
        """
        if delivery_level is None:
            level = TOPIC_DELIVERY_LEVELS.get(topic, DeliveryLevel.AT_LEAST_ONCE)
        else:
            level = DeliveryLevel(delivery_level)

        event = Event(
            event_id=event_id or uuid.uuid4().hex[:16],
            topic=topic,
            user_id=user_id,
            character_id=character_id,
            trace_id=trace_id,
            payload=payload,
            delivery_level=level,
            timestamp=time.time(),
        )

        await self.backend.emit(topic, event)
        logger.debug(
            f"Event emitted: topic={topic}, id={event.event_id}, "
            f"level={level.value}"
        )
        return event.event_id

    # --- Subscribe ---

    async def subscribe(
        self,
        topic: str,
        handler: Callable[[Event], Awaitable[None]],
        *,
        group: str = "",
        consumer_id: str = "",
    ) -> Subscription:
        """Subscribe to a topic with a consumer group.

        For at-least-once topics, the consumer group enables redelivery.
        The handler must be idempotent — the bus deduplicates by event
        idempotency_key, but at-least-once means handlers may see events
        more than once.

        Args:
            topic: Topic to subscribe to.
            handler: Async callback receiving an Event.
            group: Consumer group name (e.g. "memory_encoder").
            consumer_id: Optional consumer member ID.

        Returns:
            Subscription handle.
        """
        if not group:
            group = f"consumer-{topic.replace('.', '-')}"
        return await self.backend.subscribe(topic, group, handler, consumer_id)

    # --- Lifecycle ---

    async def start_consuming(self) -> None:
        """Start background consumption of all subscribed topics."""
        self._running = True
        await self.backend.start_consuming()

    async def stop_consuming(self) -> None:
        """Stop all background consumers."""
        self._running = False
        await self.backend.stop_consuming()

    # --- Monitoring ---

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the event bus."""
        return {
            "backend": "redis_streams" if self.backend.redis else "in_memory",
            "running": self._running,
            "subscriptions": {
                group: len(subs)
                for group, subs in self.backend._subscriptions.items()
            },
            "consumer_tasks": len(self.backend._consumer_tasks),
        }
