"""Voice API routes — per runtime_specs/08_voice.md"""

from __future__ import annotations

import uuid
from io import BytesIO

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db
from heart.billing import InsufficientCreditsError, deduct_credits, get_balance
from heart.core.auth import TokenData, get_current_user
from heart.core.config import settings
from heart.membership import CloneForbiddenError, assert_clone_allowed, get_effective_tier

from .deps import require_age_verified
from .wiring import get_mimo_asr_provider, get_voice_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Hardcoded fallback clone cost — superseded by config-driven action_cost_fen()
# when billing/pricing.py is available.  Kept for safety during startup.
_CLONE_COST_FEN_FALLBACK = 80_000
_VALID_CLONE_PROVIDERS = frozenset({"mimo", "fish", "minimax"})


def _clone_cost_fen(provider: str) -> int:
    """Return clone cost in fen for the given TTS provider (config-driven)."""
    try:
        from heart.billing.pricing import action_cost_fen

        cost = action_cost_fen(f"clone_{provider}")
        return cost if cost > 0 else _CLONE_COST_FEN_FALLBACK
    except Exception:
        return _CLONE_COST_FEN_FALLBACK


def _check_clone_provider_available(provider: str) -> None:
    """Raise HTTPException 503 if the requested clone provider is not configured."""
    if provider == "fish":
        if not settings.fish_api_key:
            raise HTTPException(
                status_code=503,
                detail="Fish 音色克隆服务未配置，请联系管理员或改用预设音色。",
            )
    elif provider == "mimo":
        # MiMo clone is zero-shot: no external clone API and no voiceId — the
        # uploaded reference audio IS the timbre and rides along on every synth
        # call. So it only needs the MiMo *synthesis* key, not MiniMax.
        if not settings.mimo_api_key:
            raise HTTPException(
                status_code=503,
                detail="音色克隆服务未配置，请联系管理员或改用预设音色。",
            )
    else:
        # Legacy minimax clone path.
        if not settings.minimax_api_key:
            raise HTTPException(
                status_code=503,
                detail="音色克隆服务未配置，请联系管理员或改用预设音色。",
            )


# Preset voice sample cache: preset_id -> (media_type, audio_bytes).  Filled on
# first request so we hit the TTS provider at most once per preset per process.
# Preset voices are static rows, so cache TTL is process lifetime. media_type
# varies by provider (MiMo → audio/wav, MiniMax → audio/mpeg).
_PRESET_SAMPLE_CACHE: dict[str, tuple[str, bytes]] = {}


