"""Ownership gate for POST /voice/preset (regression for 2026-07-30 leak).

Bug: the gate was `if owner is not None and owner != uid` which short-circuited
for imported/built-in characters (owner_user_id IS NULL), letting any logged-in
user write a GLOBAL voice onto shared cast characters. Fixed to mirror /clone:
`if owner is None or owner != uid -> 403`.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from heart.core.auth import TokenData
from heart.api.routes_voice import PresetVoiceBody, set_preset_voice

_UID = "550e8400-e29b-41d4-a716-446655440000"
_USER = TokenData(user_id=_UID, email="t@example.com")


def _preset_result():
    r = MagicMock()
    r.mappings.return_value.fetchone.return_value = {"id": "mimo_male_cool", "provider": "mimo"}
    return r


def _char_result(owner):
    r = MagicMock()
    r.fetchone.return_value = (owner,) if owner is not None else (None,)
    return r


def _body():
    return PresetVoiceBody(preset_voice_id="mimo_male_cool", character_id="bai_zhi")


@pytest.mark.asyncio
async def test_imported_char_null_owner_is_rejected():
    """Built-in/imported character (owner NULL) must be 403, not silently set."""
    db = AsyncMock()
    db.execute.side_effect = [_preset_result(), _char_result(None)]
    with pytest.raises(HTTPException) as ei:
        await set_preset_voice(_body(), current_user=_USER, db=db)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_other_users_char_is_rejected():
    db = AsyncMock()
    db.execute.side_effect = [_preset_result(), _char_result(str(uuid.uuid4()))]
    with pytest.raises(HTTPException) as ei:
        await set_preset_voice(_body(), current_user=_USER, db=db)
    assert ei.value.status_code == 403


@pytest.mark.asyncio
async def test_owner_can_set_own_char():
    db = AsyncMock()
    # preset lookup, char lookup (owned), INSERT, UPDATE has_voice
    db.execute.side_effect = [_preset_result(), _char_result(_UID), AsyncMock(), AsyncMock()]
    out = await set_preset_voice(_body(), current_user=_USER, db=db)
    assert out["ok"] is True
    assert out["voice_type"] == "preset"
