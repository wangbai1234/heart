"""
Memory Extractor Golden Set — PR gate + nightly live regression.

Fake mode (pytest.mark.golden):
  Loads all cases from cases.jsonl and validates each expected_envelope
  against the locked ExtractionEnvelope schema, checking turn-id consistency
  and source_turns / dropped_signals references.

  Fast, no DB/LLM needed — runs on every PR that touches ss02_memory.

Live mode (pytest.mark.golden_live):
  Runs each case through the real LLM Extractor and compares the output to
  the expected envelope using semantic scoring (entity/attribute match + value
  comparison).  Generates an HTML score report.

  Nightly only — requires --live flag + LLM API key.

Usage:
  pytest tests/golden -m golden -v          # fake mode (PR gate)
  pytest tests/golden -m golden_live --live -v  # real LLM (nightly)

Author: 心屿团队
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pytest

_CASES_DIR = Path(__file__).resolve().parent
_CASES_PATH = _CASES_DIR / "cases.jsonl"

pytestmark_fake = [pytest.mark.golden]
pytestmark_live = [pytest.mark.golden_live, pytest.mark.live]


# ── Case loader ────────────────────────────────────────────────


def _load_all_cases() -> list[dict]:
    """Load all golden cases from cases.jsonl."""
    if not _CASES_PATH.exists():
        pytest.skip(f"Golden cases not found: {_CASES_PATH}")
    cases: list[dict] = []
    with open(_CASES_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))
    return cases


def _case_ids() -> list[str]:
    """Return case IDs for parameterization."""
    cases = _load_all_cases()
    return [c["case_id"] for c in cases]


def _get_case(case_id: str) -> dict:
    """Get a single case by ID."""
    for c in _load_all_cases():
        if c["case_id"] == case_id:
            return c
    raise ValueError(f"Case not found: {case_id}")


# ── Fake mode: schema validation ───────────────────────────────


@pytest.mark.golden
@pytest.mark.parametrize("case_id", _case_ids())
def test_golden_case_schema_valid(case_id: str) -> None:
    """Each golden case's expected_envelope must validate against the schema."""
    from heart.ss02_memory.extractor.types import ExtractionEnvelope

    case = _get_case(case_id)
    envelope = case["expected_envelope"]
    validated = ExtractionEnvelope.model_validate(envelope)
    assert validated is not None


@pytest.mark.golden
@pytest.mark.parametrize("case_id", _case_ids())
def test_golden_case_window_consistency(case_id: str) -> None:
    """Window turn_ids must match input window."""
    from heart.ss02_memory.extractor.types import ExtractionEnvelope

    case = _get_case(case_id)
    envelope = case["expected_envelope"]
    validated = ExtractionEnvelope.model_validate(envelope)

    input_turn_ids = {t["turn_id"] for t in case["window"]}
    env_turn_ids = set(validated.window.turn_ids)

    assert env_turn_ids == input_turn_ids, (
        f"envelope.window.turn_ids {sorted(env_turn_ids)} "
        f"≠ input.window turn_ids {sorted(input_turn_ids)}"
    )


@pytest.mark.golden
@pytest.mark.parametrize("case_id", _case_ids())
def test_golden_case_source_turns_valid(case_id: str) -> None:
    """All source_turns in candidates must reference valid window turn_ids."""
    from heart.ss02_memory.extractor.types import ExtractionEnvelope

    case = _get_case(case_id)
    envelope = case["expected_envelope"]
    validated = ExtractionEnvelope.model_validate(envelope)

    valid_turn_ids = set(validated.window.turn_ids)
    for ci, cand in enumerate(validated.candidates):
        for st in cand.source_turns:
            assert st in valid_turn_ids, (
                f"candidates[{ci}].source_turns contains {st} "
                f"which is not in window turn_ids {sorted(valid_turn_ids)}"
            )


