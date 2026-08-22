"""User mask (explicit persona) API."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user

router = APIRouter(prefix="/api/masks", tags=["masks"])


class MaskInput(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    gender: Literal["male", "female", "unspecified"] = "unspecified"
    bio: str = Field(min_length=1, max_length=2000)

    @field_validator("name", "bio")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("不能为空")
        return value


def _row(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "name": row["name"],
        "gender": row["gender"],
        "bio": row["bio"],
        "bound_character_ids": list(row.get("bound_character_ids") or []),
        "created_at": row["created_at"].isoformat(),
        "updated_at": row["updated_at"].isoformat(),
    }


async def _ensure_character_visible(db: AsyncSession, uid: uuid.UUID, character_id: str) -> None:
    result = await db.execute(
        text(
            """SELECT 1 FROM characters WHERE id = :cid AND status = 'active'
               AND (owner_user_id = :uid OR (visibility IN ('public', 'unlisted') AND review_status = 'approved'))
               LIMIT 1"""
        ),
        {"cid": character_id, "uid": uid},
    )
    if result.scalar_one_or_none() is None:
        from heart.ss01_soul.character_catalog import is_known_character

        if not is_known_character(character_id):
            raise HTTPException(status_code=404, detail="角色不存在或不可用")


@router.get("")
async def list_masks(
    current_user: TokenData = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text(
            """SELECT m.*,
                      COALESCE(
                        ARRAY_AGG(b.character_id) FILTER (WHERE b.deleted_at IS NULL),
                        ARRAY[]::TEXT[]
                      ) AS bound_character_ids
               FROM user_masks m
               LEFT JOIN user_character_mask_bindings b ON b.mask_id = m.id
               WHERE m.user_id = :uid AND m.deleted_at IS NULL
               GROUP BY m.id
               ORDER BY m.updated_at DESC, m.created_at DESC"""
        ),
        {"uid": uid},
    )
    return {"items": [_row(dict(row)) for row in result.mappings().all()]}


@router.post("")
async def create_mask(
    body: MaskInput,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    mask_id = uuid.uuid4()
    await db.execute(
        text("""INSERT INTO user_masks (id, user_id, name, gender, bio)
        VALUES (:id, :uid, :name, :gender, :bio)"""),
        {
            "id": mask_id,
            "uid": uid,
            "name": body.name.strip(),
            "gender": body.gender,
            "bio": body.bio.strip(),
        },
    )
    result = await db.execute(
        text("SELECT *, ARRAY[]::TEXT[] AS bound_character_ids FROM user_masks WHERE id = :id"),
        {"id": mask_id},
    )
    return {"item": _row(dict(result.mappings().one()))}


@router.patch("/{mask_id}")
async def update_mask(
    mask_id: uuid.UUID,
    body: MaskInput,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    exists = await db.execute(
        text("SELECT 1 FROM user_masks WHERE id = :id AND user_id = :uid AND deleted_at IS NULL"),
        {"id": mask_id, "uid": uid},
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="面具不存在")
    await db.execute(
        text("""UPDATE user_masks SET name = :name, gender = :gender, bio = :bio,
        updated_at = NOW() WHERE id = :id AND user_id = :uid AND deleted_at IS NULL"""),
        {
            "id": mask_id,
            "uid": uid,
            "name": body.name.strip(),
            "gender": body.gender,
            "bio": body.bio.strip(),
        },
    )
    result = await db.execute(
        text(
            """SELECT m.*,
                      COALESCE(ARRAY_AGG(b.character_id) FILTER (WHERE b.deleted_at IS NULL), ARRAY[]::TEXT[]) AS bound_character_ids
               FROM user_masks m
               LEFT JOIN user_character_mask_bindings b ON b.mask_id = m.id
               WHERE m.id = :id GROUP BY m.id"""
        ),
        {"id": mask_id},
    )
    return {"item": _row(dict(result.mappings().one()))}


@router.post("/{mask_id}/bind")
async def bind_mask(
    mask_id: uuid.UUID,
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    await _ensure_character_visible(db, uid, character_id)
    exists = await db.execute(
        text("SELECT 1 FROM user_masks WHERE id = :id AND user_id = :uid AND deleted_at IS NULL"),
        {"id": mask_id, "uid": uid},
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="面具不存在")
    await db.execute(
        text(
            """UPDATE user_character_mask_bindings
               SET deleted_at = NOW(), updated_at = NOW()
               WHERE user_id = :uid AND character_id = :cid AND deleted_at IS NULL"""
        ),
        {"uid": uid, "cid": character_id},
    )
    await db.execute(
        text(
            """INSERT INTO user_character_mask_bindings
               (id, user_id, character_id, mask_id)
               VALUES (:binding_id, :uid, :cid, :id)"""
        ),
        {"binding_id": uuid.uuid4(), "id": mask_id, "uid": uid, "cid": character_id},
    )
    result = await db.execute(
        text(
            """SELECT m.*,
                      COALESCE(ARRAY_AGG(b.character_id) FILTER (WHERE b.deleted_at IS NULL), ARRAY[]::TEXT[]) AS bound_character_ids
               FROM user_masks m
               LEFT JOIN user_character_mask_bindings b ON b.mask_id = m.id
               WHERE m.id = :id GROUP BY m.id"""
        ),
        {"id": mask_id},
    )
    return {"item": _row(dict(result.mappings().one()))}


@router.post("/{mask_id}/unbind")
async def unbind_mask(
    mask_id: uuid.UUID,
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    exists = await db.execute(
        text("SELECT 1 FROM user_masks WHERE id = :id AND user_id = :uid AND deleted_at IS NULL"),
        {"id": mask_id, "uid": uid},
    )
    if exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="面具不存在")
    await db.execute(
        text(
            """UPDATE user_character_mask_bindings
               SET deleted_at = NOW(), updated_at = NOW()
               WHERE user_id = :uid AND character_id = :cid AND mask_id = :id
                 AND deleted_at IS NULL"""
        ),
        {"id": mask_id, "uid": uid, "cid": character_id},
    )
    return {"ok": True}


@router.delete("/{mask_id}")
async def delete_mask(
    mask_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text(
            "UPDATE user_masks SET deleted_at = NOW(), updated_at = NOW() WHERE id = :id AND user_id = :uid AND deleted_at IS NULL RETURNING id"
        ),
        {"id": mask_id, "uid": uid},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="面具不存在")
    await db.execute(
        text(
            """UPDATE user_character_mask_bindings
               SET deleted_at = NOW(), updated_at = NOW()
               WHERE mask_id = :id AND user_id = :uid AND deleted_at IS NULL"""
        ),
        {"id": mask_id, "uid": uid},
    )
    return {"ok": True}


async def get_bound_mask(db: AsyncSession, user_id: uuid.UUID, character_id: str) -> dict | None:
    result = await db.execute(
        text(
            """SELECT m.name, m.gender, m.bio
               FROM user_character_mask_bindings b
               JOIN user_masks m ON m.id = b.mask_id
               WHERE b.user_id = :uid AND b.character_id = :cid
                 AND b.deleted_at IS NULL AND m.deleted_at IS NULL
               LIMIT 1"""
        ),
        {"uid": user_id, "cid": character_id},
    )
    row = result.mappings().first()
    return dict(row) if row else None
