"""Explicit owner publication authorization, distinct from specialist review."""

from collections import Counter
from urllib.parse import urlsplit

from heart.locales import LOCALE_REGISTRY, RESOURCE_VERSION
from heart.localization.batch import digest


def validate_release(records: list[dict], receipt: dict) -> None:
    authorization = receipt.get("authorization", {})
    if (
        receipt.get("schema_version") != 1
        or not receipt.get("release_id")
        or not receipt.get("batch_id")
        or authorization.get("by") != "project_owner"
        or not authorization.get("request")
        or not authorization.get("date")
        or not authorization.get("scope")
        or receipt.get("review_evidence", {}).get("human_reviewed") is not False
    ):
        raise ValueError("Missing explicit owner publication authorization")
    if receipt.get("resource_version") != RESOURCE_VERSION:
        raise ValueError("Stale release resource version")
    if receipt.get("package_sha256") != digest(records):
        raise ValueError("Release package differs from authorized digest")
    counts = dict(Counter(record["locale"] for record in records))
    if not counts or counts != receipt.get("edition_counts"):
        raise ValueError("Release language counts differ from authorization")
    for record in records:
        code = record["locale"]
        if code not in LOCALE_REGISTRY or LOCALE_REGISTRY[code]["status"] != "live":
            raise ValueError("Publication requires a live registered locale")
        if record.get("human_reviewed") is not False:
            raise ValueError("Owner authorization must not claim specialist review")
        if (
            record.get("published") is not True
            or record.get("review_status") != "owner_authorized_release"
        ):
            raise ValueError("Invalid authorized publication state")
        _validate_media(record["draft"])


def _validate_media(draft: dict) -> None:
    for field in ("cover_url", "avatar_url"):
        url = draft.get(field)
        if not url:
            continue
        parsed = urlsplit(url)
        if not (
            (not parsed.netloc and url.startswith("/") and not url.startswith("//"))
            or (parsed.scheme == "https" and parsed.hostname == "yuoyuo.app")
        ):
            raise ValueError("Edition media must use production origin paths")


async def import_release(db, records: list[dict], *, receipt: dict) -> list[str]:
    """Caller owns transaction. Publish only the exact owner-authorized package."""
    from heart.localization.edition_import import _import_editions

    validate_release(records, receipt)
    return await _import_editions(db, records, batch_id=receipt["batch_id"], publish=True)