@pytest.mark.golden
@pytest.mark.parametrize("case_id", _case_ids())
def test_golden_case_dropped_signals_valid(case_id: str) -> None:
    """All dropped_signals turn_ids must reference valid window turn_ids."""
    from heart.ss02_memory.extractor.types import ExtractionEnvelope

    case = _get_case(case_id)
    envelope = case["expected_envelope"]
    validated = ExtractionEnvelope.model_validate(envelope)

    valid_turn_ids = set(validated.window.turn_ids)
    for di, ds in enumerate(validated.dropped_signals):
        assert ds.turn_id in valid_turn_ids, (
            f"dropped_signals[{di}].turn_id {ds.turn_id} "
            f"is not in window turn_ids {sorted(valid_turn_ids)}"
        )


@pytest.mark.golden
def test_golden_set_coverage() -> None:
    """Golden set must meet the coverage matrix minimums."""
    cases = _load_all_cases()
    categories: dict[str, int] = {}
    for c in cases:
        cat = c.get("category", "?")
        categories[cat] = categories.get(cat, 0) + 1

    minimums = {
        "coreference": 6,
        "fragmentation": 5,
        "rhetoric": 6,
        "question": 4,
        "negation": 4,
        "supersession": 5,
        "plain_disclosure": 8,
        "sensitive": 3,
        "adversarial": 5,
        "mixed": 2,
    }

    for cat, minimum in minimums.items():
        actual = categories.get(cat, 0)
        assert actual >= minimum, f"Coverage gap: {cat} has {actual} cases, minimum is {minimum}"

    assert len(cases) >= 30, f"Golden set must have ≥ 30 cases, got {len(cases)}"


# ── Live mode: real LLM scoring ────────────────────────────────


@dataclass
class CandidateScore:
    """Per-candidate score from live LLM comparison."""

    matched: bool = False
    entity_type_match: bool = False
    attribute_match: bool = False
    value_exact: bool = False
    value_fuzzy: bool = False
    notes: str = ""


def _score_value(expected: str, actual: str) -> tuple[bool, bool]:
    """Compare two values. Returns (exact_match, fuzzy_match)."""
    e = expected.strip().lower()
    a = actual.strip().lower()
    if e == a:
        return True, True
    # Fuzzy: one contains the other, or differ by whitespace/punctuation
    if e in a or a in e:
        return False, True
    return False, False


