"""replay/bundle_dump.py — PromptBundle persistence: record, fetch, and prune snapshots."""

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


# ── Data-classes ────────────────────────────────────────────────────


@dataclass
class LayerSnapshot:
    """Snapshot of a single composer layer's content at composition time."""

    name: str
    content: str
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PromptBundle:
    """Complete prompt bundle recorded for one turn."""

    turn_id: uuid.UUID
    session_id: uuid.UUID
    user_id: str
    character_id: str

    system_prompt: str
    messages: List[Dict[str, str]]
    layers: Dict[str, LayerSnapshot]

    raw_response: str
    final_response: str
    latency_ms: int
    model_name: str
    token_count: int

    anti_pattern_hits: List[str] = field(default_factory=list)
    blocked: bool = False

    critic_score: Optional[float] = None
    critic_feedback: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["turn_id"] = str(self.turn_id)
        d["session_id"] = str(self.session_id)
        d["layers"] = {k: asdict(v) for k, v in self.layers.items()}
        d["created_at"] = self.created_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptBundle":
        layers = {
            k: LayerSnapshot(
                name=v.get("name", k),
                content=v.get("content", ""),
                token_count=v.get("token_count", 0),
                metadata=v.get("metadata", {}),
            )
            for k, v in data.get("layers", {}).items()
        }
        return cls(
            turn_id=uuid.UUID(data["turn_id"]),
            session_id=uuid.UUID(data["session_id"]),
            user_id=data["user_id"],
            character_id=data["character_id"],
            system_prompt=data["system_prompt"],
            messages=data["messages"],
            layers=layers,
            raw_response=data["raw_response"],
            final_response=data["final_response"],
            latency_ms=data["latency_ms"],
            model_name=data["model_name"],
            token_count=data["token_count"],
            anti_pattern_hits=data.get("anti_pattern_hits", []),
            blocked=data.get("blocked", False),
            critic_score=data.get("critic_score"),
            critic_feedback=data.get("critic_feedback"),
            created_at=datetime.fromisoformat(data["created_at"])
            if isinstance(data.get("created_at"), str)
            else data.get("created_at", datetime.now(timezone.utc)),
        )


# ── ReplayRecorder ──────────────────────────────────────────────────


