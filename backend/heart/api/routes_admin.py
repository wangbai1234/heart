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
    - 升级当日按当前档位补足每日签到币（当天已领 20 币时只补 60 币）
    """
    tier = body.tier.strip().lower()
    if tier not in _GRANTABLE_TIERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="tier 仅支持 plus（进阶版）或 immersive（沉浸版）",
        )

    user = await _resolve_user(db, body.user_id, body.email)
    uid = user["id"]

    # Each admin action is distinct. Activation itself handles the idempotent
    # daily grant/top-up for the current Shanghai calendar day.
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


class ReferralReviewRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str = Field("", max_length=500)


class LotteryPoolCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=64)
    total_chances: int = Field(..., gt=0, le=1_000_000)


class LotteryPrizeCreateRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=32, pattern="^[a-z0-9_]+$")
    kind: str = Field(..., pattern="^(coins|membership)$")
    payload: dict[str, object]
    weight: int = Field(..., gt=0, le=10_000)
    face_value_fen: int = Field(..., ge=0)
    total_stock: int | None = Field(None, ge=0)
    daily_stock: int | None = Field(None, ge=0)
    per_user_limit_json: dict[str, object] | None = None
    fallback_prize_code: str | None = Field(
        None, min_length=3, max_length=32, pattern="^[a-z0-9_]+$"
    )
    enabled: bool = True


class LotteryPrizeUpdateRequest(BaseModel):
    weight: int | None = Field(None, gt=0)
    total_stock: int | None = Field(None, ge=0)
    daily_stock: int | None = Field(None, ge=0)
    enabled: bool | None = None


class GrowthRuleUpdateRequest(BaseModel):
    config: dict[str, int]


_GROWTH_RULE_KEYS = {
    "invite": {
        "qualification_days",
        "binding_hours",
        "min_messages",
        "min_ai_replies",
        "min_valid_chars",
        "min_span_seconds",
        "chance_expiry_days",
        "daily_limit_free",
        "daily_limit_plus",
        "daily_limit_immersive",
    },
    "commission": {
        "rate_percent",
        "attribution_days",
        "settlement_days",
        "risk_settlement_days",
    },
}


def _validate_lottery_prize(body: LotteryPrizeCreateRequest) -> None:
    if body.kind == "coins":
        coins = body.payload.get("coins")
        if isinstance(coins, bool) or not isinstance(coins, int) or coins <= 0:
            raise HTTPException(status_code=422, detail="悠悠币奖品 payload.coins 必须为正整数")
    else:
        tier = body.payload.get("tier")
        days = body.payload.get("days")
        if tier not in {"plus", "immersive"}:
            raise HTTPException(status_code=422, detail="会员奖品 payload.tier 无效")
        if isinstance(days, bool) or not isinstance(days, int) or days <= 0:
            raise HTTPException(status_code=422, detail="会员奖品 payload.days 必须为正整数")
    if body.total_stock is not None and body.daily_stock is not None:
        if body.daily_stock > body.total_stock:
            raise HTTPException(status_code=422, detail="每日库存不能大于总库存")
    if body.fallback_prize_code == body.code:
        raise HTTPException(status_code=422, detail="兜底奖品不能指向自身")
    if body.per_user_limit_json is not None:
        days = body.per_user_limit_json.get("days")
        maximum = body.per_user_limit_json.get("max")
        invalid_days = isinstance(days, bool) or not isinstance(days, int) or days <= 0
        invalid_max = isinstance(maximum, bool) or not isinstance(maximum, int) or maximum <= 0
        if invalid_days or invalid_max:
            raise HTTPException(status_code=422, detail="单用户限制必须包含正整数 days 和 max")


@router.get("/growth/rules")
async def admin_get_growth_rules(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        (await db.execute(text("SELECT namespace, config, updated_at FROM growth_rule_settings")))
        .mappings()
        .all()
    )
    return {
        row["namespace"]: {"config": row["config"], "updated_at": row["updated_at"]} for row in rows
    }


@router.put("/growth/rules/{namespace}")
async def admin_update_growth_rules(
    namespace: str,
    body: GrowthRuleUpdateRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    allowed = _GROWTH_RULE_KEYS.get(namespace)
    if not allowed:
        raise HTTPException(status_code=404, detail="未知配置命名空间")
    if set(body.config) != allowed or any(value <= 0 for value in body.config.values()):
        raise HTTPException(status_code=422, detail="配置字段不完整或数值无效")
    if namespace == "commission" and body.config["rate_percent"] > 100:
        raise HTTPException(status_code=422, detail="返佣比例不能超过 100%")
    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO growth_rule_settings (namespace, config, updated_at)
                VALUES (:namespace, CAST(:config AS jsonb), NOW())
                ON CONFLICT (namespace) DO UPDATE
                SET config = EXCLUDED.config, updated_at = NOW()
                RETURNING namespace, config, updated_at
                """
                ),
                {"namespace": namespace, "config": json.dumps(body.config)},
            )
        )
        .mappings()
        .one()
    )
    await db.execute(
        text(
            """
            INSERT INTO admin_audit_logs (action, subject_type, subject_id, detail)
            VALUES ('growth_rules_update', 'growth_rules', :namespace, CAST(:detail AS jsonb))
            """
        ),
        {"namespace": namespace, "detail": json.dumps(body.config)},
    )
    return dict(row)


