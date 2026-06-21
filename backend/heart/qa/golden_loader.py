#!/usr/bin/env python3
"""
Golden Set loader and validator for SS02 Memory Extractor.

Loads cases from backend/tests/golden/memory_extraction/cases.jsonl,
validates each case against the locked ExtractionEnvelope schema (v1.0.0),
and reports any duplicates, missing fields, schema violations, or
turn-id consistency errors.

Usage:
    python -m heart.qa.golden_loader                     # validate + summary
    python -m heart.qa.golden_loader --verbose           # print per-case detail
    python -m heart.qa.golden_loader --ids-only          # list case IDs only

Author: 心屿团队
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# ── Case format ──────────────────────────────────────────
#
# Each line in cases.jsonl is a JSON object with these fields:
#
#   case_id          : str       — unique identifier (e.g. "coref-001")
#   category         : str       — coverage category
#   window           : list[dict]— TurnInput list
#   l3_snapshot      : list[dict]— L3FactSnapshot list (may be empty)
#   hints            : list[dict]— Hint list (may be empty)
#   expected_envelope : dict     — ExtractionEnvelope (Pydantic-validated)
#   notes            : str       — explanation of expected behavior
#


def _resolve_cases_path() -> Path:
    """Resolve the path to cases.jsonl."""
    # __file__ = backend/heart/qa/golden_loader.py
    # parent.parent.parent = backend/
    return (
        Path(__file__).resolve().parent.parent.parent
        / "tests"
        / "golden"
        / "memory_extraction"
        / "cases.jsonl"
    )


def load_cases(path: Path | None = None) -> list[dict]:
    """Load all cases from the JSONL file.

    Returns:
        List of case dicts (parsed JSON).
    """
    filepath = path or _resolve_cases_path()

    if not filepath.exists():
        print(f"Error: cases file not found at {filepath}", file=sys.stderr)
        sys.exit(1)

    cases: list[dict] = []
    with open(filepath, encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                case = json.loads(line)
                cases.append(case)
            except json.JSONDecodeError as e:
                print(f"Error: invalid JSON at line {lineno}: {e}", file=sys.stderr)
                sys.exit(1)

    return cases


def _check_required_fields(case: dict) -> list[str]:
    """Check that all required top-level fields exist."""
    errors: list[str] = []
    required = ["case_id", "category", "window", "expected_envelope", "notes"]
    for field in required:
        if field not in case:
            errors.append(f"missing required field: {field}")
    return errors


def _validate_window(window: list[dict]) -> tuple[set[int], list[str]]:
    """Validate the window array. Returns (turn_ids, errors)."""
    turn_ids: set[int] = set()
    errors: list[str] = []
    for i, turn in enumerate(window):
        if "turn_id" not in turn:
            errors.append(f"window[{i}] missing turn_id")
        else:
            tid = turn["turn_id"]
            if not isinstance(tid, int):
                errors.append(f"window[{i}].turn_id must be int, got {type(tid).__name__}")
            else:
                turn_ids.add(tid)
        if "speaker" not in turn:
            errors.append(f"window[{i}] missing speaker")
        if "text" not in turn:
            errors.append(f"window[{i}] missing text")
    return turn_ids, errors


def _validate_envelope_consistency(envelope: dict, window_turn_ids: set[int]) -> list[str]:
    """Validate the expected_envelope via Pydantic and check cross-consistency."""
    from heart.ss02_memory.extractor.types import ExtractionEnvelope

    errors: list[str] = []
    validated = ExtractionEnvelope.model_validate(envelope)
    env_turn_ids = set(validated.window.turn_ids)

    if window_turn_ids and env_turn_ids != window_turn_ids:
        errors.append(
            f"envelope.window.turn_ids {sorted(env_turn_ids)} "
            f"≠ input.window turn_ids {sorted(window_turn_ids)}"
        )

    for ci, cand in enumerate(validated.candidates):
        for st in cand.source_turns:
            if st not in env_turn_ids:
                errors.append(
                    f"candidates[{ci}].source_turns contains {st} "
                    f"which is not in window turn_ids {sorted(env_turn_ids)}"
                )

    for di, ds in enumerate(validated.dropped_signals):
        if ds.turn_id not in env_turn_ids:
            errors.append(
                f"dropped_signals[{di}].turn_id {ds.turn_id} "
                f"is not in window turn_ids {sorted(env_turn_ids)}"
            )

    return errors


def _validate_l3_snapshot(l3_snapshot: list[dict]) -> list[str]:
    """Validate the optional l3_snapshot array."""
    fields = ["fact_id", "entity_type", "attribute", "value", "confidence", "last_seen"]
    errors: list[str] = []
    for i, snap in enumerate(l3_snapshot):
        for f in fields:
            if f not in snap:
                errors.append(f"l3_snapshot[{i}] missing {f}")
    return errors


def _validate_case(case: dict) -> list[str]:
    """Validate a single case. Returns a list of error messages (empty = valid)."""
    errors = _check_required_fields(case)
    if errors:
        return errors

    window = case.get("window", [])
    if not isinstance(window, list):
        return ["window must be a list"]

    window_turn_ids, win_errors = _validate_window(window)
    errors.extend(win_errors)

    envelope = case.get("expected_envelope", {})
    try:
        env_errors = _validate_envelope_consistency(envelope, window_turn_ids)
        errors.extend(env_errors)
    except Exception as e:
        errors.append(f"envelope validation failed: {e}")

    l3_snapshot = case.get("l3_snapshot", [])
    if isinstance(l3_snapshot, list):
        errors.extend(_validate_l3_snapshot(l3_snapshot))

    return errors


def validate_all(cases: list[dict], verbose: bool = False) -> tuple[int, int]:
    """Validate all cases. Returns (passed, total)."""
    passed = 0
    total = len(cases)

    for case in cases:
        cid = case.get("case_id", "<missing id>")
        cat = case.get("category", "?")
        errors = _validate_case(case)

        if errors:
            print(f"FAIL  {cid:20s}  ({cat})")
            for e in errors:
                print(f"      └─ {e}")
        else:
            passed += 1
            if verbose:
                candidates = len(case.get("expected_envelope", {}).get("candidates", []))
                dropped = len(case.get("expected_envelope", {}).get("dropped_signals", []))
                turns = len(case.get("window", []))
                print(
                    f"OK    {cid:20s}  ({cat:20s})  turns={turns}  candidates={candidates}  dropped={dropped}"
                )

    return passed, total


def check_duplicates(cases: list[dict]) -> list[str]:
    """Check for duplicate case_ids."""
    seen: dict[str, int] = {}
    dups: list[str] = []
    for case in cases:
        cid = case.get("case_id")
        if cid:
            if cid in seen:
                dups.append(cid)
            else:
                seen[cid] = 1
    return dups


def print_summary(cases: list[dict], passed: int, total: int) -> None:
    """Print a coverage and validation summary."""
    categories: dict[str, int] = {}
    for case in cases:
        cat = case.get("category", "?")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n" + "=" * 60)
    print("Golden Set Summary")
    print("=" * 60)
    print(f"  Total cases:   {total}")
    print(f"  Passed:        {passed}")
    print(f"  Failed:        {total - passed}")

    print("\n  Coverage:")
    for cat in sorted(categories):
        print(f"    {cat:<20s} {categories[cat]}")

    dups = check_duplicates(cases)
    if dups:
        print(f"\n  Duplicate case_ids: {dups}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Memory Extractor golden set")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print per-case detail")
    parser.add_argument("--ids-only", action="store_true", help="List case IDs only")
    parser.add_argument("--file", type=str, help="Path to cases.jsonl (default: auto-resolve)")
    args = parser.parse_args()

    filepath = Path(args.file) if args.file else None
    cases = load_cases(filepath)

    if not cases:
        print("Error: no cases loaded", file=sys.stderr)
        sys.exit(1)

    if args.ids_only:
        for case in cases:
            cid = case.get("case_id", "?")
            cat = case.get("category", "?")
            print(f"{cid}  ({cat})")
        return

    passed, total = validate_all(cases, verbose=args.verbose)
    print_summary(cases, passed, total)

    if passed < total:
        sys.exit(1)


if __name__ == "__main__":
    main()
