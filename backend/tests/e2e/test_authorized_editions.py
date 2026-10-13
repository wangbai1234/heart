"""Owner release through real PostgreSQL and HTTP; synthetic authorization only."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from heart.locales import RESOURCE_VERSION
from heart.localization.batch import SOURCE_SQL, digest
from heart.localization.release import import_release
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from tests.e2e.test_international_release import login
from tests.e2e.test_locale_batch_import import isolated_url

pytestmark = pytest.mark.e2e


def test_owner_publication_is_atomic_idempotent_and_discoverable(api_context, pg_conn):
    token = login(api_context, str(uuid4()))
    response = api_context.post('/api/characters', headers={'Authorization': f'Bearer {token}'}, data={
        'display_name': {'zh': '发布测试书店店主'}, 'locale': 'zh',
        'persona': 'An adult bookseller with a long personal history.',
        'creation_mode': 'workshop', 'visibility': 'private'})
    assert response.ok, response.text()
    source = response.json()['id']
    with pg_conn.cursor() as cursor:
        cursor.execute("UPDATE characters SET visibility='public', review_status='approved' WHERE id=%s", (source,))
    pg_conn.commit()
    with ThreadPoolExecutor(max_workers=1) as pool:
        ids = pool.submit(lambda: asyncio.run(publish_and_check(source))).result()
    for locale, cid in ids.items():
        response = api_context.get('/api/characters', headers={'Accept-Language': locale})
        assert response.ok, response.text()
        rows = response.json()['characters']
        entry = next(r for r in rows if r['id'] == cid)
        assert not entry.get('local_preview') and entry['review_status'] == 'approved'
        assert entry['visibility'] == 'public' and entry['language_priority'] == 0
        assert not entry['discovery_hidden']
        assert next(r for r in rows if r['id'] == source)['discovery_hidden']
        assert all(next(r for r in rows if r['id'] == other)['discovery_hidden']
                   for other in set(ids.values()) - {cid})
        profile = api_context.get(f'/api/characters/{cid}/profile', headers={'Accept-Language': locale})
        assert profile.ok, profile.text()
    zh = api_context.get('/api/characters', headers={'Accept-Language': 'zh'}).json()['characters']
    assert not next(r for r in zh if r['id'] == source)['discovery_hidden']


async def publish_and_check(source_id):
    engine = create_async_engine(isolated_url())
    try:
        async with engine.connect() as db:
            source = dict((await db.execute(text(SOURCE_SQL), {'id': source_id})).mappings().one())
        records = []
        for locale, name in [('en', 'Evan'), ('vi', 'Minh'), ('bn', 'আরিফ')]:
            cid = 'release_' + locale + '_' + uuid4().hex[:16]
            draft = CharacterDraft.model_validate({**source['draft'], 'visibility': 'public',
                'locale': locale, 'response_language': locale,
                'display_name': {'localized': {locale: name}}})
            spec = build_soul_spec_from_draft(draft, character_id=cid)
            records.append(dict(id=cid, source_id=source_id, source_sha256=digest(source),
                locale=locale, draft=draft.model_dump(mode='json'), spec=spec.model_dump(mode='json'),
                resource_version=RESOURCE_VERSION, human_reviewed=False, published=True,
                review_status='owner_authorized_release'))
        receipt = dict(schema_version=1, release_id='synthetic-test', batch_id=source_id,
            authorization=dict(by='project_owner', request='SYNTHETIC TEST ONLY', date='2026-10-13', scope='test'),
            resource_version=RESOURCE_VERSION, package_sha256=digest(records),
            edition_counts=dict(en=1, vi=1, bn=1), review_evidence=dict(human_reviewed=False))
        # A valid first row must roll back when a later source digest is stale.
        invalid = deepcopy(records)
        invalid[-1]['source_sha256'] = 'stale'
        with pytest.raises(ValueError, match='Source changed'):
            async with engine.begin() as db:
                await import_release(db, invalid, receipt={**receipt, 'package_sha256': digest(invalid)})
        async with engine.connect() as db:
            assert (await db.execute(text('SELECT count(*) FROM characters WHERE id=ANY(:ids)'),
                {'ids': [r['id'] for r in records]})).scalar_one() == 0
        async with engine.begin() as db:
            ids = await import_release(db, records, receipt=receipt)
            assert await import_release(db, records, receipt=receipt) == ids
        with pytest.raises(ValueError, match='Source changed'):
            async with engine.begin() as db:
                await db.execute(text("UPDATE characters SET tags='[\"changed\"]'::jsonb WHERE id=:id"), {'id':source_id})
                await import_release(db, records, receipt=receipt)
        async with engine.begin() as db:
            assert await import_release(db, records, receipt=receipt) == ids
            assert (await db.execute(text('SELECT count(*) FROM character_editions WHERE batch_id=:batch AND NOT local_preview'),
                {'batch':source_id})).scalar_one() == 3
        return {r['locale']: r['id'] for r in records}
    finally:
        await engine.dispose()