def _score_envelope(
    expected: dict,
    actual: dict,
    case_id: str,
) -> dict:
    """Score a live LLM output against the expected envelope.

    Per memory_golden_set_design.md §4.2: all HARD fields (kind / operation /
    prior_value_id / entity_type / attribute / dropped turn_id+reason) must
    match. SEMI fields (source_turns / value) are checked but don't block
    pass individually. SOFT fields (confidence / reasoning citation) are
    recorded for audit.

    Returns a dict with overall score, per-candidate details, and hard_fails.
    """
    import re as _re

    exp_cands = expected.get("candidates", [])
    act_cands = actual.get("candidates", [])
    exp_dropped = expected.get("dropped_signals", [])

    # ── Candidate key matching ────────────────────────────────
    exp_by_key: dict[tuple[str, str], dict] = {}
    for c in exp_cands:
        key = (c["entity_type"], c["attribute"])
        exp_by_key[key] = c

    act_by_key: dict[tuple[str, str], dict] = {}
    for c in act_cands:
        key = (c["entity_type"], c["attribute"])
        act_by_key[key] = c

    exp_keys = set(exp_by_key)
    act_keys = set(act_by_key)

    # Both empty → perfect score
    if not exp_keys and not act_keys:
        # Still check dropped_signals
        drop_score = _score_dropped(exp_dropped, actual.get("dropped_signals", []))
        return {
            "case_id": case_id,
            "expected_candidates": 0,
            "actual_candidates": 0,
            "expected_dropped": len(exp_dropped),
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "precision": 1.0,
            "recall": 1.0,
            "f1": 1.0,
            "exact_match_rate": 1.0,
            "passed": len(drop_score["hard_fails"]) == 0,
            "tp_details": [],
            "fp_details": [],
            "fn_details": [],
            "hard_fails": drop_score["hard_fails"],
            "drop_tp": drop_score["tp"],
            "drop_fp": drop_score["fp"],
            "drop_fn": drop_score["fn"],
        }

    # ── True positives / false positives / false negatives ─────
    tp_keys = exp_keys & act_keys
    fp_keys = act_keys - exp_keys
    fn_keys = exp_keys - act_keys

    # ── Score each TP with full HARD / SEMI / SOFT checks ─────
    hard_fails: list[str] = []
    tp_details: list[dict] = []
    for key in tp_keys:
        exp = exp_by_key[key]
        act = act_by_key[key]
        exact_val, fuzzy_val = _score_value(exp["value"], act["value"])
        detail = {
            "entity_type": key[0],
            "attribute": key[1],
            "expected_value": exp["value"],
            "actual_value": act["value"],
            "value_exact": exact_val,
            "value_fuzzy": fuzzy_val,
            "operation_match": exp.get("operation") == act.get("operation"),
        }
        kind_match = exp.get("kind") == act.get("kind")
        detail["kind_match"] = kind_match
        if not kind_match:
            hard_fails.append(
                f"{key[0]}.{key[1]}: kind mismatch "
                f"(exp={exp.get('kind')}, act={act.get('kind')})"
            )
        if not detail["operation_match"]:
            hard_fails.append(
                f"{key[0]}.{key[1]}: operation mismatch "
                f"(exp={exp.get('operation')}, act={act.get('operation')})"
            )
        exp_pvid = exp.get("prior_value_id")
        act_pvid = act.get("prior_value_id")
        pvid_match = (exp_pvid or None) == (act_pvid or None)
        detail["prior_value_id_match"] = pvid_match
        if not pvid_match:
            hard_fails.append(
                f"{key[0]}.{key[1]}: prior_value_id mismatch "
                f"(exp={exp_pvid}, act={act_pvid})"
            )

        # source_turns SEMI: accept any overlap; only HARD when completely disjoint
        exp_st = set(exp.get("source_turns", []))
        act_st = set(act.get("source_turns", []))
        st_overlap = bool(exp_st & act_st)
        st_exact = exp_st == act_st
        detail["source_turns_match"] = st_exact
        detail["source_turns_overlap"] = st_overlap
        if exp_st and act_st and not st_overlap:
            # Complete disjoint → HARD failure
            hard_fails.append(
                f"{key[0]}.{key[1]}: source_turns completely disjoint "
                f"(exp={sorted(exp_st)}, act={sorted(act_st)})"
            )

        # reasoning floor check: must cite at least one source turn
        reasoning = act.get("reasoning", "")
        src_ids = act.get("source_turns", [])
        cites_turn = any(
            _re.search(rf"\bT{sid}\b", reasoning, _re.IGNORECASE)
            for sid in src_ids
        )
        detail["reasoning_citation_ok"] = cites_turn
        if not cites_turn and src_ids:
            hard_fails.append(
                f"{key[0]}.{key[1]}: reasoning missing turn citation"
            )

        tp_details.append(detail)

    fp_details = [
        {
            "entity_type": key[0],
            "attribute": key[1],
            "actual_value": act_by_key[key]["value"],
        }
        for key in fp_keys
    ]
    fn_details = [
        {
            "entity_type": key[0],
            "attribute": key[1],
            "expected_value": exp_by_key[key]["value"],
        }
        for key in fn_keys
    ]

    # ── Dropped signals scoring ────────────────────────────────
    act_dropped = actual.get("dropped_signals", [])
    drop_score = _score_dropped(exp_dropped, act_dropped)
    hard_fails.extend(drop_score["hard_fails"])

    # ── Candidate precision / recall ───────────────────────────
    precision = len(tp_keys) / max(len(act_keys), 1)
    recall = len(tp_keys) / max(len(exp_keys), 1)
    f1 = 2 * precision * recall / max(precision + recall, 0.001)
    exact_matches = sum(1 for d in tp_details if d["value_exact"])
    exact_rate = exact_matches / max(len(tp_keys), 1)

    # ── Pass / fail ────────────────────────────────────────────
    drop_recall = drop_score["recall"]
    has_hard_fail = len(hard_fails) > 0
    passed = (
        not has_hard_fail
        and recall >= 0.8
        and precision >= 0.7
        and drop_recall >= 0.8
    )

    return {
        "case_id": case_id,
        "expected_candidates": len(exp_cands),
        "actual_candidates": len(act_cands),
        "expected_dropped": len(exp_dropped),
        "tp": len(tp_keys),
        "fp": len(fp_keys),
        "fn": len(fn_keys),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
        "exact_match_rate": round(exact_rate, 3),
        "passed": passed,
        "hard_fails": hard_fails,
        "tp_details": tp_details,
        "fp_details": fp_details,
        "fn_details": fn_details,
        "drop_tp": drop_score["tp"],
        "drop_fp": drop_score["fp"],
        "drop_fn": drop_score["fn"],
        "drop_recall": drop_score["recall"],
        "drop_precision": drop_score["precision"],
        "soft_warnings": drop_score.get("soft_warnings", []),
    }


