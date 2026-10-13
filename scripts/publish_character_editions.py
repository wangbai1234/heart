#!/usr/bin/env python3
"""Check or atomically publish an exact owner-authorized character package."""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from heart.core.config import settings
from heart.localization.release import import_release, validate_release
from sqlalchemy.ext.asyncio import create_async_engine


async def run(args) -> None:
    records = json.loads(args.package.read_text(encoding="utf-8"))
    receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
    validate_release(records, receipt)
    if not args.apply:
        print(json.dumps({"validated": len(records), "release": receipt["release_id"]}))
        return
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as db:
            ids = await import_release(db, records, receipt=receipt)
        print(json.dumps({"published": len(ids), "release": receipt["release_id"], "human_reviewed": False}))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    asyncio.run(run(parser.parse_args()))
