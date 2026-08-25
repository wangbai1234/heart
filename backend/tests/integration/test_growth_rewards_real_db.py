"""Real-PostgreSQL integration tests for invite, lottery, coupons, and commission."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from heart.core.config import settings

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration,
    pytest.mark.requires_postgres,
]


@pytest_asyncio.fixture
async def growth_engine():
    engine = create_async_engine(settings.database_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def growth_user_factory(
    growth_engine,
) -> Callable[[], Awaitable[uuid.UUID]]:
    user_ids: list[uuid.UUID] = []

    async def create_user() -> uuid.UUID:
        user_id = uuid.uuid4()
        async with growth_engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO users (id, email, age_verified_at) VALUES (:uid, :email, NOW())"),
                {"uid": user_id, "email": f"growth-{user_id.hex}@test.invalid"},
            )
        user_ids.append(user_id)
        return user_id

    yield create_user

    cleanup_statements = (
        "DELETE FROM commission_ledger WHERE user_id = :uid",
        "DELETE FROM commission_entries WHERE inviter_id = :uid OR invitee_id = :uid",
        "DELETE FROM lottery_draws WHERE user_id = :uid",
        "DELETE FROM invite_draw_chances WHERE user_id = :uid",
        "DELETE FROM membership_reward_coupons WHERE user_id = :uid",
        "DELETE FROM user_memberships WHERE user_id = :uid",
        "DELETE FROM invite_qualification_events WHERE invite_use_id IN "
        "(SELECT id FROM user_invite_uses WHERE inviter_id = :uid OR invitee_id = :uid)",
        "DELETE FROM user_invite_uses WHERE inviter_id = :uid OR invitee_id = :uid",
        "DELETE FROM user_invite_codes WHERE user_id = :uid",
        "DELETE FROM credit_transactions WHERE user_id = :uid",
        "DELETE FROM users WHERE id = :uid",
    )
    async with growth_engine.begin() as conn:
        for user_id in reversed(user_ids):
            for statement in cleanup_statements:
                await conn.execute(text(statement), {"uid": user_id})


async def test_seeded_pool_has_exact_weight_and_prize_count(growth_engine):
    async with growth_engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT COUNT(*) AS prize_count, SUM(p.weight) AS total_weight
                    FROM lottery_prizes p
                    JOIN lottery_pool_versions v ON v.id = p.pool_id
                    WHERE v.status = 'active' AND p.enabled = TRUE
                    """
                    )
                )
            )
            .mappings()
            .one()
        )

    assert int(row["prize_count"]) == 10
    assert int(row["total_weight"]) == 10_000


async def test_concurrent_same_chance_creates_one_draw_and_reward(
    growth_engine, growth_user_factory, monkeypatch
):
    from heart.lottery.service import draw

    user_id = await growth_user_factory()
    async with growth_engine.begin() as conn:
        chance_id = int(
            (
                await conn.execute(
                    text(
                        """
                        INSERT INTO invite_draw_chances
                          (user_id, source, grant_day, daily_ordinal, expires_at,
                           idem_key, pool_id)
                        SELECT :uid, 'integration', CURRENT_DATE, 1, NOW() + INTERVAL '1 day',
                               :idem, id
                        FROM lottery_pool_versions WHERE status = 'active'
                        RETURNING id
                        """
                    ),
                    {"uid": user_id, "idem": f"integration-chance:{uuid.uuid4()}"},
                )
            ).scalar_one()
        )

    def choose_coin_20(prizes):
        return next(prize for prize in prizes if prize["code"] == "coin_20")

    monkeypatch.setattr("heart.lottery.service.choose_weighted", choose_coin_20)
    session_factory = async_sessionmaker(growth_engine, class_=AsyncSession, expire_on_commit=False)

    async def run_draw() -> dict:
        async with session_factory() as session, session.begin():
            return await draw(session, user_id, chance_id)

    first, second = await asyncio.gather(run_draw(), run_draw())
    assert first["id"] == second["id"]

    async with growth_engine.connect() as conn:
        draw_count = int(
            (
                await conn.execute(
                    text("SELECT COUNT(*) FROM lottery_draws WHERE chance_id = :chance_id"),
                    {"chance_id": chance_id},
                )
            ).scalar_one()
        )
        reward_count = int(
            (
                await conn.execute(
                    text(
                        "SELECT COUNT(*) FROM credit_transactions "
                        "WHERE user_id = :uid AND ref_type = 'lottery'"
                    ),
                    {"uid": user_id},
                )
            ).scalar_one()
        )
        balance = int(
            (
                await conn.execute(
                    text("SELECT credits_balance FROM users WHERE id = :uid"),
                    {"uid": user_id},
                )
            ).scalar_one()
        )

    assert draw_count == 1
    assert reward_count == 1
    assert balance == 2_000