def _score_dropped(
    exp_dropped: list[dict],
    act_dropped: list[dict],
) -> dict:
    """Score dropped_signals by turn_id only (reason is SOFT).

    If both sides agree a turn should be dropped, it's a TP regardless of
    reason text.  Reason mismatches are recorded as soft_warnings for audit.
    """
    # Index by turn_id
    exp_by_turn: dict[int, str] = {d["turn_id"]: d.get("reason", "") for d in exp_dropped}
    act_by_turn: dict[int, str] = {d["turn_id"]: d.get("reason", "") for d in act_dropped}

    exp_turns = set(exp_by_turn)
    act_turns = set(act_by_turn)

    # TP: turn dropped by both (reason may differ → soft warning)
    tp_turns = exp_turns & act_turns
    fp_turns = act_turns - exp_turns
    fn_turns = exp_turns - act_turns

    n_exp = max(len(exp_turns), 1)
    n_act = max(len(act_turns), 1)

    precision = len(tp_turns) / n_act
    recall = len(tp_turns) / n_exp

    if not exp_turns and not act_turns:
        precision = 1.0
        recall = 1.0

    hard_fails: list[str] = []
    soft_warnings: list[str] = []

    for turn_id in fp_turns:
        hard_fails.append(
            f"dropped T{turn_id}: unexpected drop (reason={act_by_turn[turn_id]})"
        )
    for turn_id in fn_turns:
        hard_fails.append(
            f"dropped T{turn_id}: missed expected drop (reason={exp_by_turn[turn_id]})"
        )
    for turn_id in tp_turns:
        exp_reason = exp_by_turn[turn_id]
        act_reason = act_by_turn[turn_id]
        if exp_reason != act_reason:
            soft_warnings.append(
                f"dropped T{turn_id}: reason differs "
                f"(exp={exp_reason}, act={act_reason})"
            )

    return {
        "tp": len(tp_turns),
        "fp": len(fp_turns),
        "fn": len(fn_turns),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "hard_fails": hard_fails,
        "soft_warnings": soft_warnings,
    }


