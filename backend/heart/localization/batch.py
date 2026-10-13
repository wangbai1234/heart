"""One immutable source × language task; no model calls or silent truncation."""

import hashlib
import json
from datetime import datetime

from sqlalchemy import text

from heart.locales import LOCALE_REGISTRY, RESOURCE_VERSION
from heart.ss01_soul.draft import CharacterDraft
from heart.ss01_soul.spec_builder import build_soul_spec_from_draft
from heart.ss01_soul.spec_store import insert_spec

COPY_FIELDS = (
    "persona",
    "backstory",
    "intro",
    "opening",
    "tagline",
    "one_liner",
    "archetype_label",
    "tags",
    "catchphrases",
    "speech_samples",
    "world_book",
    "soul_profile",
    "hard_never_user",
    "profile_blocks",
    "premise_card",
    "starter_config",
    "custom_html",
)
PROTECTED_FIELDS = (
    "gender",
    "age_range",
    "cast_type",
    "content_rating",
    "greeting_style",
    "sliders",
    "cover_url",
    "avatar_url",
    "ui_chrome",
    "creation_mode",
    "opening_format",
)
SOURCE_SQL = """SELECT c.id, c.owner_user_id, c.cover_url, c.visibility, c.status,
    c.review_status, c.tags, s.draft, s.spec FROM characters c JOIN soul_specs s
    ON c.id=s.character_id AND s.status='active' WHERE c.id=:id"""


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
        ).encode()
    ).hexdigest()


def plan(sources: list[dict], locales: list[str]) -> list[dict]:
    if not sources or not locales or len(locales) != len(set(locales)):
        raise ValueError("Provide unique target languages and nonempty sources")
    if len({source["id"] for source in sources}) != len(sources):
        raise ValueError("Duplicate source")
    tasks = []
    for source in sources:
        if not source.get("draft"):
            raise ValueError("A complete source draft is required; reconstruct and review it first")
        CharacterDraft.model_validate(source["draft"])
        for locale in locales:
            if locale not in LOCALE_REGISTRY:
                raise ValueError("Unknown locale")
            task = {
                "schema_version": 1,
                "source_id": source["id"],
                "locale": locale,
                "source_sha256": digest(source),
                "resource_version": RESOURCE_VERSION,
                "source": source,
            }
            task["task_id"] = digest({k: v for k, v in task.items() if k != "source"})
            tasks.append(task)
    return tasks


def require_structure(source, target, path: str) -> None:
    """Require every populated field/list member, including nested soul content."""
    if source in (None, ""):
        return
    if isinstance(source, dict):
        if not isinstance(target, dict) or not source.keys() <= target.keys():
            raise ValueError("Missing object fields: " + path)
        for key, value in source.items():
            require_structure(value, target.get(key), path + "." + key)
    elif isinstance(source, list):
        if not isinstance(target, list) or len(source) != len(target):
            raise ValueError("Missing list members: " + path)
        for i, (before, after) in enumerate(zip(source, target, strict=True)):
            require_structure(before, after, f"{path}[{i}]")
    else:
        require_scalar(source, target, path)


def require_scalar(source, target, path: str) -> None:
    if isinstance(source, str):
        if not isinstance(target, str) or not target.strip():
            raise ValueError("Missing text: " + path)
    elif source != target:
        raise ValueError("Changed structural value: " + path)


def validate(task: dict, candidate: dict, *, approved: bool = False) -> CharacterDraft:
    expected = plan([task["source"]], [task["locale"]])[0]
    if task != expected:
        raise ValueError("Stale or altered source/resource task")
    if candidate.get("task_id") != task["task_id"]:
        raise ValueError("Candidate belongs to another task")
    raw = candidate["draft"]
    draft = CharacterDraft.model_validate(raw)
    if draft.locale != task["locale"] or draft.response_language != task["locale"]:
        raise ValueError("Wrong target language")
    names = draft.display_name.model_dump()
    if not (names.get(task["locale"]) or names["localized"].get(task["locale"])):
        raise ValueError("Missing target name")
    original = CharacterDraft.model_validate(task["source"]["draft"])
    source_data, target_data = original.model_dump(mode="json"), draft.model_dump(mode="json")
    for field in COPY_FIELDS:
        require_structure(source_data[field], target_data[field], field)
    for field in PROTECTED_FIELDS:
        if source_data[field] != target_data[field]:
            raise ValueError("Changed source identity/configuration: " + field)
    if not isinstance(candidate.get("editorial_notes"), str):
        raise ValueError("Editorial notes required")
    if approved:
        validate_review(task, candidate)
    return draft


