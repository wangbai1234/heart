"""Local editorial import → real HTTP catalog/profile; no paid model calls."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from heart.locales import RESOURCE_VERSION
from heart.localization.batch import SOURCE_SQL, digest
from heart.localization.edition_import import import_preview
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from tests.e2e.test_international_release import login
from tests.e2e.test_locale_batch_import import isolated_url

pytestmark = pytest.mark.e2e


def test_preview_import_discovery_and_profile(api_context, pg_conn):
    token = login(api_context, str(uuid4()))
    headers = {'Authorization': f'Bearer {token}'}
    response = api_context.post('/api/characters', headers=headers, data={
        'display_name': {'zh': '原版书店店主'}, 'locale': 'zh',
        'persona': 'An adult bookseller with a long personal history.',
        'creation_mode': 'workshop', 'visibility': 'private'})
    assert response.ok, response.text()
    source = response.json()['id']
    with pg_conn.cursor() as cursor:
        cursor.execute("UPDATE characters SET visibility='public', review_status='approved' WHERE id=%s", (source,))
    pg_conn.commit()
    with ThreadPoolExecutor(max_workers=1) as pool:
        ids = pool.submit(lambda: asyncio.run(import_and_check(source))).result()
    for locale, cid in ids.items():
        response = api_context.get('/api/characters', headers={'Accept-Language': locale})
        assert response.ok, response.text()
        rows = response.json()['characters']
        entry = next(r for r in rows if r['id'] == cid)
        assert entry['local_preview'] and entry['review_status'] == 'pending'
        assert entry['visibility'] == 'private' and entry['language_priority'] == 0
        assert not entry['discovery_hidden']
        assert next(r for r in rows if r['id'] == source)['discovery_hidden']
        for other in set(ids.values()) - {cid}:
            assert next(r for r in rows if r['id'] == other)['discovery_hidden']
        response = api_context.get(f'/api/characters/{cid}/profile', headers={'Accept-Language': locale})
        assert response.ok, response.text()
        assert response.json()['display_name'] == {'en': 'Evan', 'vi': 'Minh', 'bn': 'আরিফ'}[locale]
        assert api_context.post(f'/api/characters/{cid}/view', headers=headers).ok
    zh = api_context.get('/api/characters', headers={'Accept-Language': 'zh'}).json()['characters']
    assert not next(r for r in zh if r['id'] == source)['discovery_hidden']
    companions = api_context.get('/api/companions', headers=headers)
    assert companions.ok, companions.text()
    assert set(ids.values()) <= {c['character_id'] for c in companions.json()['companions']}


async def import_and_check(source_id):
    engine = create_async_engine(isolated_url())
    records = []
    try:
        async with engine.begin() as db:
            source = dict((await db.execute(text(SOURCE_SQL), {'id': source_id})).mappings().one())
            for locale, name in [('en', 'Evan'), ('vi', 'Minh'), ('bn', 'আরিফ')]:
                cid = 'edition_' + locale + '_' + uuid4().hex[:16]
                draft = CharacterDraft.model_validate({**source['draft'], 'visibility': 'private',
                    'locale': locale, 'response_language': locale,
                    'display_name': {'localized': {locale: name}}})
                spec = build_soul_spec_from_draft(draft, character_id=cid)
                records.append(dict(id=cid, source_id=source_id, source_sha256=digest(source),
                    locale=locale, draft=draft.model_dump(mode='json'), spec=spec.model_dump(mode='json'),
                    resource_version=RESOURCE_VERSION, human_reviewed=False, published=False,
                    review_status='editorial_draft'))
            first = await import_preview(db, records, batch_id=source_id)
            assert await import_preview(db, records, batch_id=source_id) == first
        with pytest.raises(ValueError, match='Source changed'):
            async with engine.begin() as db:
                await db.execute(text("UPDATE characters SET tags='[\"changed\"]'::jsonb WHERE id=:id"), {'id': source_id})
                await import_preview(db, records, batch_id=source_id)
        with pytest.raises(ValueError, match='already exists'):
            async with engine.begin() as db:
                changed = {**records[0], 'draft': {**records[0]['draft'], 'persona': 'A changed adult bookseller with a different history.'}}
                changed['spec'] = build_soul_spec_from_draft(CharacterDraft.model_validate(changed['draft']), character_id=changed['id']).model_dump(mode='json')
                await import_preview(db, [changed], batch_id=source_id)
        async with engine.begin() as db:
            assert await import_preview(db, records, batch_id=source_id) == first
        return {r['locale']: r['id'] for r in records}
    finally:
        await engine.dispose()
