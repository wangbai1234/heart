"""Voice API routes — per runtime_specs/08_voice.md"""

from __future__ import annotations

from io import BytesIO
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from .wiring import get_voice_service

logger = structlog.get_logger()

router = APIRouter(prefix="/api/voice", tags=["voice"])


class SynthesizeRequest(BaseModel):
    text: str
    character_id: str = "rin"
    emotion: str = "neutral"


class SynthesizeWithStateRequest(BaseModel):
    text: str
    character_id: str = "rin"
    vad: Optional[Dict[str, float]] = None
    intimacy: float = 0.0
    active_emotions: Optional[List[str]] = None


@router.post("/synthesize")
async def synthesize(req: SynthesizeRequest):
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


@router.post("/synthesize_with_state")
async def synthesize_with_state(req: SynthesizeWithStateRequest):
    """Synthesize speech with emotion/relationship state."""
    voice_service = get_voice_service()
    if not voice_service:
        raise HTTPException(
            status_code=503,
            detail="Voice service not configured. Set MINIMAX_API_KEY in .env",
        )

    try:
        result = await voice_service.synthesize_with_state(
            text=req.text,
            character_id=req.character_id,
            vad=req.vad,
            intimacy=req.intimacy,
            active_emotions=req.active_emotions,
        )
        return StreamingResponse(
            BytesIO(result.audio),
            media_type=f"audio/{result.format}",
        )
    except Exception as e:
        logger.error("voice_synthesize_with_state_failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
