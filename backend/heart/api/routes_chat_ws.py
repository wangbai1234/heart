"""WebSocket chat route — per runtime_specs/08_voice.md VP3+VP4+VP5."""

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


def _create_stream_session(voice_service: Any, ws: WebSocket, cache: Any = None) -> Any:
    """Create a StreamSession if voice service is available."""
    if not voice_service:
        return None

    from heart.ss08_voice.stream_session import StreamSession

    async def send_audio(
        t_id: str, sentence_seq: int, seq: int, audio_bytes: bytes, is_last: bool
    ) -> None:
        """Send audio chunk to WebSocket."""
        logger.debug(
            "audio_send", turn_id=t_id, sentence_seq=sentence_seq, seq=seq, is_last=is_last
        )
        await ws.send_json(
            {
                "type": "audio_chunk",
                "turn_id": t_id,
                "sentence_seq": sentence_seq,
                "seq": seq,
                "format": "mp3",
                "data_b64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
                "is_last": is_last,
            }
        )

    session = StreamSession(voice_service, send_audio, cache=cache)
    return session


async def _send_text_delta(ws: WebSocket, turn_id: str, delta: str) -> None:
    """Send text delta event."""
    await ws.send_json({"type": "text_delta", "turn_id": turn_id, "delta": delta})


async def _send_sentence(ws: WebSocket, turn_id: str, event: dict) -> None:
    """Send sentence event."""
    await ws.send_json(
        {
            "type": "sentence",
            "turn_id": turn_id,
            "text": event["text"],
            "vad": event.get("vad"),
            "intimacy": event.get("intimacy", 0.0),
        }
    )


async def _send_turn_end(ws: WebSocket, turn_id: str) -> None:
    """Send turn end event."""
    await ws.send_json({"type": "turn_end", "turn_id": turn_id})


async def _handle_event(
    ws: WebSocket,
    event: dict,
    stream_session: Any,
    turn_id: str,
    character_id: str,
) -> bool:
    """Handle a single stream event. Returns True if turn ended."""
    event_type = event.get("type")
    if event_type == "text_delta":
        await _send_text_delta(ws, turn_id, event["delta"])
    elif event_type == "sentence":
        await _send_sentence(ws, turn_id, event)
        if stream_session:
            await stream_session.submit(
                turn_id=turn_id,
                sentence=event["text"],
                vad=event.get("vad"),
                intimacy=event.get("intimacy", 0.0),
                character_id=character_id,
                locked_emotion=event.get("locked_emotion"),
                locked_speed_base=event.get("locked_speed_base"),
                locked_pitch_base=event.get("locked_pitch_base"),
            )
    elif event_type == "turn_end":
        if stream_session:
            await stream_session.finish(turn_id=turn_id)
        await _send_turn_end(ws, turn_id)
        return True
    return False


async def _process_stream_events(
    ws: WebSocket,
    orch: Any,
    req: Any,
    stream_session: Any,
    turn_id: str,
    character_id: str,
    active_turns: dict[str, Any],
) -> None:
    """Process stream events from orchestrator."""
    if stream_session:
        active_turns[turn_id] = stream_session

    try:
        async for event in orch.process_turn_stream(req, db_session=None):
            if stream_session and stream_session.is_cancelled:
                break
            if await _handle_event(ws, event, stream_session, turn_id, character_id):
                break
    except Exception as e:
        logger.error("chat_ws_stream_error", error=str(e))
        if stream_session:
            stream_session.cancel(turn_id=turn_id)
        await ws.send_json({"type": "error", "msg": str(e)})
    finally:
        active_turns.pop(turn_id, None)


async def _handle_chat_message(
    ws: WebSocket, msg: dict[str, Any], active_turns: dict[str, Any], cache: Any = None
) -> None:
    """Handle a single chat message."""
    turn_id = msg.get("turn_id") or str(uuid.uuid4())
    user_text = msg.get("text", "")
    user_id = msg.get("user_id")
    character_id = msg.get("character_id", "rin")

    if not user_text:
        await ws.send_json({"type": "error", "msg": "Missing text"})
        return

    user_uuid = _parse_user_id(user_id)
    orch = get_orchestrator()
    if orch is None:
        await ws.send_json({"type": "error", "msg": "Orchestrator not available"})
        return

    voice_service = get_voice_service()
    stream_session = _create_stream_session(voice_service, ws, cache=cache)
    if stream_session:
        await stream_session.start()

    from heart.ss07_orchestration.models import TurnRequest

    req = TurnRequest(
        user_id=user_uuid,
        character_id=character_id,
        user_message=user_text,
        history=[],
        trace_id=uuid.UUID(turn_id),
    )

    await ws.send_json({"type": "turn_start", "turn_id": turn_id})
    await _process_stream_events(ws, orch, req, stream_session, turn_id, character_id, active_turns)


async def _handle_interrupt(ws: WebSocket, msg: dict[str, Any], active_turns: dict) -> None:
    """Handle interrupt message."""
    turn_id = msg.get("turn_id")
    if turn_id and turn_id in active_turns:
        session = active_turns[turn_id]
        session.cancel(turn_id=turn_id)
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


async def _handle_message(
    ws: WebSocket,
    msg: dict[str, Any],
    active_turns: dict[str, Any],
    cache: Any,
) -> None:
    """Handle a single WebSocket message."""
    msg_type = msg.get("type")
    if msg_type == "chat":
        await _handle_chat_message(ws, msg, active_turns, cache)
    elif msg_type == "interrupt":
        await _handle_interrupt(ws, msg, active_turns)
    elif msg_type == "backpressure":
        await _handle_backpressure(msg, active_turns)
    elif msg_type == "resume":
        await _handle_resume(msg, active_turns)


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
            {"type": "audio_chunk", "turn_id": "...", "sentence_seq": N, "seq": M, "format": "mp3", "data_b64": "...", "is_last": bool}
            {"type": "turn_end", "turn_id": "..."}
            {"type": "interrupted", "turn_id": "..."}
    """
    await ws.accept()
    active_turns: dict[str, Any] = {}

    from heart.ss08_voice.voice_cache import VoiceCache

    cache = VoiceCache()

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "msg": "Invalid JSON"})
                continue
            await _handle_message(ws, msg, active_turns, cache)

    except WebSocketDisconnect:
        logger.info("chat_ws_disconnect")
        for turn_id, session in active_turns.items():
            session.cancel(turn_id=turn_id)
    except Exception as e:
        logger.error("chat_ws_error", error=str(e))
        for turn_id, session in active_turns.items():
            session.cancel(turn_id=turn_id)
        try:
            await ws.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass
