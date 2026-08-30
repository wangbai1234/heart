"""Admin API routes — /api/admin/*

Protected by X-Admin-Key header. Set ADMIN_SECRET_KEY in .env.
Empty ADMIN_SECRET_KEY = all admin endpoints return 503.
"""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.core.config import settings
from heart.membership.service import activate_or_extend
from heart.ss01_soul.character_catalog import coerce_tags, display_name_from_spec

from .wiring import get_db

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def require_admin(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> None:
    if not settings.admin_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Admin API disabled"
        )
    if x_admin_key != settings.admin_secret_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin key")


def _json_rows(result) -> list[dict]:
    """Convert SQLAlchemy mappings to JSON-safe primitive rows."""
    rows = []
    for row in result.mappings().all():
        item = {}
        for key, value in row.items():
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            item[key] = value
        rows.append(item)
    return rows


@router.get("/analytics")
async def admin_analytics(
    start: date | None = Query(None, description="统计开始日期（上海时区）"),
    end: date | None = Query(None, description="统计结束日期（上海时区）"),
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return aggregate product-health metrics for the admin dashboard.

    All activity is derived from persisted user/chat/story/payment/character
    records. No PII or message content is selected. ``end`` is inclusive and
    dates are interpreted in Asia/Shanghai to match the product reports.
    """
    today = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    end = end or today
    start = start or end - timedelta(days=29)
    if start > end:
        raise HTTPException(status_code=422, detail="start 不能晚于 end")
    if (end - start).days > 180:
        raise HTTPException(status_code=422, detail="统计区间不能超过 181 天")
    params = {"start": start, "end": end, "end_exclusive": end + timedelta(days=1)}

    # Canonical activity: user-authored chat turns and story player turns.
    activity_cte = """
        SELECT user_id, created_at, (created_at AT TIME ZONE 'Asia/Shanghai')::date AS day,
               'chat' AS mode
        FROM chat_messages
        WHERE role = 'user' AND rewound_at IS NULL
        UNION ALL
        SELECT user_id, created_at, (created_at AT TIME ZONE 'Asia/Shanghai')::date,
               'story' AS mode
        FROM story_messages
        WHERE role = 'player'
    """

    scope = (
        (
            await db.execute(
                text(
                    """
                SELECT
                  (SELECT count(*) FROM users) AS total_users,
                  (SELECT count(*) FROM users WHERE status = 'active') AS active_users,
                  (SELECT count(*) FROM users WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start
                    AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS new_users,
                  (SELECT count(DISTINCT user_id) FROM chat_messages
                    WHERE role='user' AND rewound_at IS NULL
                    AND (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS chat_users,
                  (SELECT count(DISTINCT user_id) FROM story_messages
                    WHERE role='player' AND (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start
                    AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS story_users,
                  (SELECT count(DISTINCT user_id) FROM ("""
                    + activity_cte
                    + """ ) a WHERE day >= :start AND day < :end_exclusive) AS active_users_in_range,
                  (SELECT count(*) FROM sessions
                    WHERE (last_activity_at AT TIME ZONE 'Asia/Shanghai')::date >= :start
                    AND (last_activity_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS sessions_in_range,
                  (SELECT count(DISTINCT resolved_user_id) FROM afdian_orders
                    WHERE fulfilled_at IS NOT NULL AND resolved_user_id IS NOT NULL
                    AND total_amount > 0 AND (received_at AT TIME ZONE 'Asia/Shanghai')::date >= :start
                    AND (received_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS paid_users,
                  (SELECT coalesce(sum(total_amount), 0) FROM afdian_orders
                    WHERE fulfilled_at IS NOT NULL AND resolved_user_id IS NOT NULL
                    AND total_amount > 0 AND (received_at AT TIME ZONE 'Asia/Shanghai')::date >= :start
                    AND (received_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive) AS revenue_cny
                """
                ),
                params,
            )
        )
        .mappings()
        .one()
    )

    daily = _json_rows(
        await db.execute(
            text(
                """
                WITH days AS (
                  SELECT generate_series(CAST(:start AS date), CAST(:end AS date), interval '1 day')::date AS day
                ), activity AS ("""
                + activity_cte
                + """), ad AS (SELECT DISTINCT user_id, day FROM activity)
                SELECT d.day,
                  (SELECT count(*) FROM ad WHERE day=d.day) AS dau,
                  (SELECT count(*) FROM ad WHERE day BETWEEN d.day-6 AND d.day) AS wau,
                  (SELECT count(*) FROM ad WHERE day BETWEEN d.day-29 AND d.day) AS mau,
                  (SELECT count(DISTINCT user_id) FROM activity WHERE day=d.day AND mode='chat') AS chat_dau,
                  (SELECT count(DISTINCT user_id) FROM activity WHERE day=d.day AND mode='story') AS story_dau,
                  (SELECT count(*) FROM activity WHERE day=d.day) AS user_turns,
                  round(100.0 * (SELECT count(*) FROM ad WHERE day=d.day)
                    / nullif((SELECT count(*) FROM ad WHERE day BETWEEN d.day-29 AND d.day),0), 2) AS dau_mau_pct
                FROM days d ORDER BY d.day
                """
            ),
            params,
        )
    )

    retention = _json_rows(
        await db.execute(
            text(
                """
                WITH cohort AS (
                  SELECT id, (created_at AT TIME ZONE 'Asia/Shanghai')::date AS reg_day
                  FROM users WHERE (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive
                ), activity AS (
                  SELECT DISTINCT user_id, (created_at AT TIME ZONE 'Asia/Shanghai')::date AS day
                  FROM chat_messages WHERE role='user' AND rewound_at IS NULL
                  UNION
                  SELECT DISTINCT user_id, (created_at AT TIME ZONE 'Asia/Shanghai')::date
                  FROM story_messages WHERE role='player'
                )
                SELECT reg_day, count(*) AS cohort_users,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day)) AS d0_users,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+1)) AS d1_users,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+3)) AS d3_users,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+7)) AS d7_users,
                  round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day))/count(*),2) AS d0_pct,
                  CASE WHEN reg_day+1 <= (now() AT TIME ZONE 'Asia/Shanghai')::date THEN round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+1))/count(*),2) END AS d1_pct,
                  CASE WHEN reg_day+3 <= (now() AT TIME ZONE 'Asia/Shanghai')::date THEN round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+3))/count(*),2) END AS d3_pct,
                  CASE WHEN reg_day+7 <= (now() AT TIME ZONE 'Asia/Shanghai')::date THEN round(100.0*count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=c.id AND a.day=reg_day+7))/count(*),2) END AS d7_pct
                FROM cohort c GROUP BY reg_day ORDER BY reg_day
                """
            ),
            params,
        )
    )

    depth = _json_rows(
        await db.execute(
            text(
                """
                WITH turns AS (
                  SELECT user_id, count(*) AS turns, count(DISTINCT (created_at AT TIME ZONE 'Asia/Shanghai')::date) AS active_days
                  FROM chat_messages WHERE role='user' AND rewound_at IS NULL
                    AND (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive
                  GROUP BY user_id
                )
                SELECT count(*) AS active_chat_users, coalesce(sum(turns),0) AS user_turns,
                  round(coalesce(avg(turns),0),2) AS avg_turns_per_user,
                  round(coalesce(percentile_cont(.5) within group (order by turns),0)::numeric,2) AS median_turns,
                  round(coalesce(avg(active_days),0),2) AS avg_active_days,
                  count(*) FILTER (WHERE turns >= 10) AS ten_turn_users,
                  count(*) FILTER (WHERE turns >= 30) AS thirty_turn_users
                FROM turns
                """
            ),
            params,
        )
    )

    characters = _json_rows(
        await db.execute(
            text(
                """
                WITH pairs AS (
                  SELECT character_id, user_id,
                    count(*) FILTER (WHERE role='user') AS user_turns,
                    count(DISTINCT (created_at AT TIME ZONE 'Asia/Shanghai')::date) FILTER (WHERE role='user') AS active_days
                  FROM chat_messages WHERE rewound_at IS NULL
                    AND (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive
                  GROUP BY character_id, user_id
                ), specs AS (
                  SELECT DISTINCT ON (character_id) character_id,
                    coalesce(nullif(CASE WHEN jsonb_typeof(spec->'display_name')='object' THEN spec->'display_name'->>'zh' ELSE spec->>'display_name' END,''), character_id) AS character_name
                  FROM soul_specs ORDER BY character_id, created_at DESC
                )
                SELECT coalesce(s.character_name, p.character_id) AS character_name,
                  count(*) AS entered_users, count(*) FILTER (WHERE user_turns > 0) AS chat_users,
                  sum(user_turns) AS user_turns,
                  round(coalesce(avg(user_turns) FILTER (WHERE user_turns > 0),0),2) AS avg_turns,
                  round(100.0*count(*) FILTER (WHERE user_turns > 0 AND active_days >= 2)
                    / nullif(count(*) FILTER (WHERE user_turns > 0),0),2) AS return_rate_pct,
                  round(100.0*count(*) FILTER (WHERE user_turns > 0)/nullif(count(*),0),2) AS entry_to_chat_pct
                FROM pairs p LEFT JOIN specs s ON s.character_id=p.character_id
                GROUP BY p.character_id, s.character_name
                ORDER BY chat_users DESC, user_turns DESC LIMIT 20
                """
            ),
            params,
        )
    )

    churn = _json_rows(
        await db.execute(
            text(
                """
                WITH activity AS (
                  SELECT DISTINCT user_id, (created_at AT TIME ZONE 'Asia/Shanghai')::date AS day
                  FROM chat_messages WHERE role='user' AND rewound_at IS NULL
                  UNION
                  SELECT DISTINCT user_id, (created_at AT TIME ZONE 'Asia/Shanghai')::date
                  FROM story_messages WHERE role='player'
                ), users AS (SELECT DISTINCT user_id FROM activity)
                SELECT count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=u.user_id AND a.day BETWEEN CAST(:end AS date)-6 AND CAST(:end AS date))) AS active_last_7d,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=u.user_id AND a.day BETWEEN CAST(:end AS date)-13 AND CAST(:end AS date)-7)
                    AND NOT EXISTS (SELECT 1 FROM activity a WHERE a.user_id=u.user_id AND a.day BETWEEN CAST(:end AS date)-6 AND CAST(:end AS date))) AS lapsed_7_to_13d,
                  count(*) FILTER (WHERE EXISTS (SELECT 1 FROM activity a WHERE a.user_id=u.user_id AND a.day < CAST(:end AS date)-13)
                    AND NOT EXISTS (SELECT 1 FROM activity a WHERE a.user_id=u.user_id AND a.day BETWEEN CAST(:end AS date)-13 AND CAST(:end AS date))) AS lapsed_14d_plus
                FROM users u
                """
            ),
            params,
        )
    )

    payments = _json_rows(
        await db.execute(
            text(
                """
                SELECT (received_at AT TIME ZONE 'Asia/Shanghai')::date AS day,
                  count(*) AS orders, count(DISTINCT resolved_user_id) AS paid_users,
                  coalesce(sum(total_amount),0) AS revenue_cny
                FROM afdian_orders
                WHERE fulfilled_at IS NOT NULL AND resolved_user_id IS NOT NULL AND total_amount > 0
                  AND (received_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (received_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive
                GROUP BY 1 ORDER BY 1
                """
            ),
            params,
        )
    )

    ai_cost = _json_rows(
        await db.execute(
            text(
                """
                SELECT count(*) AS llm_transactions, count(DISTINCT user_id) AS llm_users,
                  coalesce(sum(abs(delta)),0)::numeric / 100 AS llm_credits_spent
                FROM credit_transactions
                WHERE type IN ('consume_llm', 'spend')
                  AND (ref_type='message' OR ref_type='llm' OR ref_type ILIKE '%llm%')
                  AND (created_at AT TIME ZONE 'Asia/Shanghai')::date >= :start AND (created_at AT TIME ZONE 'Asia/Shanghai')::date < :end_exclusive
                """
            ),
            params,
        )
    )

    return {
        "window": {"start": start.isoformat(), "end": end.isoformat(), "timezone": "Asia/Shanghai"},
        "scope": dict(scope),
        "daily": daily,
        "retention": retention,
        "depth": depth[0] if depth else {},
        "characters": characters,
        "churn": churn[0] if churn else {},
        "payments": payments,
        "ai_cost": {
            **(ai_cost[0] if ai_cost else {}),
            "token_tracking": "not_recorded",
            "tracked_usd": None,
            "note": "当前数据库未持久化每次 LLM 的 token usage 与供应商成本；积分消耗为真实账本数据。",
        },
        "data_quality": {
            "activity_sources": [
                "chat_messages.user",
                "story_messages.player",
                "sessions.last_activity_at",
            ],
            "behavior_log": "未单独建行为事件表；会话表与聊天/剧情持久化记录作为行为事实源",
            "current_day_partial": end == today,
        },
    }


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


async def _grant_approval_rewards(
    db: AsyncSession,
    character_id: str,
    owner_id: uuid.UUID,
    visibility: str,
) -> dict:
    """Grant rewards only when an approved character is public.

    - Coins: idempotent per character (idempotency_key = char_review:{cid}).
    - Link-only (unlisted) approval: moderation succeeds, but grants no reward.
    - Existing 5-approved milestone behavior is unchanged and remains guarded.
    Returns a summary of what was granted (for the admin response / logs).
    """
    reward_eligible = visibility == "public"
    coins_granted = 0
    if reward_eligible:
        # Avoid calling grant() on an idempotency hit: grant() rolls the current
        # transaction back on conflict, which would also undo this approval.
        already_rewarded = (
            await db.execute(
                text("SELECT 1 FROM credit_transactions" " WHERE idempotency_key = :key LIMIT 1"),
                {"key": f"char_review:{character_id}"},
            )
        ).scalar_one_or_none()
        if already_rewarded is None:
            await grant(
                db,
                owner_id,
                _REVIEW_APPROVE_COINS * 100,  # display → internal fen
                idempotency_key=f"char_review:{character_id}",
                type_str="grant",
                ref_type="character_review",
                ref_id=character_id,
            )
            coins_granted = _REVIEW_APPROVE_COINS

    # Preserve the existing milestone rule: all approved characters count,
    # regardless of whether their visibility is public or link-only.
    cnt_row = await db.execute(
        text(
            """
            SELECT COUNT(*) FROM characters
            WHERE owner_user_id = :uid
              AND status = 'active'
              AND review_status = 'approved'
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
        "reward_eligible": reward_eligible,
        "coins_granted": coins_granted,
        "approved_count": approved_count,
        "milestone_plus_granted": milestone_granted,
    }


@router.get("/characters/pending")
async def admin_list_pending_characters(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """列出所有待审核（pending）的用户角色，含头像、封面、简介，供审核台展示。"""
    result = await db.execute(
        text(
            """
            SELECT c.id, c.owner_user_id, c.visibility, c.cover_url, c.submitted_at,
                   c.tags,
                   u.email AS owner_email,
                   s.draft AS draft, s.spec AS spec
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
                "display_name": display_name_from_spec(row["spec"], row["id"]),
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
    """通过审核：公开角色发放奖励；链接可见角色仅通过审核。"""
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
             RETURNING owner_user_id, visibility
            """
        ),
        {"cid": character_id},
    )
    approved = row.mappings().one_or_none()
    if approved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="角色不存在或不在可审核状态"
        )

    owner_id = approved["owner_user_id"]
    visibility = approved["visibility"]
    rewards = await _grant_approval_rewards(db, character_id, owner_id, visibility)
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
