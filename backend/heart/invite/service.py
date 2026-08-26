"""Invite system service — per yuoyuocoin_plan §6."""

from __future__ import annotations

import secrets
import string
import uuid
from hashlib import sha256

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

logger = structlog.get_logger(__name__)

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LEN = 8


async def load_invite_rules(db: AsyncSession) -> dict[str, int]:
    defaults = {
        "qualification_days": settings.invite_qualification_days,
        "binding_hours": settings.invite_binding_hours,
        "min_messages": settings.invite_min_messages,
        "min_ai_replies": settings.invite_min_ai_replies,
        "min_valid_chars": settings.invite_min_valid_chars,
        "min_span_seconds": settings.invite_min_span_seconds,
        "chance_expiry_days": settings.invite_chance_expiry_days,
        "daily_limit_free": settings.invite_daily_limit_free,
        "daily_limit_plus": settings.invite_daily_limit_plus,
        "daily_limit_immersive": settings.invite_daily_limit_immersive,
    }
    result = await db.execute(
        text("SELECT config FROM growth_rule_settings WHERE namespace = 'invite'")
    )
    configured = result.scalar_one_or_none() or {}
    return {key: int(configured.get(key, value)) for key, value in defaults.items()}


def _gen_code() -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(_CODE_LEN))


async def get_or_create_code(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Return existing invite code or create one."""
    row = (
        (
            await db.execute(
                text("SELECT code FROM user_invite_codes WHERE user_id = :uid"),
                {"uid": user_id},
            )
        )
        .mappings()
        .fetchone()
    )
    if row:
        return str(row["code"])

    code = _gen_code()
    await db.execute(
        text(
            "INSERT INTO user_invite_codes (user_id, code) VALUES (:uid, :code) "
            "ON CONFLICT (user_id) DO NOTHING"
        ),
        {"uid": user_id, "code": code},
    )
    # Re-read to handle the rare race where another request inserted first
    row2 = (
        (
            await db.execute(
                text("SELECT code FROM user_invite_codes WHERE user_id = :uid"),
                {"uid": user_id},
            )
        )
        .mappings()
        .fetchone()
    )
    return str(row2["code"]) if row2 else code


async def record_invite_signup(
    db: AsyncSession,
    invitee_id: uuid.UUID,
    code: str,
    *,
    device_id: str | None = None,
    ip: str | None = None,
) -> str:
    """Record that invitee used an invite code at signup. Idempotent.

    Returns one of: "ok" | "invalid_code" | "already_bound" | "self_invite".
    """
    upper_code = code.upper()
    row = (
        (
            await db.execute(
                text("SELECT user_id FROM user_invite_codes WHERE code = :code"),
                {"code": upper_code},
            )
        )
        .mappings()
        .fetchone()
    )
    if not row:
        logger.info("invite_code_not_found", code=upper_code)
        return "invalid_code"
    inviter_id = uuid.UUID(str(row["user_id"]))
    if inviter_id == invitee_id:
        return "self_invite"

    # Check if invitee already bound to any inviter
    existing = (
        await db.execute(
            text("SELECT id FROM user_invite_uses WHERE invitee_id = :invitee"),
            {"invitee": invitee_id},
        )
    ).fetchone()
    if existing:
        return "already_bound"

    eligible = (
        await db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM users
                    WHERE id = :uid
                      AND created_at >= NOW() - make_interval(hours => :hours)
                )
                AND NOT EXISTS (
                    SELECT 1 FROM afdian_orders
                    WHERE resolved_user_id = :uid AND fulfilled_at IS NOT NULL
                )
                """
            ),
            {"uid": invitee_id, "hours": (await load_invite_rules(db))["binding_hours"]},
        )
    ).scalar_one()
    if not eligible:
        return "binding_window_closed"

    inserted = (
        await db.execute(
            text(
                "INSERT INTO user_invite_uses (inviter_id, invitee_id, code) "
                "VALUES (:inviter, :invitee, :code) "
                "ON CONFLICT (invitee_id) DO NOTHING RETURNING id"
            ),
            {"inviter": inviter_id, "invitee": invitee_id, "code": upper_code},
        )
    ).fetchone()
    if inserted:
        from heart.invite.risk import score_binding

        await score_binding(db, int(inserted[0]), device_id, ip)
    logger.info("invite_signup_recorded", inviter=str(inviter_id), invitee=str(invitee_id))
    return "ok"


