"""Admin API routes — /api/admin/*

Protected by X-Admin-Key header. Set ADMIN_SECRET_KEY in .env.
Empty ADMIN_SECRET_KEY = all admin endpoints return 503.
"""

from __future__ import annotations

import json
import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.core.config import settings
from heart.membership.service import activate_or_extend
from heart.ss01_soul.character_catalog import coerce_tags

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _coerce_draft(raw: object) -> dict:
    """Normalize a JSONB draft column into a dict (driver may return str or dict)."""
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except (ValueError, TypeError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return raw if isinstance(raw, dict) else {}


def _coerce_str_list(raw: object) -> list[str]:
    """Keep only non-empty string entries from a draft list field."""
    if not isinstance(raw, list):
        return []
    return [s.strip() for s in raw if isinstance(s, str) and s.strip()]


async def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    if not settings.admin_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API disabled"
        )
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


async def _resolve_user(db: AsyncSession, user_id: str | None, email: str | None) -> dict:
    """Resolve a live user by user_id or email (user_id wins if both supplied).

    Returns the user row mapping ({"id": UUID, "email": str}). Raises HTTPException
    (422 for bad input, 404 for missing user).
    """
    if not user_id and not email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id 或 email 必填一个"
        )

    if user_id:
        try:
            uid = uuid.UUID(user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id 格式错误"
            ) from None
        row = await db.execute(
            text("SELECT id, email FROM users WHERE id = :uid AND deleted_at IS NULL"),
            {"uid": uid},
        )
    else:
        assert email is not None  # guaranteed by the guard above; narrows for type-checker
        row = await db.execute(
            text("SELECT id, email FROM users WHERE email = :email AND deleted_at IS NULL"),
            {"email": email.lower().strip()},
        )

    user = row.mappings().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return dict(user)


class GrantCreditsRequest(BaseModel):
    user_id: str | None = Field(None, description="用户 UUID（与 email 二选一）")
    email: str | None = Field(None, description="用户邮箱（与 user_id 二选一）")
    amount: int = Field(..., gt=0, description="增加的积分数（display credits，内部×100 存储）")
    note: str = Field("admin_grant", description="备注，写入 ref_type 日志")
    idempotency_key: str | None = Field(None, description="幂等键，不填则自动生成")


class GrantCreditsResponse(BaseModel):
    ok: bool
    user_id: str
    email: str | None
    credited: int
    new_balance: float


