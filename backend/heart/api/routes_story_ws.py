"""WebSocket route for SS09 story mode — the real-time turn channel.

Speaks the SAME frame vocabulary as /api/chat/ws (turn_start / text_delta /
message_bubble / turn_end / error) but is a slim, self-contained loop that
delegates to StoryService.process_turn_stream. No audio (text-only MVP), no
per-character voice/model branching.

Age-gate: unlike chat (which gates the whole socket), story gates per-run —
only when the run's scenario is maturity='adult' and the user isn't verified.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import auth_manager
from heart.ss09_story import repository as repo

from .wiring import _get_engine, get_story_service

logger = structlog.get_logger(__name__)

router = APIRouter()


def _parse_turn_id(value: Any) -> uuid.UUID:
    """Parse a client-supplied turn_id, minting a fresh one if absent/invalid."""
    if value:
        try:
            return uuid.UUID(str(value))
        except (ValueError, TypeError):
            pass
    return uuid.uuid4()


async def _verify_story_token(ws: WebSocket, token: Optional[str]) -> Optional[str]:
    """Verify the JWT and return user_id (ws already closed on failure).

    Does NOT enforce age verification here — that is per-run (adult scenarios
    only), checked when a story_chat targets an adult run.
    """
    if not token:
        await ws.close(code=1008, reason="Missing token")
        return None
    try:
        token_data = auth_manager.verify_token(token)
    except Exception:
        await ws.close(code=1008, reason="Invalid token")
        return None
    return token_data.user_id


async def _load_run_scenario_and_gate(
    user_id: str, run_id: uuid.UUID
) -> tuple[Any, Any, Optional[str]]:
    """Return (run, scenario, gate_error). gate_error is a code string or None.

    gate_error ∈ {run_not_found, scenario_not_found, age_gate_required}.
    """
    async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
        run = await repo.get_run(db, run_id, uuid.UUID(user_id))
        if run is None or run.status != "active":
            return None, None, "run_not_found"
        scenario = await repo.get_scenario(db, run.scenario_id)
        if scenario is None:
            return run, None, "scenario_not_found"
        if scenario.maturity == "adult":
            result = await db.execute(
                sql_text("SELECT age_verified_at FROM users WHERE id = :uid"),
                {"uid": uuid.UUID(user_id)},
            )
            if result.scalar_one_or_none() is None:
                return run, scenario, "age_gate_required"
        return run, scenario, None


class _StorySession:
    """Per-socket state + turn dispatch for one story WebSocket connection.

    Keeps the endpoint function itself trivial (accept → loop → disconnect) and
    the branchy turn logic in small, individually-simple methods.
    """

    def __init__(self, ws: WebSocket, user_id: str, service: Any):
        self._ws = ws
        self._user_id = user_id
        self._service = service
        self._send_lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None

    async def send(self, frame: dict[str, Any]) -> None:
        async with self._send_lock:
            await self._ws.send_json(frame)

    async def dispatch(self, msg: dict[str, Any]) -> None:
        mtype = msg.get("type")
        if mtype == "story_chat":
            await self._start_chat(msg)
        elif mtype == "interrupt":
            if self._task is not None and not self._task.done():
                self._task.cancel()
        else:
            await self.send({"type": "error", "code": "unknown_type"})

    async def _start_chat(self, msg: dict[str, Any]) -> None:
        if self._task is not None and not self._task.done():
            await self.send({"type": "error", "code": "turn_in_progress"})
            return
        try:
            run_id = uuid.UUID(str(msg.get("run_id")))
        except (ValueError, TypeError):
            await self.send({"type": "error", "code": "bad_run_id"})
            return

        run, scenario, gate = await _load_run_scenario_and_gate(self._user_id, run_id)
        if gate is not None:
            await self.send({"type": "error", "code": gate})
            return

        turn_id = _parse_turn_id(msg.get("turn_id"))
        if msg.get("model"):
            run.model = str(msg["model"])
        self._task = asyncio.create_task(
            self._run_turn(run, scenario, str(msg.get("text", "")), turn_id)
        )

    async def _run_turn(self, run: Any, scenario: Any, text: str, turn_id: uuid.UUID) -> None:
        try:
            async for event, payload in self._service.process_turn_stream(
                run_id=run.id,
                user_id=uuid.UUID(self._user_id),
                player_text=text,
                scenario=scenario,
                turn_id=turn_id,
            ):
                await self.send({"type": event, **payload})
        except asyncio.CancelledError:
            await self.send(
                {"type": "turn_end", "turn_id": str(turn_id), "ok": False, "interrupted": True}
            )
            raise
        except Exception:
            logger.exception("story_ws_turn_failed", run_id=str(run.id))
            await self.send({"type": "error", "code": "turn_failed", "turn_id": str(turn_id)})
            await self.send({"type": "turn_end", "turn_id": str(turn_id), "ok": False})

    async def drain_on_disconnect(self) -> None:
        """Let an in-flight turn finish persisting rather than dropping it."""
        if self._task is None or self._task.done():
            return
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout=45.0)
        except asyncio.TimeoutError:
            logger.warning("story_ws_turn_persist_timeout", user_id=self._user_id)
        except Exception:
            logger.exception("story_ws_turn_persist_failed", user_id=self._user_id)


@router.websocket("/api/story/ws")
async def story_ws(ws: WebSocket, token: Optional[str] = Query(None)):
    """Story turn WebSocket.

    Client → Server:
        {"type": "story_chat", "run_id": "...", "text": "...", "turn_id": "...?", "model": "...?"}
        {"type": "interrupt", "turn_id": "..."}
    Server → Client:
        {"type": "turn_start" | "text_delta" | "message_bubble" | "turn_end" | "error", ...}
    """
    user_id = await _verify_story_token(ws, token)
    if not user_id:
        return

    await ws.accept()

    service = get_story_service()
    if service is None:
        await ws.send_json({"type": "error", "code": "engine_unavailable"})
        await ws.close(code=1011, reason="engine_unavailable")
        return

    session = _StorySession(ws, user_id, service)
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await session.send({"type": "error", "code": "invalid_json"})
                continue
            await session.dispatch(msg)
    except WebSocketDisconnect:
        logger.info("story_ws_disconnect", user_id=user_id)
        await session.drain_on_disconnect()
    except Exception as e:
        logger.error("story_ws_error", error=str(e))
