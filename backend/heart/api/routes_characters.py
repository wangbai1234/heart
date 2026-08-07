"""Character settings API routes — /api/characters/*"""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss01_soul.character_catalog import (
    CharacterRow,
    build_catalog_entries,
    coerce_tags,
    ensure_character_loaded,
)
from heart.ss01_soul.character_content import CharacterContent, get_display_name
from heart.ss01_soul.draft import CharacterDraft

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])

# Valid character_id pattern (same as SoulSpec)
_CID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class VoiceSettingUpdate(BaseModel):
    voice_enabled: bool


class VoiceProviderUpdate(BaseModel):
    provider: str  # 'mimo' (日常语音) | 'fish' (真人语音)


async def _require_known_character(character_id: str, db: AsyncSession) -> None:
    """Reject a ``character_id`` that has no loaded Soul Spec (boundary guard).

    DB-authoritative with lazy hydrate: with ``--workers 2`` a UGC character
    created on the other worker is absent from this process's in-memory
    registry, so ``is_known_character`` alone would 404 management calls (e.g.
    clear-conversations → "清空失败") for a character that plainly exists. The
    DB fallback hydrates it on hit.
    """
    if not await ensure_character_loaded(character_id, db):
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
            SELECT id, owner_user_id, visibility, status, has_voice,
                   tags, cover_url, review_status, review_reason, created_at
            FROM characters
            WHERE status = 'active'
              AND (
                    owner_user_id = :uid
                    OR (visibility = 'public' AND review_status = 'approved')
              )
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
            review_status=row.get("review_status", "not_required"),
            review_reason=row.get("review_reason"),
            tags=coerce_tags(row.get("tags")),
            cover_url=row.get("cover_url"),
            created_at=(row["created_at"].isoformat() if row.get("created_at") else None),
        )
        for row in raw_rows
    ]
    has_voice_map = {row["id"]: bool(row.get("has_voice", False)) for row in raw_rows}

    # Fetch avatar_url from soul_specs.draft for UGC characters
    avatar_urls: dict[str, str | None] = {}
    taglines: dict[str, str | None] = {}
    ugc_ids = [row.id for row in rows if row.owner_user_id is not None]
    if ugc_ids:
        content_result = await db.execute(
            text(
                """
                SELECT character_id,
                       draft->>'avatar_url' AS avatar_url,
                       draft->>'tagline' AS tagline
                FROM soul_specs
                WHERE character_id = ANY(:ids) AND status = 'active'
                """
            ),
            {"ids": ugc_ids},
        )
        for row in content_result:
            if row.avatar_url:
                avatar_urls[row.character_id] = row.avatar_url
            if row.tagline:
                taglines[row.character_id] = row.tagline

    # Compute popularity by counting distinct chat users per character
    popularity: dict[str, int] = {}
    pop_result = await db.execute(
        text(
            """
            SELECT character_id, COUNT(DISTINCT user_id) AS cnt
            FROM chat_messages
            GROUP BY character_id
            """
        )
    )
    for row in pop_result:
        popularity[row.character_id] = int(row.cnt)

    entries = build_catalog_entries(rows, uid, avatar_urls, popularity, taglines)
    result_list = []
    for e in entries:
        entry_dict = asdict(e)
        entry_dict["has_voice"] = has_voice_map.get(e.id, False)
        result_list.append(entry_dict)
    return {"characters": result_list}


def _coerce_json(raw: object) -> dict:
    """Normalize a JSONB column value into a dict (driver may return str or dict)."""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return raw if isinstance(raw, dict) else {}


def _first_nonempty_line(text_block: str) -> str:
    for line in (text_block or "").splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


# UGC slider key → user-facing 性格轴 label (kept in sync with draft.SliderSet).
_SLIDER_LABELS = {
    "warmth": "亲切",
    "talkativeness": "健谈",
    "directness": "直率",
    "humor": "幽默",
    "playfulness": "俏皮",
    "steadiness": "沉稳",
}


def _slider_personality(sliders: dict) -> list[dict]:
    out: list[dict] = []
    for key, label in _SLIDER_LABELS.items():
        val = sliders.get(key)
        if isinstance(val, (int, float)) and not isinstance(val, bool):
            out.append({"label": label, "value": round(float(val), 2)})
    return out