@router.post("/credits/grant", response_model=GrantCreditsResponse)
async def admin_grant_credits(
    body: GrantCreditsRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GrantCreditsResponse:
    """后台直接给指定用户增加积分。

    - 传 user_id 或 email（二选一，同时传以 user_id 为准）
    - amount 单位：display credits（前端显示的数字）
    - 幂等：相同 idempotency_key 重复调用不重复加分
    """
    user = await _resolve_user(db, body.user_id, body.email)
    uid = user["id"]

    amount_fen = body.amount * 100  # display → internal fen
    idem_key = body.idempotency_key or f"admin_grant:{uuid.uuid4()}"

    new_balance_fen = await grant(
        db,
        uid,
        amount_fen,
        idempotency_key=idem_key,
        ref_type=body.note,
    )

    logger.info(
        "admin_credits_granted",
        user_id=str(uid),
        email=user["email"],
        amount=body.amount,
        note=body.note,
        idem_key=idem_key,
    )

    return GrantCreditsResponse(
        ok=True,
        user_id=str(uid),
        email=user["email"],
        credited=body.amount,
        new_balance=new_balance_fen / 100,
    )


class FulfillOrderRequest(BaseModel):
    out_trade_no: str = Field(..., description="爱发电订单号")
    user_id: str = Field(..., description="指定履约的用户 UUID")


@router.post("/afdian/fulfill")
async def admin_fulfill_afdian_order(
    body: FulfillOrderRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """手动将 unmatched 爱发电订单履约给指定用户。

    适用于买家备注里没有有效绑定码、自动履约失败的订单。
    管理员核实身份后调此端点，指定 user_id 直接发放会员/币包。
    """
    from heart.afdian.fulfillment import admin_fulfill_order

    try:
        uid = uuid.UUID(body.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id 格式错误"
        ) from None

    # Verify user exists
    row = await db.execute(
        text("SELECT id FROM users WHERE id = :uid AND deleted_at IS NULL"),
        {"uid": uid},
    )
    if row.fetchone() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    try:
        detail = await admin_fulfill_order(db, body.out_trade_no, uid)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    logger.info(
        "admin_afdian_fulfill",
        out_trade_no=body.out_trade_no,
        user_id=str(uid),
        detail=detail,
    )
    return {"ok": True, "fulfilled": detail, "out_trade_no": body.out_trade_no}


class ReconcileOrderRequest(BaseModel):
    out_trade_no: str = Field(..., description="爱发电订单号")


@router.post("/afdian/reconcile")
async def admin_reconcile_afdian_order(
    body: ReconcileOrderRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """从爱发电 API 拉取订单并重新履约（补偿漏掉的 webhook / 配置前下的单）。

    自动按备注里的绑定码匹配用户。若匹配不到用户或 SKU 未配置，订单会被记录
    但返回 success=False，此时改用 POST /api/admin/afdian/fulfill 指定 user_id。
    """
    from heart.afdian.fulfillment import reconcile_order

    success, message = await reconcile_order(db, body.out_trade_no.strip())
    logger.info(
        "admin_afdian_reconcile",
        out_trade_no=body.out_trade_no,
        success=success,
        message=message,
    )
    return {"ok": success, "message": message, "out_trade_no": body.out_trade_no}


class GrantMembershipRequest(BaseModel):
    user_id: str | None = Field(None, description="用户 UUID（与 email 二选一）")
    email: str | None = Field(None, description="用户邮箱（与 user_id 二选一）")
    tier: str = Field(..., description="会员等级：plus（进阶版）/ immersive（沉浸版）")
    days: int = Field(30, gt=0, le=3650, description="开通/延长天数，默认 30 天")


class GrantMembershipResponse(BaseModel):
    ok: bool
    user_id: str
    email: str | None
    tier: str
    expires_at: str


# Tiers an admin may grant. `free` is excluded — it is the fallback, not a grantable plan.
_GRANTABLE_TIERS = frozenset({"plus", "immersive"})


@router.post("/membership/grant", response_model=GrantMembershipResponse)
async def admin_grant_membership(
    body: GrantMembershipRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GrantMembershipResponse:
    """后台手动将指定用户升级为进阶版 / 沉浸版会员。

    - 传 user_id 或 email（二选一，同时传以 user_id 为准）
    - tier：`plus`（进阶版）或 `immersive`（沉浸版）
    - days：开通/延长天数，默认 30。已有同档会员则从当前到期时间顺延
    - 升级同时按档位发放对应的每月赠币（进阶版 400 / 沉浸版 800）
    """
    tier = body.tier.strip().lower()
    if tier not in _GRANTABLE_TIERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tier 仅支持 plus（进阶版）或 immersive（沉浸版）",
        )

    user = await _resolve_user(db, body.user_id, body.email)
    uid = user["id"]

    # Fresh UUID per call: activate_or_extend derives the monthly-grant
    # idempotency key from granted_by, so a static key would suppress the coin
    # grant on every renewal. Each admin action is a distinct, intentional grant.
    new_expires = await activate_or_extend(
        db, uid, tier, body.days, granted_by=f"admin:{uuid.uuid4()}"
    )

    logger.info(
        "admin_membership_granted",
        user_id=str(uid),
        email=user["email"],
        tier=tier,
        days=body.days,
        expires_at=new_expires.isoformat(),
    )

    return GrantMembershipResponse(
        ok=True,
        user_id=str(uid),
        email=user["email"],
        tier=tier,
        expires_at=new_expires.isoformat(),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Character review (human moderation of UGC public/unlisted characters)
# ─────────────────────────────────────────────────────────────────────────────

# Reward config for approved characters.
_REVIEW_APPROVE_COINS = 100  # display credits per approved character
_MILESTONE_APPROVED_COUNT = 5  # approved characters that unlock the Plus reward
_MILESTONE_PLUS_DAYS = 30  # length of the milestone Plus membership


class RejectRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500, description="驳回原因（用户可见）")


async def _grant_approval_rewards(db: AsyncSession, character_id: str, owner_id: uuid.UUID) -> dict:
    """Grant the per-approval coin reward and, at the 5-approved milestone, Plus.

    - Coins: idempotent per character (idempotency_key = char_review:{cid}).
    - Milestone: guarded by user_reward_milestones so Plus is granted at most once.
    Returns a summary of what was granted (for the admin response / logs).
    """
    # 100 coins, idempotent on character id.
    await grant(
        db,
        owner_id,
        _REVIEW_APPROVE_COINS * 100,  # display → internal fen
        idempotency_key=f"char_review:{character_id}",
        type_str="grant",
        ref_type="character_review",
        ref_id=character_id,
    )

    # Count this user's approved characters (this one is already 'approved').
    cnt_row = await db.execute(
        text(
            """
            SELECT COUNT(*) FROM characters
            WHERE owner_user_id = :uid AND status = 'active' AND review_status = 'approved'
            """
        ),
        {"uid": owner_id},
    )
    approved_count = int(cnt_row.scalar() or 0)

    milestone_granted = False
    if approved_count >= _MILESTONE_APPROVED_COUNT:
        # Guard: insert the milestone marker; only the first insert wins.
        ins = await db.execute(
            text(
                """
                INSERT INTO user_reward_milestones (user_id, milestone)
                VALUES (:uid, 'approved_5_plus')
                ON CONFLICT (user_id, milestone) DO NOTHING
                RETURNING user_id
                """
            ),
            {"uid": owner_id},
        )
        if ins.scalar_one_or_none() is not None:
            await activate_or_extend(
                db,
                owner_id,
                "plus",
                _MILESTONE_PLUS_DAYS,
                granted_by=f"milestone:approved_5:{uuid.uuid4()}",
            )
            milestone_granted = True

    return {
        "coins_granted": _REVIEW_APPROVE_COINS,
        "approved_count": approved_count,
        "milestone_plus_granted": milestone_granted,
    }


@router.get("/characters/pending")
async def admin_list_pending_characters(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """列出所有待审核（pending）的用户角色，含头像、封面、简介，供审核台展示。"""
    from heart.ss01_soul.character_content import get_display_name

    result = await db.execute(
        text(
            """
            SELECT c.id, c.owner_user_id, c.visibility, c.cover_url, c.submitted_at,
                   c.tags,
                   u.email AS owner_email,
                   s.draft AS draft
            FROM characters c
            LEFT JOIN users u ON u.id = c.owner_user_id
            LEFT JOIN soul_specs s ON s.character_id = c.id AND s.status = 'active'
            WHERE c.review_status = 'pending' AND c.status = 'active'
            ORDER BY c.submitted_at ASC NULLS LAST
            """
        )
    )
    items = []
    for row in result.mappings():
        draft = _coerce_draft(row["draft"])
        items.append(
            {
                "id": row["id"],
                "display_name": get_display_name(row["id"]),
                "owner_user_id": str(row["owner_user_id"]) if row["owner_user_id"] else None,
                "owner_email": row["owner_email"],
                "visibility": row["visibility"],
                "avatar_url": draft.get("avatar_url"),
                "cover_url": row["cover_url"],
                # Full review payload: everything an admin needs to judge the
                # character without opening it separately. All display/authoring
                # fields only — internal persona layers are not stored in draft.
                "persona": draft.get("persona"),
                "intro": draft.get("intro"),
                "tagline": draft.get("tagline"),
                "backstory": draft.get("backstory"),
                "opening": draft.get("opening"),
                "greeting_style": draft.get("greeting_style"),
                "gender": draft.get("gender"),
                "age_range": draft.get("age_range"),
                "tags": coerce_tags(row["tags"]),
                "catchphrases": _coerce_str_list(draft.get("catchphrases")),
                "speech_samples": _coerce_str_list(draft.get("speech_samples")),
                "hard_never_user": _coerce_str_list(draft.get("hard_never_user")),
                "submitted_at": row["submitted_at"].isoformat() if row["submitted_at"] else None,
            }
        )
    return {"pending": items, "count": len(items)}


@router.post("/characters/{character_id}/approve")
async def admin_approve_character(
    character_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """通过审核：角色进入公开目录，并发放奖励（100 币 + 满 5 个送 1 月进阶版）。"""
    row = await db.execute(
        text(
            """
            UPDATE characters
               SET review_status = 'approved',
                   review_reason = NULL,
                   reviewed_at   = NOW(),
                   result_ack_at = NULL
             WHERE id = :cid AND status = 'active'
               AND review_status IN ('pending','rejected')
             RETURNING owner_user_id
            """
        ),
        {"cid": character_id},
    )
    owner_id = row.scalar_one_or_none()
    if owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在或不在可审核状态"
        )

    rewards = await _grant_approval_rewards(db, character_id, owner_id)
    await db.commit()
    logger.info("character_approved", character_id=character_id, owner_id=str(owner_id), **rewards)
    return {"ok": True, "id": character_id, **rewards}


@router.post("/characters/{character_id}/reject")
async def admin_reject_character(
    character_id: str,
    body: RejectRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """驳回审核：记录原因（用户可见），角色不进入公开目录。"""
    row = await db.execute(
        text(
            """
            UPDATE characters
               SET review_status = 'rejected',
                   review_reason = :reason,
                   reviewed_at   = NOW(),
                   result_ack_at = NULL
             WHERE id = :cid AND status = 'active'
               AND review_status IN ('pending','approved')
             RETURNING owner_user_id
            """
        ),
        {"cid": character_id, "reason": body.reason},
    )
    owner_id = row.scalar_one_or_none()
    if owner_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在或不在可审核状态"
        )
    await db.commit()
    logger.info("character_rejected", character_id=character_id, owner_id=str(owner_id))
    return {"ok": True, "id": character_id, "reason": body.reason}
