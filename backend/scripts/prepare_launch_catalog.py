"""Prepare reviewed launch adaptations on a loopback restored database only.

Never alters a source character, its visibility, or chats. Each adaptation gets
its own ID and immutable provenance in the private local_review schema.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from heart.core.config import settings
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss01_soul.spec_store import insert_spec

ROOT = Path(__file__).resolve().parents[2]


def make_draft(item: dict, source: dict) -> CharacterDraft:
    lang = item['locale']
    label = {'ja': ('物語の始まり', '言語', '形式', '成人の架空キャラクター。選択はあなた自身で。'),
             'ko': ('이야기의 시작', '언어', '구성', '성인 가상 캐릭터입니다. 선택은 당신에게 있어요.'),
             'en': ('Where the story begins', 'Language', 'Cast', 'Fictional adult characters. Your choices remain yours.')}[lang]
    cast = {'ja': {'single': '単独', 'multiple': '複数'}, 'ko': {'single': '단일', 'multiple': '여러 인물'}, 'en': {'single': 'Single', 'multiple': 'Ensemble'}}[lang][item['cast_type']]
    return CharacterDraft(
        display_name={lang: item['name']}, persona=item['persona'], intro=item['intro'],
        tagline=item['tagline'], opening=item['opening'], locale=lang, response_language=lang,
        tags=item['tags'], cast_type=item['cast_type'], content_rating='general',
        greeting_style=item['greeting_style'], gender=item['gender'], visibility='public',
        creation_mode='workshop', cover_url=source.get('cover_url'),
        ui_chrome=(source.get('draft') or {}).get('ui_chrome'),
        premise_card={'accent': '#8b749b', 'leadIn': item['tagline'], 'title': label[0],
            'rows': [{'label': label[1], 'value': {'ja':'日本語','ko':'한국어','en':'English'}[lang]}, {'label':label[2], 'value':cast}], 'note':label[3]},
        profile_blocks=[{'type':'prose', 'title':label[0], 'text': item['intro']}],
    )


async def main(apply: bool) -> None:
    url = make_url(settings.database_url)
    if url.host not in {'localhost', '127.0.0.1'} or url.database != 'heart_review':
        raise SystemExit('This script is restricted to local heart_review; never run on production.')
    items = json.loads((ROOT/'docs/international/launch_catalog.json').read_text())
    engine = create_async_engine(settings.database_url)
    try:
        async with engine.begin() as db:
            if apply:
                await db.execute(text('''CREATE TABLE IF NOT EXISTS local_review.international_adaptations (
                    character_id TEXT PRIMARY KEY, source_character_id TEXT NOT NULL,
                    source_sha256 TEXT NOT NULL, source_snapshot JSONB NOT NULL,
                    adapted_draft JSONB NOT NULL, market TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'editorial_draft', created_at TIMESTAMPTZ NOT NULL DEFAULT NOW())'''))
            for item in items:
                result = await db.execute(text("SELECT c.cover_url, c.owner_user_id, c.visibility, c.status, c.review_status, s.draft, s.spec FROM characters c JOIN soul_specs s ON s.character_id=c.id AND s.status='active' WHERE c.id=:id"), {'id':item['source_character_id']})
                source = dict(result.mappings().one())
                if source['owner_user_id'] is not None or source['visibility'] != 'public' or source['review_status'] != 'approved':
                    raise ValueError('Only original public first-party sources are eligible')
                draft = make_draft(item, source)
                spec = build_soul_spec_from_draft(draft, character_id=item['id'])
                snapshot = json.dumps(source, ensure_ascii=False, sort_keys=True, default=str)
                print(item['id'], item['market'], 'validated')
                if not apply:
                    continue
                inserted = await db.execute(text("INSERT INTO characters (id,visibility,status,soul_spec_version,tags,cover_url,review_status) VALUES (:id,'public','active',:version,CAST(:tags AS jsonb),:cover,'approved') ON CONFLICT (id) DO NOTHING RETURNING id"), {'id':item['id'], 'version':spec.spec_version, 'tags':json.dumps(item['tags']), 'cover':draft.cover_url})
                if not inserted.scalar_one_or_none():
                    continue
                await insert_spec(db, character_id=item['id'], spec_version=spec.spec_version, spec=spec.model_dump(mode='json'), draft=draft.model_dump(mode='json'))
                await db.execute(text('INSERT INTO local_review.international_adaptations (character_id,source_character_id,source_sha256,source_snapshot,adapted_draft,market) VALUES (:id,:source,:hash,CAST(:snapshot AS jsonb),CAST(:draft AS jsonb),:market)'), {'id':item['id'], 'source':item['source_character_id'], 'hash':hashlib.sha256(snapshot.encode()).hexdigest(), 'snapshot':snapshot, 'draft':draft.model_dump_json(), 'market':item['market']})
    finally:
        await engine.dispose()


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    asyncio.run(main(parser.parse_args().apply))