@router.get("/growth/referrals/review")
async def admin_referral_review_queue(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT iu.id, iu.inviter_id, iu.invitee_id, iu.status, iu.risk_level,
                       iu.msg_count, iu.ai_reply_count, iu.valid_char_count,
                       iu.qualified_at, iu.created_at,
                       COALESCE(re.signals, '{}'::jsonb) AS signals,
                       COALESCE(re.score, 0) AS risk_score
                FROM user_invite_uses iu
                LEFT JOIN LATERAL (
                  SELECT signals, score FROM referral_risk_events
                  WHERE subject_id = iu.id::text ORDER BY created_at DESC LIMIT 1
                ) re ON TRUE
                WHERE iu.status IN ('review', 'rejected')
                ORDER BY iu.qualified_at NULLS LAST, iu.created_at
                LIMIT 200
                """
                )
            )
        )
        .mappings()
        .all()
    )
    return {"items": [dict(row) for row in rows], "count": len(rows)}


@router.post("/growth/referrals/{use_id}/review")
async def admin_review_referral(
    use_id: int,
    body: ReferralReviewRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = (
        (
            await db.execute(
                text(
                    """
                SELECT id, inviter_id, invitee_id, status FROM user_invite_uses
                WHERE id = :use_id FOR UPDATE
                """
                ),
                {"use_id": use_id},
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="邀请记录不存在")

    if body.decision == "approve":
        await db.execute(
            text(
                """
                UPDATE user_invite_uses SET status = 'qualified', risk_level = 'low'
                WHERE id = :use_id
                """
            ),
            {"use_id": use_id},
        )
        from heart.commission.service import backfill_commissions_for_invitee
        from heart.invite.service import _grant_chance

        chance_granted = await _grant_chance(db, uuid.UUID(str(row["inviter_id"])), use_id)
        await backfill_commissions_for_invitee(db, uuid.UUID(str(row["invitee_id"])))
    else:
        chance_granted = False
        await db.execute(
            text("UPDATE user_invite_uses SET status = 'rejected' WHERE id = :use_id"),
            {"use_id": use_id},
        )

    await db.execute(
        text(
            """
            INSERT INTO admin_audit_logs (action, subject_type, subject_id, detail)
            VALUES (:action, 'invite', :subject_id, CAST(:detail AS jsonb))
            """
        ),
        {
            "action": f"referral_{body.decision}",
            "subject_id": str(use_id),
            "detail": json.dumps({"reason": body.reason, "chance_granted": chance_granted}),
        },
    )
    return {"ok": True, "decision": body.decision, "chance_granted": chance_granted}


@router.get("/growth/lottery/pools")
async def admin_list_lottery_pools(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT p.id, p.name, p.status, p.total_chances, p.created_at,
                       p.activated_at, COUNT(d.id) AS draws,
                       COALESCE(SUM(d.face_value_fen), 0) AS awarded_face_value_fen
                FROM lottery_pool_versions p
                LEFT JOIN lottery_draws d ON d.pool_id = p.id
                GROUP BY p.id ORDER BY p.created_at DESC
                """
                )
            )
        )
        .mappings()
        .all()
    )
    return {"pools": [dict(row) for row in rows]}