def _derive_intro(archetype: str, persona: str, backstory: str) -> str:
    """Fallback 叙引 body when the draft carries no explicit ``intro`` override."""
    if archetype.strip():
        return archetype.strip()
    if backstory.strip():
        return f"{persona.strip()}\n\n{backstory.strip()}".strip()
    return persona.strip()


def _derive_personality(draft: dict) -> list[dict]:
    """性格轴 from an explicit ``personality`` list, else derived from sliders."""
    personality: list[dict] = []
    raw_pers = draft.get("personality")
    if isinstance(raw_pers, list):
        for item in raw_pers:
            if isinstance(item, dict) and item.get("label"):
                personality.append({"label": str(item["label"]), "value": item.get("value")})
            elif isinstance(item, str) and item.strip():
                personality.append({"label": item.strip(), "value": None})
    if not personality and isinstance(draft.get("sliders"), dict):
        personality = _slider_personality(draft["sliders"])
    return personality


def _derive_profile_presentation(spec: dict, draft: dict, is_builtin: bool = False) -> dict:
    """Best-effort public presentation fields (tagline / one_liner / intro / …).

    Precedence per field: an explicit override in ``draft`` (used by the seed
    importer and the UGC form) → derivation from ``persona``/``backstory``.

    The ``identity_anchor.archetype`` is only a meaningful public label for
    *built-ins* (curated Chinese archetypes seeded from YAML). For UGC it is a
    deterministic English style template ("Passionate Soul" / "Gentle
    Companion" …) that ``spec_builder`` stamps from ``greeting_style`` — an
    internal register hint, NOT authored content. Surfacing it made most UGC
    profiles read as identical template text, so it is never used as a UGC
    fallback here (``is_builtin`` gates it). This also retroactively fixes
    already-created UGC without any migration.

    Every field degrades to '' / [] so a partial or malformed spec never 500s.
    Only ever reads public-facing content. Internal persona layers
    (core_wound / core_fear / core_belief / core_desire) are deliberately NOT
    touched — this endpoint must not leak them.
    """
    spec = spec or {}
    draft = draft or {}
    try:
        archetype = str((spec.get("identity_anchor") or {}).get("archetype", "") or "")
    except Exception:
        archetype = ""
    # Only built-ins may surface the archetype as public copy; for UGC treat it
    # as empty so derivations fall through to authored persona/backstory.
    public_archetype = archetype if is_builtin else ""
    persona = str(draft.get("persona", "") or "")
    backstory = str(draft.get("backstory", "") or "")

    def override(key: str, fallback: str) -> str:
        v = draft.get(key)
        return v.strip() if isinstance(v, str) and v.strip() else fallback

    archetype_first = _first_nonempty_line(public_archetype)
    persona_first = _first_nonempty_line(persona)

    tagline = override("tagline", archetype_first or persona_first)
    archetype_label = override("archetype_label", "")
    one_liner = override("one_liner", archetype_first or persona_first)

    intro = override("intro", "") or _derive_intro(public_archetype, persona, backstory)
    personality = _derive_personality(draft)

    return {
        "tagline": tagline,
        "archetype_label": archetype_label,
        "one_liner": one_liner,
        "intro": intro,
        "personality": personality,
    }


