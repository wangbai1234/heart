"""Companions aggregation API — /api/companions

The Character page ("羁绊中心" / bond center) needs, for every character the
user can see, a single view that fuses four otherwise-separate data sources:

  1. characters          — catalog row (display name, avatar, built-in vs UGC)
  2. relationship_states — current stage + intimacy (SS04)
  3. chat_messages       — last message line + server-side unread count
  4. proactive_messages  — whether the character is actively reaching out

Rather than make the frontend fan out to 4+ endpoints (and N calls for the
per-character relationship endpoint), this route does the join server-side in a
fixed number of batched queries and returns a ready-to-render list.

Design notes
------------
- The RAW relationship stage (uppercase enum, e.g. ``ROMANTIC_INTEREST``) and
  the RAW intimacy float (0..1) are returned. Label mapping (初遇/靠近/心动/…
  and cold_war → 闹别扭) and percent formatting live on the frontend so there is
  a single source of truth for presentation.
- ``companion_status`` is always ``"companioned"`` in V1. The
  locked/encountered states belong to the story-encounter unlock flow (a later
  wave); the field exists now so the frontend view-model is stable.
- ``source`` is ``"built_in"`` or ``"user_created"`` in V1. ``imported`` /
  ``story_encounter`` have no backing data yet.
- The list is sorted by the bond-center rule so the frontend can render item[0]
  as the "今日陪伴" hero card and the rest as the gallery.
"""

from __future__ import annotations

import json
import uuid
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.rate_limit import limiter
from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss01_soul.character_catalog import (
    CharacterRow,
    build_catalog_entries,
    coerce_tags,
    display_name_from_spec,
)
from heart.ss04_relationship.stage_engine import STAGE_ORDER, RelationshipStage

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/companions", tags=["companions"])


def _stage_rank(raw_stage: str) -> int:
    """RAW stage enum string → STAGE_ORDER rank; unknown/cold_war → -1 (ineligible)."""
    try:
        return STAGE_ORDER[RelationshipStage(raw_stage)]
    except (ValueError, KeyError):
        return -1


def _pick_story_hook(hooks: list[dict], stage_raw: str, intimacy: float) -> dict | None:
    """Highest-threshold hook the user qualifies for (stage rank AND intimacy met).

    cold_war ranks -1, so a hook with any real ``trigger_stage_min`` is never
    eligible mid-conflict. Returns the frontend-facing card payload, or None.
    """
    user_rank = _stage_rank(stage_raw)
    for hook in sorted(
        hooks,
        key=lambda h: (_stage_rank(h["trigger_stage_min"]), h["trigger_intimacy_min"]),
        reverse=True,
    ):
        hook_rank = _stage_rank(hook["trigger_stage_min"])
        if user_rank >= hook_rank >= 0 and intimacy >= hook["trigger_intimacy_min"]:
            return {
                "scenario_id": hook["scenario_id"],
                "invite_title": hook["invite_title"],
                "invite_copy": hook["invite_copy"],
                "cta_label": hook["cta_label"],
                "cooldown_hours": hook["cooldown_hours"],
            }
    return None


def sort_companions(companions: list[dict]) -> list[dict]:
    """Order companions by the bond-center priority rule (in place, returns same list).

    Priority (most significant first):
      1. Active companions — those with unread messages OR a pending proactive
         message — float to the top.
      2. Most recent interaction next (``last_message_at`` ISO string, newest first;
         missing → sinks within its rank).
      3. Higher intimacy as the final tie-break.

    Implemented as a stable multi-pass sort (least→most significant), which lets
    ``build_catalog_entries``' original built-in-first/id ordering survive as the
    ultimate tie-break for otherwise-equal companions.
    """
    companions.sort(key=lambda c: c["intimacy"], reverse=True)
    companions.sort(key=lambda c: c["last_message_at"] or "", reverse=True)
    companions.sort(key=lambda c: 0 if (c["unread_count"] > 0 or c["has_proactive"]) else 1)
    return companions


