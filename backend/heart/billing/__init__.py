"""Billing service — credits ledger operations.

All operations are atomic: write ledger entry + update cached balance
in the same DB transaction. Balance never goes negative (CHECK constraint).
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

logger = structlog.get_logger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user has insufficient credits for an operation."""

    def __init__(self, needed: int, balance: int) -> None:
        self.needed = needed
        self.balance = balance
        super().__init__(f"Insufficient credits: need {needed}, have {balance}")


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key already exists with different data."""


async def get_balance(db: AsyncSession, user_id: uuid.UUID) -> int:
    """Get current credits balance for user."""
    result = await db.execute(
        text("SELECT credits_balance FROM users WHERE id = :uid"),
        {"uid": user_id},
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise ValueError(f"User {user_id} not found")
    return row


async def grant(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    idempotency_key: str,
    type_str: str = "grant",
    ref_type: Optional[str] = None,
    ref_id: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> int:
    """Grant credits (signup bonus, manual adjustment).

    Returns new balance. Idempotent — duplicate key returns existing balance.
    type_str must be one of the contract §0.1 enum values (grant/invite/membership_grant/…).
    """
    import json

    tx_id = uuid.uuid4()
    try:
        result = await db.execute(
            text("""
                WITH updated AS (
                    UPDATE users SET credits_balance = credits_balance + :delta
                    WHERE id = :uid
                    RETURNING credits_balance AS balance_after
                )
                INSERT INTO credit_transactions (id, user_id, delta, balance_after, type, ref_type, ref_id, idempotency_key, metadata)
                SELECT :tx_id, :uid, :delta, updated.balance_after, :type_str, :ref_type, :ref_id, :idem_key, :meta
                FROM updated
                ON CONFLICT (idempotency_key) DO NOTHING
                RETURNING balance_after
            """),
            {
                "tx_id": tx_id,
                "uid": user_id,
                "delta": amount,
                "type_str": type_str,
                "ref_type": ref_type,
                "ref_id": ref_id,
                "idem_key": idempotency_key,
                "meta": json.dumps(metadata) if metadata else None,
            },
        )
        new_balance = result.scalar_one_or_none()
        if new_balance is not None:
            await db.commit()
            logger.info("credits_granted", user_id=str(user_id), amount=amount, balance=new_balance)
            return new_balance

        # Idempotency hit — return current balance
        await db.rollback()
        return await get_balance(db, user_id)
    except Exception:
        await db.rollback()
        raise


async def redeem(
    db: AsyncSession,
    user_id: uuid.UUID,
    code: str,
) -> int:
    """Redeem a redemption code. Returns new balance.

    Raises ValueError if code invalid/used/expired.
    """
    # Lock the code row
    result = await db.execute(
        text("""
            SELECT id, credits_value, status, expires_at
            FROM redemption_codes
            WHERE code = :code
            FOR UPDATE
        """),
        {"code": code.upper().strip()},
    )
    row = result.mappings().first()

    if row is None:
        await db.rollback()
        raise ValueError("无效的兑换码")

    if row["status"] == "redeemed":
        await db.rollback()
        raise ValueError("该兑换码已被使用")

    if row["status"] == "disabled":
        await db.rollback()
        raise ValueError("该兑换码已失效")

    if row["expires_at"] and row["expires_at"].timestamp() < __import__("time").time():
        await db.rollback()
        raise ValueError("该兑换码已过期")

    credits_value = row["credits_value"]
    tx_id = uuid.uuid4()

    # Mark code as redeemed
    await db.execute(
        text("""
            UPDATE redemption_codes
            SET status = 'redeemed', redeemed_by = :uid, redeemed_at = NOW()
            WHERE id = :code_id
        """),
        {"uid": user_id, "code_id": row["id"]},
    )

    # Atomic balance update + ledger entry
    result = await db.execute(
        text("""
            WITH updated AS (
                UPDATE users SET credits_balance = credits_balance + :delta
                WHERE id = :uid
                RETURNING credits_balance AS balance_after
            )
            INSERT INTO credit_transactions (id, user_id, delta, balance_after, type, ref_type, ref_id, idempotency_key)
            SELECT :tx_id, :uid, :delta, updated.balance_after, 'redeem', 'redemption', :code, :idem_key
            FROM updated
            RETURNING balance_after
        """),
        {
            "tx_id": tx_id,
            "uid": user_id,
            "delta": credits_value,
            "code": code.upper().strip(),
            "idem_key": f"redeem:{code.upper().strip()}",
        },
    )
    new_balance = result.scalar_one()
    await db.commit()

    logger.info(
        "code_redeemed",
        user_id=str(user_id),
        code=code[:4] + "***",
        credited=credits_value,
        balance=new_balance,
    )
    return new_balance


async def charge_turn(
    db: AsyncSession,
    user_id: uuid.UUID,
    turn_id: str,
    modality: str,
) -> int:
    """Charge credits for a completed turn. Returns new balance.

    modality: 'text' or 'voice'
    Idempotent — duplicate turn_id returns existing balance.
    """
    if modality == "voice":
        amount = settings.credits_per_voice_turn
    else:
        amount = settings.credits_per_text_turn

    idempotency_key = f"turn:{turn_id}"
    tx_id = uuid.uuid4()

    result = await db.execute(
        text("""
            WITH updated AS (
                UPDATE users SET credits_balance = credits_balance - :delta
                WHERE id = :uid AND credits_balance >= :delta
                RETURNING credits_balance AS balance_after
            )
            INSERT INTO credit_transactions (id, user_id, delta, balance_after, type, ref_type, ref_id, idempotency_key)
            SELECT :tx_id, :uid, -:delta, updated.balance_after, :type, 'turn', :turn_id, :idem_key
            FROM updated
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING balance_after
        """),
        {
            "tx_id": tx_id,
            "uid": user_id,
            "delta": amount,
            "type": f"consume_{modality}",
            "turn_id": turn_id,
            "idem_key": idempotency_key,
        },
    )
    new_balance = result.scalar_one_or_none()

    if new_balance is not None:
        await db.commit()
        logger.info(
            "turn_charged",
            user_id=str(user_id),
            turn_id=turn_id,
            modality=modality,
            amount=amount,
            balance=new_balance,
        )
        return new_balance

    # Idempotency hit or insufficient balance
    await db.rollback()

    # Check if it was an idempotency hit (already charged)
    existing = await db.execute(
        text("SELECT balance_after FROM credit_transactions WHERE idempotency_key = :key"),
        {"key": idempotency_key},
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        return existing_row

    # Insufficient balance
    balance = await get_balance(db, user_id)
    raise InsufficientCreditsError(needed=amount, balance=balance)


async def deduct_credits(
    db: AsyncSession,
    user_id: uuid.UUID,
    amount: int,
    idempotency_key: str,
    type_str: str = "consume_text",
) -> int:
    """Deduct *amount* fen from the user balance. Returns new balance in fen.

    Idempotent: a duplicate *idempotency_key* with the same amount returns the
    previously recorded ``balance_after`` without re-deducting.

    Raises InsufficientCreditsError when the balance would go negative.
    """
    tx_id = uuid.uuid4()

    result = await db.execute(
        text("""
            WITH updated AS (
                UPDATE users SET credits_balance = credits_balance - :delta
                WHERE id = :uid AND credits_balance >= :delta
                RETURNING credits_balance AS balance_after
            )
            INSERT INTO credit_transactions
                (id, user_id, delta, balance_after, type, ref_type, ref_id, idempotency_key)
            SELECT :tx_id, :uid, -:delta, updated.balance_after,
                   :type, 'message', :idem_key, :idem_key
            FROM updated
            ON CONFLICT (idempotency_key) DO NOTHING
            RETURNING balance_after
        """),
        {
            "tx_id": tx_id,
            "uid": user_id,
            "delta": amount,
            "type": type_str,
            "idem_key": idempotency_key,
        },
    )
    new_balance = result.scalar_one_or_none()

    if new_balance is not None:
        logger.debug(
            "credits_deducted",
            user_id=str(user_id),
            amount=amount,
            balance=new_balance,
            idem_key=idempotency_key,
        )
        return new_balance

    # Idempotency hit or insufficient balance — check which
    existing = await db.execute(
        text("SELECT balance_after FROM credit_transactions WHERE idempotency_key = :key"),
        {"key": idempotency_key},
    )
    existing_row = existing.scalar_one_or_none()
    if existing_row is not None:
        return existing_row

    balance = await get_balance(db, user_id)
    raise InsufficientCreditsError(needed=amount, balance=balance)


async def refund(
    db: AsyncSession,
    user_id: uuid.UUID,
    turn_id: str,
    amount: int,
    reason: str = "safety_blocked",
) -> int:
    """Refund credits for a blocked/failed turn. Returns new balance."""
    tx_id = uuid.uuid4()

    result = await db.execute(
        text("""
            WITH updated AS (
                UPDATE users SET credits_balance = credits_balance + :delta
                WHERE id = :uid
                RETURNING credits_balance AS balance_after
            )
            INSERT INTO credit_transactions (id, user_id, delta, balance_after, type, ref_type, ref_id, idempotency_key, metadata)
            SELECT :tx_id, :uid, :delta, updated.balance_after, 'refund', 'turn', :turn_id, :idem_key, :meta
            FROM updated
            RETURNING balance_after
        """),
        {
            "tx_id": tx_id,
            "uid": user_id,
            "delta": amount,
            "turn_id": turn_id,
            "idem_key": f"refund:{turn_id}",
            "meta": f'{{"reason": "{reason}"}}',
        },
    )
    new_balance = result.scalar_one()
    await db.commit()
    logger.info(
        "turn_refunded", user_id=str(user_id), turn_id=turn_id, amount=amount, balance=new_balance
    )
    return new_balance