async def test_free_daily_chance_cap_is_atomic(growth_engine, growth_user_factory):
    from heart.invite.service import _grant_chance

    inviter_id = await growth_user_factory()
    invitee_id = await growth_user_factory()
    async with growth_engine.begin() as conn:
        pool_id = int(
            (
                await conn.execute(
                    text("SELECT id FROM lottery_pool_versions WHERE status = 'active'")
                )
            ).scalar_one()
        )
        use_id = int(
            (
                await conn.execute(
                    text(
                        """
                        INSERT INTO user_invite_uses
                          (inviter_id, invitee_id, code, qualified_at, status)
                        VALUES (:inviter, :invitee, 'REALCAP1', NOW(), 'qualified')
                        RETURNING id
                        """
                    ),
                    {"inviter": inviter_id, "invitee": invitee_id},
                )
            ).scalar_one()
        )
        for ordinal in range(1, 6):
            await conn.execute(
                text(
                    """
                    INSERT INTO invite_draw_chances
                      (user_id, source, grant_day, daily_ordinal, expires_at, idem_key, pool_id)
                    VALUES (:uid, :source, CURRENT_DATE, :ordinal,
                            NOW() + INTERVAL '1 day', :idem, :pool_id)
                    """
                ),
                {
                    "uid": inviter_id,
                    "source": f"cap:{ordinal}",
                    "ordinal": ordinal,
                    "idem": f"cap:{inviter_id}:{ordinal}",
                    "pool_id": pool_id,
                },
            )

    session_factory = async_sessionmaker(growth_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session, session.begin():
        granted = await _grant_chance(session, inviter_id, use_id)
    assert granted is False

    async with growth_engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT chance_limit_reached_at FROM user_invite_uses WHERE id = :use_id"),
                {"use_id": use_id},
            )
        ).one()
    assert row[0] is not None


async def test_coupon_activation_schedules_after_existing_entitlements(
    growth_engine, growth_user_factory
):
    from heart.membership.coupons import activate_coupon, grant_coupon

    user_id = await growth_user_factory()
    async with growth_engine.begin() as conn:
        paid_expires = (await conn.execute(text("SELECT NOW() + INTERVAL '2 days'"))).scalar_one()
        await conn.execute(
            text(
                """
                INSERT INTO user_memberships (id, user_id, tier, expires_at, granted_by)
                VALUES (:id, :uid, 'plus', :expires_at, 'integration')
                """
            ),
            {"id": uuid.uuid4(), "uid": user_id, "expires_at": paid_expires},
        )

    session_factory = async_sessionmaker(growth_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session, session.begin():
        first_id = await grant_coupon(
            session, user_id, "plus", 3, "integration", f"coupon:{uuid.uuid4()}"
        )
        second_id = await grant_coupon(
            session, user_id, "immersive", 3, "integration", f"coupon:{uuid.uuid4()}"
        )
        first = await activate_coupon(session, user_id, first_id)
        second = await activate_coupon(session, user_id, second_id)

    assert first["starts_at"] >= paid_expires
    assert second["starts_at"] == first["expires_at"]


async def test_commission_settle_reverse_and_spend_are_idempotent(
    growth_engine, growth_user_factory
):
    from heart.commission.service import (
        apply_ledger_delta,
        reverse_commission_by_order,
        settle_due_commissions,
        spend_commission,
    )

    inviter_id = await growth_user_factory()
    invitee_id = await growth_user_factory()
    order_id = f"integration-{uuid.uuid4()}"
    async with growth_engine.begin() as conn:
        await conn.execute(
            text(
                """
                INSERT INTO commission_entries
                  (inviter_id, invitee_id, order_id, paid_fen, commission_fen,
                   settle_at, idem_key)
                VALUES (:inviter, :invitee, :order_id, 29000, 2900,
                        NOW() - INTERVAL '1 second', :idem)
                """
            ),
            {
                "inviter": inviter_id,
                "invitee": invitee_id,
                "order_id": order_id,
                "idem": f"commission:{order_id}",
            },
        )

    session_factory = async_sessionmaker(growth_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session, session.begin():
        assert await settle_due_commissions(session) >= 1
    async with session_factory() as session, session.begin():
        assert await reverse_commission_by_order(session, order_id) is True

    spend_token = uuid.uuid4().hex
    async with session_factory() as session, session.begin():
        await apply_ledger_delta(
            session,
            inviter_id,
            6900,
            "integration_grant",
            "integration",
            f"integration-credit:{spend_token}",
            allow_negative=True,
        )
        spent = await spend_commission(session, inviter_id, "membership", "plan_plus", spend_token)
    assert spent["applied"] is True
    assert spent["balance_fen"] == 4000

    async with session_factory() as session, session.begin():
        repeated = await spend_commission(
            session, inviter_id, "membership", "plan_plus", spend_token
        )
    assert repeated["applied"] is False
    assert repeated["balance_fen"] == 4000

    async with growth_engine.connect() as conn:
        row = (
            (
                await conn.execute(
                    text(
                        """
                    SELECT u.commission_balance_fen,
                           COUNT(m.id) FILTER (WHERE m.granted_by = :granted_by) AS memberships
                    FROM users u
                    LEFT JOIN user_memberships m ON m.user_id = u.id
                    WHERE u.id = :uid
                    GROUP BY u.id
                    """
                    ),
                    {"uid": inviter_id, "granted_by": f"commission:{spend_token}"},
                )
            )
            .mappings()
            .one()
        )
        cancelled = (
            await conn.execute(
                text("SELECT status FROM commission_entries WHERE order_id = :order_id"),
                {"order_id": order_id},
            )
        ).scalar_one()

    assert int(row["commission_balance_fen"]) == 4000
    assert int(row["memberships"]) == 1
    assert cancelled == "cancelled"
