"""Character settings API routes — /api/characters/*"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db, get_safety_agent
from heart.core.auth import TokenData, get_current_user
from heart.ss01_soul.character_catalog import (
    CharacterRow,
    build_catalog_entries,
    is_known_character,
)
from heart.ss01_soul.character_content import CharacterContent
from heart.ss01_soul.draft import CharacterDraft

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])

# Max UGC characters per user
_UGC_MAX_PER_USER = 5

# Valid character_id pattern (same as SoulSpec)
_CID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class VoiceSettingUpdate(BaseModel):
    voice_enabled: bool


def _require_known_character(character_id: str) -> None:
    """Reject a ``character_id`` that has no loaded Soul Spec (boundary guard)."""
    if not is_known_character(character_id):
        raise HTTPException(status_code=404, detail=f"未知角色: {character_id}")


@router.get("")
async def list_characters(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List characters visible to the current user (built-ins + own UGC).

    Display names are derived from the Soul Spec, not stored on the row.
    Avatar URLs are extracted from the draft stored in soul_specs for UGC characters.
    """
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text(
            """
            SELECT id, owner_user_id, visibility, status, has_voice
            FROM characters
            WHERE status = 'active'
              AND (visibility = 'public' OR owner_user_id = :uid)
            """
        ),
        {"uid": uid},
    )
    raw_rows = list(result.mappings())
    rows = [
        CharacterRow(
            id=row["id"],
            owner_user_id=row["owner_user_id"],
            visibility=row["visibility"],
            status=row["status"],
        )
        for row in raw_rows
    ]
    has_voice_map = {row["id"]: bool(row.get("has_voice", False)) for row in raw_rows}

    # Fetch avatar_url from soul_specs.draft for UGC characters
    avatar_urls: dict[str, str | None] = {}
    ugc_ids = [row.id for row in rows if row.owner_user_id is not None]
    if ugc_ids:
        avatar_result = await db.execute(
            text(
                """
                SELECT character_id, draft->>'avatar_url' AS avatar_url
                FROM soul_specs
                WHERE character_id = ANY(:ids) AND status = 'active'
                """
            ),
            {"ids": ugc_ids},
        )
        for row in avatar_result:
            if row.avatar_url:
                avatar_urls[row.character_id] = row.avatar_url

    entries = build_catalog_entries(rows, uid, avatar_urls)
    result_list = []
    for e in entries:
        entry_dict = asdict(e)
        entry_dict["has_voice"] = has_voice_map.get(e.id, False)
        result_list.append(entry_dict)
    return {"characters": result_list}


