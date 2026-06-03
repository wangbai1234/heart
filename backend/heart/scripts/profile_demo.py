"""
Heart Turn Profiler Demo — runs 10 turns against live DeepSeek and prints aggregated report.

Usage:
    HEART_TURN_PROFILER=1 python -m heart.scripts.profile_demo

Requires:
    - DEEPSEEK_API_KEY in .env
    - Heart API running on localhost:8000
"""

from __future__ import annotations

import asyncio
import os
import statistics
import sys
import time
from typing import Any, Dict, List

# Enable turn profiling for this demo
os.environ["HEART_TURN_PROFILER"] = "1"

import uuid

import httpx

DEMO_MESSAGES = [
    "你好，今天天气不错。",
    "我最近有点累，工作压力很大。",
    "你有什么喜欢做的事情吗？",
    "我觉得自己不够好，总是达不到期望。",
    "能给我讲个故事吗？",
    "我今天遇到了一件很有趣的事情，在地铁上看到一只导盲犬。",
    "有时候我觉得很孤独，虽然周围有很多人。",
    "说一个冷笑话给我听听。",
    "你对未来有什么期待吗？",
    "谢谢你陪我聊天，我感觉好多了。",
]

CHARACTER_ID = "rin"
API_URL = os.environ.get("HEART_API_URL", "http://localhost:8000")


async def register_and_login(client: httpx.AsyncClient) -> str:
    user_id = f"profiler-demo-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        f"{API_URL}/api/auth/login",
        json={"user_id": user_id, "email": f"{user_id}@demo.test"},
    )
    if resp.status_code == 200:
        return resp.json()["access_token"]
    resp.raise_for_status()
    return ""  # unreachable, satisfies mypy


