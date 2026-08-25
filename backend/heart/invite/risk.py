"""Privacy-preserving referral risk scoring for an email-only account system."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings


def hash_signal(value: str | None) -> str | None:
    if not value:
        return None
    salt = settings.referral_signal_salt or settings.admin_secret_key or "yuoyuo-referral-v1"
    return hashlib.sha256(f"{salt}:{value.strip()}".encode()).hexdigest()


async def score_binding(
    db: AsyncSession, use_id: int, device_id: str | None, ip: str | None
) -> str:
    device_hash = hash_signal(device_id)
    ip_hash = hash_signal(ip)
    await db.execute(
        text(
            """
            UPDATE user_invite_uses SET device_hash = :device_hash, ip_hash = :ip_hash
            WHERE id = :use_id
            """
        ),
        {"use_id": use_id, "device_hash": device_hash, "ip_hash": ip_hash},
    )
    device_count = 0
    if device_hash:
        device_count = int(
            (
                await db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM user_invite_uses
                        WHERE device_hash = :device_hash
                          AND created_at >= NOW() - INTERVAL '7 days'
                        """
                    ),
                    {"device_hash": device_hash},
                )
            ).scalar_one()
        )
    ip_count = 0
    if ip_hash:
        ip_count = int(
            (
                await db.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM user_invite_uses
                        WHERE ip_hash = :ip_hash
                          AND created_at >= NOW() - INTERVAL '24 hours'
                        """
                    ),
                    {"ip_hash": ip_hash},
                )
            ).scalar_one()
        )

    score = 60 if device_count >= 3 else 30 if device_count >= 2 else 0
    if ip_count >= 5 and device_count >= 2:
        score += 20
    risk_level = "high" if score >= 60 else "mid" if score >= 30 else "low"
    await db.execute(
        text("UPDATE user_invite_uses SET risk_level = :risk WHERE id = :use_id"),
        {"risk": risk_level, "use_id": use_id},
    )
    if score:
        await db.execute(
            text(
                """
                INSERT INTO referral_risk_events
                    (event_type, subject_id, signals, score, risk_level)
                VALUES ('invite_binding', :subject_id, :signals, :score, :risk_level)
                """
            ),
            {
                "subject_id": str(use_id),
                "signals": json.dumps(
                    {"device_accounts_7d": device_count, "ip_accounts_24h": ip_count}
                ),
                "score": score,
                "risk_level": risk_level,
            },
        )
    return risk_level
