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


def display_name_from_spec(spec: object, fallback_id: str) -> str:
    """Read zh → ja → en from a persisted Soul Spec.

    API presentation must be database-authoritative. The in-memory registry is
    still the fallback for built-ins and malformed legacy rows, but a freshly
    created UGC name must not depend on which Uvicorn worker serves the request.
    """
    if isinstance(spec, str):
        import json

        try:
            spec = json.loads(spec)
        except (TypeError, ValueError):
            spec = None
    if isinstance(spec, dict):
        raw = spec.get("display_name")
        if isinstance(raw, dict):
            for locale in ("zh", "ja", "en"):
                value = raw.get(locale)
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return get_display_name(fallback_id)


@dataclass(frozen=True)
class CharacterRow:
    """A raw row from the ``characters`` table."""

    id: str
    owner_user_id: Optional[UUID]
    visibility: str
    status: str
    review_status: str = "not_required"
    review_reason: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    cover_url: Optional[str] = None
    # ISO-8601 creation timestamp; drives the "新角色" (newest) discovery sort.
    created_at: Optional[str] = None


@dataclass(frozen=True)
class CharacterEntry:
    """One character as exposed by ``GET /api/characters``."""

    id: str
    display_name: str
    visibility: str
    is_builtin: bool
    is_owner: bool
    # Lifecycle state: 'active' | 'disabled'. Only the owner ever sees a
    # 'disabled' row (drives the「已停用」badge + re-publish action).
    status: str = "active"
    review_status: str = "not_required"
    # review_reason is only populated for the owner; never exposed to other users.
    review_reason: Optional[str] = None
    avatar_url: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    cover_url: Optional[str] = None
    chat_user_count: int = 0
    # One-line public plot hook shown under the name on the discovery card
    # (display-only, ≤60 chars). Sourced from the active draft for both seeded
    # first-party characters and UGC.
    tagline: Optional[str] = None
    # ISO-8601 creation timestamp; drives the "新角色" (newest) discovery sort.
    created_at: Optional[str] = None
    # Creation mode: 'quick' (快速创建) | 'workshop' (角色创作) | None (built-in).
    # Drives the edit route in CharacterCard: quick → quick-edit, workshop → workshop edit.
    creation_mode: Optional[str] = None


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


def visible_to(row: CharacterRow, viewer_id: UUID | None) -> bool:
    """Whether ``viewer_id`` may see ``row`` in their catalog.

    Rules:
    - Non-active rows are never listed.
    - Built-in characters (no owner) are always visible.
    - An authenticated owner sees their own characters regardless of review status.
    - ``public`` rows with review_status='approved' are visible to everyone.
    - ``unlisted`` / ``private`` rows (or un-approved public) are owner-only.
    """
    if row.owner_user_id is None:
        # Built-in character — always listed (only ever 'active').
        return row.status == "active"
    if viewer_id is not None and row.owner_user_id == viewer_id:
        # Owner sees their own characters at any status — including 'disabled',
        # so the creator can find and re-publish them from the creation hub.
        return True
    # Non-owner can only see active public+approved characters.
    return row.status == "active" and row.visibility == "public" and row.review_status == "approved"


def build_catalog_entries(
    rows: Sequence[CharacterRow],
    viewer_id: UUID | None,
    avatar_urls: dict[str, str | None] | None = None,
    popularity: dict[str, int] | None = None,
    taglines: dict[str, str | None] | None = None,
    creation_modes: dict[str, str | None] | None = None,
    display_names: dict[str, str | None] | None = None,
) -> list[CharacterEntry]:
    """Shape visible rows into API entries, built-ins first then by popularity.

    Display names are derived from the Soul Spec (single source of truth for
    identity) rather than stored on the row.

    Args:
        avatar_urls: Optional mapping of character_id → avatar_url (from draft).
            Built-in characters don't have UGC avatars; they're resolved client-side.
        popularity: Optional mapping of character_id → chat user count.
            Higher count = more engagement. Used to sort UGC characters.
        taglines: Optional mapping of character_id → one-line plot hook (from draft).
        creation_modes: Optional mapping of character_id → 'quick' | 'workshop'.
            Drives the edit route in CharacterCard.
        display_names: Optional DB-authoritative mapping of character_id → name.
            Production runs multiple API workers, so a newly-created character
            may not yet be present in every worker's in-memory SoulRegistry.
            Passing names read from ``soul_specs`` prevents a transient fallback
            to the technical ``char_xxx`` id on those workers.
    """
    avatar_urls = avatar_urls or {}
    popularity = popularity or {}
    taglines = taglines or {}
    creation_modes = creation_modes or {}
    display_names = display_names or {}

    def is_owner_fn(row: CharacterRow) -> bool:
        return (
            viewer_id is not None
            and row.owner_user_id is not None
            and row.owner_user_id == viewer_id
        )

    entries = [
        CharacterEntry(
            id=row.id,
            display_name=display_names.get(row.id) or get_display_name(row.id),
            visibility=row.visibility,
            is_builtin=row.owner_user_id is None,
            is_owner=is_owner_fn(row),
            status=row.status,
            review_status=row.review_status,
            # Only expose rejection reason to the character owner.
            review_reason=row.review_reason if is_owner_fn(row) else None,
            avatar_url=avatar_urls.get(row.id),
            tags=list(row.tags or []),
            cover_url=row.cover_url,
            chat_user_count=popularity.get(row.id, 0),
            tagline=taglines.get(row.id),
            created_at=row.created_at,
            creation_mode=creation_modes.get(row.id),
        )
        for row in rows
        if visible_to(row, viewer_id)
    ]

    # Built-ins first (stable, familiar ordering), then user characters by engagement (chat user count).
    # Exclude rin/dorothy from popularity sorting as they were the only characters available at launch.
    def sort_key(e):
        # Rin and dorothy stay in their natural builtin position, not sorted by popularity
        if e.id in ("rin", "dorothy"):
            return (False, 0, e.id)  # Builtin, zero popularity sort, then by id
        return (not e.is_builtin, -popularity.get(e.id, 0), e.id)

    entries.sort(key=sort_key)
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
