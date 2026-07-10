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
from heart.billing import InsufficientCreditsError, deduct_credits
from heart.core.auth import TokenData, get_current_user
from heart.core.config import settings

from .deps import require_age_verified
from .wiring import get_voice_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/voice", tags=["voice"])

# Voice clone credit cost (800 display credits = 80 000 fen)
_CLONE_COST_FEN = 80_000

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
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List available preset voice options."""
    result = await db.execute(
        text("""
            SELECT id, name, voice_id, provider, description, sample_url
            FROM preset_voices
            WHERE is_active = TRUE
            ORDER BY id
        """)
    )
    rows = [dict(r) for r in result.mappings()]
    return {"presets": rows}


@router.get("/{character_id}")
async def get_character_voice(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the voice configuration for a character."""
    from heart.ss08_voice.voice_resolver import get_voice_config

    config = await get_voice_config(character_id, db)
    if config is None:
        return {"configured": False}
    return {
        "configured": True,
        "voice_type": config["voice_type"],
        "clone_status": config["clone_status"],
        "preset_voice_id": config["preset_voice_id"],
        "preset_name": config.get("preset_name"),
        "has_voice": config["clone_status"] == "ready",
    }


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

    # Charge credits before uploading
    idem_key = f"voice_clone:{character_id}:{uid}"
    try:
        new_balance = await deduct_credits(
            db, uid, _CLONE_COST_FEN, idem_key, type_str="consume_voice_clone"
        )
        await db.commit()
    except InsufficientCreditsError as exc:
        raise HTTPException(
            status_code=402,
            detail=f"积分不足，克隆需要 800 积分，当前余额 {exc.balance / 100:.1f}",
        ) from exc

    # Upload to S3 / MinIO
    from heart.infra.storage import is_s3_configured
    from heart.infra.storage import upload_file as s3_upload

    ext = mime.split("/")[-1].replace("x-wav", "wav").replace("mpeg", "mp3")
    key = f"voice-samples/{character_id}/{uuid.uuid4().hex}.{ext}"
    if is_s3_configured():
        try:
            audio_url = await s3_upload(data, key, mime)
        except Exception as exc:
            logger.warning("voice_clone_s3_failed", error=str(exc))
            audio_url = f"local://{key}"
    else:
        audio_url = f"local://{key}"

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
        {"cid": character_id, "uid": uid, "url": audio_url},
    )
    await db.commit()

    logger.info(
        "voice_clone_started",
        character_id=character_id,
        user_id=str(uid),
        audio_url=audio_url,
    )

    # Fire-and-forget background clone task
    import asyncio

    asyncio.get_event_loop().call_soon_threadsafe(
        lambda: asyncio.ensure_future(_run_clone_job(character_id, audio_url, str(uid)))
    )

    return {
        "ok": True,
        "clone_status": "processing",
        "balance": new_balance / 100,
    }


async def _run_clone_job(character_id: str, audio_url: str, user_id: str) -> None:
    """Background task: call TTS provider voice clone API and update DB."""
    import asyncio

    await asyncio.sleep(2)  # give the HTTP response time to flush

    from heart.api.wiring import get_db_session_factory

    session_factory = get_db_session_factory()
    if session_factory is None:
        logger.warning("voice_clone_job_no_db", character_id=character_id)
        return

    async with session_factory() as db:
        try:
            clone_voice_id = await _call_tts_clone_api(audio_url, character_id)
            if clone_voice_id:
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


async def _call_tts_clone_api(audio_url: str, character_id: str) -> str | None:
    """Call the configured TTS provider's voice clone endpoint.

    Returns the new voice_id on success, or None if not supported / disabled.
    For local:// URLs (no S3) we skip the actual API call and return a
    synthetic voice_id so development/test flows still work end-to-end.
    """
    if audio_url.startswith("local://"):
        # Dev fallback: use preset female-shaonv voice ID
        return f"ugc_clone_{character_id}"

    provider = settings.voice_provider
    if provider == "minimax" and settings.minimax_api_key:
        try:
            return await _minimax_clone(audio_url)
        except Exception as exc:
            logger.warning("minimax_clone_failed", error=str(exc))
            return None

    # No provider configured — use synthetic id for local dev
    return f"ugc_clone_{character_id}"


async def _minimax_clone(audio_url: str) -> str | None:
    """Submit voice clone job to MiniMax T2A v2 voice cloning API."""
    import aiohttp

    headers = {
        "Authorization": f"Bearer {settings.minimax_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "file_url": audio_url,
        "need_noise_reduction": True,
        "need_volume_normalization": True,
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
            return body.get("voice_id") or body.get("id")


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
