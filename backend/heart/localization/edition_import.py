"""Local acceptance import for editorial adaptations, never human approval."""

import json

from sqlalchemy import text

from heart.locales import RESOURCE_VERSION
from heart.localization.batch import SOURCE_SQL, digest
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.schema_validator import SoulSpec
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss01_soul.spec_store import insert_spec


async def import_preview(db, records: list[dict], *, batch_id: str) -> list[str]:
    """Caller owns the transaction. Guard the target even if called outside CLI."""
    url = db.engine.url
    if url.host not in {"localhost", "127.0.0.1"} or url.database not in {
        "heart_review",
        "heart_ui_test",
    }:
        raise ValueError("Editorial preview imports require an isolated local database")
    ids = [r["id"] for r in records]
    pairs = [(r["source_id"], r["locale"]) for r in records]
    if not ids or len(set(ids)) != len(ids) or len(set(pairs)) != len(pairs):
        raise ValueError("Empty or duplicate edition batch")
    await db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:batch, 0))"),
        {"batch": "edition-preview:" + batch_id},
    )
    for record in records:
        cid = record["id"]
        draft = CharacterDraft.model_validate(record["draft"])
        spec = build_soul_spec_from_draft(draft, character_id=cid)
        if (
            draft.locale != record["locale"]
            or draft.response_language != record["locale"]
            or draft.visibility != "private"
            or record.get("human_reviewed") is not False
            or record.get("published") is not False
            or record.get("review_status") != "editorial_draft"
            or record.get("resource_version") != RESOURCE_VERSION
        ):
            raise ValueError("Invalid editorial draft or resource version")
        if SoulSpec.model_validate(record["spec"]) != spec:
            raise ValueError("Spec differs from draft")
        current = dict(
            (await db.execute(text(SOURCE_SQL + " FOR SHARE OF c, s"), {"id": record["source_id"]}))
            .mappings()
            .one()
        )
        if digest(current) != record["source_sha256"]:
            raise ValueError("Source changed since export")
        candidate_hash = digest({"draft": record["draft"], "spec": record["spec"]})
        existing = (
            (
                await db.execute(
                    text("""SELECT candidate_sha256, source_id, locale,
            source_sha256, batch_id FROM character_editions WHERE character_id=:id"""),
                    {"id": cid},
                )
            )
            .mappings()
            .first()
        )
        if existing:
            if (
                existing["candidate_sha256"] != candidate_hash
                or existing["source_id"] != record["source_id"]
                or existing["locale"] != record["locale"]
                or existing["source_sha256"] != record["source_sha256"]
                or existing["batch_id"] != batch_id
            ):
                raise ValueError("Edition already exists with different content/provenance")
            actual = (
                (
                    await db.execute(
                        text(
                            "SELECT spec, draft FROM soul_specs WHERE character_id=:id AND status='active'"
                        ),
                        {"id": cid},
                    )
                )
                .mappings()
                .one()
            )
            if digest(dict(actual)) != candidate_hash:
                raise ValueError("Imported edition changed; refusing to overwrite")
            continue
        await db.execute(
            text("""INSERT INTO characters
            (id, owner_user_id, visibility, status, soul_spec_version, tags, cover_url, review_status)
            VALUES (:id, :owner, 'private', 'active', :version, CAST(:tags AS jsonb), :cover, 'pending')"""),
            {
                "id": cid,
                "owner": current["owner_user_id"],
                "version": spec.spec_version,
                "tags": json.dumps(draft.tags),
                "cover": draft.cover_url,
            },
        )
        await insert_spec(
            db,
            character_id=cid,
            spec_version=spec.spec_version,
            spec=record["spec"],
            draft=record["draft"],
        )
        await db.execute(
            text("""INSERT INTO character_editions
            (character_id, source_id, locale, source_sha256, candidate_sha256, batch_id, local_preview)
            VALUES (:id, :source, :locale, :source_hash, :candidate_hash, :batch, TRUE)"""),
            {
                "id": cid,
                "source": record["source_id"],
                "locale": record["locale"],
                "source_hash": record["source_sha256"],
                "candidate_hash": candidate_hash,
                "batch": batch_id,
            },
        )
    return ids
