"""Character catalog logic — the readable view over the ``characters`` table.

C2 of the UGC refactor introduces a global ``characters`` directory (see
migration 019). This module holds the *pure* shaping / visibility / validation
logic that sits between the raw table rows and the API, so it is unit-testable
without a database:

  - ``build_catalog_entries`` turns raw rows into the API-facing list, applying
    visibility rules and enriching each with its Soul-Spec-derived display name.
  - ``is_known_character`` is the boundary guard used to reject unknown
    ``character_id`` values before they reach the chat / settings paths. It is
    backed by the in-memory SoulRegistry (a character is "known" iff it has a
    loaded Soul Spec — exactly the precondition the downstream prompt build needs),
    so it costs no database round-trip on the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence
from uuid import UUID

import structlog

from heart.ss01_soul.character_content import get_display_name
from heart.ss01_soul.registry import get_soul_registry

logger = structlog.get_logger()


@dataclass(frozen=True)
class CharacterRow:
    """A raw row from the ``characters`` table."""

    id: str
    owner_user_id: Optional[UUID]
    visibility: str
    status: str
    tags: list[str] = field(default_factory=list)
    cover_url: Optional[str] = None


@dataclass(frozen=True)
class CharacterEntry:
    """One character as exposed by ``GET /api/characters``."""

    id: str
    display_name: str
    visibility: str
    is_builtin: bool
    is_owner: bool
    avatar_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    cover_url: Optional[str] = None


def coerce_tags(raw: object) -> list[str]:
    """Normalize a ``characters.tags`` JSONB value into a ``list[str]``.

    Depending on the DB driver, a JSONB column may arrive already decoded to a
    Python ``list`` (asyncpg) or as a raw JSON ``str``. Anything unexpected
    (None, non-list) degrades to an empty list so the catalog never breaks.
    """
    if isinstance(raw, str):
        import json

        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return []
    if isinstance(raw, list):
        return [str(t) for t in raw if isinstance(t, (str, int, float))]
    return []


def visible_to(row: CharacterRow, viewer_id: UUID) -> bool:
    """Whether ``viewer_id`` may see ``row`` in their catalog.

    - Non-active rows are never listed.
    - ``public`` rows are visible to everyone.
    - ``unlisted`` / ``private`` rows are visible only to their owner.
    """
    if row.status != "active":
        return False
    if row.visibility == "public":
        return True
    return row.owner_user_id is not None and row.owner_user_id == viewer_id


def build_catalog_entries(
    rows: Sequence[CharacterRow],
    viewer_id: UUID,
    avatar_urls: dict[str, str | None] | None = None,
) -> list[CharacterEntry]:
    """Shape visible rows into API entries, built-ins first then by id.

    Display names are derived from the Soul Spec (single source of truth for
    identity) rather than stored on the row.

    Args:
        avatar_urls: Optional mapping of character_id → avatar_url (from draft).
            Built-in characters don't have UGC avatars; they're resolved client-side.
    """
    avatar_urls = avatar_urls or {}
    entries = [
        CharacterEntry(
            id=row.id,
            display_name=get_display_name(row.id),
            visibility=row.visibility,
            is_builtin=row.owner_user_id is None,
            is_owner=row.owner_user_id is not None and row.owner_user_id == viewer_id,
            avatar_url=avatar_urls.get(row.id),
            tags=list(row.tags or []),
            cover_url=row.cover_url,
        )
        for row in rows
        if visible_to(row, viewer_id)
    ]
    # Built-ins first (stable, familiar ordering), then user characters by id.
    entries.sort(key=lambda e: (not e.is_builtin, e.id))
    return entries


def is_known_character(character_id: str) -> bool:
    """Whether ``character_id`` maps to a loaded Soul Spec.

    Used as a boundary guard: an id that is not known has no persona/prompt and
    must be rejected rather than silently accepted. Registry failures fall back to
    ``False`` (fail-closed) so an un-loaded registry cannot wave unknown ids
    through.
    """
    try:
        return character_id in set(get_soul_registry().list_characters())
    except Exception:
        return False


async def ensure_character_loaded(character_id: str, db: Any) -> bool:
    """DB-authoritative boundary check with lazy per-process hydration.

    ``is_known_character`` only sees the *current worker's* in-memory registry.
    Prod runs multiple uvicorn workers (``--workers 2``), and a UGC character is
    hot-loaded (``reload_character``) into just the one worker that handled its
    creation — the other worker(s) stay ignorant of it until the next restart's
    DB warm (``load_db_overlay`` in the lifespan). That window makes a
    freshly-created character fail ~50% of the time, flakily by which worker the
    request lands on: chat rejects it as ``SOUL_NOT_LOADED`` ("角色加载中") and
    clear-conversations 404s ("清空失败").

    This closes the gap on the hot path: if the id isn't in this process's
    registry, fetch its single active spec from the DB once and overlay it, so
    any worker can serve any character that actually exists. Returns True iff the
    character is (now) known. A DB error fails closed (returns the in-memory
    answer) rather than waving unknown ids through.
    """
    if is_known_character(character_id):
        return True

    # Not in this worker's registry — it may have been created on another worker
    # after startup. Authoritatively check the DB and hydrate on hit.
    from heart.ss01_soul.spec_store import fetch_active_spec

    try:
        row = await fetch_active_spec(db, character_id)
    except Exception:
        logger.exception("ensure_character_loaded_fetch_failed", character_id=character_id)
        return False

    if row is None:
        return False

    get_soul_registry().load_db_overlay([row])
    known = is_known_character(character_id)
    if known:
        logger.info("ensure_character_loaded_lazy_hydrated", character_id=character_id)
    return known
