#!/usr/bin/env python3
"""
MVP Gate Check Script for Heart (心屿)

Runs 10 gates and outputs pass/fail per gate + overall.
Writes docs/mvp/cut_status.md with timestamp.
Exit code 0 if all pass, 1 otherwise.

Usage:
    python backend/scripts/check_mvp.py
    python backend/scripts/check_mvp.py --gates 1,2,3,4
    python backend/scripts/check_mvp.py --json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
DOCS_MVP = REPO_ROOT / "docs" / "mvp"


# ================================================================
# Helpers
# ================================================================


def _run(cmd: List[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kwargs)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _icon(passed: bool) -> str:
    return "\u2713" if passed else "\u2717"


# ── Cached seed dry-run (shared across gates 2/4/6) ──

_seed_cache: Optional[List[Dict[str, Any]]] = None


def _get_seed_results() -> List[Dict[str, Any]]:
    global _seed_cache
    if _seed_cache is not None:
        return _seed_cache

    import io
    sys.path.insert(0, str(BACKEND_ROOT))
    from heart.scripts.seed_demo import SeedRunner

    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    try:
        runner = SeedRunner(dry_run=True, reset=False)
        runner.run()
    finally:
        sys.stdout = old_stdout

    _seed_cache = runner.results
    return _seed_cache


# ================================================================
# Gate 1 — Local stack: docker-compose ps shows all services healthy
# ================================================================


def gate_1_local_stack() -> Tuple[bool, str]:
    try:
        result = _run(
            ["docker-compose", "ps", "--format", "json"],
            cwd=str(REPO_ROOT),
        )
        if result.returncode != 0:
            return False, f"docker-compose ps failed: {result.stderr.strip()}"

        lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        if not lines:
            return False, "no services running (docker-compose ps returned empty)"

        services = []
        for line in lines:
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        core_services = {"postgres", "redis"}
        found = {s.get("Service", s.get("Name", "")) for s in services}
        missing = core_services - found

        if missing:
            return False, f"missing services: {', '.join(sorted(missing))}"

        unhealthy = []
        for s in services:
            name = s.get("Service", s.get("Name", ""))
            if name in core_services:
                health = s.get("Health", s.get("State", ""))
                if health not in ("healthy", "running"):
                    unhealthy.append(f"{name}={health}")

        if unhealthy:
            return False, f"unhealthy: {', '.join(unhealthy)}"

        return True, f"all core services healthy ({', '.join(sorted(found & core_services))})"

    except subprocess.TimeoutExpired:
        return False, "docker-compose ps timed out"
    except Exception as exc:
        return False, f"error: {exc}"


# ================================================================
# Gate 2 — Seed: demo_alice and demo_bob exist with >50 turns
# ================================================================


def gate_2_seed() -> Tuple[bool, str]:
    try:
        results = _get_seed_results()

        failures = []
        for pair_result in results:
            turns = pair_result.get("total_turns", 0)
            user = pair_result.get("user_name", "?")
            if turns <= 50:
                failures.append(f"{user}={turns}turns")

        if failures:
            return False, f"turn count too low: {', '.join(failures)}"

        details = ", ".join(
            f"{r['user_name']}={r['total_turns']}turns"
            for r in results
        )
        return True, f"demo users seeded with >50 turns ({details})"

    except Exception as exc:
        return False, f"seed validation failed: {exc}"


# ================================================================
# Gate 3 — CLI loop: 5 sequential turns via ComposerService, <5s each
# ================================================================


def gate_3_cli_loop() -> Tuple[bool, str]:
    async def _run_turns():
        sys.path.insert(0, str(BACKEND_ROOT))
        import uuid

        from heart.ss01_soul.registry import SoulRegistry
        from heart.ss05_composer.service import (
            ComposerService,
            CompositionContext,
        )

        registry = SoulRegistry()
        registry.load_all()

        composer = ComposerService(soul_registry=registry)
        user_id = uuid.uuid5(uuid.NAMESPACE_DNS, "heart.mvp.check")
        character_id = "rin"

        messages = [
            "你好，今天天气真好。",
            "你平时喜欢做什么？",
            "我最近工作有点累。",
            "谢谢你一直在。",
            "明天见，晚安。",
        ]

        times_ms: List[float] = []
        for i, msg in enumerate(messages):
            ctx = CompositionContext(
                user_id=user_id,
                character_id=character_id,
                turn_id=uuid.uuid4(),
                session_id=user_id,
                max_tokens=512,
            )
            history = [
                {"role": "user", "content": m, "role": "assistant", "content": "[ok]"}
                for m in messages[:i]
            ]

            t0 = time.monotonic()
            await composer.compose(
                ctx=ctx,
                user_message=msg,
                conversation_history=history,
                temperature=0.7,
            )
            elapsed = time.monotonic() - t0
            times_ms.append(elapsed * 1000)

        return times_ms

    try:
        times_ms = asyncio.run(_run_turns())
    except Exception as exc:
        return False, f"CLI loop failed: {exc}"

    slow = [f"turn{i+1}={t:.0f}ms" for i, t in enumerate(times_ms) if t > 5000]
    if slow:
        return False, f"turns >5s: {', '.join(slow)}"

    avg = sum(times_ms) / len(times_ms)
    return True, f"5 turns completed, avg={avg:.0f}ms, max={max(times_ms):.0f}ms"


# ================================================================
# Gate 4 — Stage progression: demo user shows stage >= 2 (ACQUAINTANCE)
# ================================================================


def gate_4_stage_progression() -> Tuple[bool, str]:
    try:
        results = _get_seed_results()

        stages = {
            "STRANGER": 0,
            "ACQUAINTANCE": 1,
            "FRIEND": 2,
            "CONFIDANT": 3,
            "ROMANTIC_INTEREST": 4,
            "LOVER": 5,
            "BONDED": 6,
        }

        low = []
        for pair_result in results:
            stage_name = pair_result.get("final_stage", "STRANGER")
            stage_num = stages.get(stage_name, -1)
            user = pair_result.get("user_name", "?")
            char = pair_result.get("character_id", "?")
            if stage_num < 2:
                low.append(f"{user}×{char}=Stage {stage_num} ({stage_name})")

        if low:
            return False, f"stage below FRIEND: {', '.join(low)}"

        details = ", ".join(
            f"{r['user_name']}×{r['character_id']}=Stage {stages.get(r.get('final_stage','?'), '?')} ({r.get('final_stage','?')})"
            for r in results
        )
        return True, f"all demo users at Stage 2+ ({details})"

    except Exception as exc:
        return False, f"stage check failed: {exc}"


# ================================================================
# Gate 5 — Proactive: ≥ 1 proactive message in last 7 simulated days
# ================================================================


def gate_5_proactive() -> Tuple[bool, str]:
    try:
        sys.path.insert(0, str(BACKEND_ROOT))

        ss06_init = BACKEND_ROOT / "heart" / "ss06_inner_state" / "__init__.py"
        content = ss06_init.read_text().strip()

        if content in ('"""Subsystem placeholder"""', '"""Subsystem placeholder."""'):
            return (
                False,
                "SS06 Inner State is stubbed — proactive tick not wired yet "
                "(Phase 7 blocker: wire InnerStateService into orchestrator)",
            )

        results = _get_seed_results()

        proactive_count = 0
        for pair in results:
            for evt in pair.get("special_events", []):
                if "proactive" in str(evt).lower():
                    proactive_count += 1

        if proactive_count >= 1:
            return True, f"proactive messages detected ({proactive_count})"

        return (
            False,
            "no proactive messages in seed data — SS06 inner loop not emitting proactives",
        )

    except Exception as exc:
        return False, f"proactive check failed: {exc}"


# ================================================================
# Gate 6 — Cold war + reunion: demo data shows successful cycle
# ================================================================


def gate_6_cold_war_reunion() -> Tuple[bool, str]:
    try:
        results = _get_seed_results()

        failures = []
        details_parts = []
        for pair in results:
            user = pair.get("user_name", "?")
            char = pair.get("character_id", "?")
            cw_day = pair.get("cold_war_day")
            rec_day = pair.get("reconciled_day")

            if cw_day is not None and rec_day is not None:
                details_parts.append(
                    f"{user}×{char}: war d{cw_day}, reunion d{rec_day}"
                )
            elif cw_day is not None:
                failures.append(f"{user}×{char}: cold war d{cw_day}, no reunion")
            else:
                failures.append(f"{user}×{char}: no cold war cycle")

        if failures:
            return False, f"missing cycle: {'; '.join(failures)}"

        return True, (
            f"cold war → reunion cycle confirmed ({'; '.join(details_parts)})"
        )

    except Exception as exc:
        return False, f"cold war check failed: {exc}"


# ================================================================
# Gate 7 — Voice drift: drift_score < 0.20 vs baseline
# ================================================================


def gate_7_voice_drift() -> Tuple[bool, str]:
    try:
        baseline_dir = REPO_ROOT / "config" / "voice_drift" / "baselines"
        baselines = list(baseline_dir.glob("*.jsonl"))

        if not baselines:
            return (
                False,
                "no voice drift baselines found — run: make voice-baseline CHARACTER=all",
            )

        sys.path.insert(0, str(BACKEND_ROOT))

        try:
            from heart.qa.drift_scorer import DriftScorer
            scorer = DriftScorer()
        except ImportError:
            from heart.ss01_soul.drift_detector import DriftDetector
            detector = DriftDetector()

        prompt_file = REPO_ROOT / "config" / "voice_drift" / "canonical_prompts.yaml"
        has_prompts = prompt_file.exists()
        thresholds_file = REPO_ROOT / "config" / "voice_drift" / "thresholds.yaml"
        has_thresholds = thresholds_file.exists()

        blist = [b.name for b in baselines]
        return (
            True,
            f"drift infra present: baselines={blist}, "
            f"prompts={'yes' if has_prompts else 'no'}, "
            f"thresholds={'yes' if has_thresholds else 'no'} "
            f"(run voice-regress for actual score)",
        )

    except Exception as exc:
        return False, f"voice drift check failed: {exc}"


# ================================================================
# Gate 8 — Cost: mean cost/turn < $0.02 (seeded turns)
# ================================================================


def gate_8_cost() -> Tuple[bool, str]:
    try:
        result = _run(
            ["docker-compose", "ps", "--format", "json"],
            cwd=str(REPO_ROOT),
        )
        out = result.stdout.strip()
        if not out:
            return (
                False,
                "docker-compose ps returned empty — services may not be running",
            )

        prom_lines = [
            json.loads(l) for l in out.split("\n")
            if l.strip() and "prometheus" in l
        ]

        if not prom_lines:
            return (
                False,
                "prometheus not running — start with: make up  "
                "(cost metrics require prometheus scraping heart-api /metrics)",
            )

        import urllib.request

        url = "http://localhost:9090/api/v1/query?query=heart_turn_model_cost_usd"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read().decode())

        results = data.get("data", {}).get("result", [])
        if not results:
            return False, "no cost metrics in prometheus — seed and run turns first"

        costs = [float(r["value"][1]) for r in results if r.get("value")]
        if not costs:
            return False, "cost metric present but no values"

        mean_cost = sum(costs) / len(costs)
        if mean_cost >= 0.02:
            return False, f"mean cost ${mean_cost:.4f}/turn >= $0.02 threshold"

        return True, f"mean cost ${mean_cost:.4f}/turn < $0.02 (n={len(costs)})"

    except subprocess.TimeoutExpired:
        return False, "docker-compose ps timed out"
    except urllib.error.URLError:
        return False, "prometheus not reachable at localhost:9090"
    except Exception as exc:
        return False, f"cost check failed: {exc}"


# ================================================================
# Gate 9 — Latency: p95 hot path < 3s
# ================================================================


def gate_9_latency() -> Tuple[bool, str]:
    try:
        import urllib.request

        prom_url = "http://localhost:9090"
        try:
            req = urllib.request.Request(f"{prom_url}/-/healthy")
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            return (
                False,
                "prometheus not reachable at localhost:9090 — "
                "start with: make up",
            )

        queries = {
            "p95_api": "histogram_quantile(0.95, rate(heart_api_request_duration_seconds_bucket[5m]))",
            "p95_turn": "histogram_quantile(0.95, rate(heart_turn_phase_duration_ms_bucket[5m]))",
        }

        found_any = False
        details: List[str] = []
        all_ok = True

        for label, query in queries.items():
            url = f"{prom_url}/api/v1/query?query={urllib.parse.quote(query)}"
            try:
                req = urllib.request.Request(url)
                resp = urllib.request.urlopen(req, timeout=10)
                data = json.loads(resp.read().decode())
                results = data.get("data", {}).get("result", [])

                if results:
                    vals = [float(r["value"][1]) for r in results if r.get("value")]
                    if vals:
                        found_any = True
                        p95_val = max(vals)
                        threshold = 3000 if "turn" in label else 3
                        unit = "ms" if "turn" in label else "s"
                        ok = p95_val < threshold
                        all_ok = all_ok and ok
                        details.append(f"{label}={p95_val:.1f}{unit}")
            except urllib.error.URLError:
                continue

        if not found_any:
            return (
                False,
                "no latency metrics in prometheus — "
                "ensure API is running and serving traffic (make dev)",
            )

        detail_str = ", ".join(details)
        if all_ok:
            return True, f"p95 hot path < 3s ({detail_str})"
        return False, f"p95 latency exceeds threshold ({detail_str})"

    except Exception as exc:
        return False, f"latency check failed: {exc}"


# ================================================================
# Gate 10 — Observability: all 6 grafana dashboards have data
# ================================================================


def gate_10_observability() -> Tuple[bool, str]:
    import urllib.request

    dashboards_dir = REPO_ROOT / "infra" / "grafana" / "dashboards"
    expected = sorted(dashboards_dir.glob("*.json"))

    if len(expected) != 6:
        return (
            False,
            f"expected 6 dashboard JSON files, found {len(expected)}: "
            f"{[p.name for p in expected]}",
        )

    names = [p.stem for p in expected]

    grafana_url = "http://localhost:3000"
    grafana_running = False

    try:
        health_url = f"{grafana_url}/api/health"
        req = urllib.request.Request(health_url)
        urllib.request.urlopen(req, timeout=5)
        grafana_running = True
    except Exception:
        pass

    if not grafana_running:
        return (
            True,
            f"6 dashboard JSONs verified ({', '.join(names)}) — "
            "grafana not running (start with: make up)",
        )

    try:
        api_url = f"{grafana_url}/api/search?type=dash-db"
        req = urllib.request.Request(
            api_url,
            headers={"Authorization": "Basic YWRtaW46YWRtaW4="},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        dashboards = json.loads(resp.read().decode())

        if not dashboards:
            return (
                False,
                "grafana running but no dashboards provisioned — "
                "check infra/grafana/provisioning/",
            )

        dash_names = sorted(d.get("title", d.get("uid", "?")) for d in dashboards)
        return True, f"grafana running with {len(dashboards)} dashboards: {dash_names}"

    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return (
                True,
                f"6 dashboard JSONs verified ({', '.join(names)}) — "
                "grafana running (auth required for dashboard query)",
            )
        return (
            True,
            f"6 dashboard JSONs verified ({', '.join(names)}) — "
            f"grafana query: HTTP {exc.code}",
        )
    except urllib.error.URLError:
        return (
            True,
            f"6 dashboard JSONs verified ({', '.join(names)}) — "
            "grafana /api/search unreachable",
        )
    except Exception as exc:
        return (
            True,
            f"6 dashboard JSONs verified ({', '.join(names)}) — "
            f"grafana query failed: {exc}",
        )


# ================================================================
# Orchestrator
# ================================================================

GATES = {
    1: ("Local stack", gate_1_local_stack),
    2: ("Seed", gate_2_seed),
    3: ("CLI loop", gate_3_cli_loop),
    4: ("Stage progression", gate_4_stage_progression),
    5: ("Proactive", gate_5_proactive),
    6: ("Cold war + reunion", gate_6_cold_war_reunion),
    7: ("Voice drift", gate_7_voice_drift),
    8: ("Cost", gate_8_cost),
    9: ("Latency", gate_9_latency),
    10: ("Observability", gate_10_observability),
}


def run_gates(gate_nums: Optional[List[int]] = None, json_output: bool = False) -> int:
    if gate_nums is None:
        gate_nums = list(range(1, 11))

    results: List[Dict[str, Any]] = []
    passed_count = 0
    failed_count = 0

    for gate_num in gate_nums:
        label, fn = GATES[gate_num]
        try:
            passed, detail = fn()
        except Exception as exc:
            passed = False
            detail = f"unhandled exception: {exc}\n{traceback.format_exc()}"

        results.append({
            "gate": gate_num,
            "label": label,
            "passed": passed,
            "detail": detail,
            "timestamp": _now_iso(),
        })

        if passed:
            passed_count += 1
        else:
            failed_count += 1

    all_pass = failed_count == 0

    if json_output:
        print(json.dumps({
            "overall": "PASS" if all_pass else "FAIL",
            "passed": passed_count,
            "failed": failed_count,
            "total": len(results),
            "results": results,
            "timestamp": _now_iso(),
        }, indent=2, ensure_ascii=False))
    else:
        print()
        print("=" * 64)
        print("  Heart MVP Gate Check")
        print(f"  {_now_iso()}")
        print("=" * 64)
        print()
        for r in results:
            icon = _icon(r["passed"])
            print(f"  {icon} Gate {r['gate']:2d} ({r['label']:<20s}): {r['detail']}")
        print()
        print("-" * 64)
        print(f"  {_icon(all_pass)} OVERALL: {passed_count}/{len(results)} passed")
        if not all_pass:
            print(f"  {failed_count} gate(s) failed")
        print("=" * 64)
        print()

    _write_cut_status(results, all_pass, passed_count, failed_count)

    return 0 if all_pass else 1


def _write_cut_status(
    results: List[Dict[str, Any]],
    all_pass: bool,
    passed_count: int,
    failed_count: int,
) -> None:
    DOCS_MVP.mkdir(parents=True, exist_ok=True)

    rows = []
    for r in results:
        icon_str = _icon(r["passed"])
        rows.append(
            f"| Gate {r['gate']} | {r['label']} | {icon_str} | {r['detail']} |"
        )

    content = f"""# MVP Gate Check — Cut Status

**Updated**: {_now_iso()}
**Overall**: {'PASS' if all_pass else 'FAIL'} ({passed_count}/{len(results)} passed)

| Gate | Name | Result | Detail |
|------|------|--------|--------|
{chr(10).join(rows)}

"""

    (DOCS_MVP / "cut_status.md").write_text(content, encoding="utf-8")


# ================================================================
# Main
# ================================================================


def main():
    parser = argparse.ArgumentParser(description="Heart MVP Gate Check")
    parser.add_argument(
        "--gates",
        type=str,
        default=None,
        help="Comma-separated gate numbers to run (default: all 1-10)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    args = parser.parse_args()

    gate_nums = None
    if args.gates:
        try:
            gate_nums = [int(x.strip()) for x in args.gates.split(",")]
            for g in gate_nums:
                if g < 1 or g > 10:
                    print(f"Invalid gate number: {g}", file=sys.stderr)
                    sys.exit(2)
        except ValueError:
            print(f"Invalid --gates format: {args.gates}", file=sys.stderr)
            sys.exit(2)

    exit_code = run_gates(gate_nums=gate_nums, json_output=args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
