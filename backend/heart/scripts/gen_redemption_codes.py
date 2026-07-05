#!/usr/bin/env python3
"""Generate redemption codes and export to CSV.

Usage:
    python -m heart.scripts.gen_redemption_codes --count 100 --value 300 --batch batch-001
    python -m heart.scripts.gen_redemption_codes --count 50 --value 1800 --batch batch-002 --expires 2026-12-31

Output: writes to stdout as CSV + inserts into database.
"""

from __future__ import annotations

import argparse
import csv
import secrets
import sys
import uuid
from datetime import datetime, timezone

# Character set: no confusing chars (no 0/O, 1/I/L)
CHARSET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 12


def generate_code() -> str:
    """Generate a 12-character redemption code."""
    return "".join(secrets.choice(CHARSET) for _ in range(CODE_LENGTH))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate redemption codes")
    parser.add_argument("--count", type=int, required=True, help="Number of codes")
    parser.add_argument("--value", type=int, required=True, help="Credits value per code")
    parser.add_argument("--batch", type=str, default="", help="Batch ID for tracking")
    parser.add_argument("--expires", type=str, default=None, help="Expiration date (ISO)")
    parser.add_argument("--db", action="store_true", help="Insert into database")
    args = parser.parse_args()

    expires_at = None
    if args.expires:
        expires_at = datetime.fromisoformat(args.expires).replace(tzinfo=timezone.utc)

    codes = []
    for _ in range(args.count):
        code = generate_code()
        codes.append(
            {
                "id": str(uuid.uuid4()),
                "code": code,
                "credits_value": args.value,
                "batch_id": args.batch,
                "status": "active",
                "expires_at": expires_at.isoformat() if expires_at else "",
            }
        )

    # Output CSV to stdout
    writer = csv.DictWriter(
        sys.stdout, fieldnames=["code", "credits_value", "batch_id", "expires_at"]
    )
    writer.writeheader()
    for c in codes:
        writer.writerow(
            {
                "code": c["code"],
                "credits_value": c["credits_value"],
                "batch_id": c["batch_id"],
                "expires_at": c["expires_at"],
            }
        )

    print(
        f"\n# Generated {len(codes)} codes (value={args.value}, batch={args.batch})",
        file=sys.stderr,
    )

    # Optionally insert into DB
    if args.db:
        import asyncio

        asyncio.run(_insert_to_db(codes, expires_at))


async def _insert_to_db(codes: list[dict], expires_at: datetime | None) -> None:
    """Insert codes into database."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    from heart.core.config import settings

    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        for c in codes:
            await conn.execute(
                text("""
                    INSERT INTO redemption_codes (id, code, credits_value, batch_id, status, expires_at)
                    VALUES (:id, :code, :value, :batch, 'active', :expires)
                    ON CONFLICT (code) DO NOTHING
                """),
                {
                    "id": c["id"],
                    "code": c["code"],
                    "value": c["credits_value"],
                    "batch": c["batch_id"],
                    "expires": expires_at,
                },
            )
    await engine.dispose()
    print(f"# Inserted {len(codes)} codes into database", file=sys.stderr)


if __name__ == "__main__":
    main()
