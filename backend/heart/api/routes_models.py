"""Selectable chat-model catalog, live status, and per-character preference."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.auth import TokenData, get_current_user
from heart.infra.model_catalog import DEFAULT_CHAT_MODEL, MODEL_CATALOG, get_model_spec
from heart.infra.model_health import model_status
from heart.membership import get_effective_tier

from .wiring import get_db

router = APIRouter(prefix="/api/models", tags=["models"])


def _configured(model_id: str) -> bool:
    try:
        from heart.infra.llm_providers import get_registry

        return get_registry().has_model(model_id)
    except RuntimeError:
        return False


@router.get("")
async def list_models(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    tier = await get_effective_tier(db, uuid.UUID(current_user.user_id))
    models = []
    for spec in MODEL_CATALOG:
        item = spec.public_dict()
        item.update(model_status(spec.id, configured=_configured(spec.id)))
        item["included"] = tier == "immersive"
        models.append(item)
    return {"default_model": DEFAULT_CHAT_MODEL, "models": models}


@router.get("/preferences")
async def model_preferences(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        (
            await db.execute(
                text(
                    "SELECT character_id, model_id FROM user_character_model_preferences "
                    "WHERE user_id = :uid"
                ),
                {"uid": uuid.UUID(current_user.user_id)},
            )
        )
        .mappings()
        .all()
    )
    return {
        "default_model": DEFAULT_CHAT_MODEL,
        "preferences": {row["character_id"]: row["model_id"] for row in rows},
    }


class PreferenceBody(BaseModel):
    model_id: str


@router.put("/preferences/{character_id}")
async def save_model_preference(
    character_id: str,
    body: PreferenceBody,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    spec = get_model_spec(body.model_id)
    if spec is None:
        raise HTTPException(status_code=422, detail="unknown_model")
    if not _configured(spec.id):
        raise HTTPException(status_code=409, detail="model_unavailable")
    await db.execute(
        text(
            "INSERT INTO user_character_model_preferences "
            "(user_id, character_id, model_id, updated_at) "
            "VALUES (:uid, :cid, :model, NOW()) "
            "ON CONFLICT (user_id, character_id) DO UPDATE "
            "SET model_id = EXCLUDED.model_id, updated_at = NOW()"
        ),
        {
            "uid": uuid.UUID(current_user.user_id),
            "cid": character_id,
            "model": spec.id,
        },
    )
    await db.commit()
    return {"character_id": character_id, "model_id": spec.id}
