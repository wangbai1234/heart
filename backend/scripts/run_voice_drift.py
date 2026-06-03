#!/usr/bin/env python3
"""Voice Drift CLI — generate baseline, run regression, build reports.

Per docs/design/soul_drift_regression.md §8.

Usage:
  python backend/scripts/run_voice_drift.py generate-baseline --character rin
  python backend/scripts/run_voice_drift.py regress --character rin
  python backend/scripts/run_voice_drift.py report --scores artifacts/.../scores.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from heart.core.config import settings
from heart.infra.llm import get_model_router, initialize_router


def _init_router():
    """Initialize the model router from settings."""
    llm_config = settings.get_llm_config()
    initialize_router(llm_config)
    return get_model_router()


async def cmd_generate_baseline(args):
    """Generate baseline JSONL for a character."""
    from heart.qa.baseline_runner import BaselineRunner

    router = _init_router()
    characters = [args.character] if args.character != "all" else ["rin", "dorothy"]

    for char in characters:
        runner = BaselineRunner(
            model_router=router,
            runs_per_prompt=args.runs,
        )
        if args.dry_run:
            cost = runner.estimate_cost(char)
            print(
                f"[dry-run] {char}: {runner._runs_per_prompt} prompts × {args.runs} runs ≈ ${cost:.2f}"
            )
        else:
            out = await runner.generate(char, output_path=args.output)
            print(f"[{char}] Baseline → {out}")


async def cmd_regress(args):
    """Run regression against baseline."""
    from heart.qa.regression_runner import RegressionRunner
    from heart.qa.report_builder import ReportBuilder

    router = _init_router()
    characters = [args.character] if args.character != "all" else ["rin", "dorothy"]

    for char in characters:
        runner = RegressionRunner(model_router=router)
        print(f"[{char}] Running regression...")
        result = await runner.regress(char, output_dir=args.output_dir)
        print(f"[{char}] drift_score={result.drift_score:.4f} verdict={result.verdict}")
        print(f"[{char}] anti_pattern_hits={result.total_anti_pattern_hits}")

        # Build report
        if args.report:
            scores_path = (
                Path(args.output_dir or f"artifacts/voice_drift/{char}_*") / "scores.jsonl"
            )
            # Find latest output dir
            import glob

            dirs = sorted(glob.glob(f"artifacts/voice_drift/{char}_*"), reverse=True)
            if dirs:
                scores_path = Path(dirs[0]) / "scores.jsonl"
                if scores_path.exists():
                    builder = ReportBuilder()
                    out = builder.build(char, str(scores_path))
                    print(f"[{char}] Report → {out}")

        if args.strict and not result.passed:
            sys.exit(1)


async def cmd_report(args):
    """Build HTML report from scores.jsonl."""
    from heart.qa.report_builder import ReportBuilder

    builder = ReportBuilder()
    out = builder.build(
        character=args.character or "unknown",
        scores_path=args.scores,
        output_path=args.output or "/tmp/heart_drift_report.html",
        baseline_path=args.baseline,
    )
    print(f"Report → {out}")


def main():
    parser = argparse.ArgumentParser(description="Heart Voice Drift CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # generate-baseline
    gen = sub.add_parser("generate-baseline", help="Generate baseline JSONL")
    gen.add_argument("--character", choices=["rin", "dorothy", "all"], required=True)
    gen.add_argument("--runs", type=int, default=3, help="Runs per prompt (default: 3)")
    gen.add_argument("--dry-run", action="store_true", help="Estimate cost, skip LLM")
    gen.add_argument("--output", help="Output path")

    # regress
    reg = sub.add_parser("regress", help="Run regression vs baseline")
    reg.add_argument("--character", choices=["rin", "dorothy", "all"], required=True)
    reg.add_argument("--against", help="Baseline dir (default: config/voice_drift/baselines)")
    reg.add_argument("--output-dir", help="Artifact output dir")
    reg.add_argument("--report", action="store_true", default=True, help="Generate HTML report")
    reg.add_argument("--strict", action="store_true", help="Non-zero exit on WARN or FAIL")

    # report
    rep = sub.add_parser("report", help="Generate HTML report from scores.jsonl")
    rep.add_argument("--scores", required=True, help="Path to scores.jsonl")
    rep.add_argument("--character", help="Character ID for report header")
    rep.add_argument("--output", help="Output path (default: /tmp/heart_drift_report.html)")
    rep.add_argument("--baseline", help="Optional baseline JSONL for diff")

    args = parser.parse_args()

    if args.command == "generate-baseline":
        asyncio.run(cmd_generate_baseline(args))
    elif args.command == "regress":
        asyncio.run(cmd_regress(args))
    elif args.command == "report":
        asyncio.run(cmd_report(args))


if __name__ == "__main__":
    main()