def validate_review(task: dict, candidate: dict) -> None:
    review = candidate.get("review", {})
    binding = {
        "task_id": task["task_id"],
        "source_sha256": task["source_sha256"],
        "resource_version": RESOURCE_VERSION,
        "candidate_sha256": digest({k: v for k, v in candidate.items() if k != "review"}),
    }
    if any(review.get(key) != value for key, value in binding.items()):
        raise ValueError("Review does not match current candidate")
    if review.get("approved") is not True or not str(review.get("reviewer", "")).strip():
        raise ValueError("Human approval required")
    when = datetime.fromisoformat(review.get("reviewed_at", "").replace("Z", "+00:00"))
    if when.tzinfo is None:
        raise ValueError("Review time requires timezone")
    for field in ("field_fidelity", "name_consistency", "safety", "output_format", "rights"):
        if review.get("checks", {}).get(field) is not True:
            raise ValueError("Incomplete human review: " + field)


async def import_review(db, tasks: list[dict], candidates: list[dict]) -> list[str]:
    """Caller owns one transaction. Only creates private, pending-review copies."""
    if len(tasks) != len(candidates) or len({t["task_id"] for t in tasks}) != len(tasks):
        raise ValueError("Duplicate or incomplete batch")
    validated = [validate(t, c, approved=True) for t, c in zip(tasks, candidates, strict=True)]
    await db.execute(text("CREATE SCHEMA IF NOT EXISTS local_review"))
    await db.execute(
        text("""CREATE TABLE IF NOT EXISTS local_review.locale_imports (
        task_id TEXT PRIMARY KEY, character_id TEXT UNIQUE NOT NULL,
        source_id TEXT NOT NULL, locale TEXT NOT NULL, source_sha256 TEXT NOT NULL,
        candidate_sha256 TEXT NOT NULL, source_snapshot JSONB NOT NULL,
        review JSONB NOT NULL, imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW())""")
    )
    ids = []
    for task, candidate, draft in zip(tasks, candidates, validated, strict=True):
        # Locks source rows until the same transaction commits the import/ledger.
        result = await db.execute(
            text(SOURCE_SQL + " FOR SHARE OF c, s"), {"id": task["source_id"]}
        )
        current = result.mappings().one()
        if digest(dict(current)) != task["source_sha256"]:
            raise ValueError("Source changed since export")
        candidate_hash = digest(candidate)
        existing = (
            (
                await db.execute(
                    text(
                        "SELECT character_id, candidate_sha256 FROM local_review.locale_imports WHERE task_id=:task"
                    ),
                    {"task": task["task_id"]},
                )
            )
            .mappings()
            .first()
        )
        cid = "loc_" + task["locale"] + "_" + task["task_id"][:24]
        if existing:
            if existing["candidate_sha256"] != candidate_hash or existing["character_id"] != cid:
                raise ValueError("Imported task differs; never overwrite reviewed content")
            ids.append(cid)
            continue
        draft = draft.model_copy(update={"visibility": "private"})
        spec = build_soul_spec_from_draft(draft, character_id=cid)
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
            spec=spec.model_dump(mode="json"),
            draft=draft.model_dump(mode="json"),
        )
        await db.execute(
            text("""INSERT INTO local_review.locale_imports
            (task_id, character_id, source_id, locale, source_sha256, candidate_sha256, source_snapshot, review)
            VALUES (:task, :id, :source, :locale, :source_hash, :candidate_hash, CAST(:snapshot AS jsonb), CAST(:review AS jsonb))"""),
            {
                "task": task["task_id"],
                "id": cid,
                "source": task["source_id"],
                "locale": task["locale"],
                "source_hash": task["source_sha256"],
                "candidate_hash": candidate_hash,
                "snapshot": json.dumps(task["source"], default=str),
                "review": json.dumps(candidate["review"]),
            },
        )
        ids.append(cid)
    return ids
