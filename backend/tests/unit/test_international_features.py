from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from heart.api.routes_characters import _matches_discovery
from heart.i18n import LanguagePreferences, character_preferences
from heart.ss01_soul.draft import CharacterDraft
from heart.ss05_composer.world_book import select_world_book


@pytest.mark.asyncio
async def test_explicit_reader_language_wins_over_creator():
    db = AsyncMock()
    with patch('heart.i18n.load_preferences', AsyncMock(return_value=LanguagePreferences(response_language='ko', response_follows_interface=False))):
        result = await character_preferences(db, uuid4(), 'test')
    assert result.response_language == 'ko'
    db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_creator_language_does_not_mutate_interface():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: 'ja')
    with patch('heart.i18n.load_preferences', AsyncMock(return_value=LanguagePreferences(interface_language='en'))):
        result = await character_preferences(db, uuid4(), 'test')
    assert result.response_language == 'ja'
    assert result.interface_language == 'en'


def test_lore_retrieval_can_find_detail_at_end_and_respects_budget():
    book = 'ordinary scenery ' * 500 + '\n星見図書館 秘密の鍵 星見図書館'
    selected = select_world_book(book, '星見図書館の鍵は？')
    assert len(selected) <= 3000
    assert '秘密の鍵' in selected


def test_world_book_limit_rejects_oversize():
    with pytest.raises(ValidationError):
        CharacterDraft(display_name={'en': 'Rin'}, persona='A friendly adult fiction character.', world_book='a' * 10001)


def test_searches_author_and_intro_with_combined_filters():
    entry = {'display_name': 'Haru', 'creator_name': 'Mina', 'intro': 'A hidden library', 'tags': ['fantasy'], 'content_language': 'ja', 'cast_type': 'single', 'content_rating': 'general'}
    assert _matches_discovery(entry, 'mina', 'ja', 'fantasy', 'single', 'general')
    assert _matches_discovery(entry, 'library', None, '', None, None)
    assert not _matches_discovery(entry, 'mina', 'ko', '', None, None)


def test_underage_correction_revokes_stale_verification():
    from datetime import date
    from heart.api.routes_profile import _apply_birthdate
    updates, params = [], {}
    assert _apply_birthdate(f'{date.today().year - 10}-01-01', updates, params) is False
    assert 'age_verified_at = NULL' in updates
