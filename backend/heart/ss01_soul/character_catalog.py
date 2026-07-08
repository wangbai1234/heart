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

from dataclasses import dataclass
from typing import Optional, Sequence
from uuid import UUID

from heart.ss01_soul.character_content import get_display_name
from heart.ss01_soul.registry import get_soul_registry


@dataclass(frozen=True)
class CharacterRow:
    """A raw row from the ``characters`` table."""

    id: str
    owner_user_id: Optional[UUID]
    visibility: str
    status: str


@dataclass(frozen=True)
class CharacterEntry:
    """One character as exposed by ``GET /api/characters``."""

    id: str
    display_name: str
    visibility: str
    is_builtin: bool
    is_owner: bool


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


def build_catalog_entries(rows: Sequence[CharacterRow], viewer_id: UUID) -> list[CharacterEntry]:
    """Shape visible rows into API entries, built-ins first then by id.

    Display names are derived from the Soul Spec (single source of truth for
    identity) rather than stored on the row.
    """
    entries = [
        CharacterEntry(
            id=row.id,
            display_name=get_display_name(row.id),
            visibility=row.visibility,
            is_builtin=row.owner_user_id is None,
            is_owner=row.owner_user_id is not None and row.owner_user_id == viewer_id,
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
