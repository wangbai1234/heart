"""Seed original international characters. Run from backend; dry-run by default."""

import argparse
import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from heart.core.config import settings
from heart.international_catalog import CHARACTERS
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss01_soul.spec_store import insert_spec


async def main(apply: bool) -> None:
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as db:
            for character in CHARACTERS:
                cid = character["id"]
                draft = CharacterDraft(
                    display_name=character["names"],
                    persona=character["persona"],
                    intro=character["persona"][:500],
                    tagline=character["taglines"][character["locale"]],
                    opening=character["opening"],
                    locale=character["locale"],
                    visibility="public",
                    greeting_style=character["greeting_style"],
                    gender=character["gender"],
                    age_range="25-39",
                    creation_mode="workshop",
                    cover_url=f"/international/{cid}.svg",
                )
                spec = build_soul_spec_from_draft(draft, character_id=cid)
                print(f"{'seed' if apply else 'validate'}: {cid}")
                if not apply:
                    continue
                # Never replace existing characters, authored specs or user content.
                inserted = await db.execute(
                    text("""
                    INSERT INTO characters (id, visibility, status, soul_spec_version,
                        tags, cover_url, review_status)
                    VALUES (:cid, 'public', 'active', :version, CAST(:tags AS jsonb), :cover, 'approved')
                    ON CONFLICT (id) DO NOTHING RETURNING id
                """),
                    {
                        "cid": cid,
                        "version": spec.spec_version,
                        "tags": json.dumps([]),
                        "cover": draft.cover_url,
                    },
                )
                if inserted.scalar_one_or_none() is None:
                    print(f"already exists: {cid}")
                    continue
                await insert_spec(
                    db,
                    character_id=cid,
                    spec_version=spec.spec_version,
                    source="ugc",
                    spec=spec.model_dump(mode="json"),
                    draft=draft.model_dump(mode="json"),
                )
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    asyncio.run(main(parser.parse_args().apply))
