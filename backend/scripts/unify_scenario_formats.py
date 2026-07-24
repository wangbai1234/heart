#!/usr/bin/env python3
"""Strip embedded GM output-format instructions from scenario txt files.

Root cause (per product owner, 2026-07-24): the 46 scenario packs each embed
their own GM "output format" directives (many share a near-identical
```markdown 【系统指令：互动叙事模式】 ... ``` block; a few use LaTeX \\colorbox
speech bubbles, a 弹幕 markdown-codeblock convention, or a standalone 输出格式
section). These conflict with each other and with the platform's own bubble
contract (backend/heart/ss09_story/prompt.py:_FORMAT_GUIDE, appended at the end
of every GM system prompt), which is why different scenarios produced
differently-shaped dialogue/action bubbles that the frontend parser
(split_gm_text) couldn't consistently classify.

Fix: surgically remove ONLY the output-format directives listed above.
Everything else — character sheets, plot content, writing-style/pacing
checklists (写作问题清单·格式规范), and the 18+ mode content the scenario
authors wrote — is left byte-for-byte untouched. This was an explicit
product decision (2026-07-24): "保留不动，只改格式" — we do not touch or
neuter any content outside the specific GM-output-formatting directives.

Once the conflicting directives are gone, the platform's own _FORMAT_GUIDE
(now the *only* format instruction reaching the model) is authoritative for
every scenario. No new instructions are appended into these files — that
keeps the diff minimal and preserves the "verbatim injection" storage
convention import_scenarios.py already documents.

Usage:
    python scripts/unify_scenario_formats.py --dry-run          # preview
    python scripts/unify_scenario_formats.py --dry-run --diff   # preview + full diff
    python scripts/unify_scenario_formats.py                    # apply (writes .backup)
    python scripts/unify_scenario_formats.py --only 登仙路       # single file
"""

import argparse
import difflib
import re
from pathlib import Path

DEFAULT_SRC = Path("/Users/wanglixun/Downloads/剧情设定")

# ── Targeted removal patterns ───────────────────────────────────────────
# Each pattern removes ONLY a GM-output-format directive. None of these touch
# character sheets, plot/NPC content, writing-style checklists, or 18+ mode
# instructions — verified file-by-file before this list was finalized.

_PATTERNS: list[tuple[str, re.RegexFlag]] = [
    # 1. The "心理活动用 markdown 代码块" sentence (42 files, verbatim/near-verbatim).
    (
        r"对话末尾用Markdown语法的符号代码块[“\"]text[”\"]形式表示你的心理活动，"
        r"一次三行，每行十五字左右，心理活动真实直白丰富具体，要有真人感。",
        re.MULTILINE,
    ),
    # 2. The fenced ```markdown 【系统指令：互动叙事模式】 ... ``` block (redundant
    #    re-specification of narration/dialogue/action format + turn-taking flow).
    #    Anchored on the distinctive header so unrelated code fences (character
    #    sheet fill-in-the-blank blocks, NPC stat blocks) are never touched.
    (
        r"```markdown\s*\n\s*【系统指令：互动叙事模式】.*?```",
        re.DOTALL,
    ),
    # 3. Now-empty "【格式要求】" headers left behind after (1)+(2) strip their body.
    (r"[ 　]*【格式要求】[ 　]*\n+(?=[ 　]*(?:```|---|\n))", re.MULTILINE),
    (r"[ 　]*【格式要求】[ 　]*(?=\n)", re.MULTILINE),
    # 4. Unfenced "一、输出格式 … 七、首条任务 …" full re-spec (金丝雀一天打三份工).
    #    Lazy match up to (not including) the next 【格式要求】/section marker.
    (
        r"一、输出格式\s*\n.*?七、首条任务.*?(?=\n[ 　]*(?:【格式要求】|需要改进|$))",
        re.DOTALL,
    ),
    # 5. LaTeX \colorbox speech-bubble convention (笼中鸟 / 为躲雨进城堡).
    (
        r"用这个格式(?:用这个格式)?跟我说话[^\n]*\n"
        r"[ 　]*\\?\(\\colorbox\{[^}]+\}\{[^}]+\}\)[^\n]*\n?"
        r"(?:[ 　]*[·\-][^\n]*\n?)*",
        re.MULTILINE,
    ),
    # 6. 弹幕格式 markdown-codeblock convention (笼中鸟).
    (
        r"弹幕格式用Markdown语法的符号代码块[^\n]+\n[ 　]*一次三行到五行[^\n]*\n"
        r"[ 　]*要在前面加一个【弹幕】[^\n]*",
        re.MULTILINE,
    ),
]


def strip_format_instructions(content: str) -> str:
    result = content
    for pattern, flags in _PATTERNS:
        result = re.sub(pattern, "", result, flags=flags)
    # Collapse runs of 3+ blank lines left behind by removal (cosmetic only).
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return result


def unify_one(path: Path, dry_run: bool, show_diff: bool) -> tuple[bool, str]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            original = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        original = raw.decode("utf-8", errors="replace")

    cleaned = strip_format_instructions(original)

    if cleaned == original:
        return False, "unchanged"

    if show_diff:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            cleaned.splitlines(keepends=True),
            fromfile=f"{path.name} (before)",
            tofile=f"{path.name} (after)",
        )
        print("".join(diff))

    if not dry_run:
        backup = path.with_suffix(path.suffix + ".backup")
        if not backup.exists():
            backup.write_bytes(raw)
        path.write_text(cleaned, encoding="utf-8")

    delta = len(original.encode("utf-8")) - len(cleaned.encode("utf-8"))
    return True, f"removed {delta} bytes"


def main() -> None:
    ap = argparse.ArgumentParser(description="Strip conflicting GM output-format directives")
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--diff", action="store_true", help="Print unified diff (use with --dry-run)")
    ap.add_argument("--only", help="Only process files whose name contains this substring")
    args = ap.parse_args()

    if not args.src.is_dir():
        raise SystemExit(f"Directory not found: {args.src}")

    files = sorted(args.src.glob("*.txt"))
    if args.only:
        files = [f for f in files if args.only in f.name]
    if not files:
        raise SystemExit(f"No .txt files found in {args.src} (only={args.only!r})")

    print(f"{'[dry-run] ' if args.dry_run else ''}Processing {len(files)} scenario files\n")

    changed = 0
    for path in files:
        modified, detail = unify_one(path, dry_run=args.dry_run, show_diff=args.diff)
        print(f"{'CHANGED' if modified else 'skip':>8} · {path.name} — {detail}")
        changed += modified

    print(f"\n=== Summary: {changed}/{len(files)} changed ===")
    if args.dry_run:
        print("(dry-run: no files written)")


if __name__ == "__main__":
    main()
