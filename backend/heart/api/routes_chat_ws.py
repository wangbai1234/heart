"""WebSocket chat route — per runtime_specs/08_voice.md VP3."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .wiring import get_orchestrator

logger = structlog.get_logger(__name__)

router = APIRouter()


async def _handle_chat_message(ws: WebSocket, msg: dict[str, Any]) -> None:
    """Handle a single chat message."""
    turn_id = msg.get("turn_id") or str(uuid.uuid4())
    user_text = msg.get("text", "")
    user_id = msg.get("user_id")
    character_id = msg.get("character_id", "rin")

    if not user_text:
        await ws.send_json({"type": "error", "msg": "Missing text"})
        return

    # Parse user_id
    try:
        user_uuid = (
            uuid.UUID(user_id) if user_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
        )
    except ValueError:
        user_uuid = uuid.UUID("00000000-0000-0000-0000-000000000001")

    # Get orchestrator
    orch = get_orchestrator()
    if orch is None:
        await ws.send_json({"type": "error", "msg": "Orchestrator not available"})
        return

    # Build turn request
    from heart.ss07_orchestration.models import TurnRequest

    req = TurnRequest(
        user_id=user_uuid,
        character_id=character_id,
        user_message=user_text,
        history=[],  # WebSocket doesn't have history context
        trace_id=uuid.UUID(turn_id),
    )

    await ws.send_json({"type": "turn_start", "turn_id": turn_id})

    try:
        async for event in orch.process_turn_stream(req, db_session=None):
            event_type = event.get("type")
            if event_type == "text_delta":
                await ws.send_json(
                    {
                        "type": "text_delta",
                        "turn_id": turn_id,
                        "delta": event["delta"],
                    }
                )
            elif event_type == "sentence":
                await ws.send_json(
                    {
                        "type": "sentence",
                        "turn_id": turn_id,
                        "text": event["text"],
                        "vad": event.get("vad"),
                        "intimacy": event.get("intimacy", 0.0),
                    }
                )
            elif event_type == "turn_end":
                await ws.send_json(
                    {
                        "type": "turn_end",
                        "turn_id": turn_id,
                    }
                )
    except Exception as e:
        logger.error("chat_ws_stream_error", error=str(e))
        await ws.send_json({"type": "error", "msg": str(e)})


@router.websocket("/api/chat/ws")
async def chat_ws(ws: WebSocket):
    """WebSocket chat endpoint.

    Protocol:
        Client → Server:
            {"type": "chat", "text": "...", "user_id": "...", "character_id": "rin", "turn_id": "..."}

        Server → Client:
            {"type": "turn_start", "turn_id": "..."}
            {"type": "text_delta", "turn_id": "...", "delta": "..."}
            {"type": "sentence", "turn_id": "...", "text": "...", "vad": {...}, "intimacy": 0.0}
            {"type": "turn_end", "turn_id": "..."}
    """
    await ws.accept()
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "msg": "Invalid JSON"})
                continue

            if msg.get("type") != "chat":
                continue

            await _handle_chat_message(ws, msg)

    except WebSocketDisconnect:
        logger.info("chat_ws_disconnect")
    except Exception as e:
        logger.error("chat_ws_error", error=str(e))
        try:
            await ws.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass
