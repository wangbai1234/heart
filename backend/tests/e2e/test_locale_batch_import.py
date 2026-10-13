"""Real isolated PostgreSQL import and rollback checks; synthetic approvals only."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from heart.localization.batch import SOURCE_SQL, digest, import_review, plan
from tests.e2e.test_international_release import login

pytestmark = pytest.mark.e2e


def isolated_url():
    url = make_url(os.environ["DATABASE_URL"])
    assert url.host in {"127.0.0.1", "localhost"} and url.database == "heart_ui_test"
    return url


def test_review_import_is_atomic_idempotent_and_source_bound(api_context):
    token = login(api_context, str(uuid4()))
    headers = {"Authorization": f"Bearer {token}"}
    created = api_context.post("/api/characters", headers=headers, data={
        "display_name": {"en": "Source"}, "locale": "en", "response_language": "en",
        "persona": "An adult author with a distinctive personal history.",
        "backstory": "A family of librarians raised this author.", "creation_mode": "workshop"})
    assert created.ok, created.text()
    cid = created.json()["id"]
    with ThreadPoolExecutor(max_workers=1) as pool:
        pool.submit(lambda: asyncio.run(check_import(cid))).result()


async def check_import(cid):
    engine = create_async_engine(isolated_url())
    try:
        async with engine.begin() as db:
            source = dict((await db.execute(text(SOURCE_SQL), {"id": cid})).mappings().one())
            task = plan([source], ["vi"])[0]
            candidate = {"task_id": task["task_id"], "editorial_notes": "Synthetic test only",
                "draft": {**source["draft"], "locale": "vi", "response_language": "vi",
                    "display_name": {"localized": {"vi": "Minh"}},
                    "persona": "Một nhà văn trưởng thành có quá khứ riêng biệt.",
                    "backstory": "Nhà văn này lớn lên trong một gia đình thủ thư."}}
            candidate["review"] = {"task_id": task["task_id"], "source_sha256": task["source_sha256"],
                "resource_version": task["resource_version"], "candidate_sha256": digest(candidate),
                "approved": True, "reviewer": "SYNTHETIC TEST ONLY", "reviewed_at": "2026-10-13T00:00:00Z",
                "checks": dict.fromkeys(["field_fidelity", "name_consistency", "safety", "output_format", "rights"], True)}
            first = await import_review(db, [task], [candidate])
            assert await import_review(db, [task], [candidate]) == first
            row = (await db.execute(text("SELECT visibility, review_status FROM characters WHERE id=:id"), {"id": first[0]})).one()
            assert tuple(row) == ("private", "pending")
        with pytest.raises(ValueError, match="Source changed"):
            async with engine.begin() as db:
                await db.execute(text("UPDATE characters SET tags='[\"changed\"]'::jsonb WHERE id=:id"), {"id": cid})
                await import_review(db, [task], [candidate])
        async with engine.begin() as db:
            assert await import_review(db, [task], [candidate]) == first
            assert (await db.execute(text("SELECT count(*) FROM soul_specs WHERE character_id=:id"), {"id": first[0]})).scalar_one() == 1
    finally:
        await engine.dispose()


def test_migration_preserves_preferences_and_allows_reentry():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    path = Path(__file__).resolve().parents[2] / "migrations/versions/080_extensible_locales.py"
    module_spec = importlib.util.spec_from_file_location("test_locale_migration", path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    engine = create_engine(isolated_url().set(drivername="postgresql+psycopg2"))
    schema = "locale_migration_" + uuid4().hex
    try:
        with engine.connect() as db:
            transaction = db.begin()
            try:
                db.execute(text(f"CREATE SCHEMA {schema}"))
                db.execute(text(f"SET LOCAL search_path TO {schema}, public"))
                db.execute(text("""CREATE TABLE user_language_preferences (
                    user_id int PRIMARY KEY, interface_language varchar(2) CHECK(interface_language IN ('en','ja','ko')),
                    response_language varchar(2) CHECK(response_language IN ('en','ja','ko')),
                    response_follows_interface boolean NOT NULL)"""))
                db.execute(text("INSERT INTO user_language_preferences VALUES (1,'ja','ko',false),(2,'en','en',true)"))
                with Operations.context(MigrationContext.configure(db)):
                    module.upgrade()
                    assert db.execute(text("SELECT response_mode FROM user_language_preferences ORDER BY user_id")).scalars().all() == ["fixed", "auto"]
                    db.execute(text("UPDATE user_language_preferences SET interface_language='bn', response_language='vi' WHERE user_id=1"))
                    module.upgrade()
                    module.downgrade()
                    assert tuple(db.execute(text("SELECT interface_language, response_language, response_mode FROM user_language_preferences WHERE user_id=1")).one()) == ("bn", "vi", "fixed")
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
