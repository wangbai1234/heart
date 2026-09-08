"""Social promotion tasks: user submissions and moderation workflow."""

from __future__ import annotations

import base64
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant
from heart.core.auth import TokenData, get_current_user
from heart.membership.coupons import grant_coupon

from .routes_admin import require_admin
from .wiring import get_db

router = APIRouter(prefix="/api/promotions", tags=["promotions"])
admin_router = APIRouter(prefix="/api/admin/promotions", tags=["admin-promotions"])

DAILY_LIMIT = 5
ALLOWED_PLATFORMS = {"douyin", "xiaohongshu"}
TASK_TYPES = {"ambassador", "creator", "likes"}
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
MEMBERSHIP_REWARDS = (
    {"threshold": 300, "tier": "plus", "label": "29 元档 VIP", "days": 30},
    {"threshold": 1000, "tier": "immersive", "label": "69 元档 VIP", "days": 30},
)


def _today_start() -> datetime:
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, f"{field_name} 格式无效") from exc


def _pending_membership_rewards(
    likes_count: int,
    milestone_300_granted: bool,
    milestone_1000_granted: bool,
) -> list[dict]:
    granted_by_threshold = {
        300: milestone_300_granted,
        1000: milestone_1000_granted,
    }
    return [
        dict(reward)
        for reward in MEMBERSHIP_REWARDS
        if likes_count >= reward["threshold"] and not granted_by_threshold[reward["threshold"]]
    ]


async def _current_submission_count(db: AsyncSession, uid: uuid.UUID) -> int:
    row = await db.execute(
        text(
            "SELECT COUNT(*) FROM promotion_submissions WHERE user_id=:uid AND submitted_at >= :start"
        ),
        {"uid": uid, "start": _today_start()},
    )
    return int(row.scalar() or 0)


