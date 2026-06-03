"""
SS07 Orchestration — SessionManager per docs/design/orchestrator_min_viable.md §3.4.

Manages per-(user, character) conversation sessions backed by the
sessions DB table (migration 006_sessions.py). Provides get-or-create
semantics with turn-count tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Tuple
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from heart.ss07_orchestration.models import Session

logger = structlog.get_logger(__name__)

# ── In-process cache for read-heavy session lookups ────────────────
# Key: (str(user_id), character_id) → Session
# Reduces DB round-trips for repeated lookups within the same process.


class SessionManager:
    """Manages conversation sessions per (user_id, character_id) pair.

    Sessions are persisted to the `sessions` DB table via raw SQL.
    An in-process cache avoids repeated DB lookups for active sessions.

    Usage:
        mgr = SessionManager()
        session = await mgr.get_or_create_session(db_session, user_id, character_id)
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], Session] = {}

    async def get_or_create_session(
        self,
        db_session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ) -> Session:
        """Get the active session for (user, character), creating one if absent.

        Uses the sessions DB table as source of truth. An in-process
        cache avoids repeated DB queries within the same process lifetime.

        Returns:
            Session with session_id, turn_count, and metadata.
        """
        cache_key = (str(user_id), character_id)

        # Fast path: in-process cache hit
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        # DB lookup + insert-or-select
        session = await self._load_or_create(db_session, user_id, character_id)

        # Populate cache
        self._cache[cache_key] = session
        return session

    async def record_turn(
        self,
        db_session: AsyncSession,
        session: Session,
    ) -> None:
        """Increment turn_count and update last_activity_at.

        Args:
            db_session: Active DB session.
            session: The session to update (mutated in-place).
        """
        try:
            await db_session.execute(
                __import__("sqlalchemy").text(
                    "UPDATE sessions "
                    "SET turn_count = turn_count + 1, last_activity_at = NOW() "
                    "WHERE id = :session_id"
                ),
                {"session_id": str(session.session_id)},
            )
            await db_session.commit()

            # Mutate in-place to keep cache in sync
            session.turn_count += 1
            session.last_activity_at = datetime.now(timezone.utc)
        except Exception:
            logger.exception("session_record_turn_failed", session_id=str(session.session_id))

    # ── Private ─────────────────────────────────────────────────────

    async def _load_or_create(
        self,
        db_session: AsyncSession,
        user_id: UUID,
        character_id: str,
    ) -> Session:
        """Load an existing session or insert a new one atomically."""
        try:
            result = await db_session.execute(
                __import__("sqlalchemy").text(
                    "SELECT id, user_id, character_id, started_at, last_activity_at, "
                    "       turn_count, suicide_protocol_active "
                    "FROM sessions "
                    "WHERE user_id = :user_id AND character_id = :character_id "
                    "LIMIT 1"
                ),
                {
                    "user_id": str(user_id),
                    "character_id": character_id,
                },
            )
            row = result.fetchone()
        except Exception:
            logger.exception("session_db_lookup_failed")
            row = None

        if row is not None:
            return Session(
                session_id=UUID(str(row[0])),
                user_id=UUID(str(row[1])),
                character_id=str(row[2]),
                started_at=row[3],
                last_activity_at=row[4],
                turn_count=int(row[5]),
                suicide_protocol_active=bool(row[6]),
            )

        # No existing session → insert
        session_id = uuid4()
        now = datetime.now(timezone.utc)
        try:
            await db_session.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO sessions (id, user_id, character_id, started_at, last_activity_at) "
                    "VALUES (:id, :user_id, :character_id, :started_at, :last_activity_at)"
                ),
                {
                    "id": str(session_id),
                    "user_id": str(user_id),
                    "character_id": character_id,
                    "started_at": now,
                    "last_activity_at": now,
                },
            )
            await db_session.commit()
        except Exception:
            logger.exception("session_create_failed")
            # Fallback: return an ephemeral in-memory session
            return Session(
                session_id=session_id,
                user_id=user_id,
                character_id=character_id,
                started_at=now,
                last_activity_at=now,
                turn_count=0,
            )

        return Session(
            session_id=session_id,
            user_id=user_id,
            character_id=character_id,
            started_at=now,
            last_activity_at=now,
            turn_count=0,
        )

    def invalidate_cache(self, user_id: UUID, character_id: str) -> None:
        """Remove a session from the in-process cache (e.g. after session reset)."""
        cache_key = (str(user_id), character_id)
        self._cache.pop(cache_key, None)