class ReplayRecorder:
    """Records PromptBundles to the replay_snapshots table.

    Usage:
        recorder = ReplayRecorder(engine)
        await recorder.record(bundle)

    The recorder is designed to be injected into ComposerService as an
    optional dependency. If not provided, no snapshots are saved.
    """

    # Auto-prune retention window (days)
    RETENTION_DAYS = 7

    def __init__(self, engine: Any = None) -> None:
        """Initialize ReplayRecorder with an optional async engine.

        Args:
            engine: SQLAlchemy async engine. If None, save/load operations
                    will raise RuntimeError.
        """
        self._engine = engine

    # ── Record ──────────────────────────────────────────────────

    async def record(self, bundle: PromptBundle) -> bool:
        """Persist a PromptBundle to the replay_snapshots table.

        Also triggers auto-prune of expired snapshots (best-effort).
        """
        if self._engine is None:
            logger.warning("replay_recorder_no_engine", turn_id=str(bundle.turn_id))
            return False

        try:
            from sqlalchemy import text

            async with self._engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                    INSERT INTO replay_snapshots
                        (id, turn_id, session_id, user_id, character_id,
                         prompt_bundle, raw_response, final_response,
                         latency_ms, model_name, token_count,
                         anti_pattern_hits, blocked, critic_score, critic_feedback,
                         created_at)
                    VALUES
                        (:id, :turn_id, :session_id, :user_id, :character_id,
                         :prompt_bundle, :raw_response, :final_response,
                         :latency_ms, :model_name, :token_count,
                         :anti_pattern_hits, :blocked, :critic_score, :critic_feedback,
                         :created_at)
                    """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "turn_id": str(bundle.turn_id),
                        "session_id": str(bundle.session_id),
                        "user_id": bundle.user_id,
                        "character_id": bundle.character_id,
                        "prompt_bundle": json.dumps(self._serialize_bundle(bundle)),
                        "raw_response": bundle.raw_response,
                        "final_response": bundle.final_response,
                        "latency_ms": bundle.latency_ms,
                        "model_name": bundle.model_name,
                        "token_count": bundle.token_count,
                        "anti_pattern_hits": json.dumps(bundle.anti_pattern_hits),
                        "blocked": bundle.blocked,
                        "critic_score": bundle.critic_score,
                        "critic_feedback": bundle.critic_feedback,
                        "created_at": bundle.created_at,
                    },
                )

            logger.debug(
                "replay_snapshot_saved",
                turn_id=str(bundle.turn_id),
                session_id=str(bundle.session_id),
            )

            # Best-effort prune
            await self.prune_old(try_only=True)
            return True

        except Exception as e:
            logger.warning(
                "replay_record_failed",
                turn_id=str(bundle.turn_id),
                error=str(e),
            )
            return False

    # ── Load ────────────────────────────────────────────────────

    async def load_by_turn(self, turn_id: uuid.UUID) -> Optional[PromptBundle]:
        """Load a single snapshot by turn_id."""
        return await self._load_one(turn_id)

    async def load_by_session(
        self, session_id: uuid.UUID, turn_n: Optional[int] = None
    ) -> List[PromptBundle]:
        """Load all snapshots for a session, ordered by created_at.

        If turn_n is provided, returns only that single snapshot (1-indexed).
        """
        bundles = await self._load_many(session_id)
        if turn_n is not None:
            if 1 <= turn_n <= len(bundles):
                return [bundles[turn_n - 1]]
            return []
        return bundles

    async def _load_one(self, turn_id: uuid.UUID) -> Optional[PromptBundle]:
        if self._engine is None:
            return None
        try:
            from sqlalchemy import text

            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text(
                        """
                    SELECT prompt_bundle, raw_response, final_response,
                           latency_ms, model_name, token_count,
                           anti_pattern_hits, blocked, critic_score, critic_feedback,
                           created_at
                    FROM replay_snapshots
                    WHERE turn_id = :id
                    LIMIT 1
                    """
                    ),
                    {"id": str(turn_id)},
                )
                row = result.fetchone()
                if row is None:
                    return None
                return self._row_to_bundle(row)
        except Exception:
            logger.exception("replay_load_failed")
            return None

    async def _load_many(self, session_id: uuid.UUID) -> List[PromptBundle]:
        if self._engine is None:
            return []
        try:
            from sqlalchemy import text

            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text(
                        """
                    SELECT prompt_bundle, raw_response, final_response,
                           latency_ms, model_name, token_count,
                           anti_pattern_hits, blocked, critic_score, critic_feedback,
                           created_at
                    FROM replay_snapshots
                    WHERE session_id = :sid
                    ORDER BY created_at ASC
                    """
                    ),
                    {"sid": str(session_id)},
                )
                return [self._row_to_bundle(row) for row in result.fetchall()]
        except Exception:
            logger.exception("replay_load_many_failed")
            return []

    def _row_to_bundle(self, row: Any) -> PromptBundle:
        bundle_data = row.prompt_bundle or {}
        bundle_data.update(
            {
                "raw_response": row.raw_response,
                "final_response": row.final_response,
                "latency_ms": row.latency_ms or 0,
                "model_name": row.model_name or "unknown",
                "token_count": row.token_count or 0,
                "anti_pattern_hits": row.anti_pattern_hits or [],
                "blocked": row.blocked or False,
                "critic_score": float(row.critic_score) if row.critic_score else None,
                "critic_feedback": row.critic_feedback,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
        return PromptBundle.from_dict(bundle_data)

    # ── Prune ───────────────────────────────────────────────────

    async def prune_old(self, *, try_only: bool = False) -> int:
        """Delete snapshots older than RETENTION_DAYS.

        Args:
            try_only: If True, suppress errors (for best-effort background pruning).

        Returns:
            Number of rows deleted.
        """
        if self._engine is None:
            return 0
        try:
            from sqlalchemy import text

            cutoff = datetime.now(timezone.utc) - timedelta(days=self.RETENTION_DAYS)
            async with self._engine.begin() as conn:
                result = await conn.execute(
                    text("DELETE FROM replay_snapshots WHERE created_at < :cutoff"),
                    {"cutoff": cutoff},
                )
                deleted: int = result.rowcount or 0
                if deleted:
                    logger.info(
                        "replay_pruned",
                        deleted=deleted,
                        retention_days=self.RETENTION_DAYS,
                    )
                return deleted
        except Exception:
            if not try_only:
                raise
            logger.debug("replay_prune_skipped", reason="best_effort")
            return 0

    # ── Serialization ───────────────────────────────────────────

    def _serialize_bundle(self, bundle: PromptBundle) -> Dict[str, Any]:
        """Serialize a PromptBundle into a JSONB-appropriate dict."""
        return {
            "turn_id": str(bundle.turn_id),
            "session_id": str(bundle.session_id),
            "user_id": bundle.user_id,
            "character_id": bundle.character_id,
            "system_prompt": bundle.system_prompt,
            "messages": bundle.messages,
            "layers": {k: asdict(v) for k, v in bundle.layers.items()},
        }