def _generate_html_report(scores: list[dict], output_path: str) -> None:
    """Generate an HTML score report with HARD-fail details."""
    total = len(scores)
    passed = sum(1 for s in scores if s["passed"])
    pass_rate = passed / max(total, 1) * 100
    avg_precision = sum(s["precision"] for s in scores) / max(total, 1)
    avg_recall = sum(s["recall"] for s in scores) / max(total, 1)
    avg_f1 = sum(s["f1"] for s in scores) / max(total, 1)
    drop_tp = sum(s.get("drop_tp", 0) for s in scores)
    drop_fp = sum(s.get("drop_fp", 0) for s in scores)
    drop_fn = sum(s.get("drop_fn", 0) for s in scores)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows_html = ""
    for s in scores:
        status = "✅ PASS" if s["passed"] else "❌ FAIL"
        tp_fmt = ", ".join(
            f"{d['entity_type']}.{d['attribute']}={d['actual_value']}"
            + (" ✓" if d.get("value_exact") else " ~")
            for d in s["tp_details"]
        )
        fn_fmt = ", ".join(
            f"{d['entity_type']}.{d['attribute']}={d['expected_value']}" for d in s["fn_details"]
        )
        fp_fmt = ", ".join(
            f"{d['entity_type']}.{d['attribute']}={d['actual_value']}" for d in s["fp_details"]
        )
        hf_fmt = "; ".join(s.get("hard_fails", []))
        sw_fmt = "; ".join(s.get("soft_warnings", []))
        hf_display = hf_fmt
        if sw_fmt:
            hf_display = hf_fmt + ("; " if hf_fmt else "") + "[SOFT] " + sw_fmt
        if not hf_display:
            hf_display = "—"
        rows_html += f"""<tr>
            <td>{html.escape(s["case_id"])}</td>
            <td>{status}</td>
            <td>{s["precision"]}</td>
            <td>{s["recall"]}</td>
            <td>{s["f1"]}</td>
            <td>{s["tp"]}/{s["fp"]}/{s["fn"]}</td>
            <td>{html.escape(tp_fmt) if tp_fmt else "—"}</td>
            <td>{html.escape(fn_fmt) if fn_fmt else "—"}</td>
            <td>{html.escape(fp_fmt) if fp_fmt else "—"}</td>
            <td style="color:#ff9800">{html.escape(hf_display)}</td>
        </tr>"""

    html_content = f"""<!DOCTYPE html>
<html lang="zh">
<head>
    <meta charset="UTF-8">
    <title>Memory Extractor Golden Set — Live Score Report</title>
    <style>
        body {{ font-family: Menlo, Monaco, monospace; margin: 2em; background: #1a1a2e; color: #e0e0e0; }}
        h1 {{ color: #7b68ee; }}
        .summary {{ display: flex; gap: 2em; margin: 1em 0; flex-wrap: wrap; }}
        .metric {{ background: #16213e; padding: 1em; border-radius: 8px; text-align: center; min-width: 120px; }}
        .metric .value {{ font-size: 2em; font-weight: bold; color: #7b68ee; }}
        .metric .label {{ font-size: 0.85em; color: #aaa; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 1em; font-size: 0.80em; }}
        th {{ background: #16213e; padding: 8px; text-align: left; position: sticky; top: 0; }}
        td {{ padding: 6px 8px; border-bottom: 1px solid #333; vertical-align: top; max-width: 320px; overflow-wrap: break-word; }}
        tr:hover {{ background: #1f3460; }}
        .pass {{ color: #4caf50; }}
        .fail {{ color: #f44336; }}
    </style>
</head>
<body>
    <h1>Memory Extractor Golden Set — Live Score Report (Strict)</h1>
    <p>Generated: {now}Z | Threshold: no HARD failures, recall ≥ 0.8, precision ≥ 0.7, drop_recall ≥ 0.8</p>

    <div class="summary">
        <div class="metric">
            <div class="value">{passed}/{total}</div>
            <div class="label">Passed ({pass_rate:.0f}%)</div>
        </div>
        <div class="metric">
            <div class="value">{avg_precision:.3f}</div>
            <div class="label">Avg Precision</div>
        </div>
        <div class="metric">
            <div class="value">{avg_recall:.3f}</div>
            <div class="label">Avg Recall</div>
        </div>
        <div class="metric">
            <div class="value">{avg_f1:.3f}</div>
            <div class="label">Avg F1</div>
        </div>
        <div class="metric">
            <div class="value">{drop_tp}/{drop_fp}/{drop_fn}</div>
            <div class="label">Drop TP/FP/FN</div>
        </div>
    </div>

    <table>
        <tr>
            <th>Case</th>
            <th>Status</th>
            <th>Prec</th>
            <th>Recall</th>
            <th>F1</th>
            <th>TP/FP/FN</th>
            <th>True Positives</th>
            <th>Missed (FN)</th>
            <th>Extra (FP)</th>
            <th>Hard Fail Details</th>
        </tr>
        {rows_html}
    </table>
</body>
</html>"""

    Path(output_path).write_text(html_content, encoding="utf-8")
    print(f"\nScore report written to {output_path}")


