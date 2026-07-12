"""Voice API routes — per runtime_specs/08_voice.md"""

from __future__ import annotations

import uuid
from io import BytesIO

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db
from heart.billing import InsufficientCreditsError, deduct_credits, get_balance
from heart.core.auth import TokenData, get_current_user
from heart.core.config import settings

from .deps import require_age_verified
from .wiring import get_voice_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Voice clone credit cost (800 display credits = 80 000 fen)
_CLONE_COST_FEN = 80_000

# Preset voice sample cache: preset_id -> MP3 bytes.  Filled on first request
# so we hit MiniMax at most once per preset per process.  Preset voices are
# static rows, so cache TTL is process lifetime.
_PRESET_SAMPLE_CACHE: dict[str, bytes] = {}

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
    if gender is None:
        result = await db.execute(
            text("""
                SELECT id, name, voice_id, provider, description, sample_url, gender
                FROM preset_voices
                WHERE is_active = TRUE
                ORDER BY gender, id
            """)
        )
    else:
        result = await db.execute(
            text("""
                SELECT id, name, voice_id, provider, description, sample_url, gender
                FROM preset_voices
                WHERE is_active = TRUE AND gender = :gender
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

    Returns MP3 audio bytes so the character-creation UI can play a preview
    when the user taps the ▶ button.  Cached per preset_id for the lifetime
    of the process so we hit the TTS provider at most once per voice.
    """
    from fastapi.responses import Response

    if not settings.minimax_api_key:
        raise HTTPException(status_code=503, detail="TTS provider not configured")

    cached = _PRESET_SAMPLE_CACHE.get(preset_id)
    if cached is not None:
        return Response(content=cached, media_type="audio/mpeg")

    row = (
        (
            await db.execute(
                text("""
                SELECT id, name, voice_id
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

    from heart.ss08_voice.errors import TTSProviderError
    from heart.ss08_voice.minimax_provider import MiniMaxProvider
    from heart.ss08_voice.types import TTSRequest

    provider = MiniMaxProvider(
        api_key=settings.minimax_api_key,
        group_id=settings.minimax_group_id or "",
        base_url=settings.minimax_base_url,
    )
    try:
        result = await provider.synthesize(TTSRequest(text=sample_text, voice_id=row["voice_id"]))
    except TTSProviderError as exc:
        # Surface the provider's real error to the client so the UI can show a
        # useful message ("voice_id female-wenrou not found") instead of a
        # generic "please try again". Truncate the raw provider payload to
        # 320 chars — enough to spot the failure mode without leaking a full
        # stack trace or huge JSON body.
        provider_msg = str(exc)
        if len(provider_msg) > 320:
            provider_msg = provider_msg[:317] + "..."
        logger.warning(
            "preset_sample_synthesize_failed",
            preset_id=preset_id,
            voice_id=row["voice_id"],
            status_code=exc.status_code,
            error=provider_msg,
        )
        raise HTTPException(
            status_code=502,
            detail=f"试听合成失败：{provider_msg}",
        ) from exc

    _PRESET_SAMPLE_CACHE[preset_id] = result.audio
    logger.info(
        "preset_sample_synthesized",
        preset_id=preset_id,
        bytes=len(result.audio),
    )
    return Response(content=result.audio, media_type="audio/mpeg")


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
    from heart.ss08_voice.voice_resolver import get_voice_config

    config = await get_voice_config(character_id, db)
    if config is not None:
        return {
            "configured": True,
            "voice_type": config["voice_type"],
            "clone_status": config["clone_status"],
            "preset_voice_id": config["preset_voice_id"],
            "preset_name": config.get("preset_name"),
            "has_voice": config["clone_status"] == "ready",
        }
    if character_id in VOICE_CATALOG:
        return {
            "configured": True,
            "voice_type": "preset",
            "clone_status": "ready",
            "preset_voice_id": None,
            "preset_name": None,
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

    # Validate preset exists
    result = await db.execute(
        text("SELECT id FROM preset_voices WHERE id = :pid AND is_active = TRUE"),
        {"pid": body.preset_voice_id},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="预设音色不存在")

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
                (character_id, user_id, voice_type, preset_voice_id, clone_status)
            VALUES (:cid, :uid, 'preset', :pid, 'ready')
            ON CONFLICT (character_id) DO UPDATE
                SET voice_type      = 'preset',
                    preset_voice_id = :pid,
                    clone_status    = 'ready',
                    updated_at      = NOW()
        """),
        {"cid": body.character_id, "uid": uid, "pid": body.preset_voice_id},
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
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_age_verified),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload an audio sample to clone a voice for a UGC character.

    Deducts 800 credits (80 000 fen) on success. The clone job runs
    asynchronously; poll GET /api/voice/{character_id} for status.
    """
    uid = uuid.UUID(current_user.user_id)

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
    balance = await get_balance(db, uid)
    if balance < _CLONE_COST_FEN:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，克隆需要 800 积分，当前余额 {balance / 100:.1f}",
        )

    # MiniMax must be configured — clone always ends up calling their API,
    # regardless of how we hand it the audio. We deliberately DON'T require
    # ``voice_provider == "minimax"`` here: even when the deployment picks
    # MiMo as its primary TTS, MiniMax remains the only clone backend, and
    # the resulting voice_id will be reached via fallback at chat time.
    if not settings.minimax_api_key:
        raise HTTPException(
            status_code=503,
            detail="音色克隆服务未配置，请联系管理员或改用预设音色。",
        )

    audio_source = await _stage_audio_for_clone(
        data=data,
        filename=file.filename or "sample.wav",
        mime=mime,
        character_id=character_id,
    )

    # Upsert character_voices row with status = 'processing'
    await db.execute(
        text("""
            INSERT INTO character_voices
                (character_id, user_id, voice_type, clone_audio_url, clone_status)
            VALUES (:cid, :uid, 'clone', :url, 'processing')
            ON CONFLICT (character_id) DO UPDATE
                SET voice_type      = 'clone',
                    clone_audio_url = :url,
                    clone_voice_id  = NULL,
                    clone_status    = 'processing',
                    error_msg       = NULL,
                    updated_at      = NOW()
        """),
        {"cid": character_id, "uid": uid, "url": audio_source},
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

    asyncio.get_event_loop().call_soon_threadsafe(
        lambda: asyncio.ensure_future(_run_clone_job(character_id, audio_source, str(uid)))
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
) -> str:
    """Hand the audio bytes to MiniMax and return a tagged handle.

    Two paths:
      1. S3/MinIO configured → upload once, return the public file_url.
      2. Otherwise → forward to MiniMax `/files/upload` and return
         ``minimax_file://<file_id>``. Lets dev / small deploys run voice
         clone end-to-end without provisioning S3.
    """
    from heart.infra.storage import is_s3_configured
    from heart.infra.storage import upload_file as s3_upload

    if is_s3_configured():
        ext = mime.split("/")[-1].replace("x-wav", "wav").replace("mpeg", "mp3")
        key = f"voice-samples/{character_id}/{uuid.uuid4().hex}.{ext}"
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


async def _run_clone_job(character_id: str, audio_source: str, user_id: str) -> None:
    """Background task: call TTS provider voice clone API and update DB.

    ``audio_source`` is the tagged handle stored in ``character_voices.clone_audio_url``.
    See ``_call_tts_clone_api`` for the accepted schemes.
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
            clone_voice_id = await _call_tts_clone_api(audio_source, character_id)
            if clone_voice_id:
                # Charge credits only after the provider returns a voice_id —
                # a failed clone should not cost the user anything.
                # Idempotency key ties to the specific audio source (unique per
                # upload) so retries within the same source don't double-charge.
                try:
                    await deduct_credits(
                        db,
                        uuid.UUID(user_id),
                        _CLONE_COST_FEN,
                        f"voice_clone_success:{audio_source}",
                        type_str="consume_voice_clone",
                    )
                except InsufficientCreditsError:
                    # Rare race: balance dropped after the pre-check.  We've
                    # already burned the TTS API call, so log and let the clone
                    # succeed — the user effectively gets one free clone.
                    logger.warning(
                        "voice_clone_deduct_after_success_failed",
                        character_id=character_id,
                        user_id=user_id,
                    )
                await db.execute(
                    text("""
                        UPDATE character_voices
                        SET clone_voice_id = :vid, clone_status = 'ready',
                            updated_at = NOW()
                        WHERE character_id = :cid
                    """),
                    {"vid": clone_voice_id, "cid": character_id},
                )
                await db.execute(
                    text("UPDATE characters SET has_voice = TRUE WHERE id = :cid"),
                    {"cid": character_id},
                )
                logger.info("voice_clone_ready", character_id=character_id, voice_id=clone_voice_id)
            else:
                await db.execute(
                    text("""
                        UPDATE character_voices
                        SET clone_status = 'failed', error_msg = 'Provider returned no voice id',
                            updated_at = NOW()
                        WHERE character_id = :cid
                    """),
                    {"cid": character_id},
                )
                logger.warning("voice_clone_failed", character_id=character_id)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error("voice_clone_job_error", character_id=character_id, error=str(exc))
            try:
                await db.execute(
                    text("""
                        UPDATE character_voices
                        SET clone_status = 'failed', error_msg = :err, updated_at = NOW()
                        WHERE character_id = :cid
                    """),
                    {"cid": character_id, "err": str(exc)[:200]},
                )
                await db.commit()
            except Exception:
                pass


async def _call_tts_clone_api(audio_source: str, character_id: str) -> str | None:
    """Call the configured TTS provider's voice clone endpoint.

    Returns the new voice_id on success, or None on any failure so the caller
    marks the job as failed and reports it back to the user honestly.  There
    is no synthetic-id fallback: pretending to succeed produced voice_ids the
    TTS provider rejected at chat time, which surfaced as the "stuck at 正在
    回复" bug (2026-07-11).

    ``audio_source`` carries a scheme prefix identifying how MiniMax should
    receive the audio:
      - ``minimax_file://<file_id>`` — a MiniMax-hosted file_id from the
        ``/files/upload`` endpoint. Used when S3 isn't configured.
      - anything else — treated as a publicly-fetchable ``file_url``.
    """
    if audio_source.startswith("local://"):
        logger.warning("voice_clone_local_url_rejected", audio_source=audio_source)
        return None

    # See endpoint gate above: clone is MiniMax-only regardless of primary TTS.
    if not settings.minimax_api_key:
        logger.warning("voice_clone_provider_unavailable", provider=settings.voice_provider)
        return None

    try:
        if audio_source.startswith("minimax_file://"):
            file_id_str = audio_source[len("minimax_file://") :]
            return await _minimax_clone_by_file_id(int(file_id_str), character_id)
        return await _minimax_clone_by_url(audio_source, character_id)
    except Exception as exc:
        logger.warning("minimax_clone_failed", error=str(exc))
        return None


async def _minimax_clone_by_url(audio_url: str, character_id: str) -> str | None:
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


async def _minimax_clone_by_file_id(file_id: int, character_id: str) -> str | None:
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


async def _minimax_voice_clone_request(payload: dict) -> str | None:
    """Post the given payload to MiniMax's ``/voice_clone`` endpoint."""
    import aiohttp

    headers = {
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.minimax_base_url}/voice_clone"
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            if resp.status != 200:
                text_body = await resp.text()
                logger.warning("minimax_clone_error", status=resp.status, body=text_body[:200])
                return None
            body = await resp.json()
            # MiniMax echoes back the voice_id we sent on success; also accept
            # `id` for defensive compatibility with older API versions.
            return payload.get("voice_id") or body.get("voice_id") or body.get("id")


async def _upload_audio_to_minimax(data: bytes, filename: str, mime: str) -> int:
    """Upload raw audio bytes to MiniMax ``/files/upload`` and return the file_id.

    Used when S3 is not configured — MiniMax hosts the audio internally so we
    still get a voice_clone-able reference without needing a public URL.
    Kept synchronous with the calling coroutine's `await`; uses ``aiohttp``
    to avoid pulling in a second HTTP client for one endpoint.
    """
    import aiohttp

    if not settings.minimax_api_key:
        raise RuntimeError("MINIMAX_API_KEY not configured")

    headers = {"Authorization": f"Bearer {settings.minimax_api_key}"}
    url = f"{settings.minimax_base_url}/files/upload"

    form = aiohttp.FormData()
    form.add_field("purpose", "voice_clone")
    form.add_field(
        "file",
        data,
        filename=filename,
        content_type=mime or "application/octet-stream",
    )

    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, data=form, headers=headers, timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            if resp.status != 200:
                text_body = await resp.text()
                raise RuntimeError(
                    f"MiniMax files/upload failed status={resp.status} body={text_body[:200]}"
                )
            body = await resp.json()
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
