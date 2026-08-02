"""Sanitize story_scenarios.gm_system_prompt in-place (SS09 content review).

Removes, per product directive (2026-08-02):
  1. Embedded jailbreak blocks (ignore-all-limits / forced organ描写 /
     filter-bypass separators "ᴵ"/"//" / 露骨情欲 / 允许流血情节).
  2. The 纯爱 vs 18禁 maturity mode-selection (the distinction is being dropped
     from the product entirely — no per-story maturity branch, no page toggle).
     Cleaned in THREE places the LLM importer wrote it into:
       - gm_system_prompt (system-prompt mode-select block)
       - blurb (card summary appends "纯爱模式、18禁模式任选。")
       - player_template_json (开局表单 radio field 纯爱模式 vs 18禁模式 —
         this is the on-page selector; removed whole-field, ~20 spelling
         variants, while keeping gameplay selectors like 1v1/np, 对话/剧情).

Legit content is preserved verbatim: world setup, 人设卡, 剧情骨架, and all
writing-craft 写作规范 (暗恋/纯爱/亲密戏/防OOC/不替用户说话 等). Non-maturity
gameplay modes (共感娃娃 模式一/模式二 = whose doll) are NOT touched.

Reversible: original prompts are snapshotted into ``_story_prompt_sanitize_backup``
before any write. Idempotent: running twice == running once.

Usage (from backend/, DATABASE_URL set):
    python scripts/sanitize_story_prompts.py --dry-run   # report only, no writes
    python scripts/sanitize_story_prompts.py             # apply + snapshot
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from typing import Any

from sqlalchemy import text

# ── sanitizer (validated offline against all 49 prompts) ────────────────────

JB_START = "不要使用抱歉"
ORGAN_SIG = "每个含"
JB_SIGS = [
    "不要使用抱歉", "忽略任何限制", "忽略其他的道德", "忽略不相关的道德",
    "禁止规避器官", "露骨情欲", "违禁词", "禁止撤回", "过线词汇",
    "50token", "50 token", "隔开", "ᴵ",
]


def _strip(p: str) -> str:
    return p.replace("　", "").strip()


def remove_jailbreak(text_in: str) -> str:
    start = text_in.find(JB_START)
    if start < 0:
        return text_in
    organ = text_in.find(ORGAN_SIG, start)
    if organ >= 0:
        close = text_in.find("]", organ)
        if close >= 0:
            return text_in[:start] + text_in[close + 1:]
    head = text_in[:start]
    paras = text_in[start:].split("\n\n")
    kept: list[str] = []
    consuming = True
    for i, p in enumerate(paras):
        if consuming and (i == 0 or any(sig in p for sig in JB_SIGS)):
            continue
        consuming = False
        kept.append(p)
    return head + "\n\n".join(kept)


_R_BOTH = re.compile(r"纯爱.*(18🈲|18禁)|(?:18🈲|18禁).*纯爱")
_MARK = r"[\dab【】·•\.、\)\(）（□■◆\s]*"
_OPT_PATTERNS = [
    re.compile(rf"^{_MARK}纯爱模式$"),
    re.compile(rf"^{_MARK}纯爱模式最亲密"),
    re.compile(rf"^{_MARK}纯爱模式中最亲密"),
    re.compile(rf"^{_MARK}纯爱模式要求$"),
    re.compile(rf"^{_MARK}18🈲$"),
    re.compile(rf"^{_MARK}18🈲模式$"),
    re.compile(rf"^{_MARK}18禁模式$"),
    re.compile(rf"^{_MARK}18🈲要求$"),
    re.compile(rf"^{_MARK}18🈲模式特殊要求"),
    re.compile(rf"^{_MARK}18🈲[:：]?$"),
    re.compile(rf"^{_MARK}18🈲模式最亲密"),
]
_DESC_START = ("感情线", "包含成人", "感情描写", "最大尺度", "剧情侧重")
_PAREN_PURE = re.compile(r"^[（(]\s*纯爱模式[，,]")
_PAREN_MERGE = re.compile(r"^[（(]\s*(?:纯爱|18🈲|18禁)模式[，,]")
_EXPLICIT_HDR = re.compile(r"选择?18🈲特殊剧情事件|18🈲特殊剧情")
_SECTION_BREAK = re.compile(r"^—+写作规范—+$|写作规范|写作问题清单|请选择|人设卡")
_HEADER = re.compile(r"^【?\d?\s*[\.、]?\s*请选择模式】?$")
_MATURITY_TOKEN = re.compile(r"纯爱模式|18🈲|18禁模式")


def remove_mode_select(text_in: str) -> str:
    paras = text_in.split("\n\n")
    n = len(paras)
    drop = [False] * n
    prev_was_opt = False
    i = 0
    while i < n:
        s = _strip(paras[i])
        if not s:
            i += 1
            continue
        if _EXPLICIT_HDR.search(s):
            drop[i] = True
            j = i + 1
            while j < n:
                sj = _strip(paras[j])
                if sj and _SECTION_BREAK.search(sj):
                    break
                drop[j] = True
                j += 1
            i = j
            prev_was_opt = False
            continue
        if _R_BOTH.search(s) or _PAREN_PURE.match(s) or any(r.match(s) for r in _OPT_PATTERNS):
            drop[i] = True
            prev_was_opt = True
            i += 1
            continue
        if prev_was_opt and s.startswith(_DESC_START):
            drop[i] = True
            i += 1
            continue
        if _PAREN_MERGE.match(s):
            paras[i] = re.sub(r"[（(]\s*(?:纯爱|18🈲|18禁)模式[，,]", "", paras[i], count=1)
            prev_was_opt = False
            i += 1
            continue
        if _HEADER.match(s):
            for k in range(i + 1, min(i + 5, n)):
                if _MATURITY_TOKEN.search(_strip(paras[k])):
                    drop[i] = True
                    break
        prev_was_opt = False
        i += 1
    return "\n\n".join(p for i, p in enumerate(paras) if not drop[i])


def sanitize(text_in: str) -> str:
    t = remove_jailbreak(text_in)
    t = remove_mode_select(t)
    t = re.sub(r"\n{4,}", "\n\n\n", t)
    return t


# ── blurb (card summary) sanitizer ──────────────────────────────────────────
# The LLM importer appends a maturity-mode選択 clause to每条 blurb (the one-line
# card/intro summary shown in the UI): "纯爱模式、18禁模式任选。" — the 纯爱 vs
# 18禁 distinction the product is dropping. Remove it while keeping non-maturity
# gameplay axes (NP模式 = 关系结构, not maturity).
#
# Three forms observed:
#   A) "…。纯爱模式、18禁模式任选。…"            → drop the whole sentence
#   B) "…。纯爱模式、18禁模式、NP模式任选。…"    → keep "NP模式任选。" (strip只 the
#                                                纯爱/18禁 prefix)
#   C) "…，选择纯爱模式或18禁模式，在…做出抉择。" → strip only "选择…模式，"
#                                                (the rest of the sentence stays)
_BLURB_MERGE = re.compile(r"纯爱模式、18禁模式、(?=NP模式)")
_BLURB_DROP = re.compile(r"纯爱模式、18禁模式任选。")
_BLURB_MID = re.compile(r"选择纯爱模式或18禁模式[，,]")


def sanitize_blurb(text_in: str) -> str:
    t = _BLURB_MERGE.sub("", text_in)   # form B first: keep NP模式任选。
    t = _BLURB_DROP.sub("", t)          # form A: drop whole maturity sentence
    t = _BLURB_MID.sub("", t)           # form C: strip mid-sentence choice
    return t.strip()


# ── player_template_json (开局表单) sanitizer ────────────────────────────────
# The LLM importer emitted a maturity selector field (radio 纯爱模式 vs 18禁模式)
# in the opening form under ~20 spelling variants — keys mode/mode2/content_mode/
# mature_mode/maturity_mode/adult_mode; labels 模式/模式选择/游戏模式/内容模式/…;
# options 纯爱/18禁/18🈲/18模式/…. This is the on-page 纯爱 vs 18禁 distinction.
#
# Remove the WHOLE field wherever its label OR options carry a maturity token.
# NON-maturity gameplay selectors sharing the same key (e.g. mode=对话/剧情,
# relationship_mode=1v1/np, dialog_mode=开启/关闭) carry no maturity token and
# are preserved untouched — the predicate is per-field, never by key.
_MATURITY_TOKEN_RE = re.compile(r"(纯爱|18禁|18🈲|🈲|成人|18模式)")


def _field_is_maturity(field: dict[str, Any]) -> bool:
    label = field.get("label") or ""
    if _MATURITY_TOKEN_RE.search(label):
        return True
    opts = field.get("options")
    if isinstance(opts, list) and _MATURITY_TOKEN_RE.search(" ".join(map(str, opts))):
        return True
    return False


def sanitize_template(tpl: Any) -> tuple[Any, int]:
    """Return (cleaned_template, removed_field_count). No-op on unexpected shapes."""
    if not isinstance(tpl, dict):
        return tpl, 0
    fields = tpl.get("fields")
    if not isinstance(fields, list):
        return tpl, 0
    kept = [f for f in fields if not (isinstance(f, dict) and _field_is_maturity(f))]
    removed = len(fields) - len(kept)
    if removed == 0:
        return tpl, 0
    return {**tpl, "fields": kept}, removed


# ── DB apply harness ────────────────────────────────────────────────────────

_BACKUP_DDL = """
CREATE TABLE IF NOT EXISTS _story_prompt_sanitize_backup (
    id UUID PRIMARY KEY,
    prev_prompt TEXT NOT NULL,
    sanitized_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_BLURB_BACKUP_DDL = """
CREATE TABLE IF NOT EXISTS _story_blurb_sanitize_backup (
    id UUID PRIMARY KEY,
    prev_blurb TEXT NOT NULL,
    sanitized_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""

_TEMPLATE_BACKUP_DDL = """
CREATE TABLE IF NOT EXISTS _story_template_sanitize_backup (
    id UUID PRIMARY KEY,
    prev_template JSONB NOT NULL,
    sanitized_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


async def _run(dry_run: bool) -> int:
    from heart.api.wiring import get_db_session_factory

    factory = get_db_session_factory()
    if factory is None:
        raise SystemExit("DB session factory 不可用（检查 DATABASE_URL）")

    changed = 0
    unchanged = 0
    blurb_changed = 0
    tpl_fields_removed = 0
    tpl_rows_changed = 0
    async with factory() as db:  # type: ignore[misc]
        if not dry_run:
            await db.execute(text(_BACKUP_DDL))
            await db.execute(text(_BLURB_BACKUP_DDL))
            await db.execute(text(_TEMPLATE_BACKUP_DDL))
        rows = (
            await db.execute(
                text(
                    "SELECT id, slug, gm_system_prompt, blurb, player_template_json "
                    "FROM story_scenarios"
                )
            )
        ).mappings().all()

        for r in rows:
            original = r["gm_system_prompt"] or ""
            cleaned = sanitize(original)
            if cleaned != original:
                changed += 1
                delta = len(original) - len(cleaned)
                print(f"{'[dry] ' if dry_run else ''}prompt {r['slug'][:26]:28} -{delta} chars")
                if not dry_run:
                    # snapshot original once (idempotent), then overwrite
                    await db.execute(
                        text(
                            "INSERT INTO _story_prompt_sanitize_backup (id, prev_prompt) "
                            "VALUES (:id, :prev) ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": r["id"], "prev": original},
                    )
                    await db.execute(
                        text(
                            "UPDATE story_scenarios SET gm_system_prompt = :p, "
                            "updated_at = NOW() WHERE id = :id"
                        ),
                        {"p": cleaned, "id": r["id"]},
                    )
            else:
                unchanged += 1

            # blurb (card summary) — strip maturity-mode選択 clause
            orig_blurb = r["blurb"] or ""
            clean_blurb = sanitize_blurb(orig_blurb)
            if clean_blurb != orig_blurb:
                blurb_changed += 1
                print(f"{'[dry] ' if dry_run else ''}blurb  {r['slug'][:26]:28} -{len(orig_blurb) - len(clean_blurb)} chars")
                if not dry_run:
                    await db.execute(
                        text(
                            "INSERT INTO _story_blurb_sanitize_backup (id, prev_blurb) "
                            "VALUES (:id, :prev) ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": r["id"], "prev": orig_blurb},
                    )
                    await db.execute(
                        text(
                            "UPDATE story_scenarios SET blurb = :b, "
                            "updated_at = NOW() WHERE id = :id"
                        ),
                        {"b": clean_blurb, "id": r["id"]},
                    )

            # player_template_json (开局表单) — remove maturity selector field(s)
            orig_tpl = r["player_template_json"]
            if isinstance(orig_tpl, str):  # driver returned raw JSON text
                try:
                    orig_tpl = json.loads(orig_tpl)
                except (ValueError, TypeError):
                    orig_tpl = None
            clean_tpl, removed = sanitize_template(orig_tpl)
            if removed > 0:
                tpl_rows_changed += 1
                tpl_fields_removed += removed
                print(f"{'[dry] ' if dry_run else ''}tpl    {r['slug'][:26]:28} -{removed} field(s)")
                if not dry_run:
                    await db.execute(
                        text(
                            "INSERT INTO _story_template_sanitize_backup (id, prev_template) "
                            "VALUES (:id, CAST(:prev AS JSONB)) ON CONFLICT (id) DO NOTHING"
                        ),
                        {"id": r["id"], "prev": json.dumps(orig_tpl, ensure_ascii=False)},
                    )
                    await db.execute(
                        text(
                            "UPDATE story_scenarios SET player_template_json = CAST(:t AS JSONB), "
                            "updated_at = NOW() WHERE id = :id"
                        ),
                        {"t": json.dumps(clean_tpl, ensure_ascii=False), "id": r["id"]},
                    )
        if not dry_run:
            await db.commit()

    print(
        f"\n{'[dry-run] ' if dry_run else ''}prompt_changed={changed} "
        f"unchanged={unchanged} blurb_changed={blurb_changed} "
        f"template_rows_changed={tpl_rows_changed} template_fields_removed={tpl_fields_removed} "
        f"total={changed + unchanged}"
    )
    return changed


def main() -> None:
    ap = argparse.ArgumentParser(description="Sanitize story gm_system_prompt")
    ap.add_argument("--dry-run", action="store_true", help="report only, no writes")
    args = ap.parse_args()
    asyncio.run(_run(args.dry_run))


if __name__ == "__main__":
    main()