@pytest.mark.golden_live
@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.parametrize("case_id", _case_ids())
async def test_golden_case_live_llm(case_id: str) -> None:
    """Run a golden case through the real LLM Extractor and score.

    Requires --live flag + LLM API key configured in .env.
    """
    case = _get_case(case_id)

    # Build QueueItem from case
    from uuid import uuid4

    from heart.core.config import settings
    from heart.infra.llm.router import get_model_router, initialize_router
    from heart.ss02_memory.extractor.llm_extractor import LLMExtractor
    from heart.ss02_memory.extractor.prompt_builder import MODEL as EXTRACTOR_MODEL
    from heart.ss02_memory.extractor.types import (
        Hint,
        L3FactSnapshot,
        QueueItem,
        TurnInput,
    )

    window = [
        TurnInput(
            turn_id=t["turn_id"],
            speaker=t.get("speaker", "user"),
            ts=t.get("ts", "2026-01-01T00:00:00Z"),
            text=t["text"],
        )
        for t in case["window"]
    ]

    l3_snapshot = [
        L3FactSnapshot(
            fact_id=s.get("fact_id", uuid4()),
            entity_type=s.get("entity_type", "self"),
            entity_ref=s.get("entity_ref"),
            attribute=s.get("attribute", "other"),
            value=s.get("value", ""),
            confidence=s.get("confidence", 0.5),
            last_seen=s.get("last_seen", "2026-01-01"),
        )
        for s in case.get("l3_snapshot", [])
    ]

    hints = [
        Hint(
            turn_id=h.get("turn_id", 1),
            raw_phrase=h.get("raw_phrase", ""),
            suspected_attribute=h.get("suspected_attribute", "other"),
        )
        for h in case.get("hints", [])
    ]

    queue_item = QueueItem(
        extractor_run_id=uuid4(),
        session_id=uuid4(),
        window=window,
        l3_snapshot=l3_snapshot,
        hints=hints,
        model=EXTRACTOR_MODEL,
    )

    # Call the real LLM
    await initialize_router()
    router = await get_model_router()
    extractor = LLMExtractor(router=router)
    results = await extractor.run([queue_item])
    result = results[0] if results else None

    if result is None or result.failed:
        pytest.fail(
            f"Live LLM extraction failed for {case_id}: {result.error if result else 'no result'}"
        )

    # Score against expected
    actual_env = result.envelope.model_dump(mode="json")
    expected_env = case["expected_envelope"]
    score = _score_envelope(expected_env, actual_env, case_id)

    # Collect scores for HTML report
    _live_scores.append(score)

    assert score["passed"], (
        f"Case {case_id} failed: precision={score['precision']}, "
        f"recall={score['recall']}, f1={score['f1']}"
    )


# ── Live mode: aggregate report ────────────────────────────────

_live_scores: list[dict] = []


@pytest.mark.golden_live
@pytest.mark.live
def test_golden_live_aggregate_report() -> None:
    """Generate HTML report from all live golden scores."""
    if not _live_scores:
        pytest.skip("No live scores collected — run individual cases first")

    total = len(_live_scores)
    passed = sum(1 for s in _live_scores if s["passed"])
    pass_rate = passed / max(total, 1) * 100

    _generate_html_report(_live_scores, "/tmp/golden_score_report.html")

    assert pass_rate >= 90, (
        f"Golden set pass rate {pass_rate:.1f}% < 90% threshold. ({passed}/{total} cases passed)"
    )
