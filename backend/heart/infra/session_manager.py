"""
Session Manager — multi-device session continuity per SS07 §3.7 + §4.1.

Session lifecycle + cross-device 一致性管理。

Design invariants (from runtime_specs/07_agent_orchestration.md):
  INV-O-8: ∀ session change (新 session / device switch), session_manager 重新加载所有状态
  O-12:    Multi-device 状态一致性强制

Per §3.7 responsibilities:
  - load_session(): 每个 turn 开始时调用，加载/创建 session
  - Cross-session 状态恢复: emotion, relationship, memory (L1), inner_state
  - _check_reunion(): 检查 7 天阈值，触发 reunion 逻辑
  - Multi-device: 共享 session_id, server 端持有 state

Session State Model (§4.1):
  - session_id, user_id, character_id
  - started_at, ended_at, last_activity_at, is_active
  - primary_device_id, active_device_ids
  - current_modality, modality_history
  - soul_spec_version
  - turn_count, trace_ids
  - user_safety_flag, suicide_protocol_active
  - current_wellbeing_state, cached_director_directives

Usage::

    from heart.infra.session_manager import SessionManager, SessionState

    mgr = SessionManager(redis_client=redis)
    session = await mgr.load_session(user_id, character_id, device_id="ios-abc")

    # Access session state
    print(session.turn_count, session.current_modality)

    # End session
    await mgr.end_session(session.session_id)

Author: 心屿团队
"""

from __future__ import annotations

import asyncio
import structlog
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set

logger = structlog.get_logger()


# ============================================================
# Data Models
# ============================================================


