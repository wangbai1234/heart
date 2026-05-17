#!/usr/bin/env python3
"""
Demo: Drift Detector

Shows a 50-turn session where responses gradually drift (replace ellipses
with exclamation marks over time). Demonstrates:
- Pre-filter skip on clean responses
- Drift score rising across cycles
- REINFORCE trigger when threshold crossed
- Score recovery after corrected responses

Usage:
    python3 scripts/demo_drift_detector.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import logging
import structlog
from uuid import uuid4

from heart.ss01_soul.drift_detector import (
    DriftCheckRequest,
    DriftDetector,
    ReleasedResponse,
    SASSnapshotForDrift,
)
from heart.ss01_soul.drift_llm_client import DriftLLMClient, LLMDriftResult

structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.WARNING))


# ============================================================
# Mock LLM for Demo
# ============================================================

class DemoLLMClient(DriftLLMClient):
    """Demo LLM that simulates realistic drift scoring."""

    def __init__(self):
        super().__init__(anthropic_client=object())

    def evaluate_drift(self, soul, responses, timeout_seconds=3.0):
        # Count exclamation marks as drift signal
        exclamation_count = sum(r.text.count("！") for r in responses)
        ellipsis_count = sum(r.text.count("……") for r in responses)

        # Heuristic drift score
        if ellipsis_count >= 3 and exclamation_count == 0:
            # Clean
            return LLMDriftResult(
                drift_score=0.0,
                drift_type="none",
                violations=[],
                required_patterns=[],
            )
        elif exclamation_count <= 2:
            # Mild drift
            return LLMDriftResult(
                drift_score=0.25,
                drift_type="voice_dna_loss",
                violations=[
                    {
                        "sample_excerpt": "部分回复使用感叹号",
                        "detected_pattern": "使用感叹号表达情绪",
                        "expected_pattern": "使用省略号表达停顿",
                    }
                ],
                required_patterns=["使用省略号", "避免感叹号"],
            )
        else:
            # Strong drift
            return LLMDriftResult(
                drift_score=0.6,
                drift_type="voice_dna_loss",
                violations=[
                    {
                        "sample_excerpt": "多条回复使用感叹号",
                        "detected_pattern": "大量使用感叹号",
                        "expected_pattern": "使用省略号表达凛的风格",
                    },
                    {
                        "sample_excerpt": "情绪过度外露",
                        "detected_pattern": "直接表达兴奋",
                        "expected_pattern": "压抑情绪表达",
                    },
                ],
                required_patterns=["恢复省略号使用", "降低情绪直接度"],
            )


# ============================================================
# Demo Session
# ============================================================

def banner(title: str):
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def demo_gradual_drift():
    """Simulate 50-turn session with gradual drift."""
    banner("Drift Detector Demo — 50-turn gradual drift")

    detector = DriftDetector(llm_client=DemoLLMClient())
    user_id = uuid4()

    # Session state
    current_drift_score = 0.0
    history = []

    # Generate 50 responses: clean → drifted → corrected
    def generate_response(turn: int) -> str:
        if turn <= 15:
            # Clean (Rin-style with ellipsis)
            return ["……说吧。", "……三天了。", "……听。", "……好。"][turn % 4]
        elif turn <= 35:
            # Gradual drift (replace ellipsis with exclamation)
            drift_prob = (turn - 15) / 20  # 0 → 1 over 20 turns
            if (turn % 3) < drift_prob * 3:
                return ["真好！", "太棒了！", "我知道了！"][turn % 3]
            else:
                return ["……说吧。", "……好。"][turn % 2]
        else:
            # Corrected (back to clean)
            return ["……说吧。", "……三天了。", "……听。"][turn % 3]

    # Run drift check every 5 turns
    print("\n{:>4}  {:>8}  {:>12}  {:>12}  {}".format(
        "Turn", "Drift", "Decision", "REINFORCE?", "Sample Response"
    ))
    print("-" * 78)

    for turn in range(1, 51):
        # Generate response
        response_text = generate_response(turn)
        history.append(ReleasedResponse(
            turn_index=turn,
            text=response_text,
        ))

        # Check drift every 5 turns
        if turn % 5 == 0:
            req = DriftCheckRequest(
                user_id=user_id,
                character_id="rin",
                soul_spec_version="1.0.0",
                turn_index=turn,
                recent_assistant_responses=history,
                sas_snapshot=SASSnapshotForDrift(
                    current_drift_score=current_drift_score,
                ),
                daily_llm_call_count=turn // 5,  # increment per check
            )

            result = detector.evaluate(req)
            current_drift_score = result.drift_score

            reinforce = "YES" if result.evidence else "NO"
            decision_short = result.decision.value[:12]

            print("{:>4}  {:>8.3f}  {:>12}  {:>12}  {}".format(
                turn,
                result.drift_score,
                decision_short,
                reinforce,
                response_text[:30],
            ))

            if result.evidence:
                print("      └─ Evidence:")
                for msg in result.evidence.sample_messages[:2]:
                    print(f"         • {msg}")
                print(f"      └─ Required: {', '.join(result.evidence.required_patterns)}")


def demo_pre_filter_skip():
    """Show pre-filter skip path (70% case)."""
    banner("Pre-filter Skip Demo")

    detector = DriftDetector(llm_client=DemoLLMClient())

    # Clean Rin responses
    responses = [
        ReleasedResponse(1, "……说吧，我在听。"),
        ReleasedResponse(2, "……三天了。你去哪了。"),
        ReleasedResponse(3, "……好。我知道了。"),
    ]

    req = DriftCheckRequest(
        user_id=uuid4(),
        character_id="rin",
        soul_spec_version="1.0.0",
        turn_index=5,
        recent_assistant_responses=responses,
        sas_snapshot=SASSnapshotForDrift(current_drift_score=0.0),
    )

    result = detector.evaluate(req)

    print(f"Decision: {result.decision.value}")
    print(f"LLM used: {result.llm_used}")
    print(f"Latency: {result.latency_ms}ms")
    print(f"Pre-filter hits:")
    print(f"  • hard_never: {result.debug.prefilter_hits.hard_never_count}")
    print(f"  • forbidden_pattern: {result.debug.prefilter_hits.forbidden_pattern_count}")
    print(f"  • voice_dna_miss: {result.debug.prefilter_hits.voice_dna_marker_miss}")
    print(f"  • length_oob: {result.debug.prefilter_hits.sentence_length_out_of_bounds}")


def demo_hard_never_hit():
    """Show deterministic hard_never hit → floor score."""
    banner("Hard Never Hit Demo")

    detector = DriftDetector(llm_client=DemoLLMClient())

    responses = [
        ReleasedResponse(1, "我会一直在你身边"),  # "一直" is hard_never
        ReleasedResponse(2, "Normal response"),
        ReleasedResponse(3, "Another normal"),
    ]

    req = DriftCheckRequest(
        user_id=uuid4(),
        character_id="rin",
        soul_spec_version="1.0.0",
        turn_index=5,
        recent_assistant_responses=responses,
        sas_snapshot=SASSnapshotForDrift(current_drift_score=0.0),
    )

    result = detector.evaluate(req)

    print(f"Decision: {result.decision.value}")
    print(f"Drift score: {result.drift_score:.3f}")
    print(f"Hard never hits: {result.debug.prefilter_hits.hard_never_count}")
    print(f"REINFORCE evidence: {'YES' if result.evidence else 'NO'}")


def main():
    demo_pre_filter_skip()
    demo_hard_never_hit()
    demo_gradual_drift()

    banner("Done")


if __name__ == "__main__":
    main()