@router.get("/{character_id}/settings")
async def get_character_settings(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get per-character settings (voice toggle)."""
    _require_known_character(character_id)
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text("""
            SELECT voice_enabled FROM user_character_settings
            WHERE user_id = :uid AND character_id = :cid
        """),
        {"uid": uid, "cid": character_id},
    )
    row = result.scalar_one_or_none()
    return {"voice_enabled": row if row is not None else False}


@router.patch("/{character_id}/settings")
async def update_character_settings(
    character_id: str,
    body: VoiceSettingUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update per-character voice toggle (upsert).

    Returns 409 when voice_enabled=True is requested but the character has no
    voice configured yet (has_voice=FALSE).
    """
    _require_known_character(character_id)
    uid = uuid.UUID(current_user.user_id)

    if body.voice_enabled:
        has_voice_result = await db.execute(
            text("SELECT has_voice FROM characters WHERE id = :cid"),
            {"cid": character_id},
        )
        has_voice = has_voice_result.scalar_one_or_none()
        if not has_voice:
            raise HTTPException(
                status_code=409,
                detail="请先为该角色配置音色，才能开启语音聊天",
            )

    await db.execute(
        text("""
            INSERT INTO user_character_settings (user_id, character_id, voice_enabled, updated_at)
            VALUES (:uid, :cid, :ve, NOW())
            ON CONFLICT (user_id, character_id)
            DO UPDATE SET voice_enabled = :ve, updated_at = NOW()
        """),
        {"uid": uid, "cid": character_id, "ve": body.voice_enabled},
    )
    await db.commit()
    logger.info(
        "character_setting_updated",
        user_id=str(uid),
        character_id=character_id,
        voice_enabled=body.voice_enabled,
    )
    return {"voice_enabled": body.voice_enabled}


@router.post("/{character_id}/clear-conversations")
async def clear_character_conversations(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear persisted chat messages for one character only."""
    _require_known_character(character_id)
    uid = uuid.UUID(current_user.user_id)

    try:
        await db.execute(
            text(
                """
                DELETE FROM chat_messages
                WHERE user_id = :uid AND character_id = :cid
                """
            ),
            {"uid": uid, "cid": character_id},
        )
    except Exception as exc:
        logger.warning(
            "character_conversations_clear_failed",
            user_id=str(uid),
            character_id=character_id,
            error=str(exc),
        )
        raise HTTPException(status_code=500, detail="清空聊天记录失败") from exc

    await db.commit()
    logger.info(
        "character_conversations_cleared",
        user_id=str(uid),
        character_id=character_id,
    )
    return {"ok": True}


# ── UGC CRUD ─────────────────────────────────────────────────────────────────


def _mint_character_id(display_name: str | None, uid: uuid.UUID) -> str:
    """Mint a unique character_id: slug + 8-char random hex (unique per call)."""
    raw = re.sub(r"[^a-z0-9]+", "_", (display_name or "char").lower()).strip("_")[:12]
    # Use a fresh uuid4 so each call produces a different suffix regardless of
    # the display name or user id (Chinese names always reduce raw to empty).
    suffix = uuid.uuid4().hex[:8]
    cid = f"{raw or 'char'}_{suffix}"
    # Must satisfy ^[a-z][a-z0-9_]*$
    if not _CID_RE.match(cid):
        cid = f"c_{suffix}"
    return cid


async def _require_owner(
    character_id: str,
    uid: uuid.UUID,
    db: AsyncSession,
    *,
    allow_edit: bool = True,
) -> dict:
    """Fetch the characters row and check ownership.

    Returns the row as a dict.  Raises 404 if not found, 403 if not owned,
    403 if it is a builtin (owner_user_id IS NULL).
    """
    result = await db.execute(
        text("SELECT id, owner_user_id, visibility, status FROM characters WHERE id = :cid"),
        {"cid": character_id},
    )
    row = result.mappings().fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"角色不存在: {character_id}")
    if row["owner_user_id"] is None:
        raise HTTPException(status_code=403, detail="内置角色不可编辑")
    if str(row["owner_user_id"]) != str(uid):
        raise HTTPException(status_code=403, detail="无权操作此角色")
    return dict(row)


def _derive_content(
    draft: CharacterDraft,
    character_id: str,
) -> CharacterContent:
    """Derive proactive content strings from a draft (deterministic, no LLM)."""
    name = draft.display_name.zh or draft.display_name.ja or draft.display_name.en or character_id
    style_greet = {
        "warm": f"{name}想着你，今天过得怎么样？",
        "cool": f"…{name}在这里。",
        "playful": f"{name}来了！嘿嘿，有没有想我？",
        "reserved": f"{name}注意到今天的你。",
        "intense": f"{name}一直在想你。",
    }
    style_name = draft.greeting_style.value
    return CharacterContent(
        proactive_persona=draft.persona[:200],
        proactive_templates=[style_greet.get(style_name, f"{name}来了。")],
        ritual_morning=f"早安。{name}想和你说声好。",
        ritual_night=f"晚安。{name}陪着你。",
    )


class VisibilityUpdate(BaseModel):
    visibility: str  # public | unlisted | private


@router.post("/avatar")
async def upload_character_avatar(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    """Upload a character avatar image. Returns an avatar_url for use in CharacterDraft."""
    uid = uuid.UUID(current_user.user_id)

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp 格式")

    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="文件不能超过 5MB")

    from heart.infra.storage import is_s3_configured
    from heart.infra.storage import upload_avatar as s3_upload

    if is_s3_configured():
        try:
            avatar_url = await s3_upload(f"character-{uid.hex[:8]}", data, file.content_type)
        except Exception as exc:
            logger.warning("character_avatar_s3_failed", error=str(exc))
            import base64

            b64 = base64.b64encode(data).decode()
            avatar_url = f"data:{file.content_type};base64,{b64}"
    else:
        import base64

        b64 = base64.b64encode(data).decode()
        avatar_url = f"data:{file.content_type};base64,{b64}"

    return {"avatar_url": avatar_url}


@router.post("")
async def create_character(
    draft: CharacterDraft,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    safety_agent=Depends(get_safety_agent),
) -> dict:
    """Create a new private UGC character and hot-load it into the registry."""
    from heart.ss01_soul.content_store import upsert_content
    from heart.ss01_soul.persona_screen import PersonaRejectedError, screen_persona
    from heart.ss01_soul.reload import reload_character
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
    from heart.ss01_soul.spec_store import insert_spec

    uid = uuid.UUID(current_user.user_id)

    # Quota guard
    count_result = await db.execute(
        text("SELECT COUNT(*) FROM characters WHERE owner_user_id = :uid AND status = 'active'"),
        {"uid": uid},
    )
    active_count = count_result.scalar() or 0
    if active_count >= _UGC_MAX_PER_USER:
        raise HTTPException(status_code=422, detail=f"最多创建 {_UGC_MAX_PER_USER} 个自定义角色")

    # Safety screen
    if safety_agent is not None:
        try:
            await screen_persona(
                draft, user_id=str(uid), character_id="pending", safety_agent=safety_agent
            )
        except PersonaRejectedError as exc:
            raise HTTPException(status_code=422, detail=f"人设审核未通过：{exc.reason}") from exc

    # Mint id
    name_zh = draft.display_name.zh
    character_id = _mint_character_id(name_zh, uid)

    # Build spec
    spec = build_soul_spec_from_draft(draft, character_id=character_id)

    # Persist — single transaction
    spec_dict = spec.model_dump(mode="json")
    draft_dict = draft.model_dump(mode="json")
    content = _derive_content(draft, character_id)

    await db.execute(
        text(
            "INSERT INTO characters (id, owner_user_id, visibility, status, soul_spec_version)"
            " VALUES (:id, :uid, 'private', 'active', :ver)"
        ),
        {"id": character_id, "uid": uid, "ver": spec.spec_version},
    )
    await insert_spec(
        db,
        character_id=character_id,
        spec_version=spec.spec_version,
        source="ugc",
        spec=spec_dict,
        draft=draft_dict,
    )
    await upsert_content(db, character_id=character_id, **content)
    await db.commit()

    # Hot-load into registry (no restart needed)
    reload_character(character_id, spec=spec)

    from heart.ss01_soul.character_content import register_content

    register_content(character_id, content)

    logger.info("ugc_character_created", character_id=character_id, user_id=str(uid))
    return {
        "id": character_id,
        "display_name": spec.display_name.zh or spec.display_name.ja or spec.display_name.en,
        "spec_version": spec.spec_version,
        "visibility": "private",
    }


@router.get("/{character_id}/draft")
async def get_character_draft(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a UGC character's creation draft (owner only)."""
    uid = uuid.UUID(current_user.user_id)
    await _require_owner(character_id, uid, db)

    result = await db.execute(
        text("""
            SELECT draft FROM soul_specs
            WHERE character_id = :cid AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
        """),
        {"cid": character_id},
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=404, detail="草稿不存在")
    return draft


@router.patch("/{character_id}")
async def update_character(
    character_id: str,
    draft: CharacterDraft,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    safety_agent=Depends(get_safety_agent),
) -> dict:
    """Edit a UGC character — bumps semver minor, supersedes old spec."""
    from heart.ss01_soul.content_store import upsert_content
    from heart.ss01_soul.persona_screen import PersonaRejectedError, screen_persona
    from heart.ss01_soul.reload import reload_character
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
    from heart.ss01_soul.spec_store import insert_spec, supersede_active

    uid = uuid.UUID(current_user.user_id)
    row = await _require_owner(character_id, uid, db)

    if safety_agent is not None:
        try:
            await screen_persona(
                draft, user_id=str(uid), character_id=character_id, safety_agent=safety_agent
            )
        except PersonaRejectedError as exc:
            raise HTTPException(status_code=422, detail=f"人设审核未通过：{exc.reason}") from exc

    # Bump semver minor (1.0.0 → 1.1.0)
    old_ver = row.get("soul_spec_version") or "1.0.0"
    parts = old_ver.split(".")
    try:
        new_ver = f"{parts[0]}.{int(parts[1]) + 1}.0"
    except (IndexError, ValueError):
        new_ver = "1.1.0"

    spec = build_soul_spec_from_draft(draft, character_id=character_id, spec_version=new_ver)
    spec_dict = spec.model_dump(mode="json")
    draft_dict = draft.model_dump(mode="json")
    content = _derive_content(draft, character_id)

    await supersede_active(db, character_id)
    await insert_spec(
        db,
        character_id=character_id,
        spec_version=new_ver,
        source="ugc",
        spec=spec_dict,
        draft=draft_dict,
    )
    await db.execute(
        text("UPDATE characters SET soul_spec_version = :ver WHERE id = :cid"),
        {"ver": new_ver, "cid": character_id},
    )
    await upsert_content(db, character_id=character_id, **content)
    await db.commit()

    reload_character(character_id, spec=spec)
    from heart.ss01_soul.character_content import register_content

    register_content(character_id, content)

    logger.info("ugc_character_updated", character_id=character_id, new_version=new_ver)
    return {"id": character_id, "spec_version": new_ver}


@router.patch("/{character_id}/visibility")
async def set_character_visibility(
    character_id: str,
    body: VisibilityUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a UGC character's visibility (public|unlisted|private)."""
    uid = uuid.UUID(current_user.user_id)
    if body.visibility not in ("public", "unlisted", "private"):
        raise HTTPException(status_code=422, detail="visibility 必须是 public / unlisted / private")
    await _require_owner(character_id, uid, db)
    await db.execute(
        text("UPDATE characters SET visibility = :vis WHERE id = :cid"),
        {"vis": body.visibility, "cid": character_id},
    )
    await db.commit()
    logger.info("ugc_visibility_updated", character_id=character_id, visibility=body.visibility)
    return {"id": character_id, "visibility": body.visibility}


@router.post("/{character_id}/disable")
async def disable_character(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Soft-delete (disable) a UGC character so it no longer appears in catalogs."""
    from heart.ss01_soul.reload import reload_character

    uid = uuid.UUID(current_user.user_id)
    await _require_owner(character_id, uid, db)
    await db.execute(
        text("UPDATE characters SET status = 'disabled' WHERE id = :cid"),
        {"cid": character_id},
    )
    await db.commit()
    reload_character(character_id, spec=None)
    logger.info("ugc_character_disabled", character_id=character_id)
    return {"id": character_id, "status": "disabled"}


@router.delete("/{character_id}")
async def delete_character(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Hard-delete a UGC character (owner only).  Cascades all per-user data."""
    from heart.ss01_soul.content_store import delete_content
    from heart.ss01_soul.reload import reload_character
    from heart.ss01_soul.spec_store import set_spec_status

    uid = uuid.UUID(current_user.user_id)
    await _require_owner(character_id, uid, db)

    # Mark all specs disabled (non-destructive to spec history)
    await db.execute(
        text("UPDATE soul_specs SET status = 'disabled' WHERE character_id = :cid"),
        {"cid": character_id},
    )
    # Remove content
    await delete_content(db, character_id)
    # Remove character row
    await db.execute(
        text("DELETE FROM characters WHERE id = :cid"),
        {"cid": character_id},
    )
    await db.commit()

    reload_character(character_id, spec=None)
    logger.info("ugc_character_deleted", character_id=character_id)
    return {"id": character_id, "deleted": True}
