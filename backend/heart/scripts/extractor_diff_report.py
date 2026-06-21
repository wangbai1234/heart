#!/usr/bin/env python3
"""
Daily dual-mode extractor diff report.

Compares LLM-extracted facts (fact_nodes) against regex-extracted facts
(memory_l3_facts_shadow_regex) for a given date, producing a markdown report
at docs/audit/memory_extractor_diff_YYYY-MM-DD.md.

Categories:
  - LLM-only (recall gain): facts the LLM found that regex missed
  - Regex-only (recall loss): facts regex found that the LLM missed
  - Value mismatch: same (user, predicate, subject) but different values

Usage:
  # Report for yesterday (default)
  python backend/heart/scripts/extractor_diff_report.py

  # Report for a specific date
  python backend/heart/scripts/extractor_diff_report.py --date 2026-06-18

  # Custom output directory
  python backend/heart/scripts/extractor_diff_report.py --output-dir /tmp/reports

Author: 心屿团队
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

_backend = Path(__file__).resolve().parent.parent
if str(_backend) not in sys.path:
    sys.path.insert(0, str(_backend))

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from heart.core.config import settings


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Daily dual-mode extractor diff report")
    p.add_argument(
        "--date",
        type=str,
        default=None,
        help="Date to report on (YYYY-MM-DD). Defaults to yesterday.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print summary to stdout instead of writing a file.",
    )
    p.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Directory for markdown reports (default: repo_root/docs/audit).",
    )
    return p.parse_args()


def _resolve_date(date_str: str | None) -> date:
    if date_str:
        return date.fromisoformat(date_str)
    return date.today() - timedelta(days=1)


def _output_dir(output_dir: str | None) -> Path:
    if output_dir:
        return Path(output_dir)
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    return repo_root / "docs" / "audit"


def _db_url() -> str:
    url = settings.database_url
    if "+asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


async def _fetch_llm_facts(session: AsyncSession, report_date: date) -> list[dict]:
    """Fetch LLM-extracted facts created on ``report_date``."""
    start = datetime(report_date.year, report_date.month, report_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    stmt = text(
        """
    SELECT id, user_id, predicate, subject, object, literal_text, confidence, created_at
    FROM fact_nodes
    WHERE created_at >= :start AND created_at < :end
      AND do_not_recall = false
      AND is_active = true
    ORDER BY user_id, predicate, subject
    """
    )
    result = await session.execute(stmt, {"start": start, "end": end})
    return [dict(row._mapping) for row in result.fetchall()]


async def _fetch_regex_facts(session: AsyncSession, report_date: date) -> list[dict]:
    """Fetch regex shadow facts created on ``report_date``."""
    start = datetime(report_date.year, report_date.month, report_date.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    stmt = text(
        """
    SELECT id, user_id, predicate, subject, object, literal_text, confidence, created_at
    FROM memory_l3_facts_shadow_regex
    WHERE created_at >= :start AND created_at < :end
    ORDER BY user_id, predicate, subject
    """
    )
    result = await session.execute(stmt, {"start": start, "end": end})
    return [dict(row._mapping) for row in result.fetchall()]


def _key(fact: dict) -> tuple:
    """Normalized matching key: (user_id, predicate, subject)."""
    return (
        str(fact["user_id"]),
        (fact["predicate"] or "").lower().strip(),
        (fact["subject"] or "").lower().strip(),
    )


def _compare(llm_facts: list[dict], regex_facts: list[dict]) -> dict:
    """Compare LLM vs regex facts and categorise differences.

    Returns a dict with three lists:
      - llm_only: facts LLM found that regex missed (recall gain)
      - regex_only: facts regex found that LLM missed (recall loss)
      - value_mismatch: dicts with llm_fact + regex_fact for same key, diff value
    """
    llm_by_key: dict[tuple, list[dict]] = {}
    for f in llm_facts:
        llm_by_key.setdefault(_key(f), []).append(f)

    regex_by_key: dict[tuple, list[dict]] = {}
    for f in regex_facts:
        regex_by_key.setdefault(_key(f), []).append(f)

    llm_keys = set(llm_by_key)
    regex_keys = set(regex_by_key)

    llm_only: list[dict] = []
    for k in llm_keys - regex_keys:
        llm_only.extend(llm_by_key[k])

    regex_only: list[dict] = []
    for k in regex_keys - llm_keys:
        regex_only.extend(regex_by_key[k])

    value_mismatch: list[dict] = []
    for k in llm_keys & regex_keys:
        for lf in llm_by_key[k]:
            for rf in regex_by_key[k]:
                lv = (lf["object"] or "").strip()
                rv = (rf["object"] or "").strip()
                if lv != rv:
                    value_mismatch.append({"llm": lf, "regex": rf})

    return {
        "llm_only": llm_only,
        "regex_only": regex_only,
        "value_mismatch": value_mismatch,
    }


def _format_markdown(
    report_date: date,
    llm_count: int,
    regex_count: int,
    diff: dict,
) -> str:
    """Format the diff report as markdown."""
    lines: list[str] = []
    lines.append(f"# Memory Extractor Diff Report — {report_date.isoformat()}")
    lines.append("")
    lines.append(f"**Generated**: {datetime.now(timezone.utc).isoformat(timespec='seconds')}Z")
    lines.append("**Mode**: dual (LLM → `fact_nodes`, regex → `memory_l3_facts_shadow_regex`)")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Metric | Count |")
    lines.append("|---|---|")
    lines.append(f"| LLM facts (total) | {llm_count} |")
    lines.append(f"| Regex facts (total) | {regex_count} |")
    lines.append(f"| LLM-only (recall gain) | {len(diff['llm_only'])} |")
    lines.append(f"| Regex-only (recall loss) | {len(diff['regex_only'])} |")
    lines.append(f"| Value mismatch | {len(diff['value_mismatch'])} |")
    lines.append("")

    # ── LLM-only (recall gain) ──
    lines.append("## LLM-only Facts (Recall Gain)")
    lines.append("")
    lines.append("Facts the LLM found that regex missed.")
    lines.append("")
    if diff["llm_only"]:
        lines.append("| user_id | predicate | subject | object | confidence |")
        lines.append("|---|---|---|---|---|")
        for f in diff["llm_only"]:
            lines.append(
                f"| {f['user_id']} | {f['predicate']} | {f['subject']} "
                f"| {f['object']} | {f['confidence']:.2f} |"
            )
    else:
        lines.append("_None — regex caught everything the LLM found._")
    lines.append("")

    # ── Regex-only (recall loss) ──
    lines.append("## Regex-only Facts (Recall Loss)")
    lines.append("")
    lines.append("Facts regex found that the LLM missed. These may indicate prompt or schema gaps.")
    lines.append("")
    if diff["regex_only"]:
        lines.append("| user_id | predicate | subject | object | confidence |")
        lines.append("|---|---|---|---|---|")
        for f in diff["regex_only"]:
            lines.append(
                f"| {f['user_id']} | {f['predicate']} | {f['subject']} "
                f"| {f['object']} | {f['confidence']:.2f} |"
            )
    else:
        lines.append("_None — LLM caught everything regex found._")
    lines.append("")

    # ── Value mismatch ──
    lines.append("## Value Mismatches")
    lines.append("")
    lines.append(
        "Same (user, predicate, subject) key but different values. Requires HUMAN arbitration."
    )
    lines.append("")
    if diff["value_mismatch"]:
        lines.append("| user_id | predicate | subject | LLM value | Regex value |")
        lines.append("|---|---|---|---|---|")
        for m in diff["value_mismatch"]:
            lf = m["llm"]
            rf = m["regex"]
            lines.append(
                f"| {lf['user_id']} | {lf['predicate']} | {lf['subject']} "
                f"| {lf['object']} | {rf['object']} |"
            )
    else:
        lines.append("_None — all shared keys have matching values._")
    lines.append("")

    # ── Cumulative metrics (if this script is run daily with persistent counters) ──
    lines.append("## Acceptance Criteria Tracking")
    lines.append("")
    lines.append("| Criterion | Status | Notes |")
    lines.append("|---|---|---|")
    llm_only_count = len(diff["llm_only"])
    regex_only_count = len(diff["regex_only"])
    total_llm = max(llm_count, 1)
    total_regex = max(regex_count, 1)
    lines.append(
        f"| LLM recall vs regex | "
        f"{'PASS' if total_llm >= total_regex * 1.5 else 'OBSERVE'} | "
        f"LLM: {total_llm}, Regex: {total_regex} "
        f"(target: LLM >= regex × 1.5) |"
    )
    lines.append(
        f"| LLM-only recall gain | "
        f"{'INFO' if llm_only_count > 0 else '—'} | "
        f"{llm_only_count} facts LLM found that regex missed |"
    )
    lines.append(
        f"| Regex-only recall loss | "
        f"{'WARN' if regex_only_count > 0 else '—'} | "
        f"{regex_only_count} facts regex found that LLM missed |"
    )
    lines.append(
        f"| Value mismatches | "
        f"{'NEEDS_REVIEW' if diff['value_mismatch'] else '—'} | "
        f"{len(diff['value_mismatch'])} facts need HUMAN arbitration |"
    )
    lines.append("")
    return "\n".join(lines)


async def run(
    date_str: str | None = None, output_dir: str | None = None, dry_run: bool = False
) -> None:
    """Main entry point — run the diff report."""
    report_date = _resolve_date(date_str)
    out_dir = _output_dir(output_dir)

    engine = create_async_engine(_db_url(), echo=False)

    async with engine.begin() as conn:
        session = AsyncSession(conn)

        llm_facts = await _fetch_llm_facts(session, report_date)
        regex_facts = await _fetch_regex_facts(session, report_date)

        diff = _compare(llm_facts, regex_facts)
        md = _format_markdown(report_date, len(llm_facts), len(regex_facts), diff)

    await engine.dispose()

    if dry_run:
        print(md)
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    filename = out_dir / f"memory_extractor_diff_{report_date.isoformat()}.md"
    filename.write_text(md, encoding="utf-8")
    print(f"Report written to {filename}")


def main() -> None:
    import asyncio

    args = _parse_args()
    asyncio.run(run(date_str=args.date, output_dir=args.output_dir, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