@router.get("/status")
async def promotion_status(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    uid = uuid.UUID(current_user.user_id)
    count = await _current_submission_count(db, uid)
    rows = (
        (
            await db.execute(
                text(
                    """
                SELECT id, task_type, platform, screenshot_url, post_url, title,
                       likes_count, status, review_reason, reward_coins,
                       milestone_300_granted, milestone_1000_granted,
                       submitted_at, reviewed_at
                FROM promotion_submissions WHERE user_id=:uid
                ORDER BY submitted_at DESC LIMIT 50
                """
                ),
                {"uid": uid},
            )
        )
        .mappings()
        .all()
    )
    return {
        "daily_limit": DAILY_LIMIT,
        "today_submitted": count,
        "today_remaining": max(0, DAILY_LIMIT - count),
        "submissions": [dict(row) for row in rows],
    }


@router.post("/submit", status_code=status.HTTP_201_CREATED)
async def submit_promotion(  # noqa: C901
    task_type: str = Form(...),
    platform: str = Form(...),
    post_url: str | None = Form(None),
    source_submission_id: str | None = Form(None),
    title: str | None = Form(None),
    likes_count: int | None = Form(None),
    file: UploadFile | None = File(None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if task_type not in TASK_TYPES:
        raise HTTPException(422, "task_type 仅支持 ambassador、creator、likes")
    if platform not in ALLOWED_PLATFORMS:
        raise HTTPException(422, "platform 仅支持 douyin、xiaohongshu")
    if task_type in {"creator", "likes"} and not post_url:
        raise HTTPException(422, "作品链接不能为空")
    if task_type == "likes" and likes_count is None:
        raise HTTPException(422, "请填写当前点赞数")

    uid = uuid.UUID(current_user.user_id)
    count = await _current_submission_count(db, uid)
    if count >= DAILY_LIMIT:
        raise HTTPException(429, "今日提交次数已用完，请明日再来")

    screenshot_url = None
    if file is not None:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(400, "截图仅支持 jpg、png、webp")
        data = await file.read()
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(400, "截图不能超过 8MB")
        try:
            from heart.infra.storage import _upload_to_s3, is_s3_configured

            if is_s3_configured():
                key = (
                    f"promotion-evidence/{uid}/{uuid.uuid4().hex}."
                    f"{CONTENT_TYPE_EXTENSIONS[file.content_type]}"
                )
                await _upload_to_s3(key, data, file.content_type)
                screenshot_url = f"s3://{key}"
            else:
                screenshot_url = (
                    "data:" + file.content_type + ";base64," + base64.b64encode(data).decode()
                )
        except Exception as exc:
            raise HTTPException(503, "截图存储暂不可用") from exc

    normalized_url = _normalize_url(post_url) if post_url else None
    source_id = (
        _parse_uuid(source_submission_id, "source_submission_id") if source_submission_id else None
    )
    if task_type == "creator" and normalized_url:
        exists = await db.execute(
            text(
                "SELECT 1 FROM promotion_submissions WHERE task_type='creator' AND normalized_url=:url"
            ),
            {"url": normalized_url},
        )
        if exists.scalar_one_or_none():
            raise HTTPException(409, "该作品已提交过")

    row = (
        (
            await db.execute(
                text(
                    """
                INSERT INTO promotion_submissions
                  (id,user_id,task_type,platform,screenshot_url,post_url,normalized_url,title,likes_count,source_submission_id)
                VALUES (:id,:uid,:task,:platform,:shot,:post,:norm,:title,:likes,:source)
                RETURNING id, task_type, status, submitted_at
                """
                ),
                {
                    "id": uuid.uuid4(),
                    "uid": uid,
                    "task": task_type,
                    "platform": platform,
                    "shot": screenshot_url,
                    "post": post_url,
                    "norm": normalized_url,
                    "title": title,
                    "likes": likes_count,
                    "source": source_id,
                },
            )
        )
        .mappings()
        .one()
    )
    await db.commit()
    return {"ok": True, **dict(row), "today_remaining": max(0, DAILY_LIMIT - count - 1)}


class AdminReviewAction(BaseModel):
    reason: str = Field("", max_length=500)


async def _admin_rows(db: AsyncSession, status_value: str | None = None) -> list[dict]:
    clause = (
        "WHERE p.status=:status" if status_value else "WHERE p.status IN ('pending','needs_info')"
    )
    params = {"status": status_value} if status_value else {}
    rows = (
        (
            await db.execute(
                text(
                    f"""
                SELECT p.*, u.email AS owner_email,
                       COALESCE(source.milestone_300_granted, p.milestone_300_granted)
                         AS source_milestone_300_granted,
                       COALESCE(source.milestone_1000_granted, p.milestone_1000_granted)
                         AS source_milestone_1000_granted
                FROM promotion_submissions p
                LEFT JOIN users u ON u.id=p.user_id
                LEFT JOIN promotion_submissions source ON source.id=p.source_submission_id
                {clause}
                ORDER BY p.submitted_at ASC LIMIT 500
                """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )
    return [dict(row) for row in rows]


@admin_router.get("/pending")
async def admin_pending_promotions(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    rows = await _admin_rows(db)
    return {"pending": rows, "count": len(rows)}


@admin_router.get("/{submission_id}/image")
async def admin_promotion_image(
    submission_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Proxy private promotion evidence to an authenticated administrator."""
    sid = _parse_uuid(submission_id, "submission_id")
    screenshot_url = (
        await db.execute(
            text("SELECT screenshot_url FROM promotion_submissions WHERE id=:id"),
            {"id": sid},
        )
    ).scalar_one_or_none()
    if not screenshot_url:
        raise HTTPException(404, "截图不存在")

    if screenshot_url.startswith("data:"):
        try:
            metadata, encoded = screenshot_url.split(",", 1)
            content_type = metadata.removeprefix("data:").split(";", 1)[0]
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise HTTPException(404, "截图数据已损坏") from exc
    else:
        from heart.infra.storage import get_s3_object, object_key_from_storage_url

        key = object_key_from_storage_url(screenshot_url)
        if not key:
            raise HTTPException(404, "截图地址无效")
        try:
            data, content_type, _etag = await get_s3_object(key)
        except Exception as exc:
            raise HTTPException(404, "截图文件不存在") from exc

    return Response(
        content=data,
        media_type=content_type,
        headers={"Cache-Control": "private, max-age=300"},
    )


@admin_router.post("/{submission_id}/approve")
async def admin_approve_promotion(
    submission_id: str,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    sid = _parse_uuid(submission_id, "submission_id")
    row = (
        (
            await db.execute(
                text("SELECT * FROM promotion_submissions WHERE id=:id FOR UPDATE"), {"id": sid}
            )
        )
        .mappings()
        .first()
    )
    if not row or row["status"] not in {"pending", "needs_info"}:
        raise HTTPException(404, "提交不存在或已处理")
    reward_coins = (
        20 if row["task_type"] == "ambassador" else 100 if row["task_type"] == "creator" else 0
    )
    if reward_coins:
        await grant(
            db,
            row["user_id"],
            reward_coins * 100,
            f"promotion:{sid}",
            ref_type="promotion",
            ref_id=str(sid),
            auto_commit=False,
        )
    granted_memberships: list[dict] = []
    if row["task_type"] == "likes" and row["likes_count"] is not None:
        source = row["source_submission_id"] or sid
        milestone_300_granted = bool(row["milestone_300_granted"])
        milestone_1000_granted = bool(row["milestone_1000_granted"])
        if source != sid:
            source_row = (
                (
                    await db.execute(
                        text(
                            "SELECT milestone_300_granted, milestone_1000_granted "
                            "FROM promotion_submissions WHERE id=:id FOR UPDATE"
                        ),
                        {"id": source},
                    )
                )
                .mappings()
                .first()
            )
            if source_row:
                milestone_300_granted = bool(source_row["milestone_300_granted"])
                milestone_1000_granted = bool(source_row["milestone_1000_granted"])

        pending_rewards = _pending_membership_rewards(
            row["likes_count"], milestone_300_granted, milestone_1000_granted
        )
        milestone_updates = {
            300: text(
                "UPDATE promotion_submissions SET milestone_300_granted=TRUE "
                "WHERE id IN (:source, :submission)"
            ),
            1000: text(
                "UPDATE promotion_submissions SET milestone_1000_granted=TRUE "
                "WHERE id IN (:source, :submission)"
            ),
        }
        for reward in pending_rewards:
            await grant_coupon(
                db,
                row["user_id"],
                reward["tier"],
                reward["days"],
                f"promotion_likes_{reward['threshold']}",
                f"promotion:{source}:likes{reward['threshold']}",
            )
            await db.execute(
                milestone_updates[reward["threshold"]],
                {"source": source, "submission": sid},
            )
            granted_memberships.append(reward)
    await db.execute(
        text(
            "UPDATE promotion_submissions SET status='approved', reward_coins=reward_coins+:coins, reviewed_at=NOW(), review_reason=NULL, updated_at=NOW() WHERE id=:id"
        ),
        {"id": sid, "coins": reward_coins},
    )
    await db.commit()
    return {
        "ok": True,
        "id": submission_id,
        "reward_coins": reward_coins,
        "granted_memberships": granted_memberships,
    }


@admin_router.post("/{submission_id}/reject")
async def admin_reject_promotion(
    submission_id: str,
    body: AdminReviewAction,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not body.reason.strip():
        raise HTTPException(422, "驳回原因不能为空")
    result = await db.execute(
        text(
            "UPDATE promotion_submissions SET status='rejected', review_reason=:reason, reviewed_at=NOW(), updated_at=NOW() WHERE id=:id AND status IN ('pending','needs_info') RETURNING id"
        ),
        {"id": _parse_uuid(submission_id, "submission_id"), "reason": body.reason.strip()},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, "提交不存在或已处理")
    await db.commit()
    return {"ok": True, "id": submission_id}


@admin_router.post("/{submission_id}/needs-info")
async def admin_needs_info(
    submission_id: str,
    body: AdminReviewAction,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if not body.reason.strip():
        raise HTTPException(422, "补充说明不能为空")
    result = await db.execute(
        text(
            "UPDATE promotion_submissions SET status='needs_info', review_reason=:reason, reviewed_at=NOW(), updated_at=NOW() WHERE id=:id AND status='pending' RETURNING id"
        ),
        {"id": _parse_uuid(submission_id, "submission_id"), "reason": body.reason.strip()},
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(404, "提交不存在或已处理")
    await db.commit()
    return {"ok": True, "id": submission_id}
