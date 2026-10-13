from unittest.mock import AsyncMock

import pytest

from heart.localization.editions import local_preview_ids, prioritize_editions


def catalog():
    entries = [
        dict(
            id=cid,
            content_language=lang,
            status="active",
            review_status="approved",
            visibility="public",
        )
        for cid, lang in [
            ("source", "zh"),
            ("fallback", "zh"),
            ("english", "en"),
            ("vietnamese", "vi"),
        ]
    ]
    editions = {
        cid: dict(source_id="source", locale=lang)
        for cid, lang in [("english", "en"), ("vietnamese", "vi")]
    }
    return entries, editions


@pytest.mark.parametrize("locale,first", [("en-US", "english"), ("vi-VN", "vietnamese")])
def test_language_first_and_replace_only_in_discovery(locale, first):
    entries, editions = catalog()
    result = prioritize_editions(entries, editions, locale, enabled=True)
    visible = [r["id"] for r in result if not r["discovery_hidden"]]
    assert visible == [first, "fallback"]
    assert {r["id"] for r in result} == {r["id"] for r in entries}


@pytest.mark.parametrize("locale,enabled", [("bn", True), ("zh", True), ("en", False)])
def test_missing_or_disabled_language_preserves_originals(locale, enabled):
    entries, editions = catalog()
    result = prioritize_editions(entries, editions, locale, enabled=enabled)
    assert [r["id"] for r in result if not r["discovery_hidden"]] == ["source", "fallback"]


def test_private_owner_draft_does_not_replace_published_source():
    entries, editions = catalog()
    entries[2].update(visibility="private", review_status="pending", is_owner=True)
    result = prioritize_editions(entries, editions, "en", enabled=True)
    assert not next(r for r in result if r["id"] == "source")["discovery_hidden"]
    entries[2]["local_preview"] = True
    result = prioritize_editions(entries, editions, "en", enabled=True)
    assert next(r for r in result if r["id"] == "source")["discovery_hidden"]


@pytest.mark.parametrize("review,localized", [(False, True), (True, False), (False, False)])
async def test_preview_gate_never_queries_database_when_disabled(monkeypatch, review, localized):
    from heart.core.config import settings

    monkeypatch.setattr(settings, "local_character_review", review)
    monkeypatch.setattr(settings, "international_localization", localized)
    db = AsyncMock()
    assert await local_preview_ids(db) == []
    db.execute.assert_not_called()
