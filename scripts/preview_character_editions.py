#!/usr/bin/env python3
"""Import an editorial package into a local acceptance database only."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from heart.core.config import settings
from heart.localization.edition_import import import_preview


async def run(package: Path, batch: str) -> None:
    records = json.loads(package.read_text(encoding='utf-8'))
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as db:
            ids = await import_preview(db, records, batch_id=batch)
        print(json.dumps({'imported': len(ids), 'visibility': 'private', 'review_status': 'pending'}))
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    asyncio.run(run(args.package, args.batch))
