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
    if not body.user_id and not body.email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id 或 email 必填一个"
        )

    # Resolve user
    if body.user_id:
        try:
            uid = uuid.UUID(body.user_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="user_id 格式错误"
            ) from None
        row = await db.execute(
            text("SELECT id, email FROM users WHERE id = :uid AND deleted_at IS NULL"),
            {"uid": uid},
        )
        user = row.mappings().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    else:
        row = await db.execute(
            text("SELECT id, email FROM users WHERE email = :email AND deleted_at IS NULL"),
            {"email": body.email.lower().strip()},
        )
        user = row.mappings().first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
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
