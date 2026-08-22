from __future__ import annotations

import uuid

import pytest

from heart.api.routes_characters import _require_owner


class _OwnerResult:
    def __init__(self, row: dict) -> None:
        self._row = row

    def mappings(self) -> "_OwnerResult":
        return self

    def fetchone(self) -> dict:
        return self._row


class _OwnerDB:
    def __init__(self, row: dict) -> None:
        self._row = row
        self.statement = ""

    async def execute(self, statement, params):  # noqa: ANN001, ANN201
        self.statement = str(statement)
        return _OwnerResult(self._row)


@pytest.mark.asyncio
async def test_owner_lookup_returns_current_soul_spec_version_for_editing():
    owner_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    db = _OwnerDB(
        {
            "id": "char_test",
            "owner_user_id": owner_id,
            "visibility": "private",
            "status": "active",
            "soul_spec_version": "1.7.0",
        }
    )

    row = await _require_owner("char_test", owner_id, db)  # type: ignore[arg-type]

    assert "soul_spec_version" in db.statement
    assert row["soul_spec_version"] == "1.7.0"