async def run_demo_turn(
    client: httpx.AsyncClient,
    token: str,
    message: str,
    history: List[Dict[str, str]],
) -> str:
    messages = history + [{"role": "user", "content": message}]
    resp = await client.post(
        f"{API_URL}/api/chat",
        json={
            "messages": messages,
            "character_id": CHARACTER_ID,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120.0,
    )
    if resp.status_code == 200:
        return resp.json()["response"]
    else:
        print(f"  ERROR: HTTP {resp.status_code}: {resp.text[:200]}")
        return "[error]"


def compute_percentiles(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "mean": 0.0}
    sorted_vals = sorted(values)
    n = len(sorted_vals)

    def _pct(p: float) -> float:
        idx = p / 100.0 * (n - 1)
        lo = int(idx)
        hi = min(lo + 1, n - 1)
        frac = idx - lo
        return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac

    return {
        "p50": _pct(50),
        "p95": _pct(95),
        "p99": _pct(99),
        "mean": statistics.mean(sorted_vals),
    }


def print_report(records: List[Dict[str, Any]]) -> None:  # noqa: C901
    if not records:
        print("\nNo profile records collected. Check HEART_TURN_PROFILER=1.")
        return

    phases_order = [
        "auth",
        "safety_pre",
        "retriever",
        "composer",
        "model_router",
        "anti_pattern",
        "memory_encode",
        "inner_loop",
    ]
    phase_values: Dict[str, List[float]] = {p: [] for p in phases_order}
    total_hot: List[float] = []
    total_cost: List[float] = []
    total_cold: List[float] = []
    model_tokens_in: List[float] = []
    model_tokens_out: List[float] = []

    for rec in records:
        for phase_data in rec.get("phases", []):
            name = phase_data["phase"]
            elapsed = phase_data.get("elapsed_ms", 0)
            if name in phase_values:
                phase_values[name].append(elapsed)
        total_hot.append(rec.get("hot_path_ms", 0))
        total_cost.append(rec.get("total_cost_usd", 0))
        total_cold.append(rec.get("cold_path_ms", 0))
        for phase_data in rec.get("phases", []):
            if "input_tokens" in phase_data:
                model_tokens_in.append(float(phase_data["input_tokens"]))
            if "output_tokens" in phase_data:
                model_tokens_out.append(float(phase_data["output_tokens"]))

    print("\n" + "=" * 92)
    print("  Heart Turn Profiler — 10-turn Aggregate Report")
    print("=" * 92)
    print(f"  {'Phase':<20} {'p50':>8} {'p95':>8} {'p99':>8} {'Mean':>8}  Notes")
    print("-" * 92)

    for phase in phases_order:
        vals = phase_values[phase]
        if not vals:
            print(f"  {phase:<20} {'—':>8} {'—':>8} {'—':>8} {'—':>8}")
            continue
        stats = compute_percentiles(vals)
        note = ""
        if phase == "model_router":
            if model_tokens_in:
                note = (
                    f"in:{int(statistics.mean(model_tokens_in))}"
                    f" out:{int(statistics.mean(model_tokens_out))}"
                )
            if total_cost:
                note += f"  ${statistics.mean(total_cost):.4f}/turn"
        print(
            f"  {phase:<20} "
            f"{stats['p50']:>8.1f} "
            f"{stats['p95']:>8.1f} "
            f"{stats['p99']:>8.1f} "
            f"{stats['mean']:>8.1f}  "
            f"{note}"
        )

    print("-" * 92)
    hot_stats = compute_percentiles(total_hot)
    cost_sum = sum(total_cost)
    cold_stats = compute_percentiles(total_cold)

    print(
        f"  {'TOTAL hot path':<20} "
        f"{hot_stats['p50']:>8.1f} "
        f"{hot_stats['p95']:>8.1f} "
        f"{hot_stats['p99']:>8.1f} "
        f"{hot_stats['mean']:>8.1f}"
    )
    print(
        f"  {'TOTAL cost':<20} {'—':>8} {'—':>8} {'—':>8} $"
        f"{cost_sum:>7.4f}  (sum over {len(records)} turns)"
    )
    print(
        f"  {'TOTAL cold path':<20} "
        f"{cold_stats['p50']:>8.1f} "
        f"{cold_stats['p95']:>8.1f} "
        f"{cold_stats['p99']:>8.1f} "
        f"{cold_stats['mean']:>8.1f}"
    )
    print("=" * 92)

    if records:
        sample_idx = min(4, len(records) - 1)
        print(f"\n  Sample turn breakdown (turn #{sample_idx + 1}):")
        for phase_data in records[sample_idx].get("phases", []):
            extra = ""
            for k, v in phase_data.items():
                if k not in ("phase", "elapsed_ms"):
                    extra += f"  {k}={v}"
            print(f"    {phase_data['phase']:<20} {phase_data['elapsed_ms']:>8.1f} ms{extra}")
        print()


def generate_markdown(records: List[Dict[str, Any]], out_path: str) -> None:
    """Generate a markdown baseline report file."""
    if not records:
        return

    phases_order = [
        "auth",
        "safety_pre",
        "retriever",
        "composer",
        "model_router",
        "anti_pattern",
        "memory_encode",
        "inner_loop",
    ]
    phase_values: Dict[str, List[float]] = {p: [] for p in phases_order}
    total_hot: List[float] = []
    total_cost: List[float] = []

    for rec in records:
        for phase_data in rec.get("phases", []):
            name = phase_data["phase"]
            elapsed = phase_data.get("elapsed_ms", 0)
            if name in phase_values:
                phase_values[name].append(elapsed)
        total_hot.append(rec.get("hot_path_ms", 0))
        total_cost.append(rec.get("total_cost_usd", 0))

    lines = []
    lines.append(f"# Heart Turn Profiler Baseline — {time.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"**Generated**: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"**Turns**: {len(records)}")
    lines.append(f"**Character**: {CHARACTER_ID}")
    lines.append("**Model**: deepseek-reasoner (main)")
    lines.append("")
    lines.append("## Aggregate (p50 / p95 / p99 / mean, ms)")
    lines.append("")
    lines.append("| Phase | p50 | p95 | p99 | Mean | Notes |")
    lines.append("|-------|-----|-----|-----|------|-------|")

    for phase in phases_order:
        vals = phase_values[phase]
        if not vals:
            lines.append(f"| {phase} | — | — | — | — | |")
            continue
        stats = compute_percentiles(vals)
        lines.append(
            f"| {phase} | {stats['p50']:.0f} | {stats['p95']:.0f} | "
            f"{stats['p99']:.0f} | {stats['mean']:.0f} | |"
        )

    hot_stats = compute_percentiles(total_hot)
    cost_sum = sum(total_cost)
    lines.append(
        f"| **TOTAL hot path** | {hot_stats['p50']:.0f} | {hot_stats['p95']:.0f} | "
        f"{hot_stats['p99']:.0f} | {hot_stats['mean']:.0f} | |"
    )
    lines.append(f"| **TOTAL cost** | — | — | — | — | ${cost_sum:.4f} total |")

    lines.append("")
    lines.append("## Per-Turn Detail")
    lines.append("")
    for i, rec in enumerate(records):
        lines.append(f"### Turn {i + 1}")
        lines.append("")
        lines.append(f"- Hot path: {rec.get('hot_path_ms', 0):.0f} ms")
        lines.append(f"- Cost: ${rec.get('total_cost_usd', 0):.6f}")
        lines.append("")
        lines.append("| Phase | Elapsed (ms) | Extra |")
        lines.append("|-------|-------------|-------|")
        for phase_data in rec.get("phases", []):
            extra_parts = [
                f"{k}={v}" for k, v in phase_data.items() if k not in ("phase", "elapsed_ms")
            ]
            extra = ", ".join(extra_parts)
            lines.append(f"| {phase_data['phase']} | {phase_data['elapsed_ms']:.1f} | {extra} |")
        lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        f.write("\n".join(lines))
    print(f"  Baseline written to: {out_path}")


async def main():
    print("Heart Turn Profiler — Demo")
    print(f"  Character: {CHARACTER_ID}")
    print(f"  API: {API_URL}")
    print(f"  Turns: {len(DEMO_MESSAGES)}")
    prof_on = os.environ.get("HEART_TURN_PROFILER") == "1"
    print(f"  Profiler: {'ENABLED' if prof_on else 'DISABLED'}")
    print()

    async with httpx.AsyncClient() as client:
        try:
            health = await client.get(f"{API_URL}/health/live", timeout=5.0)
            if health.status_code != 200:
                print(f"API not healthy: {health.status_code}")
                sys.exit(1)
        except Exception as e:
            print(f"Cannot reach API at {API_URL}: {e}")
            print("Start the API first:  cd backend && make dev")
            sys.exit(1)

        # Reset server-side profile records
        await client.post(f"{API_URL}/api/profile/reset")

        print("Logging in...")
        token = await register_and_login(client)
        print("Token acquired.")

        history: List[Dict[str, str]] = []

        for i, msg in enumerate(DEMO_MESSAGES, 1):
            print(f"\nTurn {i}/{len(DEMO_MESSAGES)}: {msg[:60]}...", end=" ", flush=True)
            t0 = time.monotonic()
            try:
                response = await run_demo_turn(client, token, msg, history)
            except Exception as e:
                print(f"\n  ERROR: {e}")
                continue
            elapsed = (time.monotonic() - t0) * 1000
            resp_preview = response[:80].replace("\n", " ")
            print(f"({elapsed:.0f}ms) → {resp_preview}...")
            history.append({"role": "user", "content": msg})
            history.append({"role": "assistant", "content": response})
            if len(history) > 12:
                history = history[-12:]

    # Fetch profile records from server
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{API_URL}/api/profile/records")
        if resp.status_code == 200:
            data = resp.json()
            records = data.get("records", [])
        else:
            records = []

    print_report(records)

    out_path = f"docs/perf/{time.strftime('%Y-%m-%d')}_baseline.md"
    # Write relative to repo root
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    full_path = repo_root / out_path
    generate_markdown(records, str(full_path))


if __name__ == "__main__":
    asyncio.run(main())
