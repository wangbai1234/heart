"""Helpers for ensuring monthly PostgreSQL range partitions exist."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def month_bounds(created_at: datetime) -> tuple[datetime, datetime]:
    """Return UTC-aligned month start and next month boundary."""
    if created_at.tzinfo is None:
        ts = created_at.replace(tzinfo=timezone.utc)
    else:
        ts = created_at.astimezone(timezone.utc)
    month_start = ts.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)
    return month_start, next_month


async def ensure_monthly_partition(
    session: AsyncSession,
    *,
    parent_table: str,
    partition_prefix: str,
    created_at: datetime,
    cache: Optional[set[str]] = None,
) -> str:
    """Create the monthly partition if it does not already exist.

    DDL on asyncpg cannot use bind parameters, so the date literals are rendered
    directly from internal datetimes in a fixed YYYY-MM-DD format.
    """
    month_start, next_month = month_bounds(created_at)
    partition_name = f"{partition_prefix}_{month_start:%Y_%m}"
    if cache is not None and partition_name in cache:
        return partition_name

    await session.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF {parent_table}
            FOR VALUES FROM ('{month_start:%Y-%m-%d}') TO ('{next_month:%Y-%m-%d}')
            """
        )
    )

    if cache is not None:
        cache.add(partition_name)
    return partition_name