def _pcm16_to_wav(pcm: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    """Wrap raw PCM16LE samples in a minimal WAV container.

    MiMo returns headerless PCM16 @ 24 kHz mono; browsers can't play that from
    an <audio> element, so the preview endpoint wraps it into WAV (which every
    browser decodes) rather than shipping a separate decoder to the client.
    """
    import struct

    data_size = len(pcm)
    byte_rate = sample_rate * channels * 2
    block_align = channels * 2
    header = b"RIFF" + struct.pack("<I", 36 + data_size) + b"WAVE"
    header += b"fmt " + struct.pack(
        "<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, 16
    )
    header += b"data" + struct.pack("<I", data_size)
    return header + pcm


# Audio upload constraints
_MAX_AUDIO_BYTES = 20 * 1024 * 1024  # 20 MB
_ALLOWED_AUDIO_MIME = {
    "audio/mpeg",
    "audio/mp4",
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/ogg",
    "audio/webm",
    "audio/aac",
    "audio/flac",
}


# ── Legacy synthesize ─────────────────────────────────────────────────────────


class SynthesizeRequest(BaseModel):
    text: str
    character_id: str = "rin"
    emotion: str = "neutral"


@router.post("/synthesize")
@limiter.limit("20/minute")
async def synthesize(
    request: Request,
    req: SynthesizeRequest,
    current_user: TokenData = Depends(require_age_verified),
):
    """Synthesize speech from text."""
    voice_service = get_voice_service()
    if not voice_service:
        raise HTTPException(
            status_code=503,
            detail="Voice service not configured. Set MINIMAX_API_KEY in .env",
        )

    try:
        result = await voice_service.synthesize_for_character(
            text=req.text,
            character_id=req.character_id,
            emotion=req.emotion,
        )
        return StreamingResponse(
            BytesIO(result.audio),
            media_type=f"audio/{result.format}",
        )
    except Exception as e:
        logger.error("voice_synthesize_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


# ── Voice management ──────────────────────────────────────────────────────────


@router.get("/presets")
async def list_preset_voices(
    gender: str | None = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List available preset voice options.

    ``gender`` — optional filter. When provided, only preset voices whose
    ``gender`` column matches are returned. Value must be 'male' or 'female'.
    """
    if gender not in (None, "male", "female"):
        raise HTTPException(status_code=400, detail="gender must be 'male' or 'female'")
    # MiMo-only: MiniMax presets are hidden (MiniMax is being retired). The
    # character-creation picker now shows MiMo voices grouped by gender, each
    # previewable on demand via /presets/{id}/sample (MiMo synth → WAV).
    if gender is None:
        result = await db.execute(
            text("""
                SELECT id, name, voice_id, provider, description, sample_url, gender
                FROM preset_voices
                WHERE is_active = TRUE AND provider = 'mimo'
                ORDER BY gender, id
            """)
        )
    else:
        result = await db.execute(
            text("""
                SELECT id, name, voice_id, provider, description, sample_url, gender
                FROM preset_voices
                WHERE is_active = TRUE AND provider = 'mimo' AND gender = :gender
                ORDER BY id
            """),
            {"gender": gender},
        )
    rows = [dict(r) for r in result.mappings()]
    return {"presets": rows}


@router.get("/presets/{preset_id}/sample")
@limiter.limit("60/hour")
async def get_preset_voice_sample(
    request: Request,
    preset_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synthesize a short sample clip for a preset voice.

    Returns playable audio bytes so the character-creation UI can preview a
    voice when the user taps ▶.  The clip is synthesized by the preset's own
    provider — MiMo (returns PCM16, wrapped to WAV here) for the mimo catalog,
    or MiniMax (MP3) for legacy rows.  Cached per preset_id for the process
    lifetime so we hit the provider at most once per voice.
    """
    from fastapi.responses import Response

    cached = _PRESET_SAMPLE_CACHE.get(preset_id)
    if cached is not None:
        media_type, audio = cached
        return Response(content=audio, media_type=media_type)

    row = (
        (
            await db.execute(
                text("""
                SELECT id, name, voice_id, provider
                FROM preset_voices
                WHERE id = :pid AND is_active = TRUE
            """),
                {"pid": preset_id},
            )
        )
        .mappings()
        .fetchone()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="预设音色不存在")

    sample_text = f"你好，我是{row['name']}，很高兴认识你，希望我们能聊得愉快。"
    provider_name = row["provider"]

    from heart.ss08_voice.errors import TTSProviderError
    from heart.ss08_voice.types import TTSRequest

    try:
        if provider_name == "mimo":
            from heart.api.wiring import get_tts_provider_registry

            mimo = get_tts_provider_registry().get("mimo")
            if mimo is None:
                raise HTTPException(status_code=503, detail="MiMo 语音服务未配置")
            # MiMo selects its voice description by character_id/voice_id; the
            # preset's voice_id (e.g. "mimo_female_gentle") is a known key.
            result = await mimo.synthesize(
                TTSRequest(text=sample_text, voice_id=row["voice_id"]),
                character_id=row["voice_id"],
            )
            audio = _pcm16_to_wav(result.audio)
            media_type = "audio/wav"
        else:
            # Legacy MiniMax presets (hidden from the picker, but the endpoint
            # still serves a preview if one is requested directly).
            if not settings.minimax_api_key:
                raise HTTPException(status_code=503, detail="TTS provider not configured")
            from heart.ss08_voice.minimax_provider import MiniMaxProvider

            provider = MiniMaxProvider(
                api_key=settings.minimax_api_key,
                group_id=settings.minimax_group_id or "",
                base_url=settings.minimax_base_url,
            )
            result = await provider.synthesize(
                TTSRequest(text=sample_text, voice_id=row["voice_id"])
            )
            audio = result.audio
            media_type = "audio/mpeg"
    except TTSProviderError as exc:
        # Surface the provider's real error so the UI shows something actionable
        # ("voice_id X not found") instead of a generic retry prompt. Truncate
        # to 320 chars — enough to spot the failure mode without leaking a huge
        # payload.
        provider_msg = str(exc)
        if len(provider_msg) > 320:
            provider_msg = provider_msg[:317] + "..."
        logger.warning(
            "preset_sample_synthesize_failed",
            preset_id=preset_id,
            voice_id=row["voice_id"],
            provider=provider_name,
            status_code=getattr(exc, "status_code", None),
            error=provider_msg,
        )
        raise HTTPException(
            status_code=502,
            detail=f"试听合成失败：{provider_msg}",
        ) from exc

    _PRESET_SAMPLE_CACHE[preset_id] = (media_type, audio)
    logger.info(
        "preset_sample_synthesized",
        preset_id=preset_id,
        provider=provider_name,
        media_type=media_type,
        bytes=len(audio),
    )
    return Response(content=audio, media_type=media_type)


@router.get("/{character_id}")
async def get_character_voice(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the voice configuration for a character.

    Fallback order:
      1. `character_voices` DB row (preset or clone)
      2. In-memory `VOICE_CATALOG` (rin/dorothy built-ins)
    """
    from heart.ss08_voice.voice_catalog import VOICE_CATALOG
    from heart.ss08_voice.voice_resolver import (
        get_selected_voice_provider,
        get_voice_config,
        list_ready_voice_providers,
    )

    uid = uuid.UUID(current_user.user_id)
    # Providers with a ready voice (drives the backstage 日常/真人 toggle) + the
    # user's current selection (which button is highlighted "使用中").
    available_providers = await list_ready_voice_providers(character_id, db)
    selected_provider = await get_selected_voice_provider(character_id, uid, db)

    config = await get_voice_config(character_id, db)
    if config is not None:
        return {
            "configured": True,
            "voice_type": config["voice_type"],
            "clone_status": config["clone_status"],
            "preset_voice_id": config["preset_voice_id"],
            "preset_name": config.get("preset_name"),
            # TTS provider that owns the *primary* row (mimo/fish/minimax).
            "voice_provider": config.get("voice_provider"),
            # All providers the user can switch between + their current choice.
            "available_providers": available_providers,
            "selected_provider": selected_provider,
            "has_voice": config["clone_status"] == "ready",
            # Surface the DB error_msg only for failed clones. The frontend
            # shows this in a toast so the user can act on it (missing
            # GroupId / unreachable audio URL / MiniMax quota etc.) instead
            # of just seeing "克隆失败，点击重试".
            "error_msg": (
                config.get("error_msg") if config.get("clone_status") == "failed" else None
            ),
        }
    if character_id in VOICE_CATALOG:
        return {
            "configured": True,
            "voice_type": "preset",
            "clone_status": "ready",
            "preset_voice_id": None,
            "preset_name": None,
            "voice_provider": None,
            "available_providers": available_providers,
            "selected_provider": selected_provider,
            "has_voice": True,
        }
    return {"configured": False}


class PresetVoiceBody(BaseModel):
    preset_voice_id: str
    character_id: str


@router.post("/preset")
async def set_preset_voice(
    body: PresetVoiceBody,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Set a preset voice for a character owned by the current user."""
    uid = uuid.UUID(current_user.user_id)

    # Validate preset exists + capture its provider (drives which voice_provider
    # row this preset occupies — see the compound unique key since migration 039).
    result = await db.execute(
        text("SELECT id, provider FROM preset_voices WHERE id = :pid AND is_active = TRUE"),
        {"pid": body.preset_voice_id},
    )
    preset_row = result.mappings().fetchone()
    if preset_row is None:
        raise HTTPException(status_code=404, detail="预设音色不存在")
    preset_provider = preset_row["provider"] or "mimo"

    # Ownership check — built-in characters (owner_user_id IS NULL) may be
    # configured by any user who owns a character-level settings row, but for
    # voice we only allow configuring characters you own.
    char_result = await db.execute(
        text("SELECT owner_user_id FROM characters WHERE id = :cid"),
        {"cid": body.character_id},
    )
    char_row = char_result.fetchone()
    if char_row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if char_row[0] is not None and str(char_row[0]) != str(uid):
        raise HTTPException(status_code=403, detail="无权配置此角色的音色")

    await db.execute(
        text("""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, preset_voice_id, clone_status, voice_provider)
            VALUES (:cid, :uid, 'preset', :pid, 'ready', :prov)
            ON CONFLICT (character_id, voice_provider) DO UPDATE
                SET voice_type      = 'preset',
                    preset_voice_id = :pid,
                    clone_status    = 'ready',
                    updated_at      = NOW()
        """),
        {
            "cid": body.character_id,
            "uid": uid,
            "pid": body.preset_voice_id,
            "prov": preset_provider,
        },
    )
    await db.execute(
        text("UPDATE characters SET has_voice = TRUE WHERE id = :cid"),
        {"cid": body.character_id},
    )
    await db.commit()

    logger.info(
        "voice_preset_set",
        character_id=body.character_id,
        preset_voice_id=body.preset_voice_id,
        user_id=str(uid),
    )
    return {"ok": True, "voice_type": "preset", "clone_status": "ready"}


@router.post("/clone")
@limiter.limit("5/hour")
async def clone_voice(
    request: Request,
    character_id: str,
    provider: str = "mimo",
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_age_verified),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload an audio sample to clone a voice for a UGC character.

    Query param `provider` selects the clone backend (default: mimo).
    Supported values: mimo, fish, minimax.
    Clone cost is config-driven via AFDIAN_SKU_MAP pricing.
    """
    uid = uuid.UUID(current_user.user_id)

    # Provider validation
    if provider not in _VALID_CLONE_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"不支持的克隆 provider: {provider}")

    # Ownership check — only UGC characters (owner_user_id = uid) allowed
    char_result = await db.execute(
        text("SELECT owner_user_id FROM characters WHERE id = :cid"),
        {"cid": character_id},
    )
    char_row = char_result.fetchone()
    if char_row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if char_row[0] is None or str(char_row[0]) != str(uid):
        raise HTTPException(status_code=403, detail="只能为自己创建的角色克隆音色")

    # Tier gate — Fish/MiMo clone requires paid membership
    tier = await get_effective_tier(db, uid)
    try:
        assert_clone_allowed(tier, provider)
    except CloneForbiddenError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": "tier_forbidden", "provider": e.provider, "tier": e.tier},
        ) from e

    # MIME check
    mime = file.content_type or ""
    if mime not in _ALLOWED_AUDIO_MIME:
        raise HTTPException(status_code=400, detail="仅支持 mp3/wav/ogg/webm/aac/flac 格式")

    data = await file.read()
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=400, detail="音频文件不能超过 20MB")
    if len(data) < 1024:
        raise HTTPException(status_code=400, detail="音频文件过小，请上传有效录音")

    # Pre-check balance without deducting.  Actual deduction happens in the
    # background clone job on success, so a failed clone leaves no charge.
    # A user's balance may still drop between here and the async deduct
    # (they spend credits chatting during the ~30-120 s clone window); in
    # that unlikely race we let the clone finish and log the deficit rather
    # than fail after work is already done.
    clone_cost = _clone_cost_fen(provider)
    balance = await get_balance(db, uid)
    if balance < clone_cost:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，克隆需要 {clone_cost // 100} 积分，当前余额 {balance / 100:.1f}",
        )

    # Provider availability check
    _check_clone_provider_available(provider)

    audio_source = await _stage_audio_for_clone(
        data=data,
        filename=file.filename or "sample.wav",
        mime=mime,
        character_id=character_id,
        provider=provider,
    )

    # Upsert the character_voices row for THIS provider (compound key since 039,
    # so a mimo clone and a fish clone coexist for the same character).
    await db.execute(
        text("""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, clone_audio_url, clone_status, voice_provider)
            VALUES (:cid, :uid, 'clone', :url, 'processing', :prov)
            ON CONFLICT (character_id, voice_provider) DO UPDATE
                SET voice_type      = 'clone',
                    clone_audio_url = :url,
                    clone_voice_id  = NULL,
                    clone_status    = 'processing',
                    error_msg       = NULL,
                    updated_at      = NOW()
        """),
        {"cid": character_id, "uid": uid, "url": audio_source, "prov": provider},
    )
    await db.commit()

    logger.info(
        "voice_clone_started",
        character_id=character_id,
        user_id=str(uid),
        audio_source=audio_source,
    )

    # Fire-and-forget background clone task
    import asyncio

    _provider_captured = provider
    _bytes_captured = data
    _mime_captured = mime
    asyncio.get_event_loop().call_soon_threadsafe(
        lambda: asyncio.ensure_future(
            _run_clone_job(
                character_id,
                audio_source,
                str(uid),
                _provider_captured,
                audio_bytes=_bytes_captured,
                mime=_mime_captured,
            )
        )
    )

    return {
        "ok": True,
        "clone_status": "processing",
        # Balance is unchanged at this point — clone credits are charged when
        # the job succeeds (see _run_clone_job).  Return the current balance
        # so the UI can render it correctly.
        "balance": balance / 100,
    }


async def _stage_audio_for_clone(
    *,
    data: bytes,
    filename: str,
    mime: str,
    character_id: str,
    provider: str,
) -> str:
    """Persist the uploaded sample and return a scheme-tagged handle for the
    background clone job. The handle is stored in ``character_voices.clone_audio_url``.

    Per provider:
      - **fish**: the clone job uploads the raw bytes to Fish directly (multipart),
        so no fetchable URL is needed. We DON'T re-download it (that anonymous GET
        was the source of the "音频下载失败 HTTP 403"). Returns ``upload://<filename>``
        purely as a record marker.
      - **mimo**: zero-shot — the reference audio must stay readable by *our* backend
        on every synth turn. Store it in S3/MinIO and return ``s3://<key>``; the MiMo
        provider fetches it with credentials (``storage.get_s3_object``), so it works
        even on a private bucket. Requires object storage to be configured.
      - **minimax** (legacy): MiniMax's servers fetch the audio, so hand back a
        publicly reachable URL, else forward to MiniMax ``/files/upload`` and return
        ``minimax_file://<id>`` (dev fallback when the endpoint is localhost/private).
    """
    if provider == "fish":
        return f"upload://{filename}"

    ext = mime.split("/")[-1].replace("x-wav", "wav").replace("mpeg", "mp3")
    key = f"voice-samples/{character_id}/{uuid.uuid4().hex}.{ext}"

    if provider == "mimo":
        from heart.infra.storage import _upload_to_s3, is_s3_configured

        if not is_s3_configured():
            raise HTTPException(
                status_code=503,
                detail="音色克隆需要对象存储支持，请联系管理员。",
            )
        try:
            await _upload_to_s3(key, data, mime)
        except Exception as exc:
            logger.warning("voice_clone_s3_failed", error=str(exc))
            raise HTTPException(status_code=502, detail="音频上传失败，请稍后重试") from exc
        # s3:// handle → backend reads with credentials, no public bucket needed.
        return f"s3://{key}"

    # Legacy minimax path.
    from heart.infra.storage import is_s3_endpoint_public
    from heart.infra.storage import upload_file as s3_upload

    if is_s3_endpoint_public():
        try:
            return await s3_upload(data, key, mime)
        except Exception as exc:
            logger.warning("voice_clone_s3_failed", error=str(exc))
            raise HTTPException(status_code=502, detail="音频上传失败，请稍后重试") from exc

    try:
        file_id = await _upload_audio_to_minimax(data, filename, mime)
    except Exception as exc:
        logger.warning("voice_clone_minimax_upload_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="音频上传失败，请稍后重试") from exc
    return f"minimax_file://{file_id}"


async def _mark_clone_ready(
    db: AsyncSession,
    *,
    character_id: str,
    user_id: str,
    provider: str,
    audio_source: str,
    clone_voice_id: str | None,
) -> None:
    """Charge clone credits (once, best-effort) and flip the row + character to ready."""
    try:
        await deduct_credits(
            db,
            uuid.UUID(user_id),
            _clone_cost_fen(provider),
            # Idempotency key ties to the specific audio source (unique per
            # upload) so retries within the same source don't double-charge.
            f"voice_clone_success:{audio_source}",
            type_str="consume_voice_clone",
        )
    except InsufficientCreditsError:
        # Rare race: balance dropped after the pre-check.  The clone work is
        # already done, so log and let it succeed (one free clone) rather than
        # discard completed work.
        logger.warning(
            "voice_clone_deduct_after_success_failed",
            character_id=character_id,
            user_id=user_id,
        )
    await db.execute(
        text("""
            UPDATE character_voices
            SET clone_voice_id = :vid, clone_status = 'ready',
                error_msg = NULL, updated_at = NOW()
            WHERE character_id = :cid AND voice_provider = :prov
        """),
        {"vid": clone_voice_id, "cid": character_id, "prov": provider},
    )
    await db.execute(
        text("UPDATE characters SET has_voice = TRUE WHERE id = :cid"),
        {"cid": character_id},
    )


async def _run_clone_job(
    character_id: str,
    audio_source: str,
    user_id: str,
    provider: str = "minimax",
    audio_bytes: bytes | None = None,
    mime: str = "audio/wav",
) -> None:
    """Background task: turn an uploaded sample into a ready voice, update DB.

    ``audio_source`` is the tagged handle stored in ``character_voices.clone_audio_url``.
    ``audio_bytes`` carries the raw sample so Fish can be cloned by direct upload
    (no re-download → no HTTP 403). See ``_call_tts_clone_api`` for schemes.
    """
    import asyncio

    await asyncio.sleep(2)  # give the HTTP response time to flush

    from heart.api.wiring import get_db_session_factory

    session_factory = get_db_session_factory()
    if session_factory is None:
        logger.warning("voice_clone_job_no_db", character_id=character_id)
        return

    async with session_factory() as db:
        try:
            if provider == "mimo":
                # Zero-shot: there is no external clone step and no voiceId. The
                # staged reference (clone_audio_url, already persisted by
                # clone_voice) IS the timbre — mark ready and charge.
                await _mark_clone_ready(
                    db,
                    character_id=character_id,
                    user_id=user_id,
                    provider=provider,
                    audio_source=audio_source,
                    clone_voice_id=None,
                )
                await db.commit()
                logger.info("voice_clone_ready", character_id=character_id, provider="mimo")
                return

            clone_voice_id, err_msg = await _call_tts_clone_api(
                audio_source, character_id, provider, audio_bytes=audio_bytes, mime=mime
            )
            if clone_voice_id:
                # Charge credits only after the provider returns a voice_id — a
                # failed clone should not cost the user anything.
                await _mark_clone_ready(
                    db,
                    character_id=character_id,
                    user_id=user_id,
                    provider=provider,
                    audio_source=audio_source,
                    clone_voice_id=clone_voice_id,
                )
                logger.info("voice_clone_ready", character_id=character_id, voice_id=clone_voice_id)
            else:
                reason = (err_msg or "音色克隆失败，请稍后重试")[:200]
                await db.execute(
                    text("""
                        UPDATE character_voices
                        SET clone_status = 'failed', error_msg = :err, updated_at = NOW()
                        WHERE character_id = :cid AND voice_provider = :prov
                    """),
                    {"cid": character_id, "err": reason, "prov": provider},
                )
                logger.warning(
                    "voice_clone_failed",
                    character_id=character_id,
                    reason=reason,
                )
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("voice_clone_job_error", character_id=character_id, error=str(exc))
            try:
                await db.execute(
                    text("""
                        UPDATE character_voices
                        SET clone_status = 'failed', error_msg = :err, updated_at = NOW()
                        WHERE character_id = :cid AND voice_provider = :prov
                    """),
                    {"cid": character_id, "err": str(exc)[:200], "prov": provider},
                )
                await db.commit()
            except Exception:
                pass


def _minimax_requires_group_id() -> bool:
    """Whether the configured MiniMax base URL requires ``?GroupId=`` on
    ``/voice_clone`` and ``/files/upload``.

    The mainland-China domains (``api.minimaxi.com``, ``api.minimaxi.chat``)
    have historically required GroupId as a query parameter on these two
    endpoints even when the Authorization header carries a scoped API key.
    The international domain (``api.minimax.io``) accepts Bearer-only auth.
    Presence-of-``minimaxi`` in the host is the sharpest signal we have.
    """
    base = (settings.minimax_base_url or "").lower()
    return "minimaxi." in base


def _minimax_endpoint(path: str) -> str:
    """Build a MiniMax endpoint URL, appending ``?GroupId=`` when set.

    Guarantees the query separator is always ``?`` (path is expected to be
    plain like ``/voice_clone``). Missing group_id → no query param, so
    callers on the international endpoint remain unaffected. When the
    Chinese endpoint is configured but group_id is empty we still build a
    URL without the param — MiniMax will reject and the raw error body is
    surfaced to the user via ``error_msg``, which is more useful than a
    silent local guard.
    """
    base = (settings.minimax_base_url or "").rstrip("/")
    url = f"{base}{path}"
    gid = (settings.minimax_group_id or "").strip()
    if gid:
        url = f"{url}?GroupId={gid}"
    return url


async def _call_tts_clone_api(
    audio_source: str,
    character_id: str,
    provider: str = "minimax",
    audio_bytes: bytes | None = None,
    mime: str = "audio/wav",
) -> tuple[str | None, str | None]:
    """Call the correct TTS provider's voice clone endpoint.

    Returns ``(voice_id, error_msg)``:
      - success: ``(voice_id, None)``
      - failure: ``(None, reason)``

    ``audio_source`` carries a scheme prefix identifying how the audio is staged:
      - ``minimax_file://<file_id>`` — a MiniMax-hosted file_id (dev fallback)
      - anything else — treated as a publicly-fetchable URL (S3/MinIO)

    ``audio_bytes`` is the raw sample; Fish is cloned by uploading it directly
    (multipart), so no fetchable URL is required. (MiMo has no external clone —
    handled in ``_run_clone_job`` before reaching here.)
    """
    if audio_source.startswith("local://"):
        logger.warning("voice_clone_local_url_rejected", audio_source=audio_source)
        return None, "internal: local:// audio source rejected"

    if provider == "fish":
        return await _fish_clone_from_bytes(audio_bytes, mime, character_id)

    # Legacy MiniMax clone backend.
    if not settings.minimax_api_key:
        logger.warning("voice_clone_provider_unavailable", provider=provider)
        return None, "MINIMAX_API_KEY 未配置"

    if _minimax_requires_group_id() and not (settings.minimax_group_id or "").strip():
        logger.warning("voice_clone_group_id_missing", base_url=settings.minimax_base_url)
        return None, "MINIMAX_GROUP_ID 未配置（大陆版 api.minimaxi 域名必填）"

    try:
        if audio_source.startswith("minimax_file://"):
            file_id_str = audio_source[len("minimax_file://") :]
            return await _minimax_clone_by_file_id(int(file_id_str), character_id)
        return await _minimax_clone_by_url(audio_source, character_id)
    except Exception as exc:
        logger.warning("minimax_clone_failed", error=str(exc))
        return None, f"MiniMax 请求异常：{str(exc)[:160]}"


def _fish_filename_for(mime: str, character_id: str) -> str:
    """Best-effort filename+extension Fish uses to sniff the audio container."""
    ext = {
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/ogg": "ogg",
        "audio/webm": "webm",
        "audio/aac": "aac",
        "audio/flac": "flac",
    }.get(mime.split(";")[0].strip(), "wav")
    return f"clone_{character_id[:8]}.{ext}"


async def _fish_clone_from_bytes(
    audio_bytes: bytes | None, mime: str, character_id: str
) -> tuple[str | None, str | None]:
    """Clone a Fish voice by uploading the raw sample bytes directly.

    Uses ``FishProvider.clone_from_bytes`` — POST ``{base}/voices`` (multipart
    field ``audioFiles``), the documented fishaudio.org open-API contract, which
    returns ``voiceId``. Passing bytes means we never re-download a staged object
    URL, so the old "音频下载失败: HTTP 403" (anonymous GET against a non-public
    bucket) can no longer happen. Returns ``(voice_id, None)`` or ``(None, err)``.
    """
    if not settings.fish_api_key:
        return None, "FISH_API_KEY 未配置"
    if not audio_bytes:
        return None, "internal: fish clone missing audio bytes"

    from heart.ss08_voice.errors import TTSProviderError
    from heart.ss08_voice.fish_provider import FishProvider

    provider = FishProvider(
        api_key=settings.fish_api_key,
        base_url=settings.fish_base_url,
        model=settings.fish_model,
    )
    try:
        voice_id = await provider.clone_from_bytes(
            audio_bytes,
            title=f"yuoyuo_{character_id[:8]}",
            filename=_fish_filename_for(mime, character_id),
            mime=mime.split(";")[0].strip() or "audio/wav",
        )
    except TTSProviderError as exc:
        logger.warning("fish_clone_failed", character_id=character_id, error=str(exc))
        return None, f"Fish Audio 克隆失败：{str(exc)[:180]}"
    except Exception as exc:
        logger.warning("fish_clone_failed", character_id=character_id, error=str(exc))
        return None, f"Fish Audio 请求异常：{str(exc)[:160]}"

    logger.info("fish_clone_ready", character_id=character_id, model_id=voice_id)
    return voice_id, None


async def _minimax_clone_by_url(audio_url: str, character_id: str) -> tuple[str | None, str | None]:
    """Submit voice clone job to MiniMax with a public ``file_url``."""
    return await _minimax_voice_clone_request(
        {
            "file_url": audio_url,
            "voice_id": _clone_voice_id_for(character_id),
            "need_noise_reduction": True,
            "need_volume_normalization": True,
            "aigc_watermark": False,
        }
    )


async def _minimax_clone_by_file_id(
    file_id: int, character_id: str
) -> tuple[str | None, str | None]:
    """Submit voice clone job to MiniMax with a MiniMax-hosted ``file_id``."""
    return await _minimax_voice_clone_request(
        {
            "file_id": file_id,
            "voice_id": _clone_voice_id_for(character_id),
            "need_noise_reduction": True,
            "need_volume_normalization": True,
            "aigc_watermark": False,
        }
    )


def _clone_voice_id_for(character_id: str) -> str:
    """Build the custom voice_id MiniMax should assign to this clone.

    MiniMax requires a unique voice_id per clone job (the value we later use
    when synthesizing). We include the character_id so the string is human-
    inspectable in the DB / logs, and a short random suffix so re-clones
    don't collide with the previous voice_id.
    """
    suffix = uuid.uuid4().hex[:8]
    # MiniMax voice_id must start with a letter; character_id may be a uuid.
    safe = "".join(c for c in character_id if c.isalnum())[:24] or "clone"
    return f"UGC_{safe}_{suffix}"


def _extract_minimax_base_resp_error(body: dict) -> str | None:
    """Return a human-readable reason if ``body`` carries a non-zero
    ``base_resp.status_code``.

    MiniMax returns HTTP 200 for logical failures too — the real signal lives
    in ``base_resp.status_code`` / ``status_msg``. Ignoring this made
    unreachable ``file_url`` responses look successful (returning the
    ``voice_id`` we ourselves supplied), which then blew up during chat.
    """
    base_resp = body.get("base_resp") if isinstance(body, dict) else None
    if not isinstance(base_resp, dict):
        return None
    status_code = base_resp.get("status_code")
    if status_code in (0, "0", None):
        return None
    status_msg = base_resp.get("status_msg") or "unknown error"
    return f"MiniMax {status_code}: {status_msg}"


async def _minimax_voice_clone_request(payload: dict) -> tuple[str | None, str | None]:
    """Post the given payload to MiniMax's ``/voice_clone`` endpoint.

    Uses ``httpx`` (which loads certifi's CA bundle by default) instead of
    ``aiohttp`` (whose default ``ssl.create_default_context()`` returns an
    empty trust store on Python.org macOS installs). WoTrus DV — the CA that
    signs ``*.minimaxi.com`` — is trusted by certifi's chain but not by an
    empty store, which is why real-device clone silently failed with
    "音频上传失败" while the preset ``/t2a_v2`` path (already on httpx) worked.
    """
    import httpx

    headers = {
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "Content-Type": "application/json",
    }
    url = _minimax_endpoint("/voice_clone")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("minimax_clone_transport_error", error=str(exc))
        return None, f"MiniMax 请求异常：{str(exc)[:160]}"
    if resp.status_code != 200:
        logger.warning("minimax_clone_error", status=resp.status_code, body=resp.text[:200])
        return None, f"MiniMax HTTP {resp.status_code}：{resp.text[:160]}"
    try:
        body = resp.json()
    except ValueError:
        logger.warning("minimax_clone_bad_json", body=resp.text[:200])
        return None, "MiniMax 返回内容不是 JSON"
    base_err = _extract_minimax_base_resp_error(body)
    if base_err is not None:
        logger.warning("minimax_clone_base_resp_error", reason=base_err, body=str(body)[:200])
        return None, base_err
    # Success: MiniMax echoes back the voice_id we sent. Fall back to
    # ``id`` for defensive compatibility with older API versions.
    voice_id = payload.get("voice_id") or body.get("voice_id") or body.get("id")
    if not voice_id:
        logger.warning("minimax_clone_missing_voice_id", body=str(body)[:200])
        return None, "MiniMax 未返回 voice_id"
    return voice_id, None


async def _upload_audio_to_minimax(data: bytes, filename: str, mime: str) -> int:
    """Upload raw audio bytes to MiniMax ``/files/upload`` and return the file_id.

    Used when S3 is not configured or the endpoint is not publicly reachable —
    MiniMax hosts the audio internally so we still get a voice_clone-able
    reference without needing a public URL.

    Uses ``httpx`` (certifi CA bundle) rather than ``aiohttp`` — see the note
    on ``_minimax_voice_clone_request`` for the WoTrus / empty-truststore
    reason. Handing MiniMax the raw bytes here avoids the S3-URL reachability
    issue entirely.
    """
    import httpx

    if not settings.minimax_api_key:
        raise RuntimeError("MINIMAX_API_KEY not configured")

    headers = {"Authorization": f"Bearer {settings.minimax_api_key}"}
    url = _minimax_endpoint("/files/upload")

    files = {"file": (filename, data, mime or "application/octet-stream")}
    form = {"purpose": "voice_clone"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, headers=headers, files=files, data=form)
    if resp.status_code != 200:
        raise RuntimeError(
            f"MiniMax files/upload failed status={resp.status_code} body={resp.text[:200]}"
        )
    try:
        body = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"MiniMax files/upload non-JSON response: {resp.text[:200]}") from exc
    base_err = _extract_minimax_base_resp_error(body)
    if base_err is not None:
        raise RuntimeError(f"MiniMax files/upload rejected: {base_err}")
    file_obj = body.get("file") or {}
    file_id = file_obj.get("file_id") or body.get("file_id")
    if file_id is None:
        raise RuntimeError(f"MiniMax files/upload missing file_id in response: {body}")
    return int(file_id)


@router.delete("/{character_id}")
async def remove_character_voice(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Remove a character's voice configuration (owner only)."""
    uid = uuid.UUID(current_user.user_id)

    char_result = await db.execute(
        text("SELECT owner_user_id FROM characters WHERE id = :cid"),
        {"cid": character_id},
    )
    char_row = char_result.fetchone()
    if char_row is None:
        raise HTTPException(status_code=404, detail="角色不存在")
    if char_row[0] is not None and str(char_row[0]) != str(uid):
        raise HTTPException(status_code=403, detail="无权删除此角色的音色配置")

    await db.execute(
        text("DELETE FROM character_voices WHERE character_id = :cid"),
        {"cid": character_id},
    )
    await db.execute(
        text("UPDATE characters SET has_voice = FALSE WHERE id = :cid"),
        {"cid": character_id},
    )
    await db.commit()

    logger.info("voice_config_removed", character_id=character_id, user_id=str(uid))
    return {"ok": True}


# ── ASR: speech-to-text ───────────────────────────────────────────────────────

_MAX_ASR_BYTES = 8 * 1024 * 1024  # 8 MB raw (base64 overhead stays under MIMO 10 MB limit)
_ALLOWED_ASR_MIME = {"audio/wav", "audio/wave", "audio/x-wav"}


async def _upload_asr_audio(user_id: str, data: bytes, mime: str) -> str | None:
    """Upload ASR recording to S3 (best-effort). Returns URL or None."""
    try:
        from heart.infra.storage import is_s3_configured, upload_voice_message

        if is_s3_configured():
            return await upload_voice_message(user_id, data, mime)
    except Exception as exc:
        logger.warning("asr_s3_upload_failed", user_id=user_id, error=str(exc))
    return None


@router.post("/transcribe")
@limiter.limit("30/minute")
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    duration_ms: int = Form(...),
    current_user: TokenData = Depends(require_age_verified),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a WAV recording and return the ASR transcript.

    Charges ``asr_cost_credits`` fen only when the transcript is non-empty.
    Empty transcriptions (silence) are free.
    Audio is NOT persisted — caller handles session-only playback.
    """
    uid = uuid.UUID(current_user.user_id)

    provider = get_mimo_asr_provider()
    if provider is None:
        raise HTTPException(status_code=503, detail="语音识别服务未配置，请联系管理员。")

    mime = (file.content_type or "audio/wav").split(";")[0].strip()
    if mime not in _ALLOWED_ASR_MIME:
        raise HTTPException(status_code=400, detail="仅支持 WAV 格式音频")

    data = await file.read()
    if len(data) > _MAX_ASR_BYTES:
        raise HTTPException(status_code=400, detail="录音文件不能超过 8MB")
    if len(data) < 1024:
        raise HTTPException(status_code=400, detail="录音文件过小，请重新录制")

    cost = settings.asr_cost_credits
    balance = await get_balance(db, uid)
    if balance < cost:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，语音识别需要 {cost // 100} 积分，当前余额 {balance / 100:.1f}",
        )

    try:
        transcript = await provider.transcribe(data, mime=mime, asr_model=settings.mimo_asr_model)
    except Exception as exc:
        logger.exception("asr_transcribe_failed", user_id=str(uid), error=str(exc))
        raise HTTPException(status_code=502, detail="语音识别失败，请稍后重试") from exc

    if not transcript:
        return {"transcript": "", "duration_ms": duration_ms}

    idempotency_key = f"asr:{uuid.uuid4().hex}"
    try:
        new_balance = await deduct_credits(db, uid, cost, idempotency_key, type_str="consume_asr")
        await db.commit()
    except InsufficientCreditsError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，语音识别需要 {cost // 100} 积分，当前余额 {balance / 100:.1f}",
        ) from exc

    # Upload to S3 for cross-session persistence (best-effort — non-fatal if it fails).
    # Requires a lifecycle rule on voice_messages/ prefix to auto-delete after 20 days.
    audio_url = await _upload_asr_audio(str(uid), data, mime)

    logger.info(
        "asr_success", user_id=str(uid), duration_ms=duration_ms, transcript_len=len(transcript)
    )
    return {
        "transcript": transcript,
        "duration_ms": duration_ms,
        "balance": new_balance / 100,
        "audio_url": audio_url,
    }
