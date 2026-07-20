"""WebSocket chat route — per runtime_specs/08_voice.md VP3+VP4+VP5.

Also provides REST chat history endpoint.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import json
import random
import uuid
from typing import Any, Optional
from urllib.parse import urlparse

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, auth_manager, get_current_user
from heart.ss01_soul.character_catalog import is_known_character

from .wiring import _get_engine, get_db, get_orchestrator, get_voice_service

logger = structlog.get_logger(__name__)

router = APIRouter()
# Recent same-character turns injected into the prompt for short-term
# continuity. 50 aligns with the commercial spec (docs/upgrade/commercial).
# Beyond this window, continuity relies on SS02 long-term recall.
RECENT_HISTORY_LIMIT = 50

# Wall-clock ceiling for a single turn's orchestration+synthesis. Kept BELOW the
# frontend watchdog (60s) so the backend always emits a proper terminal frame
# (turn_end / TURN_TIMEOUT error) before the client force-clears its own state.
# A hung/slow TTS provider therefore can never wedge the turn "forever".
_TURN_TIMEOUT_S = 45.0


def _extract_storage_key(audio_url: str) -> str | None:
    """Extract object key from stored S3/MinIO URL."""
    if not audio_url:
        return None
    parsed = urlparse(audio_url)
    path = parsed.path.lstrip("/")
    if not path or "/" not in path:
        return None
    return path.split("/", 1)[1]


async def _load_recent_conversation_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    character_id: str,
    limit: int = RECENT_HISTORY_LIMIT,
) -> list[dict[str, str]]:
    """Load the most recent persisted turns for prompt conversation history."""
    result = await db.execute(
        sql_text(
            """
            SELECT role, content
            FROM chat_messages
            WHERE user_id = :uid AND character_id = :cid
            ORDER BY created_at DESC
            LIMIT :limit
            """
        ),
        {"uid": user_id, "cid": character_id, "limit": limit},
    )
    rows = result.mappings().all()
    history = [
        {"role": row["role"], "content": row["content"] or ""}
        for row in reversed(rows)
        if row["role"] in ("user", "assistant")
    ]
    return history


def _create_stream_session(
    voice_service: Any,
    ws: WebSocket,
    cache: Any = None,
    preferred_provider_name: Optional[str] = None,
    clone_reference: Optional[str] = None,
    character_id: str = "",
) -> Any:
    """Create a StreamSession if voice service is available."""
    if not voice_service:
        return None

    from heart.ss08_voice.stream_session import StreamSession

    async def send_audio(
        t_id: str, seq: int, audio_bytes: bytes, is_last: bool, fmt: str = "pcm16"
    ) -> None:
        """Send audio chunk to WebSocket as pcm16 with sentence_seq."""
        await ws.send_json(
            {
                "type": "audio_chunk",
                "turn_id": t_id,
                "character_id": character_id,
                "sentence_seq": 0,
                "seq": seq,
                "format": fmt,
                "data_b64": base64.b64encode(audio_bytes).decode() if audio_bytes else "",
                "is_last": is_last,
            }
        )

    session = StreamSession(
        voice_service,
        send_audio,
        cache=cache,
        preferred_provider_name=preferred_provider_name,
        clone_reference=clone_reference,
    )
    return session


async def _send_text_delta(ws: WebSocket, turn_id: str, delta: str, character_id: str) -> None:
    """Send text delta event."""
    await ws.send_json(
        {"type": "text_delta", "turn_id": turn_id, "character_id": character_id, "delta": delta}
    )


async def _send_sentence(ws: WebSocket, turn_id: str, event: dict, character_id: str) -> None:
    """Send sentence event."""
    await ws.send_json(
        {
            "type": "sentence",
            "turn_id": turn_id,
            "character_id": character_id,
            "text": event["text"],
            "vad": event.get("vad"),
            "intimacy": event.get("intimacy", 0.0),
            "active_emotions": event.get("active_emotions", []),
        }
    )


async def _send_turn_end(ws: WebSocket, turn_id: str, character_id: str) -> None:
    """Send turn end event."""
    await ws.send_json({"type": "turn_end", "turn_id": turn_id, "character_id": character_id})


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
        await _send_text_delta(ws, turn_id, event["delta"], character_id)
    elif event_type == "sentence":
        await _send_sentence(ws, turn_id, event, character_id)
        if stream_session:
            await stream_session.submit(
                turn_id=turn_id,
                sentence=event["text"],
                vad=event.get("vad"),
                intimacy=event.get("intimacy", 0.0),
                active_emotions=event.get("active_emotions", []),
                character_id=character_id,
            )
    elif event_type == "turn_end":
        if stream_session:
            await stream_session.finish()
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
        async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
            async for event in orch.process_turn_stream(req, db_session=db):
                if stream_session and stream_session.is_cancelled:
                    break
                if await _handle_event(ws, event, stream_session, turn_id, character_id):
                    break
    except Exception as e:
        logger.error("chat_ws_stream_error", error=str(e))
        if stream_session:
            stream_session.cancel()
        await ws.send_json({"type": "error", "msg": str(e)})
    finally:
        active_turns.pop(turn_id, None)


def _active_tts_provider_name() -> str:
    """Name of the process-default primary TTS provider, or '' if none.

    Used as the tier-gate fallback for characters with no per-character
    voice_provider (built-in rin/dorothy): the default path synthesizes via this
    primary. UGC characters override it with their configured voice_provider
    (see _precheck_billing / resolve_voice_provider).
    """
    try:
        from .wiring import get_voice_service

        vs = get_voice_service()
        return vs.provider.name if vs and vs.provider else ""
    except Exception:
        return ""


async def _precheck_billing(
    user_uuid: uuid.UUID,
    character_id: str,
    turn_id: str,
    ws: WebSocket,
    model: str = "deepseek",
) -> tuple[bool, bool]:
    """Pre-check voice setting, membership entitlement, and balance.

    Returns (effective_voice, can_proceed).
    """
    try:
        from sqlalchemy.ext.asyncio import AsyncSession

        from heart.billing import get_balance
        from heart.billing.pricing import llm_cost_fen, tts_cost_fen
        from heart.membership import (
            ModelForbiddenError,
            assert_model_allowed,
            get_effective_tier,
        )
        from heart.ss08_voice.voice_resolver import resolve_effective_voice

        from .wiring import _get_engine

        async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
            result = await db.execute(
                sql_text(
                    "SELECT voice_enabled FROM user_character_settings WHERE user_id = :uid AND character_id = :cid"
                ),
                {"uid": user_uuid, "cid": character_id},
            )
            row = result.scalar_one_or_none()
            effective_voice = row if row is not None else False

            # Membership tier → model entitlement
            tier = await get_effective_tier(db, user_uuid)
            try:
                assert_model_allowed(tier, model)
            except ModelForbiddenError:
                await ws.send_json(
                    {
                        "type": "model_forbidden",
                        "turn_id": turn_id,
                        "character_id": character_id,
                        "model": model,
                        "tier": tier,
                    }
                )
                return effective_voice, False

            # Voice TTS entitlement (E): resolve the user's EFFECTIVE voice for
            # this character — resolve_effective_voice reads their per-character
            # provider choice and tier-gates it (free tier can't use Fish, so it
            # degrades to MiMo, still voice). We then bill by that provider. If no
            # tier-allowed ready voice exists, degrade this turn to text — never
            # block text.
            tts_cost = 0
            if effective_voice:
                ev = await resolve_effective_voice(character_id, user_uuid, db)
                if ev is None:
                    logger.info("voice_downgraded_no_usable_voice", tier=tier, turn_id=turn_id)
                    effective_voice = False
                else:
                    tts_cost = tts_cost_fen(ev.provider)

            # Balance floor (C): LLM (per model) + TTS (per provider). There is no
            # legacy per-message charge — text bubbles are free; a turn costs only
            # the LLM (by served model) plus TTS (by provider, voice turns only).
            balance = await get_balance(db, user_uuid)
            llm_cost = llm_cost_fen(model)
            min_required = llm_cost + tts_cost

            if balance < min_required:
                await ws.send_json(
                    {
                        "type": "insufficient_credits",
                        "turn_id": turn_id,
                        "character_id": character_id,
                        "needed": min_required / 100,
                        "balance": balance / 100,
                    }
                )
                return effective_voice, False

            return effective_voice, True
    except Exception as e:
        logger.exception("billing_precheck_failed", error=str(e))
        await ws.send_json(
            {
                "type": "error",
                "code": "BILLING_CHECK_FAILED",
                "turn_id": turn_id,
                "character_id": character_id,
                "msg": "Billing check failed",
            }
        )
        return False, False


async def _charge_and_insert_bubbles(
    db: Any,
    ws: WebSocket,
    user_uuid: uuid.UUID,
    turn_id: str,
    character_id: str,
    segments: list[Any],
    actual_modality: str,
    per_message_cost: int,
    audio_url: Optional[str],
    audio_duration_ms: Optional[int],
) -> tuple[int, int]:
    """Deduct credits and INSERT assistant rows.

    ``segments`` is a list of ``{kind, content}`` dicts from split_response.
    Action segments are persisted but not charged and get no audio metadata.
    Text segments are charged at per_message_cost each.
    """
    from heart.billing import InsufficientCreditsError, deduct_credits

    total_charged = 0
    new_balance = 0
    audio_attached = False

    for i, seg in enumerate(segments):
        kind = seg["kind"]
        content = seg["content"]
        try:
            credits_this_row = 0
            seg_audio_url = None
            seg_audio_dur = None
            if kind == "text":
                # per_message_cost is 0 under the model+provider billing scheme
                # (LLM charged per turn, TTS per provider). Only deduct if a
                # legacy per-message cost is explicitly configured (> 0).
                if per_message_cost > 0:
                    new_balance = await deduct_credits(
                        db,
                        user_uuid,
                        per_message_cost,
                        f"turn:{turn_id}:msg:{i}",
                        f"consume_{actual_modality}",
                    )
                    total_charged += per_message_cost
                    credits_this_row = per_message_cost
                if not audio_attached:
                    seg_audio_url = audio_url
                    seg_audio_dur = audio_duration_ms
                    audio_attached = True
            await db.execute(
                sql_text(
                    "INSERT INTO chat_messages "
                    "(id, user_id, character_id, turn_id, role, content, modality, "
                    " audio_url, audio_duration_ms, credits_charged, sequence_id, kind, "
                    " created_at) "
                    "VALUES (:id, :uid, :cid, :tid, 'assistant', :content, :modality, "
                    "        :audio_url, :audio_dur, :credits, :seq_id, :kind, "
                    "        clock_timestamp())"
                ),
                {
                    "id": uuid.uuid4(),
                    "uid": user_uuid,
                    "cid": character_id,
                    "tid": uuid.UUID(turn_id),
                    "content": content,
                    "modality": actual_modality if kind == "text" else "text",
                    "audio_url": seg_audio_url,
                    "audio_dur": seg_audio_dur,
                    "credits": credits_this_row,
                    "seq_id": i,
                    "kind": kind,
                },
            )
        except InsufficientCreditsError as ice:
            await db.rollback()
            await ws.send_json(
                {
                    "type": "insufficient_credits",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "needed": ice.needed / 100,
                    "balance": ice.balance / 100,
                }
            )
            await ws.send_json(
                {"type": "turn_end", "turn_id": turn_id, "character_id": character_id}
            )
            return -1, 0  # sentinel: caller should return early

    return total_charged, new_balance


def _derive_segments_and_cost(
    full_text: str, actual_modality: str, cfg: Any
) -> tuple[list[Any], int]:
    """Return ``(segments, per_message_cost)`` for a completed turn.

    Text mode gets the full semantic split (action + text bubbles). Voice
    mode intentionally emits a single text bubble because TTS synthesises
    the whole response as one audio clip: splitting into N bubbles would
    charge voice cost × N while only one clip plays.

    ``per_message_cost`` is always 0 under the model+provider billing scheme:
    a turn is billed per LLM turn (by served model) and per TTS (by provider),
    never per message bubble. Returning 0 here avoids the legacy double-charge
    (voice bubbles were previously charged ``credits_cost_voice_message`` *on
    top of* the per-provider TTS cost). ``cfg`` is retained for signature
    compatibility with existing callers/tests.
    """
    from heart.ss05_composer.message_splitter import split_response

    _ = cfg  # legacy per-message cost is intentionally not applied
    if actual_modality == "text":
        segments = split_response(full_text)
        if not segments:
            segments = [{"kind": "text", "content": full_text}]
        return segments, 0
    return [{"kind": "text", "content": full_text}], 0


async def _upload_turn_audio(
    stream_session: Any, user_uuid: uuid.UUID, turn_id: str
) -> tuple[Optional[str], Optional[int]]:
    """Upload voice audio to S3 if available. Returns (audio_url, duration_ms)."""
    if not (stream_session and stream_session.full_audio):
        return None, None
    try:
        from heart.infra.storage import is_s3_configured, upload_file

        if not is_s3_configured():
            return None, None
        audio_bytes = stream_session.full_audio
        key = f"chat_audio/{user_uuid}/{turn_id}.wav"
        audio_url = await upload_file(audio_bytes, key, "audio/wav")
        audio_duration_ms = int(len(audio_bytes) / (24000 * 2) * 1000)
        return audio_url, audio_duration_ms
    except Exception as e:
        logger.warning("audio_upload_failed", error=str(e))
        return None, None


async def _charge_llm_cost(
    db: Any,
    user_uuid: uuid.UUID,
    turn_id: str,
    served_model: str,
) -> tuple[int, int]:
    """Deduct LLM per-turn cost. Returns (cost_charged, new_balance). 0,0 if free."""
    from heart.billing import deduct_credits
    from heart.billing.pricing import llm_cost_fen

    llm_cost = llm_cost_fen(served_model)
    if llm_cost == 0:
        return 0, 0
    new_balance = await deduct_credits(
        db, user_uuid, llm_cost, f"turn:{turn_id}:llm", "consume_llm"
    )
    return llm_cost, new_balance


async def _charge_tts_cost(
    db: Any,
    user_uuid: uuid.UUID,
    turn_id: str,
    tts_provider: str,
) -> tuple[int, int]:
    """Deduct TTS per-turn cost. Returns (cost_charged, new_balance). 0,0 if free provider."""
    from heart.billing import deduct_credits
    from heart.billing.pricing import tts_cost_fen

    tts_cost = tts_cost_fen(tts_provider)
    if tts_cost == 0:
        return 0, 0
    new_balance = await deduct_credits(
        db, user_uuid, tts_cost, f"turn:{turn_id}:tts", "consume_tts"
    )
    return tts_cost, new_balance


async def _post_turn_billing(
    ws: WebSocket,
    user_uuid: uuid.UUID,
    turn_id: str,
    character_id: str,
    user_text: str,
    collected_text: list[str],
    actual_modality: str,
    turn_safety_blocked: bool,
    stream_session: Any = None,
    served_model: str = "deepseek",
    degraded_to: Optional[str] = None,
    tts_provider: str = "",
) -> None:
    """Charge credits and persist chat messages after turn completes.

    Text turns: split full response into up to 4 short bubbles; deduct
    credits_cost_text_message per bubble using per-message idempotency keys.
    Voice turns: single message, deduct credits_cost_voice_message once.
    """
    from sqlalchemy.ext.asyncio import AsyncSession

    from heart.core.config import settings as cfg

    from .wiring import _get_engine

    audio_url: Optional[str] = None
    audio_duration_ms: Optional[int] = None

    if actual_modality == "voice":
        audio_url, audio_duration_ms = await _upload_turn_audio(stream_session, user_uuid, turn_id)

    full_text = "".join(collected_text)
    segments, per_message_cost = _derive_segments_and_cost(full_text, actual_modality, cfg)

    try:
        async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
            await db.execute(
                sql_text(
                    "INSERT INTO chat_messages "
                    "(id, user_id, character_id, turn_id, role, content, modality, created_at) "
                    "VALUES (:id, :uid, :cid, :tid, 'user', :content, 'text', NOW())"
                ),
                {
                    "id": uuid.uuid4(),
                    "uid": user_uuid,
                    "cid": character_id,
                    "tid": uuid.UUID(turn_id),
                    "content": user_text,
                },
            )

            total_charged, new_balance = 0, 0

            if not turn_safety_blocked:
                total_charged, new_balance = await _charge_and_insert_bubbles(
                    db,
                    ws,
                    user_uuid,
                    turn_id,
                    character_id,
                    segments,
                    actual_modality,
                    per_message_cost,
                    audio_url,
                    audio_duration_ms,
                )
                if total_charged == -1:
                    return  # InsufficientCreditsError already handled

                # LLM per-turn billing (idempotent key turn:{id}:llm)
                try:
                    llm_cost, _bal = await _charge_llm_cost(db, user_uuid, turn_id, served_model)
                    if llm_cost > 0:
                        total_charged += llm_cost
                        new_balance = _bal
                except Exception as _llm_err:
                    logger.exception(
                        "llm_billing_failed",
                        turn_id=turn_id,
                        model=served_model,
                        error=str(_llm_err),
                    )
                    raise

                # TTS per-turn billing (idempotent key turn:{id}:tts)
                if actual_modality == "voice" and tts_provider:
                    try:
                        tts_cost, _bal = await _charge_tts_cost(
                            db, user_uuid, turn_id, tts_provider
                        )
                        if tts_cost > 0:
                            total_charged += tts_cost
                            new_balance = _bal
                    except Exception as _tts_err:
                        logger.exception(
                            "tts_billing_failed",
                            turn_id=turn_id,
                            provider=tts_provider,
                            error=str(_tts_err),
                        )
                        raise

                # Free turn (e.g. DeepSeek text, nothing deducted): the charge
                # helpers return 0 balance, so fetch the real balance for turn_end.
                if total_charged == 0:
                    from heart.billing import get_balance

                    new_balance = await get_balance(db, user_uuid)

            await db.commit()

        # ── Invite first-chat reward (best-effort, errors don't affect billing) ─
        try:
            from heart.invite.service import handle_first_chat

            async with AsyncSession(_get_engine(), expire_on_commit=False) as _invite_db:
                await handle_first_chat(_invite_db, user_uuid)
                await _invite_db.commit()
        except Exception:
            logger.exception("invite_first_chat_hook_failed", user_id=str(user_uuid))

        # ── Send WS events ────────────────────────────────────────────────────
        for i, seg in enumerate(segments):
            await ws.send_json(
                {
                    "type": "message_bubble",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "sequence_id": i,
                    "kind": seg["kind"],
                    "content": seg["content"],
                }
            )
            if i < len(segments) - 1:
                await asyncio.sleep(random.uniform(0.25, 0.6))

        await ws.send_json(
            {
                "type": "turn_end",
                "turn_id": turn_id,
                "character_id": character_id,
                "modality": actual_modality,
                "credits_charged": total_charged / 100,
                "balance": new_balance / 100,
                "served_model": served_model,
                "degraded_to": degraded_to,
            }
        )

    except Exception as e:
        logger.error("chat_persist_failed", error=str(e))

        with contextlib.suppress(Exception):
            await ws.send_json(
                {
                    "type": "error",
                    "code": "PERSIST_FAILED",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "msg": "消息保存失败，请重试",
                }
            )
            await ws.send_json(
                {
                    "type": "turn_end",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "modality": actual_modality,
                    "credits_charged": 0,
                    "balance": 0,
                }
            )


async def _run_orchestrator(
    ws: WebSocket,
    orch: Any,
    req: Any,
    stream_session: Any,
    turn_id: str,
    character_id: str,
    active_turns: dict[str, Any],
    db_session: AsyncSession,
) -> tuple[bool, bool, bool, list[str], str, Optional[str]]:
    """Run orchestrator stream.

    Returns (turn_completed, safety_blocked, audio_produced, collected_text,
             served_model, degraded_to).
    """
    turn_completed = False
    safety_blocked = False
    collected_text: list[str] = []
    turn_path = "normal"
    served_model: str = getattr(req, "model", "deepseek")
    degraded_to: Optional[str] = None

    if stream_session:
        active_turns[turn_id] = stream_session

    try:
        async for event in orch.process_turn_stream(req, db_session=db_session):
            if stream_session and stream_session.is_cancelled:
                break

            etype = event.get("type")
            if etype == "text_delta":
                collected_text.append(event.get("delta", ""))
            if etype == "turn_end":
                turn_completed = True
                turn_path = event.get("path", "normal")
                served_model = event.get("served_model", served_model)
                degraded_to = event.get("degraded_to")
                if turn_path in ("care", "reject", "fallback"):
                    safety_blocked = True

            if await _handle_event(ws, event, stream_session, turn_id, character_id):
                break
    except Exception as e:
        from heart.ss08_voice.voice_catalog import VoiceNotConfigured

        _is_vcfg = isinstance(e, VoiceNotConfigured)
        logger.error("chat_ws_stream_error", error=str(e))
        if stream_session:
            stream_session.cancel()
        await ws.send_json(
            {
                "type": "error",
                "code": "VOICE_NOT_CONFIGURED" if _is_vcfg else "STREAM_ERROR",
                "turn_id": turn_id,
                "character_id": character_id,
                "msg": "该角色暂未配置音色" if _is_vcfg else str(e),
            }
        )
    finally:
        active_turns.pop(turn_id, None)

    audio_produced = stream_session.audio_produced if stream_session else False
    return turn_completed, safety_blocked, audio_produced, collected_text, served_model, degraded_to


async def _handle_chat_message(
    ws: WebSocket,
    msg: dict[str, Any],
    active_turns: dict[str, Any],
    user_id: str,
    cache: Any = None,
) -> None:
    """Handle a single chat message with billing integration.

    user_id is taken from the authenticated token (not from message body).
    Flow: voice setting check → balance pre-check → orchestrator → charge → persist.
    """
    turn_id = msg.get("turn_id") or str(uuid.uuid4())
    user_text = msg.get("text", "")
    character_id = msg.get("character_id", "rin")
    # Requested LLM model — default to deepseek (free, unlimited).
    model = msg.get("model", "deepseek") or "deepseek"

    if not user_text:
        await ws.send_json(
            {
                "type": "error",
                "code": "MISSING_TEXT",
                "turn_id": turn_id,
                "character_id": character_id,
                "msg": "Missing text",
            }
        )
        return

    # Boundary guard: reject ids with no loaded Soul Spec (in-memory, no DB hit)
    # before they reach billing / orchestrator / persistence.
    if not is_known_character(character_id):
        await ws.send_json(
            {
                "type": "error",
                "code": "SOUL_NOT_LOADED",
                "turn_id": turn_id,
                "character_id": character_id,
                "msg": f"未知角色: {character_id}",
            }
        )
        return

    user_uuid = uuid.UUID(user_id)

    # ── 1. Pre-check: voice setting + membership entitlement + balance ──
    effective_voice, can_proceed = await _precheck_billing(
        user_uuid, character_id, turn_id, ws, model=model
    )
    if not can_proceed:
        return

    # ── 1b. Pre-populate voice catalog for UGC characters ──
    # VoiceDirector.derive() uses the in-memory VOICE_CATALOG which only has built-ins.
    # Resolve DB-backed voice for UGC characters now (async) and register before orchestrator starts.
    # Provider that owns this character's voice (None → process-default chain);
    # threaded into the StreamSession so synthesis routes to the right engine.
    voice_provider: Optional[str] = None
    clone_reference: Optional[str] = None
    if effective_voice:
        from heart.ss08_voice.voice_catalog import register_voice
        from heart.ss08_voice.voice_resolver import resolve_effective_voice

        async with AsyncSession(_get_engine(), expire_on_commit=False) as _vdb:
            ev = await resolve_effective_voice(character_id, user_uuid, _vdb)

        if ev is None:
            # No tier-allowed ready voice (matches _precheck degrade). Keep the
            # turn text-only rather than erroring — user still gets the reply.
            effective_voice = False
        else:
            voice_provider = ev.provider
            clone_reference = ev.reference_ref
            # Register a voice_id for the director. Fish/MiniMax use their id;
            # a MiMo zero-shot clone has none (the reference audio is the voice),
            # so register the character_id as a stable per-character key (keeps
            # the TTS cache from colliding across characters).
            register_voice(character_id, "default", ev.voice_id or character_id)

    # ── 2. Run orchestrator ──
    orch = get_orchestrator()
    if orch is None:
        await ws.send_json(
            {
                "type": "error",
                "code": "SERVICE_UNAVAILABLE",
                "turn_id": turn_id,
                "character_id": character_id,
                "msg": "Orchestrator not available",
            }
        )
        return

    voice_service = get_voice_service()
    stream_session = _create_stream_session(
        voice_service if effective_voice else None,
        ws,
        cache=cache,
        preferred_provider_name=voice_provider,
        clone_reference=clone_reference,
        character_id=character_id,
    )
    if stream_session:
        await stream_session.start()

    # A turn MUST always end with exactly one terminal frame for the client so
    # neither the "正在回复中" indicator nor a voice bubble's "加载中" can hang.
    # _terminal_sent tracks whether a turn_end (or terminal error carrying its
    # own turn_end) has gone out; the finally guarantees one otherwise.
    turn_completed = False
    turn_safety_blocked = False
    audio_produced = False
    collected_text: list[str] = []
    served_model = model
    degraded_to: Optional[str] = None
    _terminal_sent = False
    try:
        async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
            from heart.ss07_orchestration.models import TurnRequest

            history = await _load_recent_conversation_history(db, user_uuid, character_id)
            req = TurnRequest(
                user_id=user_uuid,
                character_id=character_id,
                user_message=user_text,
                history=history,
                trace_id=uuid.UUID(turn_id),
                model=model,
            )

            await ws.send_json(
                {"type": "turn_start", "turn_id": turn_id, "character_id": character_id}
            )
            try:
                (
                    turn_completed,
                    turn_safety_blocked,
                    audio_produced,
                    collected_text,
                    served_model,
                    degraded_to,
                ) = await asyncio.wait_for(
                    _run_orchestrator(
                        ws,
                        orch,
                        req,
                        stream_session,
                        turn_id,
                        character_id,
                        active_turns,
                        db,
                    ),
                    timeout=_TURN_TIMEOUT_S,
                )
            except asyncio.TimeoutError:
                # Slow/hung provider — cancel synthesis and surface a clean error.
                # turn_completed stays False, so the finally emits turn_end.
                logger.error("chat_ws_turn_timeout", turn_id=turn_id, character_id=character_id)
                if stream_session:
                    stream_session.cancel()
                with contextlib.suppress(Exception):
                    await ws.send_json(
                        {
                            "type": "error",
                            "code": "TURN_TIMEOUT",
                            "turn_id": turn_id,
                            "character_id": character_id,
                            "msg": "响应超时，请重试",
                        }
                    )

        # ── 3. Post-turn: charge + persist ──
        _full_text_empty = not "".join(collected_text).strip()
        if turn_completed and _full_text_empty:
            await ws.send_json(
                {
                    "type": "error",
                    "code": "EMPTY_RESPONSE",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "msg": "生成失败，请重试",
                }
            )
            await ws.send_json(
                {
                    "type": "turn_end",
                    "turn_id": turn_id,
                    "character_id": character_id,
                    "modality": "text",
                    "credits_charged": 0,
                    "balance": 0,
                }
            )
            _terminal_sent = True
        elif turn_completed:
            actual_modality = "voice" if audio_produced else "text"
            await _post_turn_billing(
                ws,
                user_uuid,
                turn_id,
                character_id,
                user_text,
                collected_text,
                actual_modality,
                turn_safety_blocked,
                stream_session,
                served_model=served_model,
                degraded_to=degraded_to,
                tts_provider=stream_session.tts_provider_name if stream_session else "",
            )
            _terminal_sent = True
    finally:
        # Cancelled, timed out, or any unexpected failure: the client still gets
        # a terminal frame so its per-character state clears.
        if not _terminal_sent:
            with contextlib.suppress(Exception):
                await _send_turn_end(ws, turn_id, character_id)


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


async def _handle_message(
    ws: WebSocket,
    msg: dict[str, Any],
    active_turns: dict[str, Any],
    cache: Any,
    user_id: str,
) -> None:
    """Handle a single WebSocket message."""
    msg_type = msg.get("type")
    if msg_type == "chat":
        await _handle_chat_message(ws, msg, active_turns, user_id, cache)
    elif msg_type == "interrupt":
        await _handle_interrupt(ws, msg, active_turns)
    elif msg_type == "backpressure":
        await _handle_backpressure(msg, active_turns)
    elif msg_type == "resume":
        await _handle_resume(msg, active_turns)


# ── REST: Chat History ──────────────────────────────────────────────


@router.get("/api/chat/history")
async def get_chat_history(
    character_id: str = Query(...),
    cursor: Optional[str] = Query(None),
    limit: int = Query(30, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get paginated chat history for a character (newest first)."""
    uid = uuid.UUID(current_user.user_id)

    if cursor:
        result = await db.execute(
            sql_text("""
                SELECT id, role, content, modality, audio_url, audio_duration_ms,
                       credits_charged, turn_id, created_at, kind
                FROM chat_messages
                WHERE user_id = :uid AND character_id = :cid AND created_at < :cursor
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": uid, "cid": character_id, "cursor": cursor, "limit": limit + 1},
        )
    else:
        result = await db.execute(
            sql_text("""
                SELECT id, role, content, modality, audio_url, audio_duration_ms,
                       credits_charged, turn_id, created_at, kind
                FROM chat_messages
                WHERE user_id = :uid AND character_id = :cid
                ORDER BY created_at DESC
                LIMIT :limit
            """),
            {"uid": uid, "cid": character_id, "limit": limit + 1},
        )

    rows = result.mappings().all()
    has_next = len(rows) > limit
    items = rows[:limit]

    return {
        "items": [
            {
                "id": str(r["id"]),
                "role": r["role"],
                "content": r["content"],
                "modality": r["modality"],
                "audio_url": r["audio_url"],
                "audio_duration_ms": r["audio_duration_ms"],
                "credits_charged": r["credits_charged"],
                "turn_id": str(r["turn_id"]) if r["turn_id"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                # `kind` distinguishes an action bubble (grey pill) from a text
                # bubble. Without it the frontend fell back to modality-based
                # kinds and rendered action messages as plain text on history
                # load (TEST_REPORT_20260712 BUG-5).
                "kind": r["kind"] or "text",
            }
            for r in items
        ],
        "next_cursor": items[-1]["created_at"].isoformat() if has_next and items else None,
    }


@router.get("/api/chat/inbox-summary")
async def get_inbox_summary(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return per-character last-message summary with server-side unread counts."""
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        sql_text("""
            SELECT
                m.character_id,
                m.content,
                m.modality,
                m.created_at,
                (
                    SELECT COUNT(*)
                    FROM chat_messages cm
                    WHERE cm.user_id    = :uid
                      AND cm.character_id = m.character_id
                      AND cm.role         = 'assistant'
                      AND cm.created_at   > COALESCE(rs.last_read_at, '-infinity'::timestamptz)
                ) AS unread_count
            FROM (
                SELECT DISTINCT ON (character_id)
                    character_id, content, modality, created_at
                FROM chat_messages
                WHERE user_id = :uid
                ORDER BY character_id, created_at DESC
            ) m
            LEFT JOIN user_character_read_state rs
                ON rs.user_id = :uid AND rs.character_id = m.character_id
        """),
        {"uid": uid},
    )
    rows = result.mappings().all()
    return {
        "items": [
            {
                "character_id": r["character_id"],
                "last_message_text": r["content"] or "",
                "last_message_at": r["created_at"].isoformat() if r["created_at"] else None,
                "modality": r["modality"],
                "unread_count": int(r["unread_count"] or 0),
            }
            for r in rows
        ]
    }


@router.post("/api/chat/{character_id}/mark-read")
async def mark_character_read(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upsert last_read_at for a character so subsequent inbox-summary calls
    return an accurate unread_count."""
    uid = uuid.UUID(current_user.user_id)
    await db.execute(
        sql_text("""
            INSERT INTO user_character_read_state (user_id, character_id, last_read_at)
            VALUES (:uid, :cid, NOW())
            ON CONFLICT (user_id, character_id)
            DO UPDATE SET last_read_at = EXCLUDED.last_read_at
        """),
        {"uid": uid, "cid": character_id},
    )
    await db.commit()
    return {"ok": True}


@router.get("/api/chat/audio/{message_id}")
async def get_chat_audio(
    message_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Serve a user's persisted voice message audio through same-origin auth."""
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        sql_text(
            """
            SELECT audio_url
            FROM chat_messages
            WHERE id = :mid AND user_id = :uid AND modality = 'voice'
            LIMIT 1
            """
        ),
        {"mid": uuid.UUID(message_id), "uid": uid},
    )
    row = result.mappings().first()
    if not row or not row["audio_url"]:
        raise HTTPException(status_code=404, detail="Audio not found")

    key = _extract_storage_key(row["audio_url"])
    if not key:
        raise HTTPException(status_code=404, detail="Invalid audio URL")

    try:
        from heart.infra.storage import get_s3_object

        data, content_type = await get_s3_object(key)
    except Exception as exc:
        logger.warning("chat_audio_fetch_failed", message_id=message_id, error=str(exc))
        raise HTTPException(status_code=404, detail="Audio unavailable") from exc

    return Response(content=data, media_type=content_type)


async def _check_age_verified(user_id: str) -> bool:
    """Check if user has passed age verification. Returns True if verified."""
    from sqlalchemy.ext.asyncio import AsyncSession

    from .wiring import _get_engine

    async with AsyncSession(_get_engine(), expire_on_commit=False) as db:
        result = await db.execute(
            sql_text("SELECT age_verified_at FROM users WHERE id = :uid"),
            {"uid": uuid.UUID(user_id)},
        )
        return result.scalar_one_or_none() is not None


async def _verify_ws_token(ws: WebSocket, token: Optional[str]) -> Optional[str]:
    """Verify WS token and age. Returns user_id or None (ws already closed)."""
    if not token:
        await ws.close(code=1008, reason="Missing token")
        return None
    try:
        token_data = auth_manager.verify_token(token)
    except Exception:
        await ws.close(code=1008, reason="Invalid token")
        return None

    if not await _check_age_verified(token_data.user_id):
        await ws.accept()
        await ws.send_json({"type": "error", "code": "age_verification_required"})
        await ws.close(code=1008, reason="age_verification_required")
        return None

    return token_data.user_id


@router.websocket("/api/chat/ws")
async def chat_ws(ws: WebSocket, token: Optional[str] = Query(None)):
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
    user_id = await _verify_ws_token(ws, token)
    if not user_id:
        return

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
            await _handle_message(ws, msg, active_turns, cache, user_id)

    except WebSocketDisconnect:
        logger.info("chat_ws_disconnect")
        for session in active_turns.values():
            session.cancel()
    except Exception as e:
        logger.error("chat_ws_error", error=str(e))
        for session in active_turns.values():
            session.cancel()
        try:
            await ws.send_json({"type": "error", "msg": str(e)})
        except Exception:
            pass
