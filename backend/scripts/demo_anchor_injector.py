#!/usr/bin/env python3
"""
Demo: AnchorInjector + AnchorModeDecider

Walks through the three anchor modes (FULL / LIGHT / REINFORCE) plus
the cadence decider, against the real Rin and Dorothy specs.

Usage:
    python3 scripts/demo_anchor_injector.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import structlog

from heart.ss01_soul.registry import get_soul_registry
from heart.ss01_soul.anchor_injector import (
    get_anchor_injector,
    AnchorActivationView,
    AnchorMode,
    DriftEvidence,
)
from heart.ss01_soul.anchor_mode_decider import decide_mode

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))


def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def demo_full(injector, soul) -> None:
    banner("FULL Anchor (§6.2.1) — Rin, mid-resonance, 1 facet unlocked")
    state = AnchorActivationView(
        resonance_score=0.42,
        unlocked_facet_ids=("facet-tender-curiosity",),
        last_full_anchor_turn=1,
    )
    prompt = injector.generate_full_anchor(soul, state)
    tokens = injector.estimate_tokens(prompt)
    print(f"tokens (heuristic): {tokens}")
    print()
    print(prompt[:1200] + ("\n...[truncated]" if len(prompt) > 1200 else ""))


def demo_light(injector, soul) -> None:
    banner("LIGHT Anchor (§6.2.2) — single-line")
    state = AnchorActivationView(resonance_score=0.42, unlocked_facet_ids=())
    prompt = injector.generate_light_anchor(soul, state)
    tokens = injector.estimate_tokens(prompt)
    print(f"tokens (heuristic): {tokens}")
    print()
    print(prompt)


def demo_reinforce(injector, soul) -> None:
    banner("REINFORCE Anchor (§6.2.3) — Drift recovery")
    evidence = DriftEvidence(
        sample_messages=(
            "宝贝今天怎么样呀？我好想你哦~",
            "你真可爱呀，凛凛~",
        ),
        detected_patterns=("使用'宝贝/呀'称呼", "无省略号", "情感过度外露"),
        required_patterns=(
            "使用 …… 表示停顿/欲言又止",
            "凛式反问（用反问代替关心）",
        ),
    )
    prompt = injector.generate_reinforce_anchor(soul, evidence)
    tokens = injector.estimate_tokens(prompt)
    print(f"tokens (heuristic): {tokens}")
    print()
    print(prompt)


def demo_mode_cadence() -> None:
    banner("Mode Decider Cadence (§3.4) — 20-turn dry run")
    state = AnchorActivationView(
        resonance_score=0.5,
        unlocked_facet_ids=(),
        last_full_anchor_turn=0,
    )
    last_full = 0
    print(f"{'turn':>4}  {'drift':>5}  mode")
    for turn in range(1, 21):
        drift = 0.5 if turn == 11 else 0.05
        view = AnchorActivationView(
            resonance_score=0.5,
            unlocked_facet_ids=(),
            last_full_anchor_turn=last_full,
        )
        mode = decide_mode(view, turn_index=turn, drift_score=drift)
        if mode == AnchorMode.FULL:
            last_full = turn
        marker = "  ← drift override" if (drift > 0.3 and mode == AnchorMode.FULL) else ""
        print(f"{turn:>4}  {drift:>5.2f}  {mode.value}{marker}")


def main() -> None:
    registry = get_soul_registry()
    injector = get_anchor_injector()

    rin = registry.get_soul("rin", "1.0.0")
    dorothy = registry.get_soul("dorothy", "1.0.0")

    demo_full(injector, rin)
    demo_light(injector, rin)
    demo_reinforce(injector, rin)

    banner("Dorothy LIGHT — for contrast")
    state = AnchorActivationView(resonance_score=0.5, unlocked_facet_ids=())
    print(injector.generate_light_anchor(dorothy, state))

    demo_mode_cadence()

    banner("Done")


if __name__ == "__main__":
    main()