@router.post("/growth/lottery/pools")
async def admin_create_lottery_pool(
    body: LotteryPoolCreateRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO lottery_pool_versions (name, status, total_chances)
                VALUES (:name, 'draft', :total_chances)
                RETURNING id, name, status, total_chances
                """
                ),
                {"name": body.name, "total_chances": body.total_chances},
            )
        )
        .mappings()
        .one()
    )
    return dict(row)


@router.post("/growth/lottery/pools/{pool_id}/prizes", status_code=201)
async def admin_create_lottery_prize(
    pool_id: int,
    body: LotteryPrizeCreateRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    _validate_lottery_prize(body)
    pool_status = (
        await db.execute(
            text("SELECT status FROM lottery_pool_versions WHERE id = :pool_id FOR UPDATE"),
            {"pool_id": pool_id},
        )
    ).scalar_one_or_none()
    if pool_status is None:
        raise HTTPException(status_code=404, detail="奖池不存在")
    if pool_status != "draft":
        raise HTTPException(status_code=400, detail="已发布奖池不可新增奖品")

    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO lottery_prizes
                  (pool_id, code, kind, payload, weight, face_value_fen, total_stock,
                   daily_stock, per_user_limit_json, fallback_prize_code, enabled)
                VALUES
                  (:pool_id, :code, :kind, CAST(:payload AS jsonb), :weight,
                   :face_value_fen, :total_stock, :daily_stock,
                   CAST(:per_user_limit AS jsonb), :fallback_prize_code, :enabled)
                ON CONFLICT (pool_id, code) DO NOTHING
                RETURNING code, kind, payload, weight, face_value_fen, total_stock,
                          daily_stock, per_user_limit_json, fallback_prize_code, enabled
                """
                ),
                {
                    "pool_id": pool_id,
                    "code": body.code,
                    "kind": body.kind,
                    "payload": json.dumps(body.payload),
                    "weight": body.weight,
                    "face_value_fen": body.face_value_fen,
                    "total_stock": body.total_stock,
                    "daily_stock": body.daily_stock,
                    "per_user_limit": (
                        json.dumps(body.per_user_limit_json)
                        if body.per_user_limit_json is not None
                        else None
                    ),
                    "fallback_prize_code": body.fallback_prize_code,
                    "enabled": body.enabled,
                },
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=409, detail="奖品编码已存在")
    await db.execute(
        text(
            """
            INSERT INTO admin_audit_logs (action, subject_type, subject_id, detail)
            VALUES ('lottery_prize_create', 'lottery_prize', :subject_id,
                    CAST(:detail AS jsonb))
            """
        ),
        {
            "subject_id": f"{pool_id}:{body.code}",
            "detail": json.dumps({"pool_id": pool_id, **body.model_dump()}),
        },
    )
    return dict(row)


@router.post("/growth/lottery/pools/{pool_id}/activate")
async def admin_activate_lottery_pool(
    pool_id: int,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    pool_status = (
        await db.execute(
            text("SELECT status FROM lottery_pool_versions WHERE id = :pool_id FOR UPDATE"),
            {"pool_id": pool_id},
        )
    ).scalar_one_or_none()
    if pool_status != "draft":
        raise HTTPException(status_code=400, detail="仅草稿奖池可以启用")
    weight_total = int(
        (
            await db.execute(
                text(
                    "SELECT COALESCE(SUM(weight), 0) FROM lottery_prizes "
                    "WHERE pool_id = :pool_id AND enabled = TRUE"
                ),
                {"pool_id": pool_id},
            )
        ).scalar_one()
    )
    if weight_total != 10_000:
        raise HTTPException(status_code=400, detail="启用奖品权重总和必须等于 10000")
    await db.execute(
        text("UPDATE lottery_pool_versions SET status = 'closed' WHERE status = 'active'")
    )
    row = (
        (
            await db.execute(
                text(
                    """
                UPDATE lottery_pool_versions
                SET status = 'active', activated_at = NOW()
                WHERE id = :pool_id AND status = 'draft'
                RETURNING id, name, status
                """
                ),
                {"pool_id": pool_id},
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=409, detail="奖池状态已变化，请刷新后重试")
    return dict(row)


@router.patch("/growth/lottery/pools/{pool_id}/prizes/{code}")
async def admin_update_lottery_prize(
    pool_id: int,
    code: str,
    body: LotteryPrizeUpdateRequest,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    pool_status = (
        await db.execute(
            text("SELECT status FROM lottery_pool_versions WHERE id = :pool_id"),
            {"pool_id": pool_id},
        )
    ).scalar_one_or_none()
    if pool_status != "draft":
        raise HTTPException(status_code=400, detail="已发布奖池不可修改")
    row = (
        (
            await db.execute(
                text(
                    """
                UPDATE lottery_prizes SET
                  weight = COALESCE(:weight, weight),
                  total_stock = COALESCE(:total_stock, total_stock),
                  daily_stock = COALESCE(:daily_stock, daily_stock),
                  enabled = COALESCE(:enabled, enabled)
                WHERE pool_id = :pool_id AND code = :code
                RETURNING code, weight, total_stock, daily_stock, enabled
                """
                ),
                {
                    "pool_id": pool_id,
                    "code": code,
                    "weight": body.weight,
                    "total_stock": body.total_stock,
                    "daily_stock": body.daily_stock,
                    "enabled": body.enabled,
                },
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="奖品不存在")
    return dict(row)


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
