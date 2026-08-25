"""Lottery membership experience coupons and scheduled entitlement periods."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class CouponError(ValueError):
    pass


async def grant_coupon(
    db: AsyncSession,
    user_id: uuid.UUID,
    tier: str,
    days: int,
    source: str,
    idem_key: str,
) -> int:
    row = (
        await db.execute(
            text(
                """
                INSERT INTO membership_reward_coupons
                    (user_id, tier, days, source, activate_by, idem_key)
                VALUES (:uid, :tier, :days, :source, NOW() + INTERVAL '90 days', :idem)
                ON CONFLICT (idem_key) DO UPDATE SET idem_key = EXCLUDED.idem_key
                RETURNING id
                """
            ),
            {"uid": user_id, "tier": tier, "days": days, "source": source, "idem": idem_key},
        )
    ).scalar_one()
    return int(row)


async def activate_coupon(db: AsyncSession, user_id: uuid.UUID, coupon_id: int) -> dict:
    coupon = (
        (
            await db.execute(
                text(
                    """
                SELECT id, tier, days, status, activate_by, starts_at, expires_at
                FROM membership_reward_coupons
                WHERE id = :coupon_id AND user_id = :uid
                FOR UPDATE
                """
                ),
                {"coupon_id": coupon_id, "uid": user_id},
            )
        )
        .mappings()
        .first()
    )
    if not coupon:
        raise CouponError("coupon_not_found")
    if coupon["status"] == "activated":
        return dict(coupon)
    if coupon["status"] != "active":
        raise CouponError("coupon_not_active")
    if coupon["activate_by"] <= datetime.now(tz=timezone.utc):
        raise CouponError("coupon_expired")

    activated = (
        (
            await db.execute(
                text(
                    """
                WITH latest AS (
                  SELECT GREATEST(
                    NOW(),
                    COALESCE((
                      SELECT MAX(expires_at) FROM user_memberships
                      WHERE user_id = :uid AND expires_at > NOW()
                    ), NOW()),
                    COALESCE((
                      SELECT MAX(expires_at) FROM membership_reward_coupons
                      WHERE user_id = :uid AND status = 'activated' AND expires_at > NOW()
                    ), NOW())
                  ) AS starts_at
                )
                UPDATE membership_reward_coupons
                SET status = 'activated', activated_at = NOW(),
                    starts_at = latest.starts_at,
                    expires_at = latest.starts_at + make_interval(days => days)
                FROM latest
                WHERE id = :coupon_id AND status = 'active'
                RETURNING membership_reward_coupons.id,
                          membership_reward_coupons.tier,
                          membership_reward_coupons.days,
                          membership_reward_coupons.status,
                          membership_reward_coupons.activate_by,
                          membership_reward_coupons.starts_at,
                          membership_reward_coupons.expires_at
                """
                ),
                {"coupon_id": coupon_id, "uid": user_id},
            )
        )
        .mappings()
        .one()
    )
    return dict(activated)