@dataclass
class ModalityRecord:
    """A modality history entry."""
    modality: str = "text"
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class SessionState:
    """Session state per §4.1.

    Immutable snapshot returned by SessionManager.
    """
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    character_id: str = ""

    # Lifecycle
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    ended_at: Optional[str] = None
    last_activity_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    is_active: bool = True

    # Device
    primary_device_id: str = ""
    active_device_ids: list[str] = field(default_factory=list)

    # Modality
    current_modality: str = "text"
    modality_history: list[ModalityRecord] = field(default_factory=list)

    # Soul
    soul_spec_version: str = "1.0.0"

    # Conversation
    turn_count: int = 0
    trace_ids: list[str] = field(default_factory=list)

    # Safety
    user_safety_flag: str = "normal"
    suicide_protocol_active: bool = False

    # Wellbeing snapshot
    current_wellbeing_state: Optional[dict[str, Any]] = None

    # Director state (cached)
    cached_director_directives: Optional[dict[str, Any]] = None

    # Extended state — loaded from other services on session load
    emotion_state: Optional[dict[str, Any]] = None
    relationship_state: Optional[dict[str, Any]] = None
    inner_state: Optional[dict[str, Any]] = None
    memory_l1: Optional[list[dict[str, Any]]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "character_id": self.character_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "last_activity_at": self.last_activity_at,
            "is_active": self.is_active,
            "primary_device_id": self.primary_device_id,
            "active_device_ids": self.active_device_ids,
            "current_modality": self.current_modality,
            "modality_history": [
                {"modality": m.modality, "started_at": m.started_at}
                for m in self.modality_history
            ],
            "soul_spec_version": self.soul_spec_version,
            "turn_count": self.turn_count,
            "trace_ids": self.trace_ids,
            "user_safety_flag": self.user_safety_flag,
            "suicide_protocol_active": self.suicide_protocol_active,
            "current_wellbeing_state": self.current_wellbeing_state,
            "cached_director_directives": self.cached_director_directives,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionState":
        return cls(
            session_id=data.get("session_id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            character_id=data.get("character_id", ""),
            started_at=data.get("started_at", datetime.now(timezone.utc).isoformat()),
            ended_at=data.get("ended_at"),
            last_activity_at=data.get("last_activity_at", datetime.now(timezone.utc).isoformat()),
            is_active=data.get("is_active", True),
            primary_device_id=data.get("primary_device_id", ""),
            active_device_ids=data.get("active_device_ids", []),
            current_modality=data.get("current_modality", "text"),
            modality_history=[
                ModalityRecord(**m) if isinstance(m, dict) else m
                for m in data.get("modality_history", [])
            ],
            soul_spec_version=data.get("soul_spec_version", "1.0.0"),
            turn_count=data.get("turn_count", 0),
            trace_ids=data.get("trace_ids", []),
            user_safety_flag=data.get("user_safety_flag", "normal"),
            suicide_protocol_active=data.get("suicide_protocol_active", False),
            current_wellbeing_state=data.get("current_wellbeing_state"),
            cached_director_directives=data.get("cached_director_directives"),
            emotion_state=data.get("emotion_state"),
            relationship_state=data.get("relationship_state"),
            inner_state=data.get("inner_state"),
            memory_l1=data.get("memory_l1"),
        )


@dataclass
class ConflictResolution:
    """Multi-device conflict resolution result."""
    strategy: str = "server_wins"  # "server_wins" | "last_write_wins" | "merge"
    resolved_session: SessionState | None = None
    conflicts: list[dict[str, Any]] = field(default_factory=list)
    resolution_notes: str = ""


@dataclass
class ReunionResult:
    """Result of a reunion check per §3.7."""
    triggered: bool = False
    days_since_last_interaction: int = 0
    previous_relationship_state: Optional[dict[str, Any]] = None
    reunion_type: str = ""  # "normal" | "extended" (14+ days)


# ============================================================
# Session Store Interface
# ============================================================


class SessionStore:
    """Abstract session storage backend.

    Implementations: Redis (MVP), PostgreSQL (V1 persistent).
    For MVP, Redis is used with JSON serialization; can be swapped
    for PG without changing SessionManager.
    """

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        """Get session data by ID."""
        raise NotImplementedError

    async def get_active(self, user_id: str, character_id: str) -> Optional[dict[str, Any]]:
        """Get the active session for a user+character pair."""
        raise NotImplementedError

    async def set(self, session_id: str, data: dict[str, Any], ttl: int = 86400) -> None:
        """Store session data with optional TTL (seconds)."""
        raise NotImplementedError

    async def delete(self, session_id: str) -> None:
        """Delete a session."""
        raise NotImplementedError

    async def get_all_active(self, user_id: str) -> list[dict[str, Any]]:
        """Get all active sessions for a user (multi-device)."""
        raise NotImplementedError


# ============================================================
# In-Memory Session Store (dev / testing)
# ============================================================


class InMemorySessionStore(SessionStore):
    """In-memory session store for development and testing."""

    def __init__(self):
        self._store: dict[str, dict[str, Any]] = {}
        self._active_index: dict[str, str] = {}  # (user_id:character_id) → session_id

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        return self._store.get(session_id)

    async def get_active(self, user_id: str, character_id: str) -> Optional[dict[str, Any]]:
        key = f"{user_id}:{character_id}"
        sid = self._active_index.get(key)
        if sid:
            return self._store.get(sid)
        return None

    async def set(self, session_id: str, data: dict[str, Any], ttl: int = 86400) -> None:
        self._store[session_id] = data
        # Update active index (mirrors RedisSessionStore.set)
        user_id = data.get("user_id", "")
        character_id = data.get("character_id", "")
        if user_id and character_id:
            key = f"{user_id}:{character_id}"
            if data.get("is_active", False):
                self._active_index[key] = session_id
            else:
                self._active_index.pop(key, None)

    async def delete(self, session_id: str) -> None:
        data = self._store.pop(session_id, None)
        # Clean active index
        if data:
            user_id = data.get("user_id", "")
            character_id = data.get("character_id", "")
            if user_id and character_id:
                key = f"{user_id}:{character_id}"
                self._active_index.pop(key, None)

    async def get_all_active(self, user_id: str) -> list[dict[str, Any]]:
        results = []
        for key, sid in self._active_index.items():
            if key.startswith(f"{user_id}:"):
                data = self._store.get(sid)
                if data:
                    results.append(data)
        return results


# ============================================================
# Redis Session Store
# ============================================================


SESSION_KEY_PREFIX = "heart:session:"
ACTIVE_SESSION_INDEX = "heart:active_sessions"  # Hash: {user_id:char_id} → session_id


class RedisSessionStore(SessionStore):
    """Redis-backed session store for production.

    Keys:
      heart:session:{session_id}  → JSON blob (with TTL)
      heart:active_sessions       → Hash {user_id:character_id} → session_id
    """

    def __init__(self, redis_client):
        """Initialize with a redis.asyncio.Redis client."""
        self.redis = redis_client
        self._default_ttl = 86400  # 24 hours

    async def get(self, session_id: str) -> Optional[dict[str, Any]]:
        import json
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        data = await self.redis.get(key)
        if data:
            return json.loads(data.decode())
        return None

    async def get_active(self, user_id: str, character_id: str) -> Optional[dict[str, Any]]:
        field = f"{user_id}:{character_id}"
        session_id = await self.redis.hget(ACTIVE_SESSION_INDEX, field)
        if session_id:
            return await self.get(session_id.decode())
        return None

    async def set(self, session_id: str, data: dict[str, Any], ttl: int = 86400) -> None:
        import json
        key = f"{SESSION_KEY_PREFIX}{session_id}"
        await self.redis.setex(key, ttl, json.dumps(data))

        # Update active index
        field = f"{data['user_id']}:{data['character_id']}"
        if data.get("is_active", False):
            await self.redis.hset(ACTIVE_SESSION_INDEX, field, session_id)
        else:
            await self.redis.hdel(ACTIVE_SESSION_INDEX, field)

    async def delete(self, session_id: str) -> None:
        data = await self.get(session_id)
        if data:
            field = f"{data['user_id']}:{data['character_id']}"
            await self.redis.hdel(ACTIVE_SESSION_INDEX, field)

        key = f"{SESSION_KEY_PREFIX}{session_id}"
        await self.redis.delete(key)

    async def get_all_active(self, user_id: str) -> list[dict[str, Any]]:
        import json
        # Scan the active index for user_id's sessions
        pattern = f"{user_id}:*"
        sessions = []
        cursor = 0
        while True:
            cursor, items = await self.redis.hscan(
                ACTIVE_SESSION_INDEX, cursor=cursor, match=pattern
            )
            for field, sid_bytes in items.items():
                if field.decode().startswith(f"{user_id}:"):
                    data = await self.get(sid_bytes.decode())
                    if data:
                        sessions.append(data)
            if cursor == 0:
                break
        return sessions


# ============================================================
# Session Manager
# ============================================================


# Reunion thresholds per §3.7
REUNION_THRESHOLD_DAYS = 7          # Normal reunion
REUNION_EXTENDED_DAYS = 14          # Extended reunion (deeper reconnect)


class SessionManager:
    """Session lifecycle manager per SS07 §3.7.

    Responsibilities:
      - load_session(): create or restore session for a user+character
      - Cross-session state restoration on new session
      - Reunion detection (7+ day threshold)
      - Multi-device conflict resolution
      - Session state mutation and persistence

    此实现不直接调用 SS01-06 service——而是通过注入的 callbacks 或 hook 点
    来集成。这样可以避免紧耦合，符合 O-2（通过 service adapters 通信）。
    """

    def __init__(
        self,
        *,
        store: Optional[SessionStore] = None,
        redis_client=None,
        # Service callbacks — injected dependencies
        on_load_emotion: Optional[Any] = None,
        on_load_relationship: Optional[Any] = None,
        on_load_memory: Optional[Any] = None,
        on_load_inner_state: Optional[Any] = None,
        on_reunion: Optional[Any] = None,
    ):
        """Initialize SessionManager.

        Args:
            store: SessionStore backend. If None, uses InMemorySessionStore
                   or RedisSessionStore (if redis_client provided).
            redis_client: redis.asyncio.Redis for RedisSessionStore.
            on_load_emotion: coroutine(user_id, character_id) → emotion state dict.
            on_load_relationship: coroutine(user_id, character_id) → relationship dict.
            on_load_memory: coroutine(session_id) → list[memory items].
            on_load_inner_state: coroutine(user_id, character_id) → inner state dict.
            on_reunion: coroutine(user_id, character_id, days_since) → reunion result.
        """
        if store is not None:
            self.store = store
        elif redis_client is not None:
            self.store = RedisSessionStore(redis_client)
        else:
            self.store = InMemorySessionStore()

        # Injectable service hooks
        self._on_load_emotion = on_load_emotion
        self._on_load_relationship = on_load_relationship
        self._on_load_memory = on_load_memory
        self._on_load_inner_state = on_load_inner_state
        self._on_reunion = on_reunion

        # Device tracking (active device → session mapping)
        self._device_sessions: dict[str, str] = {}

    # --- Public API ---

    async def load_session(
        self,
        user_id: str,
        character_id: str,
        *,
        device_id: str = "",
        modality: str = "text",
        soul_spec_version: str = "1.0.0",
    ) -> SessionState:
        """Load or create a session (每个 turn 入口 per §3.7).

        Steps:
          1. Try to load an active session
          2. If none, create a new session and restore cross-session state
          3. Check for reunion conditions
          4. Update device tracking

        Args:
            user_id: User identifier.
            character_id: Character identifier (e.g. "rin", "dorothy").
            device_id: Current device identifier.
            modality: Current interaction modality.
            soul_spec_version: Locked soul spec version.

        Returns:
            Active SessionState.
        """
        # Step 1: Load active session
        active_data = await self.store.get_active(user_id, character_id)
        now_iso = datetime.now(timezone.utc).isoformat()

        if active_data:
            # Existing session — refresh metadata
            session = SessionState.from_dict(active_data)
            session.last_activity_at = now_iso

            # Update device tracking
            if device_id:
                if device_id not in session.active_device_ids:
                    session.active_device_ids.append(device_id)
                if not session.primary_device_id:
                    session.primary_device_id = device_id
                self._device_sessions[device_id] = session.session_id

            # Update modality if changed
            if modality != session.current_modality:
                session.modality_history.append(ModalityRecord(
                    modality=modality,
                    started_at=now_iso,
                ))
                session.current_modality = modality

            session.turn_count += 1

            await self._persist(session)
            logger.debug(
                f"Session loaded: {session.session_id} "
                f"(turn {session.turn_count}, devices={len(session.active_device_ids)})"
            )
            return session

        # Step 2: New session — create and restore state
        session = SessionState(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            character_id=character_id,
            started_at=now_iso,
            last_activity_at=now_iso,
            is_active=True,
            primary_device_id=device_id,
            active_device_ids=[device_id] if device_id else [],
            current_modality=modality,
            modality_history=[ModalityRecord(modality=modality, started_at=now_iso)],
            soul_spec_version=soul_spec_version,
            turn_count=1,
        )

        if device_id:
            self._device_sessions[device_id] = session.session_id

        # Step 3: Cross-session state restoration (§3.7)
        await self._restore_cross_session_state(session)

        # Step 4: Reunion check
        reunion = await self._check_reunion(user_id, character_id, session)
        if reunion.triggered:
            logger.info(
                f"Reunion triggered for {user_id}/{character_id}: "
                f"{reunion.days_since_last_interaction} days"
            )
            # Tag reunion info on session for composer
            session.cached_director_directives = {
                **(session.cached_director_directives or {}),
                "reunion": {
                    "triggered": True,
                    "days_since": reunion.days_since_last_interaction,
                    "type": reunion.reunion_type,
                },
            }

        await self._persist(session)
        logger.info(
            f"New session created: {session.session_id} "
            f"for {user_id}/{character_id}, device={device_id}"
        )
        return session

    async def end_session(self, session_id: str) -> None:
        """End an active session."""
        data = await self.store.get(session_id)
        if data:
            session = SessionState.from_dict(data)
            session.is_active = False
            session.ended_at = datetime.now(timezone.utc).isoformat()
            await self._persist(session)
            logger.info(f"Session ended: {session_id}")

    async def handle_multi_device(
        self,
        user_id: str,
        character_id: str,
        new_device_id: str,
    ) -> ConflictResolution:
        """Handle a user logging in from a new device (§3.7).

        Strategy (per spec): Conflict-free — all devices share the same
        session_id. Server holds state; clients sync via WebSocket.

        Args:
            user_id: User identifier.
            character_id: Character identifier.
            new_device_id: The new device identifier.

        Returns:
            ConflictResolution with the shared session.
        """
        active_data = await self.store.get_active(user_id, character_id)

        if not active_data:
            # No active session, just create one
            session = await self.load_session(
                user_id, character_id,
                device_id=new_device_id,
            )
            return ConflictResolution(
                strategy="server_wins",
                resolved_session=session,
                resolution_notes="No conflict — new session created.",
            )

        session = SessionState.from_dict(active_data)

        # Add new device to active set
        if new_device_id not in session.active_device_ids:
            session.active_device_ids.append(new_device_id)

        self._device_sessions[new_device_id] = session.session_id
        await self._persist(session)

        return ConflictResolution(
            strategy="server_wins",
            resolved_session=session,
            conflicts=[],
            resolution_notes=(
                f"Device '{new_device_id}' joined session {session.session_id}. "
                f"Active devices: {session.active_device_ids}"
            ),
        )

    async def get_device_session(self, device_id: str) -> Optional[SessionState]:
        """Get the session associated with a device ID."""
        session_id = self._device_sessions.get(device_id)
        if session_id:
            data = await self.store.get(session_id)
            if data:
                return SessionState.from_dict(data)
        return None

    async def get_active_devices(self, user_id: str) -> list[str]:
        """Get all active device IDs for a user."""
        sessions = await self.store.get_all_active(user_id)
        devices: Set[str] = set()
        for s in sessions:
            devices.update(s.get("active_device_ids", []))
        return list(devices)

    # --- Helpers ---

    async def _restore_cross_session_state(self, session: SessionState) -> None:
        """Restore cross-session state per §3.7.

        On new session, reloads emotion, relationship, memory (L1), and
        inner state from the respective services. This ensures continuity
        across sessions (INV-O-8).
        """
        tasks = []

        if self._on_load_emotion:
            tasks.append(
                self._safe_load(
                    "emotion_state",
                    self._on_load_emotion(session.user_id, session.character_id),
                    session,
                )
            )
        if self._on_load_relationship:
            tasks.append(
                self._safe_load(
                    "relationship_state",
                    self._on_load_relationship(session.user_id, session.character_id),
                    session,
                )
            )
        if self._on_load_memory:
            tasks.append(
                self._safe_load(
                    "memory_l1",
                    self._on_load_memory(session.session_id),
                    session,
                )
            )
        if self._on_load_inner_state:
            tasks.append(
                self._safe_load(
                    "inner_state",
                    self._on_load_inner_state(session.user_id, session.character_id),
                    session,
                )
            )

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_load(
        self,
        field: str,
        coro,
        session: SessionState,
    ) -> None:
        """Safely load a state field, logging errors."""
        try:
            result = await coro
            setattr(session, field, result)
        except Exception as e:
            logger.error(
                f"Failed to restore {field} for session {session.session_id}: {e}",
                exc_info=True,
            )

    async def _check_reunion(
        self,
        user_id: str,
        character_id: str,
        session: SessionState,
    ) -> ReunionResult:
        """Check reunion conditions per §3.7.

        If > 7 days since last interaction, triggers reunion flow.
        If > 14 days, triggers extended reunion.
        """
        # Check if we have a reunion hook
        if self._on_reunion is not None:
            try:
                rel_state = await self._on_reunion(user_id, character_id)
                if rel_state and isinstance(rel_state, dict):
                    last_interaction = rel_state.get("last_interaction_at")
                    if last_interaction:
                        # Parse timestamp and compute days
                        now = datetime.now(timezone.utc)
                        if isinstance(last_interaction, str):
                            last_dt = datetime.fromisoformat(
                                last_interaction.replace("Z", "+00:00")
                            )
                        else:
                            last_dt = last_interaction
                        days_since = (now - last_dt).days

                        if days_since > REUNION_THRESHOLD_DAYS:
                            reunion_type = (
                                "extended"
                                if days_since > REUNION_EXTENDED_DAYS
                                else "normal"
                            )
                            return ReunionResult(
                                triggered=True,
                                days_since_last_interaction=days_since,
                                previous_relationship_state=rel_state,
                                reunion_type=reunion_type,
                            )
            except Exception as e:
                logger.warning(f"Reunion check failed: {e}")

        return ReunionResult(triggered=False, days_since_last_interaction=0)

    async def _persist(self, session: SessionState) -> None:
        """Persist session to the store."""
        data = session.to_dict()
        await self.store.set(session.session_id, data)

    # --- Monitoring ---

    async def health_check(self) -> dict[str, Any]:
        """Return health status of the session manager."""
        return {
            "store_type": type(self.store).__name__,
            "active_device_count": len(self._device_sessions),
        }
