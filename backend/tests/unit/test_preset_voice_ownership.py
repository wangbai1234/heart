"""Voice write scope for POST /voice/preset (migration 057 model).

History: the 2026-07-30 leak was an owner gate that short-circuited for NULL
owners, letting anyone write a GLOBAL voice onto shared cast characters. The fix
made it owner-only. Migration 057 then split voices into canonical (is_public)
vs per-user personal overrides, so the gate now CLASSIFIES the write instead of
rejecting non-owners outright:

  - owner (any visibility)            → canonical row (is_public=TRUE)
  - non-owner on public/unlisted char → personal override (is_public=FALSE)
  - non-owner on someone else's       → 403
    private/pending char

A personal override is only ever heard by the user who set it — it never leaks
to other users or becomes the character's published voice.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from heart.api.routes_voice import PresetVoiceBody, set_preset_voice
from heart.core.auth import TokenData

_UID = "550e8400-e29b-41d4-a716-446655440000"
_USER = TokenData(user_id=_UID, email="t@example.com")


def _preset_result():
    r = MagicMock()
    r.mappings.return_value.fetchone.return_value = {"id": "mimo_male_cool", "provider": "mimo"}
    return r


def _char_result(owner, visibility="public"):
    """characters row: SELECT owner_user_id, visibility."""
    r = MagicMock()
    r.fetchone.return_value = (owner, visibility) if owner is not None else (None, visibility)
    return r


def _body():
    return PresetVoiceBody(preset_voice_id="mimo_male_cool", character_id="bai_zhi")


@pytest.mark.asyncio
async def test_imported_public_char_null_owner_gets_personal_override():
    """Built-in/imported public char (owner NULL): a user may set a PERSONAL
    voice only they hear — not a global one, not a 403."""
    db = AsyncMock()
    # preset lookup, char lookup (NULL owner, public), INSERT (personal)
    db.execute.side_effect = [_preset_result(), _char_result(None, "public"), AsyncMock()]
    out = await set_preset_voice(_body(), current_user=_USER, db=db)
    assert out["ok"] is True
    assert out["is_personal"] is True


@pytest.mark.asyncio
async def test_other_users_public_char_gets_personal_override():
    db = AsyncMock()
    db.execute.side_effect = [
        _preset_result(),
        _char_result(str(uuid.uuid4()), "public"),
        AsyncMock(),
    ]
    out = await set_preset_voice(_body(), current_user=_USER, db=db)
    assert out["ok"] is True
    assert out["is_personal"] is True


@pytest.mark.asyncio
async def test_other_users_private_char_is_rejected():
    """Someone else's private char: no voice write of any kind → 403."""
    db = AsyncMock()
    db.execute.side_effect = [_preset_result(), _char_result(str(uuid.uuid4()), "private")]
    with pytest.raises(HTTPException) as ei:
        await set_preset_voice(_body(), current_user=_USER, db=db)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_owner_sets_canonical_voice():
    db = AsyncMock()
    # preset lookup, char lookup (owned), INSERT (canonical), UPDATE has_voice
    db.execute.side_effect = [
        _preset_result(),
        _char_result(_UID, "private"),
        AsyncMock(),
        AsyncMock(),
    ]
    out = await set_preset_voice(_body(), current_user=_USER, db=db)
    assert out["ok"] is True
    assert out["voice_type"] == "preset"
    assert out["is_personal"] is False