def daily_chance_limit(tier: str, rules: dict[str, int] | None = None) -> int:
    rules = rules or {
        "daily_limit_free": settings.invite_daily_limit_free,
        "daily_limit_plus": settings.invite_daily_limit_plus,
        "daily_limit_immersive": settings.invite_daily_limit_immersive,
    }
    return {
        "free": rules["daily_limit_free"],
        "plus": rules["daily_limit_plus"],
        "immersive": rules["daily_limit_immersive"],
    }.get(tier, rules["daily_limit_free"])


def _normalise_message(value: str) -> str:
    return " ".join(value.casefold().split())


def _valid_char_count(value: str) -> int:
    return sum(1 for char in value if char.isalnum())


async def _grant_chance(db: AsyncSession, inviter_id: uuid.UUID, use_id: int) -> bool:
    """Grant one chance under the inviter's tier cap, atomically and idempotently."""
    from heart.membership import get_effective_tier

    rules = await load_invite_rules(db)
    tier = await get_effective_tier(db, inviter_id)
    limit = daily_chance_limit(tier, rules)
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:uid AS text), 0))"),
        {"uid": str(inviter_id)},
    )
    pool = (
        (
            await db.execute(
                text(
                    """
                SELECT id, total_chances FROM lottery_pool_versions
                WHERE status = 'active' FOR UPDATE
                """
                )
            )
        )
        .mappings()
        .first()
    )
    if not pool:
        return False
    issued = int(
        (
            await db.execute(
                text("SELECT COUNT(*) FROM invite_draw_chances WHERE pool_id = :pool_id"),
                {"pool_id": pool["id"]},
            )
        ).scalar_one()
    )
    if issued >= int(pool["total_chances"]):
        return False
    today_count = int(
        (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) FROM invite_draw_chances
                    WHERE user_id = :uid
                      AND grant_day = DATE(NOW() AT TIME ZONE 'Asia/Shanghai')
                    """
                ),
                {"uid": inviter_id},
            )
        ).scalar_one()
    )
    if today_count >= limit:
        await db.execute(
            text(
                """
                UPDATE user_invite_uses
                SET chance_limit_reached_at = COALESCE(chance_limit_reached_at, NOW())
                WHERE id = :use_id
                """
            ),
            {"use_id": use_id},
        )
        return False

    inserted = (
        await db.execute(
            text(
                """
                INSERT INTO invite_draw_chances
                    (user_id, source, grant_day, daily_ordinal, expires_at, idem_key, pool_id)
                VALUES (
                    :uid,
                    :source,
                    DATE(NOW() AT TIME ZONE 'Asia/Shanghai'),
                    :ordinal,
                    NOW() + make_interval(days => :expiry_days),
                    :idem_key,
                    :pool_id
                )
                ON CONFLICT (idem_key) DO NOTHING
                RETURNING id
                """
            ),
            {
                "uid": inviter_id,
                "source": f"invite:{use_id}",
                "ordinal": today_count + 1,
                "expiry_days": rules["chance_expiry_days"],
                "idem_key": f"chance:invite:{use_id}",
                "pool_id": pool["id"],
            },
        )
    ).fetchone()
    if inserted:
        await db.execute(
            text(
                """
                UPDATE user_invite_uses
                SET chance_granted_at = COALESCE(chance_granted_at, NOW())
                WHERE id = :use_id
                """
            ),
            {"use_id": use_id},
        )
    return bool(inserted)


async def handle_invite_progress(
    db: AsyncSession,
    user_id: uuid.UUID,
    turn_id: uuid.UUID,
    user_text: str,
) -> None:
    """Record one successful chat turn and qualify an invite when all gates pass."""
    normalised = _normalise_message(user_text)
    char_count = _valid_char_count(normalised)
    if char_count == 0:
        return

    pending = (
        (
            await db.execute(
                text(
                    """
                    SELECT iu.id, iu.inviter_id, iu.risk_level
                    FROM user_invite_uses iu
                    WHERE iu.invitee_id = :uid AND iu.qualified_at IS NULL
                    """
                ),
                {"uid": user_id},
            )
        )
        .mappings()
        .fetchone()
    )
    if not pending:
        return

    rules = await load_invite_rules(db)

    use_id = int(pending["id"])
    event = (
        await db.execute(
            text(
                """
                INSERT INTO invite_qualification_events
                    (invite_use_id, turn_id, text_hash, valid_char_count)
                VALUES (:use_id, :turn_id, :text_hash, :valid_chars)
                ON CONFLICT (invite_use_id, turn_id) DO NOTHING
                RETURNING id
                """
            ),
            {
                "use_id": use_id,
                "turn_id": turn_id,
                "text_hash": sha256(normalised.encode("utf-8")).hexdigest(),
                "valid_chars": char_count,
            },
        )
    ).fetchone()
    if not event:
        return

    progress = (
        (
            await db.execute(
                text(
                    """
                    SELECT COUNT(*) AS msg_count,
                           COUNT(*) FILTER (WHERE ai_reply_completed) AS ai_reply_count,
                           COALESCE(SUM(valid_char_count), 0) AS valid_char_count,
                           COUNT(DISTINCT text_hash) AS distinct_message_count,
                           MIN(created_at) AS first_msg_at,
                           MAX(created_at) AS last_msg_at
                    FROM invite_qualification_events
                    WHERE invite_use_id = :use_id
                    """
                ),
                {"use_id": use_id},
            )
        )
        .mappings()
        .one()
    )
    await db.execute(
        text(
            """
            UPDATE user_invite_uses
            SET msg_count = :msg_count,
                ai_reply_count = :ai_reply_count,
                valid_char_count = :valid_char_count,
                first_msg_at = :first_msg_at
            WHERE id = :use_id
            """
        ),
        {
            "use_id": use_id,
            "msg_count": int(progress["msg_count"]),
            "ai_reply_count": int(progress["ai_reply_count"]),
            "valid_char_count": int(progress["valid_char_count"]),
            "first_msg_at": progress["first_msg_at"],
        },
    )

    # Qualification intentionally measures meaningful interaction volume only.
    # Age verification, AI reply count, a 120-second spread, and the original
    # seven-day registration window made the reward impossible to complete in
    # normal chat sessions and are no longer eligibility gates.
    qualified = (
        int(progress["msg_count"]) >= rules["min_messages"]
        and int(progress["valid_char_count"]) >= rules["min_valid_chars"]
        and int(progress["distinct_message_count"]) >= 2
    )
    if not qualified:
        return

    claimed = (
        await db.execute(
            text(
                """
                UPDATE user_invite_uses
                SET qualified_at = NOW(),
                    first_chat_at = COALESCE(first_chat_at, NOW()),
                    status = CASE risk_level
                        WHEN 'low' THEN 'qualified'
                        WHEN 'mid' THEN 'review'
                        ELSE 'rejected'
                    END
                WHERE id = :use_id
                  AND qualified_at IS NULL
                RETURNING inviter_id, risk_level
                """
            ),
            {
                "use_id": use_id,
            },
        )
    ).fetchone()
    if not claimed:
        return

    inviter_id = uuid.UUID(str(claimed[0]))
    if claimed[1] == "low":
        granted = await _grant_chance(db, inviter_id, use_id)
        from heart.commission.service import backfill_commissions_for_invitee

        await backfill_commissions_for_invitee(db, user_id)
        logger.info(
            "invite_qualified",
            inviter=str(inviter_id),
            invitee=str(user_id),
            chance_granted=granted,
        )


async def handle_first_chat(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Deprecated compatibility hook; first-chat fixed rewards were removed in V1."""
    logger.info("invite_first_chat_hook_deprecated", user_id=str(user_id))