@router.get("")
async def list_companions(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the fused companion view for every character visible to the user.

    Built-ins + the user's own UGC characters, each enriched with relationship
    stage/intimacy, last message + unread count, and proactive status. Sorted by
    the bond-center priority rule (unread/proactive → recent → intimacy).
    """
    uid = uuid.UUID(current_user.user_id)

    # --- 1. Visible catalog rows (built-ins + own UGC + public-approved), same
    #        rule as GET /api/characters. The review_status gate is REQUIRED:
    #        a public row still pending/rejected must not leak to non-owners, and
    #        it must be selected so build_catalog_entries' visible_to() sees the
    #        real value (else it defaults to 'not_required' and approved public
    #        UGC never shows here).
    char_result = await db.execute(
        text(
            """
            SELECT id, owner_user_id, visibility, status, has_voice,
                   tags, cover_url, review_status
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
    raw_rows = list(char_result.mappings())
    rows = [
        CharacterRow(
            id=r["id"],
            owner_user_id=r["owner_user_id"],
            visibility=r["visibility"],
            status=r["status"],
            review_status=r.get("review_status", "not_required"),
            tags=coerce_tags(r.get("tags")),
            cover_url=r.get("cover_url"),
        )
        for r in raw_rows
    ]
    has_voice_map = {r["id"]: bool(r.get("has_voice", False)) for r in raw_rows}

    # Avatar URLs for UGC characters live in soul_specs.draft
    avatar_urls: dict[str, str | None] = {}
    display_names: dict[str, str | None] = {}
    ugc_ids = [r.id for r in rows if r.owner_user_id is not None]
    if ugc_ids:
        avatar_result = await db.execute(
            text(
                """
                SELECT character_id, spec, draft->>'avatar_url' AS avatar_url
                FROM soul_specs
                WHERE character_id = ANY(:ids) AND status = 'active'
                """
            ),
            {"ids": ugc_ids},
        )
        for r in avatar_result:
            display_names[r.character_id] = display_name_from_spec(r.spec, r.character_id)
            if r.avatar_url:
                avatar_urls[r.character_id] = r.avatar_url

    entries = build_catalog_entries(rows, uid, avatar_urls, display_names=display_names)
    if not entries:
        return {"companions": []}

    visible_ids = [e.id for e in entries]

    # --- 2. Relationship states (batch, one query for all visible characters)
    rel_map: dict[str, dict] = {}
    rel_result = await db.execute(
        text(
            """
            SELECT character_id, current_stage, intimacy_level, last_interaction_at
            FROM relationship_states
            WHERE user_id = :uid AND character_id = ANY(:ids)
            """
        ),
        {"uid": uid, "ids": visible_ids},
    )
    for r in rel_result.fetchall():
        rel_map[r.character_id] = {
            "stage": (r.current_stage or "STRANGER"),
            "intimacy": float(r.intimacy_level or 0.0),
            "last_interaction_at": r.last_interaction_at,
        }

    # --- 3. Last message + unread count (reuse the inbox-summary shape, batched)
    inbox_map: dict[str, dict] = {}
    inbox_result = await db.execute(
        text(
            """
            SELECT
                m.character_id,
                m.content,
                m.modality,
                m.created_at,
                (
                    SELECT COUNT(*)
                    FROM chat_messages cm
                    WHERE cm.user_id      = :uid
                      AND cm.character_id = m.character_id
                      AND cm.role         = 'assistant'
                      AND cm.rewound_at IS NULL
                      AND cm.created_at   > COALESCE(rs.last_read_at, '-infinity'::timestamptz)
                ) AS unread_count
            FROM (
                SELECT DISTINCT ON (character_id)
                    character_id, content, modality, created_at
                FROM chat_messages
                WHERE user_id = :uid
                  AND rewound_at IS NULL
                ORDER BY character_id, created_at DESC
            ) m
            LEFT JOIN user_character_read_state rs
                ON rs.user_id = :uid AND rs.character_id = m.character_id
            """
        ),
        {"uid": uid},
    )
    for r in inbox_result.fetchall():
        inbox_map[r.character_id] = {
            "last_message_text": r.content or "",
            "last_message_at": r.created_at,
            "modality": r.modality,
            "unread_count": int(r.unread_count or 0),
        }

    # --- 4. Proactive: which characters have undelivered messages waiting (batch)
    proactive_ids: set[str] = set()
    proactive_result = await db.execute(
        text(
            """
            SELECT DISTINCT character_id
            FROM proactive_messages
            WHERE user_id = :uid AND delivered = false
            """
        ),
        {"uid": uid},
    )
    for r in proactive_result.fetchall():
        proactive_ids.add(r.character_id)

    # --- 4.5. Story hooks: DISABLED (产品决策 2026-07-24)
    # 角色↔剧情关联功能已暂停：角色性格无法代入 GM 驱动的剧情，语义不成立。
    # 查询与 _pick_story_hook 逻辑保留在代码里（helper + migration 047 + DTO 字段）
    # 便于日后恢复；此处直接不查，hooks_map 恒空 → _pick_story_hook 恒返回 None
    # → available_story_hook 恒为 None，前端卡片不渲染。
    # 恢复方法：取消下方查询的注释即可，第 5 步的 _pick_story_hook 调用无需改动。
    hooks_map: dict[str, list[dict]] = {}
    # hooks_result = await db.execute(
    #     text(
    #         """
    #         SELECT h.character_id, h.scenario_id, h.trigger_stage_min,
    #                h.trigger_intimacy_min, h.cooldown_hours,
    #                h.invite_title, h.invite_copy, h.cta_label
    #         FROM character_story_hooks h
    #         JOIN story_scenarios s ON s.id = h.scenario_id
    #         WHERE h.enabled = true
    #           AND s.status = 'published'
    #           AND h.character_id = ANY(:ids)
    #         """
    #     ),
    #     {"ids": visible_ids},
    # )
    # for r in hooks_result.fetchall():
    #     hooks_map.setdefault(r.character_id, []).append(
    #         {
    #             "scenario_id": str(r.scenario_id),
    #             "trigger_stage_min": r.trigger_stage_min,
    #             "trigger_intimacy_min": float(r.trigger_intimacy_min or 0.0),
    #             "cooldown_hours": int(r.cooldown_hours or 0),
    #             "invite_title": r.invite_title or "",
    #             "invite_copy": r.invite_copy or "",
    #             "cta_label": r.cta_label or "进入剧情",
    #         }
    #     )

    # --- 5. Merge into the companion view-model
    companions = []
    for e in entries:
        rel = rel_map.get(e.id)
        inbox = inbox_map.get(e.id)
        last_at = inbox["last_message_at"] if inbox else None

        # Story invitation: highest-threshold hook this user currently qualifies for.
        available_story_hook = _pick_story_hook(
            hooks_map.get(e.id, []),
            rel["stage"] if rel else "STRANGER",
            rel["intimacy"] if rel else 0.0,
        )

        companions.append(
            {
                "character_id": e.id,
                "display_name": e.display_name,
                "avatar_url": e.avatar_url,
                "cover_url": e.cover_url,
                "tags": e.tags,
                "source": "built_in" if e.is_builtin else "user_created",
                "is_owner": e.is_owner,
                "is_builtin": e.is_builtin,
                # Visibility label (公开/不公开/私密) — the bond-center card renders this.
                # Carried on the catalog entry but previously dropped from the payload,
                # which left the frontend reading an undefined `visibility`.
                "visibility": e.visibility,
                "has_voice": has_voice_map.get(e.id, False),
                # V1: everyone is a full companion; encounter/lock flow is a later wave.
                "companion_status": "companioned",
                # RAW values — frontend owns label + percent mapping.
                "relationship_stage": (rel["stage"] if rel else "STRANGER"),
                "intimacy": (rel["intimacy"] if rel else 0.0),
                "last_message_text": inbox["last_message_text"] if inbox else "",
                "last_message_at": last_at.isoformat() if last_at else None,
                "last_message_modality": inbox["modality"] if inbox else None,
                "unread_count": inbox["unread_count"] if inbox else 0,
                "has_proactive": e.id in proactive_ids,
                # Wave 3: 剧情邀约. null unless the user qualifies for a hook.
                "available_story_hook": available_story_hook,
            }
        )

    # --- 6. Order by the bond-center priority rule (see sort_companions).
    sort_companions(companions)

    return {"companions": companions}


@router.get("/{character_id}/bond")
@limiter.limit("60/minute")
async def get_shared_memories(
    request: Request,
    character_id: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Only the authenticated reader can inspect their own relationship and memories."""
    params = {"uid": uuid.UUID(current_user.user_id), "cid": character_id}
    count = await db.execute(
        text(
            "SELECT COUNT(*) AS message_count, COUNT(*) FILTER (WHERE role='user') AS user_message_count, COUNT(DISTINCT created_at::date) AS active_days, MIN(created_at) AS first_message_at FROM chat_messages WHERE user_id=:uid AND character_id=:cid"
        ),
        params,
    )
    activity = dict(count.mappings().one())
    relation = await db.execute(
        text(
            "SELECT current_stage, intimacy_level FROM relationship_states WHERE user_id=:uid AND character_id=:cid"
        ),
        params,
    )
    state = relation.mappings().first()
    emotion = await db.execute(
        text(
            "SELECT vad_valence, vad_arousal FROM emotion_states WHERE user_id=:uid AND character_id=:cid"
        ),
        params,
    )
    feeling = emotion.mappings().first()
    mood = _memory_mood(feeling) if feeling else "unknown"
    changes = await db.execute(
        text(
            "SELECT event_id, event_type, payload, created_at FROM relationship_events WHERE user_id=:uid AND character_id=:cid AND event_type IN ('stage_progression','stage_regression') ORDER BY created_at DESC LIMIT 20"
        ),
        params,
    )
    emotions = await db.execute(
        text(
            "SELECT event_id,vad_after,created_at FROM emotion_events WHERE user_id=:uid AND character_id=:cid AND vad_after IS NOT NULL ORDER BY created_at DESC LIMIT 20"
        ),
        params,
    )
    facts = await db.execute(
        text(
            "SELECT id, literal_text AS content, predicate AS category, updated_at FROM fact_nodes WHERE user_id=:uid AND character_id=:cid AND NOT do_not_recall AND is_active AND superseded_by_id IS NULL AND promoted_to_l4_at IS NULL ORDER BY importance DESC, updated_at DESC LIMIT 100"
        ),
        params,
    )
    identities = await db.execute(
        text(
            "SELECT id, value AS content, category, created_at AS updated_at FROM identity_memories WHERE user_id=:uid AND character_id=:cid AND NOT user_initiated_forget AND demoted_at IS NULL ORDER BY created_at DESC LIMIT 100"
        ),
        params,
    )
    memories = [
        {**dict(row), "id": str(row["id"]), "tier": tier}
        for tier, result in (("L3", facts), ("L4", identities))
        for row in result.mappings()
    ]
    return {
        **activity,
        "stage": state["current_stage"] if state else "stranger",
        "intimacy": state["intimacy_level"] if state else 0,
        "emotion": mood,
        "memories": memories,
        "relationship_history": [
            {
                "id": str(r.event_id),
                "from_stage": r.payload.get("from_stage"),
                "to_stage": r.payload.get("to_stage"),
                "at": r.created_at,
            }
            for r in changes
        ],
        "emotion_history": [
            {"id": str(r.event_id), "emotion": _memory_mood(r.vad_after), "at": r.created_at}
            for r in emotions
        ],
    }


def _memory_mood(vad) -> str:
    valence = vad.get("vad_valence", vad.get("valence", vad.get("v", 0)))
    arousal = vad.get("vad_arousal", vad.get("arousal", vad.get("a", 0)))
    return (
        "warm"
        if valence > 0.25
        else "low"
        if valence < -0.25
        else "excited"
        if arousal > 0.65
        else "calm"
    )


class MemoryAddition(BaseModel):
    id: uuid.UUID
    tier: Literal["L3", "L4"]
    content: str = Field(min_length=1, max_length=2000)
    confirm_identity: bool = False


@router.post("/{character_id}/memories", status_code=201)
@limiter.limit("20/minute")
async def add_shared_memory(
    request: Request,
    character_id: str,
    body: MemoryAddition,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """User-authored notes, never invented chat evidence or automatic promotion."""
    uid = uuid.UUID(current_user.user_id)
    content = body.content.strip()
    if not content:
        raise HTTPException(422, "empty_memory")
    if body.tier == "L4" and not body.confirm_identity:
        raise HTTPException(422, "identity_confirmation_required")
    visible = await db.execute(
        text(
            "SELECT id FROM characters WHERE id=:cid AND status='active' AND (owner_user_id=:uid OR (visibility IN ('public','unlisted') AND review_status='approved'))"
        ),
        {"uid": uid, "cid": character_id},
    )
    if not visible.first():
        raise HTTPException(404, "character_not_found")
    # Serialize explicit additions per account and make retries safe with the supplied UUID.
    await db.execute(text("SELECT id FROM users WHERE id=:uid FOR UPDATE"), {"uid": uid})
    table = "fact_nodes" if body.tier == "L3" else "identity_memories"
    field = "literal_text" if body.tier == "L3" else "value"
    params = {"uid": uid, "cid": character_id, "id": body.id, "content": content}
    existing = await db.execute(
        text(
            f"SELECT {field} AS content FROM {table} WHERE id=:id AND user_id=:uid AND character_id=:cid"
        ),
        params,
    )
    row = existing.mappings().first()
    if row:
        if row["content"] != content:
            raise HTTPException(409, "memory_changed_reload")
        return {"id": str(body.id), "tier": body.tier, "content": content}
    size = await db.execute(
        text(f"SELECT COUNT(*) FROM {table} WHERE user_id=:uid AND character_id=:cid"), params
    )
    if size.scalar_one() >= 1000:
        raise HTTPException(422, "memory_limit_reached")
    if body.tier == "L3":
        await db.execute(
            text(
                "INSERT INTO fact_nodes (id,user_id,character_id,predicate,subject,object,literal_text,raw_evidence,confidence,confidence_ewma,emotional_charge,importance,state,is_corrected,reconstruction_hints) VALUES (:id,:uid,:cid,'user_note','user',:content,:content,:content,1,1,0,0.8,'vivid',TRUE,'{\"origin\":\"user_authored\"}'::jsonb)"
            ),
            params,
        )
    else:
        await db.execute(
            text(
                "INSERT INTO identity_memories (id,user_id,character_id,category,key,value,disclosed_at,sacred_reason,significance_score,promotion_trigger,reconstruction_hints,audit_log) VALUES (:id,:uid,:cid,'identity',:key,:content,NOW(),'Explicitly pinned by user',0.85,'user_authored','{\"origin\":\"user_authored\"}'::jsonb,CAST(:entry AS jsonb))"
            ),
            {
                **params,
                "key": f"user_note_{body.id}",
                "entry": json.dumps([{"actor": "user", "operation": "create", "after": content}]),
            },
        )
    await db.execute(
        text(
            "INSERT INTO memory_audit_log (id,user_id,session_id,tier,operation,entity_type,entity_ref,new_value,actor,reasoning) VALUES (:audit,:uid,:op,:tier,'create',:entity,:ref,CAST(:new AS jsonb),'user','Explicit user-authored shared memory; no chat evidence claimed')"
        ),
        {
            "audit": uuid.uuid4(),
            "uid": uid,
            "op": uuid.uuid4(),
            "tier": body.tier,
            "entity": "fact_node" if body.tier == "L3" else "identity_memory",
            "ref": str(body.id),
            "new": json.dumps(
                {"character_id": character_id, "content": content, "origin": "user_authored"}
            ),
        },
    )
    await db.commit()
    return {"id": str(body.id), "tier": body.tier, "content": content}


class MemoryCorrection(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    expected_content: str = Field(max_length=20000)
    confirm_identity: bool = False


@router.patch("/{character_id}/memories/{tier}/{memory_id}")
@limiter.limit("20/minute")
async def correct_shared_memory(
    request: Request,
    character_id: str,
    tier: Literal["L3", "L4"],
    memory_id: uuid.UUID,
    body: MemoryCorrection,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Explicit, audited user correction; no new identity promotion or hard deletion."""
    if tier == "L4" and not body.confirm_identity:
        raise HTTPException(422, "identity_confirmation_required")
    content = body.content.strip()
    if not content:
        raise HTTPException(422, "empty_memory")
    params = {
        "uid": uuid.UUID(current_user.user_id),
        "cid": character_id,
        "id": memory_id,
        "content": content,
    }
    if tier == "L3":
        query = "SELECT literal_text AS content FROM fact_nodes WHERE id=:id AND user_id=:uid AND character_id=:cid AND NOT do_not_recall AND is_active AND superseded_by_id IS NULL AND promoted_to_l4_at IS NULL FOR UPDATE"
    else:
        query = "SELECT value AS content FROM identity_memories WHERE id=:id AND user_id=:uid AND character_id=:cid AND NOT user_initiated_forget AND demoted_at IS NULL FOR UPDATE"
    result = await db.execute(text(query), params)
    old = result.mappings().first()
    if not old:
        raise HTTPException(404, "memory_not_found")
    if old["content"] != body.expected_content:
        raise HTTPException(409, "memory_changed_reload")
    if tier == "L3":
        # Clear the old vector: graph/recency recall sees the corrected text immediately.
        # The existing embedding backfill can regenerate vectors without recalling stale text.
        await db.execute(
            text(
                "UPDATE fact_nodes SET literal_text=:content, object=:content, is_corrected=TRUE, semantic_vector=NULL, reconstruction_hints='{}'::jsonb, updated_at=NOW(), last_confirmed_at=NOW() WHERE id=:id AND user_id=:uid AND character_id=:cid"
            ),
            params,
        )
    else:
        await db.execute(
            text(
                "UPDATE identity_memories SET value=:content, reconstruction_hints='{}'::jsonb, audit_log=audit_log || CAST(:entry AS jsonb) WHERE id=:id AND user_id=:uid AND character_id=:cid"
            ),
            {
                **params,
                "entry": json.dumps(
                    [
                        {
                            "actor": "user",
                            "operation": "correction",
                            "before": old["content"],
                            "after": content,
                        }
                    ]
                ),
            },
        )
        # A promoted L3 source must not reintroduce the contradicted old identity.
        await db.execute(
            text(
                "UPDATE fact_nodes SET literal_text=:content, object=:content, is_corrected=TRUE, semantic_vector=NULL, reconstruction_hints='{}'::jsonb, updated_at=NOW() WHERE user_id=:uid AND character_id=:cid AND id=(SELECT promoted_from_fact_id FROM identity_memories WHERE id=:id AND user_id=:uid AND character_id=:cid)"
            ),
            params,
        )
    await db.execute(
        text(
            "INSERT INTO memory_audit_log (id,user_id,session_id,tier,operation,entity_type,entity_ref,old_value,new_value,actor,reasoning) VALUES (:audit_id,:uid,:operation_id,:tier,'update',:entity_type,:entity_ref,CAST(:old AS jsonb),CAST(:new AS jsonb),'user','Explicit shared-memory correction')"
        ),
        {
            "audit_id": uuid.uuid4(),
            "uid": params["uid"],
            "operation_id": uuid.uuid4(),
            "tier": tier,
            "entity_type": "fact_node" if tier == "L3" else "identity_memory",
            "entity_ref": str(memory_id),
            "old": json.dumps({"content": old["content"]}),
            "new": json.dumps({"content": content, "character_id": character_id}),
        },
    )
    await db.commit()
    return {"id": str(memory_id), "tier": tier, "content": content}
