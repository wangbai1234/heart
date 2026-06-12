"""WebSocket chat route — per runtime_specs/08_voice.md VP3+VP4."""

from __future__ import annotations

import base64
import json
import uuid
from typing import Any, Optional

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .wiring import get_orchestrator, get_voice_service

logger = structlog.get_logger(__name__)

router = APIRouter()


def _parse_user_id(user_id: Optional[str]) -> uuid.UUID:
    """Parse user_id string to UUID."""
    try:
        return uuid.UUID(user_id) if user_id else uuid.UUID("00000000-0000-0000-0000-000000000001")
    except ValueError:
        return uuid.UUID("00000000-0000-0000-0000-000000000001")


def _create_stream_session(voice_service: Any, ws: WebSocket) -> Any:
    """Create a StreamSession if voice service is available."""
    if not voice_service:
        return None

    from heart.ss08_voice.stream_session import StreamSession

    async def send_audio(t_id: str, seq: int, audio_bytes: bytes, is_last: bool) -> None:
        """Send audio chunk to WebSocket."""
        await ws.send_json(
            {
                "type": "audio_chunk",
                "turn_id": t_id,
                "seq": seq,
                "format": "mp3",
                "data_b64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
                "is_last": is_last,
            }
        )

    session = StreamSession(voice_service, send_audio)
    return session


async def _process_stream_events(
    ws: WebSocket,
    orch: Any,
    req: Any,
    stream_session: Any,
    turn_id: str,
    character_id: str,
) -> None:
    """Process stream events from orchestrator."""
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
                # Submit to TTS stream session
                if stream_session:
                    await stream_session.submit(
                        turn_id=turn_id,
                        sentence=event["text"],
                        vad=event.get("vad"),
                        intimacy=event.get("intimacy", 0.0),
                        character_id=character_id,
                    )
            elif event_type == "turn_end":
                # Finish stream session before sending turn_end
                if stream_session:
                    await stream_session.finish()
                    stream_session = None
                await ws.send_json(
                    {
                        "type": "turn_end",
                        "turn_id": turn_id,
                    }
                )
    except Exception as e:
        logger.error("chat_ws_stream_error", error=str(e))
        if stream_session:
            stream_session.cancel()
        await ws.send_json({"type": "error", "msg": str(e)})


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
    user_uuid = _parse_user_id(user_id)

    # Get orchestrator
    orch = get_orchestrator()
    if orch is None:
        await ws.send_json({"type": "error", "msg": "Orchestrator not available"})
        return

    # Get voice service for TTS
    voice_service = get_voice_service()

    # Create stream session if voice service available
    stream_session = _create_stream_session(voice_service, ws)
    if stream_session:
        await stream_session.start()

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

    # Process stream events
    await _process_stream_events(ws, orch, req, stream_session, turn_id, character_id)


async def _handle_interrupt(ws: WebSocket, msg: dict[str, Any], active_turns: dict) -> None:
    """Handle interrupt message."""
    turn_id = msg.get("turn_id")
    if turn_id and turn_id in active_turns:
        session = active_turns[turn_id]
        session.cancel()
        await ws.send_json({"type": "interrupted", "turn_id": turn_id})


async def _handle_backpressure(msg: dict[str, Any], active_turns: dict) -> None:
    """Handle backpressure message."""
    turn_id = msg.get("turn_id")
    if turn_id and turn_id in active_turns:
        session = active_turns[turn_id]
        session.pause()


async def _handle_resume(msg: dict[str, Any], active_turns: dict) -> None:
    """Handle resume message."""
    turn_id = msg.get("turn_id")
    if turn_id and turn_id in active_turns:
        session = active_turns[turn_id]
        session.resume()


@router.websocket("/api/chat/ws")
async def chat_ws(ws: WebSocket):
    """WebSocket chat endpoint.

    Protocol:
        Client → Server:
            {"type": "chat", "text": "...", "user_id": "...", "character_id": "rin", "turn_id": "..."}
            {"type": "interrupt", "turn_id": "..."}
            {"type": "backpressure", "turn_id": "...", "buffered_ms": N}
            {"type": "resume", "turn_id": "..."}

        Server → Client:
            {"type": "turn_start", "turn_id": "..."}
            {"type": "text_delta", "turn_id": "...", "delta": "..."}
            {"type": "sentence", "turn_id": "...", "text": "...", "vad": {...}, "intimacy": 0.0}
            {"type": "audio_chunk", "turn_id": "...", "seq": N, "format": "mp3", "data_b64": "...", "is_last": bool}
            {"type": "turn_end", "turn_id": "..."}
            {"type": "interrupted", "turn_id": "..."}
    """
    await ws.accept()

    # Track active turns for interrupt support
    active_turns: dict[str, Any] = {}

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "msg": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "chat":
                await _handle_chat_message(ws, msg)
            elif msg_type == "interrupt":
                await _handle_interrupt(ws, msg, active_turns)
            elif msg_type == "backpressure":
                await _handle_backpressure(msg, active_turns)
            elif msg_type == "resume":
                await _handle_resume(msg, active_turns)

    except WebSocketDisconnect:
        logger.info("chat_ws_disconnect")
    except Exception as e:
        logger.error("chat_ws_error", error=str(e))
        try:
            await ws.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass
