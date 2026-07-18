"""Invite system service — per yuoyuocoin_plan §6."""

from __future__ import annotations

import secrets
import string
import uuid

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.billing import grant as grant_credits
from heart.core.config import settings

logger = structlog.get_logger(__name__)

_CODE_ALPHABET = string.ascii_uppercase + string.digits
_CODE_LEN = 8


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


async def record_invite_signup(db: AsyncSession, invitee_id: uuid.UUID, code: str) -> str:
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

    await db.execute(
        text(
            "INSERT INTO user_invite_uses (inviter_id, invitee_id, code) "
            "VALUES (:inviter, :invitee, :code) "
            "ON CONFLICT (invitee_id) DO NOTHING"
        ),
        {"inviter": inviter_id, "invitee": invitee_id, "code": upper_code},
    )
    logger.info("invite_signup_recorded", inviter=str(inviter_id), invitee=str(invitee_id))
    return "ok"


async def handle_first_chat(db: AsyncSession, user_id: uuid.UUID) -> None:
    """Grant invite rewards when an invited user completes their first chat turn.

    Idempotent: the UPDATE WHERE first_chat_at IS NULL ensures rewards are
    granted exactly once even under concurrent calls.
    """
    # Fast path: most users have no invite record
    pending = (
        (
            await db.execute(
                text(
                    "SELECT id, inviter_id FROM user_invite_uses "
                    "WHERE invitee_id = :uid AND first_chat_at IS NULL"
                ),
                {"uid": user_id},
            )
        )
        .mappings()
        .fetchone()
    )
    if not pending:
        return

    use_id: int = pending["id"]
    inviter_id: uuid.UUID = uuid.UUID(str(pending["inviter_id"]))

    # Atomic claim — prevents double-grant under concurrency
    claimed = (
        await db.execute(
            text(
                "UPDATE user_invite_uses SET first_chat_at = NOW() "
                "WHERE id = :id AND first_chat_at IS NULL RETURNING id"
            ),
            {"id": use_id},
        )
    ).fetchone()
    if not claimed:
        return  # another request beat us

    grant_fen = settings.invite_referral_grant_coins * 100

    # Invitee bonus
    await grant_credits(
        db,
        user_id,
        grant_fen,
        idempotency_key=f"invite:invitee:{use_id}",
        type_str="invite",
        ref_type="invite",
    )
    # Inviter reward
    await grant_credits(
        db,
        inviter_id,
        grant_fen,
        idempotency_key=f"invite:inviter:{use_id}",
        type_str="invite",
        ref_type="invite",
    )
    logger.info(
        "invite_first_chat_rewarded",
        inviter=str(inviter_id),
        invitee=str(user_id),
        fen=grant_fen,
    )

    # Milestone bonuses (idempotent via idempotency keys in the ledger)
    count_row = (
        await db.execute(
            text(
                "SELECT COUNT(*) AS cnt FROM user_invite_uses "
                "WHERE inviter_id = :uid AND first_chat_at IS NOT NULL"
            ),
            {"uid": inviter_id},
        )
    ).fetchone()
    cnt = int(count_row[0]) if count_row else 0

    milestones = [
        (10, settings.invite_milestone_10_coins, "milestone_10_at"),
        (5, settings.invite_milestone_5_coins, "milestone_5_at"),
    ]
    for threshold, bonus_coins, col in milestones:
        if cnt >= threshold:
            # Try to mark milestone (idempotent, picks any un-marked row for this inviter)
            marked = (
                await db.execute(
                    text(
                        f"UPDATE user_invite_uses "  # noqa: S608
                        f"SET {col} = NOW() "
                        f"WHERE id = ("
                        f"  SELECT id FROM user_invite_uses "
                        f"  WHERE inviter_id = :uid AND {col} IS NULL "
                        f"  LIMIT 1"
                        f") RETURNING id"
                    ),
                    {"uid": inviter_id},
                )
            ).fetchone()
            if marked:
                bonus_fen = bonus_coins * 100
                await grant_credits(
                    db,
                    inviter_id,
                    bonus_fen,
                    idempotency_key=f"invite:milestone:{threshold}:{inviter_id}",
                    type_str="invite",
                    ref_type="invite",
                )
                logger.info(
                    "invite_milestone_granted",
                    inviter=str(inviter_id),
                    milestone=threshold,
                    bonus_fen=bonus_fen,
                )
