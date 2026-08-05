"""Regression: RelationshipEvent must auto-generate event_id client-side.

The ORM column previously used ``default=lambda: None`` ("will be set by DB"),
which made SQLAlchemy send an explicit ``event_id=NULL`` in the INSERT. That
OVERRIDES the table's ``DEFAULT gen_random_uuid()`` (a server default applies
only when the column is omitted), so every stage_progression INSERT hit a
NotNullViolation, poisoned the session, and errored the whole chat turn —
surfacing to users as the generic "偏离了轨道" stream error, including mid voice-call.
"""

from __future__ import annotations

from uuid import UUID

from heart.ss04_relationship.models import RelationshipEvent


def test_event_id_default_generates_uuid() -> None:
    # SQLAlchemy applies column defaults at flush. Invoke the column's Python-side
    # default the same way the engine would and assert it yields a real UUID —
    # the old `default=lambda: None` returned None and triggered the NULL INSERT.
    default = RelationshipEvent.__table__.c.event_id.default
    assert default is not None, "event_id must have a client-side default"
    generated = default.arg(None)  # scalar callable defaults take an ExecutionContext
    assert isinstance(generated, UUID), "event_id default must generate a UUID, not None"
