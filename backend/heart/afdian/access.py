"""Afdian payment entitlement checks used by production access gates."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from heart.core.config import settings

_PRODUCTION_VALUES = frozenset({"prod", "production", "live"})


def is_production_environment() -> bool:
    """Return whether production-only product gates should be enforced.

    ``ENVIRONMENT`` is the canonical setting. ``HEART_ENV`` is accepted as a
    deployment alias because older production compose files used that name.
    """

    return any(
        str(value or "").strip().lower() in _PRODUCTION_VALUES
        for value in (settings.environment, settings.heart_env)
    )


async def has_fulfilled_afdian_order(db: AsyncSession, user_id: uuid.UUID) -> bool:
    """Whether *user_id* has at least one successfully fulfilled Afdian order.

    ``fulfilled_at`` is deliberately used instead of merely checking that an
    order was received: unmatched or unknown-SKU orders are not proof that the
    payment was linked to this account. The query also covers coin-only orders,
    which are still valid evidence that the user paid through Afdian.
    """

    result = await db.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM afdian_orders
                WHERE resolved_user_id = :uid
                  AND fulfilled_at IS NOT NULL
            )
            """
        ),
        {"uid": user_id},
    )
    return bool(result.scalar())
