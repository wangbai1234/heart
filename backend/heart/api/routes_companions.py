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

import uuid

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.api.wiring import get_db
from heart.core.auth import TokenData, get_current_user
from heart.ss01_soul.character_catalog import CharacterRow, build_catalog_entries
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

    # --- 1. Visible catalog rows (built-ins + own UGC), same rule as GET /api/characters
    char_result = await db.execute(
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
    raw_rows = list(char_result.mappings())
    rows = [
        CharacterRow(
            id=r["id"],
            owner_user_id=r["owner_user_id"],
            visibility=r["visibility"],
            status=r["status"],
        )
        for r in raw_rows
    ]
    has_voice_map = {r["id"]: bool(r.get("has_voice", False)) for r in raw_rows}

    # Avatar URLs for UGC characters live in soul_specs.draft
    avatar_urls: dict[str, str | None] = {}
    ugc_ids = [r.id for r in rows if r.owner_user_id is not None]
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
        for r in avatar_result:
            if r.avatar_url:
                avatar_urls[r.character_id] = r.avatar_url

    entries = build_catalog_entries(rows, uid, avatar_urls)
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
                "source": "built_in" if e.is_builtin else "user_created",
                "is_owner": e.is_owner,
                "is_builtin": e.is_builtin,
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
