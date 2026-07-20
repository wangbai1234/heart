"""Admin API routes — /api/admin/*

Protected by X-Admin-Key header. Set ADMIN_SECRET_KEY in .env.
Empty ADMIN_SECRET_KEY = all admin endpoints return 503.
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.core.config import settings
from heart.membership.service import activate_or_extend

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