@router.get("/{character_id}/profile")
async def get_character_profile(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Public-facing character profile for the discovery / profile page.

    Readable for:
    - the viewer's own UGC (any visibility / review state), and
    - any ``public`` OR ``unlisted`` character that is ``approved``.

    ``unlisted`` is the "link-visible" tier: it never appears in browse lists
    (``list_characters`` / ``list_companions`` require ``public``), but anyone
    who holds the direct ``/character/:id`` link can open its profile — and from
    there start a chat — once it has cleared review. ``private`` and un-approved
    characters remain owner-only. Returns only public presentation fields derived
    from the Soul Spec / draft; internal persona (core_wound / core_fear / …) is
    never included (see ``_derive_profile_presentation``).
    """
    uid = uuid.UUID(current_user.user_id)

    char_result = await db.execute(
        text(
            """
            SELECT id, owner_user_id, visibility, status, has_voice, tags, cover_url
            FROM characters
            WHERE id = :cid AND status = 'active'
              AND (
                    owner_user_id = :uid
                    OR (visibility IN ('public', 'unlisted') AND review_status = 'approved')
              )
            """
        ),
        {"cid": character_id, "uid": uid},
    )
    row = char_result.mappings().fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"角色不存在或不可见: {character_id}")

    spec_result = await db.execute(
        text(
            """
            SELECT source, spec, draft
            FROM soul_specs
            WHERE character_id = :cid AND status = 'active'
            ORDER BY created_at DESC LIMIT 1
            """
        ),
        {"cid": character_id},
    )
    spec_row = spec_result.mappings().fetchone()
    spec_json = _coerce_json(spec_row["spec"]) if spec_row else {}
    draft_json = _coerce_json(spec_row["draft"]) if spec_row else {}

    is_builtin = row["owner_user_id"] is None
    presentation = _derive_profile_presentation(spec_json, draft_json, is_builtin=is_builtin)

    creator_name = None
    if not is_builtin:
        cr = await db.execute(
            text("SELECT display_name FROM users WHERE id = :oid"),
            {"oid": row["owner_user_id"]},
        )
        creator_name = cr.scalar_one_or_none()

    return {
        "id": row["id"],
        "display_name": get_display_name(character_id),
        "creator_name": creator_name,
        "avatar_url": draft_json.get("avatar_url"),
        "cover_url": row["cover_url"],
        "age_range": draft_json.get("age_range"),
        "tags": coerce_tags(row["tags"]),
        "source": "built_in" if is_builtin else "user_created",
        "has_voice": bool(row["has_voice"]),
        **presentation,
    }


@router.get("/{character_id}/settings")
async def get_character_settings(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get per-character settings (voice toggle)."""
    await _require_known_character(character_id, db)
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

    Returns 409 when voice_enabled=True is requested but THIS user has no
    voice this character can speak in.
    """
    await _require_known_character(character_id, db)
    uid = uuid.UUID(current_user.user_id)

    if body.voice_enabled:
        # Resolve per-user, not the global characters.has_voice flag: a personal
        # override (non-owner picks a preset for an imported character) makes a
        # ready character_voices row but never sets the global flag — the old
        # check 409'd right after the user configured a voice (the "配好音色后
        # 开语音仍提示未配置并跳回配置页" bug). get_voice_config mirrors exactly
        # what the config sheet's has_voice reads, so the two can't disagree.
        from heart.ss08_voice.voice_catalog import VOICE_CATALOG
        from heart.ss08_voice.voice_resolver import get_voice_config

        config = await get_voice_config(character_id, db, user_id=uid)
        has_voice = (config is not None and config["clone_status"] == "ready") or (
            character_id in VOICE_CATALOG
        )
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


@router.patch("/{character_id}/voice-provider")
async def set_voice_provider(
    character_id: str,
    body: VoiceProviderUpdate,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Switch which TTS engine (日常语音 mimo / 真人语音 fish) this user hears.

    Per-user, per-character: writes ``user_character_settings.voice_provider``.
    Fish is gated to paid tiers; the target provider must already have a ready
    voice row (both are pre-cloned for built-in rin/dorothy), so switching is
    instant — no re-configuration.
    """
    await _require_known_character(character_id, db)
    uid = uuid.UUID(current_user.user_id)

    provider = body.provider
    if provider not in ("mimo", "fish"):
        raise HTTPException(status_code=400, detail="provider 只能是 mimo 或 fish")

    # Tier gate — 真人语音 (Fish) requires paid membership.
    from heart.membership import TtsForbiddenError, assert_tts_allowed, get_effective_tier

    tier = await get_effective_tier(db, uid)
    try:
        assert_tts_allowed(tier, provider)
    except TtsForbiddenError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": "tier_forbidden", "provider": e.provider, "tier": e.tier},
        ) from e

    # The target engine must have a ready voice for this character — scoped to
    # this user so their personal override counts (and others' never do).
    from heart.ss08_voice.voice_resolver import list_ready_voice_providers

    ready = await list_ready_voice_providers(character_id, db, uid)
    if provider not in ready:
        raise HTTPException(status_code=409, detail="该角色暂未配置该语音，请先配置音色")

    await db.execute(
        text("""
            INSERT INTO user_character_settings (user_id, character_id, voice_provider, updated_at)
            VALUES (:uid, :cid, :prov, NOW())
            ON CONFLICT (user_id, character_id)
            DO UPDATE SET voice_provider = :prov, updated_at = NOW()
        """),
        {"uid": uid, "cid": character_id, "prov": provider},
    )
    await db.commit()
    logger.info(
        "character_voice_provider_updated",
        user_id=str(uid),
        character_id=character_id,
        voice_provider=provider,
    )
    return {"voice_provider": provider}


