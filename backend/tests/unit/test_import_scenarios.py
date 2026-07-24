"""Unit tests for the SS09 scenario importer (PR6).

Covers the pure normalization/parse helpers plus import_one's control flow
(verbatim 原文注入, source_hash skip, dry-run no-write) with a stubbed router
and a fake DB — no real LLM or Postgres.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# The importer lives under backend/scripts (not a package on the default path).
_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import import_scenarios as imp  # noqa: E402

# ── pure helpers ─────────────────────────────────────────────────────


def test_derive_slug_uses_stem():
    assert imp.derive_slug(Path("/x/登仙路.txt")) == "登仙路"
    assert imp.derive_slug(Path("/x/我在刑侦队当万人迷 (1).txt")) == "我在刑侦队当万人迷 (1)"


def test_compute_hash_is_deterministic_and_content_sensitive():
    assert imp.compute_hash("abc") == imp.compute_hash("abc")
    assert imp.compute_hash("abc") != imp.compute_hash("abd")


def test_normalize_genre_exact_substring_and_fallback():
    assert imp.normalize_genre("校园恋爱") == "校园恋爱"
    assert imp.normalize_genre("现代豪门文") == "现代豪门"  # substring hit
    assert imp.normalize_genre("赛博朋克") == "其他"  # unknown → 其他
    assert imp.normalize_genre(None) == "其他"
    assert imp.normalize_genre(123) == "其他"


def test_normalize_maturity():
    assert imp.normalize_maturity("adult") == "adult"
    assert imp.normalize_maturity("ADULT") == "adult"
    assert imp.normalize_maturity("all_ages") == "all_ages"
    assert imp.normalize_maturity("nsfw") == "all_ages"  # only literal 'adult' flips
    assert imp.normalize_maturity(None) == "all_ages"


def test_clamp_blurb_truncates_and_collapses():
    assert imp.clamp_blurb("  hello   world  ") == "hello world"
    long = "字" * 100
    assert len(imp.clamp_blurb(long)) == 40
    assert imp.clamp_blurb(None) == ""


def test_parse_metadata_clean_json():
    m = imp.parse_metadata(
        '{"title":"登仙路","genre":"修仙","blurb":"一段问道之旅","maturity":"all_ages"}',
        default_title="fallback",
    )
    assert (m.title, m.genre, m.blurb, m.maturity) == ("登仙路", "修仙", "一段问道之旅", "all_ages")


def test_parse_metadata_code_fenced_and_prose():
    raw = '好的，这是结果：\n```json\n{"title":"网黄","genre":"现代豪门","maturity":"adult"}\n```'
    m = imp.parse_metadata(raw, default_title="fallback")
    assert m.title == "网黄"
    assert m.genre == "现代豪门"
    assert m.maturity == "adult"
    assert m.blurb == ""  # missing → safe default


def test_parse_metadata_junk_falls_back():
    m = imp.parse_metadata("not json at all", default_title="文件名")
    assert m.title == "文件名"
    assert m.genre == "其他"
    assert m.maturity == "all_ages"


def test_parse_metadata_blank_title_uses_default():
    m = imp.parse_metadata('{"title":"   "}', default_title="文件名")
    assert m.title == "文件名"


# ── normalize_fields (form-block extraction, 2026-07) ────────────────


def test_normalize_fields_keeps_valid_types():
    fields = [
        {"key": "name", "label": "姓名", "type": "text", "required": True},
        {"key": "mode", "label": "模式", "type": "radio", "required": True,
         "options": ["纯爱", "18禁"]},
        {"key": "prefs", "label": "偏好", "type": "checkbox", "required": False,
         "options": ["办公室恋", "背德感"]},
    ]
    out = imp.normalize_fields(fields)
    assert [f["type"] for f in out] == ["text", "radio", "checkbox"]
    assert out[1]["options"] == ["纯爱", "18禁"]
    assert out[2]["options"] == ["办公室恋", "背德感"]


def test_normalize_fields_unknown_type_degrades_to_text():
    out = imp.normalize_fields([{"key": "x", "label": "X", "type": "slider"}])
    assert out[0]["type"] == "text"


def test_normalize_fields_choice_without_options_degrades_to_text():
    # A radio/checkbox with no options is unrenderable → becomes a text box.
    out = imp.normalize_fields([{"key": "m", "label": "模式", "type": "radio", "options": []}])
    assert out[0]["type"] == "text"
    assert "options" not in out[0]


def test_normalize_fields_drops_keyless_and_dedupes():
    out = imp.normalize_fields([
        {"label": "无key"},                       # dropped: no key
        {"key": "name", "label": "姓名1"},
        {"key": "name", "label": "姓名2"},          # dropped: duplicate key
        "not a dict",                              # dropped: not a dict
    ])
    assert len(out) == 1
    assert out[0]["key"] == "name" and out[0]["label"] == "姓名1"


def test_normalize_fields_label_falls_back_to_key():
    out = imp.normalize_fields([{"key": "zodiac", "type": "text"}])
    assert out[0]["label"] == "zodiac"


def test_parse_metadata_extracts_multi_block_template():
    raw = (
        '{"title":"臣妻","genre":"古风仙侠","maturity":"adult",'
        '"player_template":{"fields":['
        '{"key":"name","label":"姓名","type":"text","required":true},'
        '{"key":"mode","label":"模式","type":"radio","required":true,"options":["纯爱","18禁"]},'
        '{"key":"prefs","label":"设定偏好","type":"checkbox","required":false,'
        '"options":["皇帝线","丈夫线","后宫斗争"]}'
        ']}}'
    )
    m = imp.parse_metadata(raw, default_title="fallback")
    fields = m.player_template["fields"]
    assert len(fields) == 3
    assert {f["key"] for f in fields} == {"name", "mode", "prefs"}
    prefs = next(f for f in fields if f["key"] == "prefs")
    assert prefs["type"] == "checkbox"
    assert prefs["options"] == ["皇帝线", "丈夫线", "后宫斗争"]


def test_parse_metadata_empty_fields_yields_empty_template():
    m = imp.parse_metadata('{"title":"x","player_template":{"fields":[]}}', default_title="x")
    assert m.player_template == {}  # empty → backend uses default template


# ── extract_metadata (stubbed router) ────────────────────────────────


class _FakeRouter:
    def __init__(self, out: str | None = None, raise_it: bool = False):
        self._out = out
        self._raise = raise_it
        self.calls: list[dict] = []

    async def call_cheap(self, messages, **kw):
        self.calls.append({"messages": messages, "kw": kw})
        if self._raise:
            raise RuntimeError("llm down")
        return self._out or ""


@pytest.mark.asyncio
async def test_extract_metadata_parses_router_json():
    router = _FakeRouter(out='{"title":"T","genre":"悬疑","blurb":"B","maturity":"adult"}')
    m = await imp.extract_metadata(router, "原文正文" * 100, default_title="def")
    assert (m.title, m.genre, m.maturity) == ("T", "悬疑", "adult")
    # json_mode requested; excerpt bounded.
    assert router.calls[0]["kw"].get("json_mode") is True


@pytest.mark.asyncio
async def test_extract_metadata_fails_open_on_error():
    router = _FakeRouter(raise_it=True)
    m = await imp.extract_metadata(router, "x", default_title="兜底标题")
    assert m.title == "兜底标题"
    assert m.genre == "其他"
    assert m.maturity == "all_ages"


# ── import_one (fake DB) ─────────────────────────────────────────────


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDB:
    """Records upsert params; answers source_hash lookups from a dict."""

    def __init__(self, hash_by_slug: dict[str, str] | None = None):
        self.hash_by_slug = hash_by_slug or {}
        self.upserts: list[dict] = []
        self.commits = 0

    async def execute(self, stmt, params=None):
        sql = str(stmt)
        if "SELECT source_hash" in sql:
            return _FakeResult(self.hash_by_slug.get((params or {}).get("slug")))
        if "INSERT INTO story_scenarios" in sql:
            self.upserts.append(params or {})
            return _FakeResult(None)
        return _FakeResult(None)

    async def commit(self):
        self.commits += 1


@pytest.mark.asyncio
async def test_import_one_injects_raw_verbatim(tmp_path):
    """gm_system_prompt must equal the raw file byte-for-byte (原文注入)."""
    raw = "　　这是一款主控自定义游戏。\n\ndeepseek，请根据设定扮演。\n【旁白】开场。"
    f = tmp_path / "测试剧本.txt"
    f.write_text(raw, encoding="utf-8")

    db = _FakeDB()
    router = _FakeRouter(out='{"title":"测试","genre":"其他","blurb":"b","maturity":"all_ages"}')
    res = await imp.import_one(db, router, f, publish=False, dry_run=False)

    assert res.action == "created"
    assert len(db.upserts) == 1
    # Verbatim: no normalization, no stripping of the deepseek meta-instruction.
    assert db.upserts[0]["prompt"] == raw
    assert db.upserts[0]["status"] == "draft"
    assert db.commits == 1


@pytest.mark.asyncio
async def test_import_one_publish_sets_status(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("正文", encoding="utf-8")
    db = _FakeDB()
    router = _FakeRouter(out='{"title":"s","genre":"其他"}')
    res = await imp.import_one(db, router, f, publish=True, dry_run=False)
    assert res.action == "created"
    assert db.upserts[0]["status"] == "published"


@pytest.mark.asyncio
async def test_import_one_skips_unchanged_hash(tmp_path):
    """Same source_hash already in DB → skip without LLM or write."""
    raw = "稳定的正文内容"
    f = tmp_path / "s.txt"
    f.write_text(raw, encoding="utf-8")
    db = _FakeDB(hash_by_slug={"s": imp.compute_hash(raw)})
    router = _FakeRouter(out="should-not-be-called")

    res = await imp.import_one(db, router, f, publish=False, dry_run=False)

    assert res.action == "skipped"
    assert router.calls == []  # no metadata call
    assert db.upserts == []  # no write
    assert db.commits == 0


@pytest.mark.asyncio
async def test_import_one_dry_run_writes_nothing(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("正文", encoding="utf-8")
    db = _FakeDB()
    router = _FakeRouter(out='{"title":"标题","genre":"悬疑","maturity":"adult"}')

    res = await imp.import_one(db, router, f, publish=False, dry_run=True)

    assert res.action == "dry-run"
    assert res.metadata is not None
    assert res.metadata.maturity == "adult"
    assert db.upserts == []
    assert db.commits == 0


@pytest.mark.asyncio
async def test_import_one_empty_file_errors(tmp_path):
    f = tmp_path / "s.txt"
    f.write_text("   \n  ", encoding="utf-8")
    db = _FakeDB()
    router = _FakeRouter(out="{}")
    res = await imp.import_one(db, router, f, publish=False, dry_run=False)
    assert res.action == "error"
    assert db.upserts == []
