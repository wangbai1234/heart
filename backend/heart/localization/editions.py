"""Edition provenance and language-first discovery, independent of publication."""

from sqlalchemy import text

from heart.i18n import normalize_locale


async def local_preview_ids(db) -> list[str]:
    from heart.core.config import settings

    if not (settings.local_character_review and settings.international_localization):
        return []
    result = await db.execute(
        text("""SELECT e.character_id FROM character_editions e
        JOIN characters c ON c.id=e.character_id
        WHERE e.local_preview AND c.status='active'
          AND c.visibility='private' AND c.review_status='pending'""")
    )
    return list(result.scalars())


async def edition_records(db, ids: list[str]) -> dict[str, dict]:
    if not ids:
        return {}
    result = await db.execute(
        text("""SELECT character_id, source_id, locale
        FROM character_editions WHERE character_id=ANY(:ids)"""),
        {"ids": ids},
    )
    return {r["character_id"]: dict(r) for r in result.mappings()}


def prioritize_editions(
    entries: list[dict], editions: dict[str, dict], language: str, *, enabled: bool
) -> list[dict]:
    """Keep every accessible ID for old chats/favorites, annotate discovery only.

    A pending owner's draft cannot displace its published source. A source is
    replaced only by an accessible, discoverable edition in the chosen language.
    Stable sorting preserves the existing ranking within each language group.
    """
    locale = normalize_locale(language) or "en"
    replacements = set()
    for entry in entries:
        edition = editions.get(entry["id"])
        discoverable = entry.get("local_preview") or (
            entry.get("status") == "active"
            and entry.get("review_status") == "approved"
            and (
                entry.get("visibility") == "public"
                or (entry.get("local_review") and entry.get("visibility") == "unlisted")
            )
        )
        if enabled and edition and edition["locale"] == locale and discoverable:
            replacements.add(edition["source_id"])
    for entry in entries:
        edition = editions.get(entry["id"])
        entry["edition"] = edition
        entry["discovery_hidden"] = bool(
            entry.get("discovery_hidden")
            or (edition and (not enabled or edition["locale"] != locale))
            or entry["id"] in replacements
        )
        entry["language_priority"] = int(
            not (enabled and normalize_locale(entry.get("content_language", "zh")) == locale)
        )
    return sorted(entries, key=lambda entry: entry["language_priority"])