@router.post("/{character_id}/clear-conversations")
async def clear_character_conversations(
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Clear persisted chat messages for one character only."""
    await _require_known_character(character_id, db)
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


def _attach_draft(spec: object, draft_dict: dict) -> None:
    """Attach the raw draft dict onto a SoulSpec as ``_draft`` (SimpleNamespace).

    Mirrors ``registry.load_db_overlay`` so a hot-loaded UGC spec exposes the
    same authored fields (opening / persona / backstory / tags / greeting_style)
    that ss10_opening reads. Uses ``object.__setattr__`` to bypass the SoulSpec
    pydantic ``extra="forbid"`` guard.
    """
    from types import SimpleNamespace

    try:
        object.__setattr__(spec, "_draft", SimpleNamespace(**draft_dict))
    except Exception as exc:  # noqa: BLE001 — never block create/update on this
        logger.warning("attach_draft_failed", error=str(exc))


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

    # CharacterDraft.avatar_url is capped at 200 000 chars.  A base64 data URL
    # of a 130 KB image already reaches ~180 000 chars, so if we're going to
    # embed the image inline we have to refuse anything larger than that.
    # The frontend now compresses to 256×256 WebP (~40–60 KB) before uploading,
    # so this cap only triggers when someone bypasses that path.
    data_url_raw_limit = 140 * 1024  # ~190 000 chars after base64

    avatar_url: str
    if is_s3_configured():
        try:
            avatar_url = await s3_upload(f"character-{uid.hex[:8]}", data, file.content_type)
        except Exception as exc:
            logger.warning("character_avatar_s3_failed", error=str(exc))
            if len(data) > data_url_raw_limit:
                raise HTTPException(
                    status_code=413,
                    detail="头像文件过大，请上传更小的图片",
                ) from exc
            import base64

            b64 = base64.b64encode(data).decode()
            avatar_url = f"data:{file.content_type};base64,{b64}"
    else:
        if len(data) > data_url_raw_limit:
            raise HTTPException(
                status_code=413,
                detail="头像文件过大，请上传更小的图片（未配置对象存储时上限约 140KB）",
            )
        import base64

        b64 = base64.b64encode(data).decode()
        avatar_url = f"data:{file.content_type};base64,{b64}"

    return {"avatar_url": avatar_url}


@router.post("/cover")
async def upload_character_cover(
    request: Request,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    """Upload a character portrait cover. Returns a cover_url for use in CharacterDraft.

    **S3-only, no base64 fallback.** Covers are tall portrait images (used both in
    the discovery grid and as the full-screen chat background); a real cover is far
    too large to inline into a DB row, and inlining base64 is exactly what caused
    the 探索页 OOM (commit d3922fb). If object storage is unavailable we fail loudly
    with 413 rather than silently bloating the row. The frontend compresses to
    ≤800px WebP (~<200KB) before upload; the 8MB hard cap only guards direct callers.
    """
    uid = uuid.UUID(current_user.user_id)

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="仅支持 jpg/png/webp 格式")

    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="封面文件不能超过 8MB")

    from heart.infra.storage import is_s3_configured
    from heart.infra.storage import upload_cover as s3_upload_cover

    if not is_s3_configured():
        raise HTTPException(
            status_code=413,
            detail="对象存储未配置，封面暂不可用（封面不做 base64 内联，避免内存问题）",
        )
    try:
        cover_url = await s3_upload_cover(f"character-{uid.hex[:8]}", data, file.content_type)
    except Exception as exc:
        logger.warning("character_cover_s3_failed", error=str(exc))
        raise HTTPException(status_code=413, detail="封面上传失败，请稍后再试") from exc

    return {"cover_url": cover_url}


@router.post("")
async def create_character(
    draft: CharacterDraft,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new UGC character and hot-load it into the registry.

    Visibility is taken from the draft (public/unlisted/private).
    public/unlisted characters enter the review pipeline immediately;
    private characters are live immediately with no review and no reward.
    Character creation is no longer capped per user.
    """
    from heart.ss01_soul.content_store import upsert_content
    from heart.ss01_soul.reload import reload_character
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
    from heart.ss01_soul.spec_store import insert_spec

    uid = uuid.UUID(current_user.user_id)

    # Mint id
    name_zh = draft.display_name.zh
    character_id = _mint_character_id(name_zh, uid)

    # Build spec
    spec = build_soul_spec_from_draft(draft, character_id=character_id)

    # Determine initial review state based on visibility.
    vis = draft.visibility or "private"
    if vis in ("public", "unlisted"):
        initial_review_status = "pending"
        submitted_at_sql = "NOW()"
    else:
        initial_review_status = "not_required"
        submitted_at_sql = "NULL"

    # Persist — single transaction
    spec_dict = spec.model_dump(mode="json")
    draft_dict = draft.model_dump(mode="json")
    content = _derive_content(draft, character_id)

    await db.execute(
        text(
            "INSERT INTO characters"
            " (id, owner_user_id, visibility, status, soul_spec_version,"
            "  tags, cover_url, review_status, submitted_at)"
            " VALUES (:id, :uid, :vis, 'active', :ver,"
            "  CAST(:tags AS jsonb), :cover, :review_status, " + submitted_at_sql + ")"
        ),
        {
            "id": character_id,
            "uid": uid,
            "vis": vis,
            "ver": spec.spec_version,
            "tags": json.dumps(draft.tags or []),
            "cover": draft.cover_url,
            "review_status": initial_review_status,
        },
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

    # Attach the raw draft so the opening generator can read the authored
    # opening (spec._draft.opening) on the very first chat entry — without this,
    # reload_character registers a spec with no _draft and the authored opening
    # would only surface after a restart re-ran load_db_overlay.
    _attach_draft(spec, draft_dict)

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


class OpeningPreviewRequest(BaseModel):
    """Draft fields needed to generate a first-encounter opening preview.

    Deliberately loose — the creator has not saved the character yet, so we
    accept whatever they've typed so far. Only persona is truly required for a
    usable scene.
    """

    display_name: str = ""
    persona: str
    backstory: str | None = None
    tags: list[str] = []
    greeting_style: str = "warm"


@router.post("/opening-preview")
async def preview_opening(
    body: OpeningPreviewRequest,
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    """Generate a first-encounter opening draft with the MAIN model (creator-facing).

    Returns the text for the creator to accept or edit — it is NOT persisted and
    creates no character. The saved opening is later played back verbatim on
    first chat entry with zero runtime LLM calls (ss10_opening.generator). Using
    the main (high-quality) model here is intentional: this is authoring UI, run
    once per creation, not the per-user hot path.
    """
    persona = (body.persona or "").strip()
    if len(persona) < 20:
        raise HTTPException(status_code=422, detail="请先填写人设（至少 20 字）再生成开场")

    from heart.api.wiring import get_model_router
    from heart.ss10_opening.prompt_builder import build_opening_prompt

    router = get_model_router()
    if router is None:
        raise HTTPException(
            status_code=503,
            detail="AI 生成暂不可用，请手动填写开场白",
        )

    messages = build_opening_prompt(
        display_name=(body.display_name or "").strip() or "这个角色",
        persona=persona,
        backstory=(body.backstory or "").strip() or None,
        tags=list(body.tags or []),
        greeting_style=body.greeting_style or "warm",
    )

    try:
        text_out = await router.call_main(
            messages=messages,
            temperature=0.9,
            max_tokens=600,
            agent_name="OpeningPreview.ugc",
        )
    except Exception as exc:
        logger.warning("opening_preview_failed", error=str(exc))
        raise HTTPException(status_code=502, detail="AI 生成失败，请重试或手动填写") from exc

    text_out = (text_out or "").strip()
    if not text_out:
        raise HTTPException(status_code=502, detail="AI 生成为空，请重试或手动填写")

    return {"opening": text_out}


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
) -> dict:
    """Edit a UGC character — bumps semver minor, supersedes old spec."""
    from heart.ss01_soul.content_store import upsert_content
    from heart.ss01_soul.reload import reload_character
    from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
    from heart.ss01_soul.spec_store import insert_spec, supersede_active

    uid = uuid.UUID(current_user.user_id)
    row = await _require_owner(character_id, uid, db)

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
        text(
            "UPDATE characters"
            " SET soul_spec_version = :ver, tags = CAST(:tags AS jsonb), cover_url = :cover"
            " WHERE id = :cid"
        ),
        {
            "ver": new_ver,
            "cid": character_id,
            "tags": json.dumps(draft.tags or []),
            "cover": draft.cover_url,
        },
    )
    await upsert_content(db, character_id=character_id, **content)
    await db.commit()

    # See create_character: keep _draft on the hot-loaded spec so an edited
    # opening plays back immediately without a restart.
    _attach_draft(spec, draft_dict)

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
    """Update a UGC character's visibility (public|unlisted|private).

    Switching to public/unlisted enters the review pipeline (pending).
    Switching to private exits the pipeline (not_required) and clears any
    pending/rejected state so the character becomes live immediately.
    """
    uid = uuid.UUID(current_user.user_id)
    if body.visibility not in ("public", "unlisted", "private"):
        raise HTTPException(status_code=422, detail="visibility 必须是 public / unlisted / private")
    await _require_owner(character_id, uid, db)

    if body.visibility in ("public", "unlisted"):
        await db.execute(
            text(
                """
                UPDATE characters
                   SET visibility      = :vis,
                       review_status   = CASE
                                           WHEN review_status = 'approved' THEN 'approved'
                                           ELSE 'pending'
                                         END,
                       submitted_at    = CASE
                                           WHEN review_status NOT IN ('approved','pending')
                                           THEN NOW()
                                           ELSE submitted_at
                                         END,
                       result_ack_at   = NULL
                 WHERE id = :cid
                """
            ),
            {"vis": body.visibility, "cid": character_id},
        )
    else:
        # Switching to private: exit pipeline, go live immediately.
        await db.execute(
            text(
                "UPDATE characters SET visibility = :vis, review_status = 'not_required' WHERE id = :cid"
            ),
            {"vis": body.visibility, "cid": character_id},
        )

    await db.commit()
    logger.info("ugc_visibility_updated", character_id=character_id, visibility=body.visibility)
    return {"id": character_id, "visibility": body.visibility}


class ReviewAck(BaseModel):
    character_id: str


@router.get("/review/updates")
async def get_review_updates(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Review status of the caller's own UGC characters + reward context.

    Drives two client popups:
      - Result notification: any row with ``needs_ack`` (a terminal
        approved/rejected result the user hasn't confirmed yet).
      - Daily incentive: when ``approved_count == 0`` the client shows a
        once-per-day explainer about the publish reward.
    """
    uid = uuid.UUID(current_user.user_id)
    result = await db.execute(
        text(
            """
            SELECT id, visibility, review_status, review_reason,
                   submitted_at, reviewed_at,
                   (review_status IN ('approved','rejected')
                    AND result_ack_at IS NULL) AS needs_ack
            FROM characters
            WHERE owner_user_id = :uid AND status = 'active'
            ORDER BY reviewed_at DESC NULLS LAST, submitted_at DESC NULLS LAST
            """
        ),
        {"uid": uid},
    )
    items = []
    approved_count = 0
    for row in result.mappings():
        if row["review_status"] == "approved":
            approved_count += 1
        items.append(
            {
                "id": row["id"],
                "display_name": get_display_name(row["id"]),
                "visibility": row["visibility"],
                "review_status": row["review_status"],
                "review_reason": row["review_reason"],
                "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
                "reviewed_at": row["reviewed_at"].isoformat() if row["reviewed_at"] else None,
                "needs_ack": bool(row["needs_ack"]),
            }
        )
    return {"characters": items, "approved_count": approved_count}


@router.post("/review/ack")
async def ack_review_result(
    body: ReviewAck,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a review result as seen so its notification popup stops firing."""
    uid = uuid.UUID(current_user.user_id)
    await db.execute(
        text(
            """
            UPDATE characters SET result_ack_at = NOW()
            WHERE id = :cid AND owner_user_id = :uid
            """
        ),
        {"cid": body.character_id, "uid": uid},
    )
    await db.commit()
    return {"ok": True}


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
