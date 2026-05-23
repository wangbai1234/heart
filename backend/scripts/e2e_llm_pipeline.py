"""End-to-end LLM pipeline test.

Path validated: TurnContext → OrchestratorAgent.handle_turn()
  → OrchestratorSafetyAdapter.classify() (real HeuristicSafetyClassifier, Aho-Corasick)
  → branch on SafetyLevel:
      GREEN  → DirectorAgent.decide → _compose → ModelRouter.stream_main (real DeepSeek)
      RED    → _handle_red (soul-flavored rejection, no LLM)
      PURPLE → _handle_purple → CarePathEngine.render (template, no LLM)
  → Anti-pattern post-filter (skipped, no filter wired)
  → TurnResult with trace

Run from backend/:
  python3 scripts/e2e_llm_pipeline.py

Cost guard: GREEN path uses max_tokens=120 (~$0.0003 per call).
RED/PURPLE paths make zero LLM calls.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

# Allow running as a script
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load .env explicitly (heart.core.config reads from it via pydantic-settings)
from dotenv import load_dotenv

load_dotenv(ROOT.parent / ".env")

from heart.core.config import settings  # noqa: E402
from heart.infra.llm import (  # noqa: E402
    LLMProviderConfig,
    DeepSeekConfig,
    initialize_router,
    shutdown_router,
)
from heart.ss07_orchestration import (  # noqa: E402
    OrchestratorAgent,
    TurnContext,
    SafetyLevel,
    TraceStatus,
)


def _print_header(title: str) -> None:
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def _print_result(label: str, result) -> None:
    print(f"\n[{label}]")
    print(f"  safety.level           = {result.safety.level.value}")
    print(f"  safety.confidence      = {result.safety.confidence:.2f}")
    print(f"  safety.triggered_cats  = {result.safety.triggered_categories}")
    print(f"  safety.action          = {result.safety.recommended_action}")
    print(f"  trace.status           = {result.trace.status.value}")
    print(f"  trace.spans            = {len(result.trace.spans)} span(s)")
    print(f"  trace.llm_tokens       = {result.trace.llm_tokens_used}")
    print(f"  response_text          = {result.response_text!r}")


async def main() -> int:
    _print_header("STEP 0 — Configuration check")
    api_key = settings.deepseek_api_key
    base_url = settings.deepseek_base_url
    main_model = settings.main_llm_model
    cheap_model = settings.cheap_llm_model
    assert api_key, "DEEPSEEK_API_KEY missing from settings"
    assert base_url, "DEEPSEEK_BASE_URL missing from settings"
    print(f"  api_key (head)         = {api_key[:8]}***")
    print(f"  base_url               = {base_url}")
    print(f"  main_llm_model         = {main_model}")
    print(f"  cheap_llm_model        = {cheap_model}")

    _print_header("STEP 1 — Initialize ModelRouter")
    llm_config = LLMProviderConfig(
        deepseek=DeepSeekConfig(
            api_key=api_key,
            base_url=base_url,
        ),
    )
    await initialize_router(llm_config)
    print("  ModelRouter initialized.")

    _print_header("STEP 2 — Construct OrchestratorAgent")
    orchestrator = OrchestratorAgent(
        composer=None,            # use stub prompt path
        model_router=None,        # pull from global router
        cold_path_enabled=False,  # disable cold path for clean test
    )
    print(f"  safety_agent           = {type(orchestrator.safety_agent).__name__}")
    print(f"  director_agent         = {type(orchestrator.director_agent).__name__}")
    print(f"  circuit_breakers       = {list(orchestrator.circuit_breakers.keys())}")
    assert type(orchestrator.safety_agent).__name__ == "OrchestratorSafetyAdapter"
    assert "safety" in orchestrator.circuit_breakers, "safety CB missing (rename not applied?)"

    # =================================================================
    # GREEN — real LLM hit
    # =================================================================
    _print_header("STEP 3 — GREEN path (real DeepSeek call, ~120 tokens)")
    green_ctx = TurnContext(
        user_id=uuid4(),
        character_id="rin",
        user_message="你好，今天天气不错。我刚下班，有点累。",
        modality="text",
        user_locale="zh-CN",
        user_jurisdiction="CN",
    )
    green_result = await orchestrator.handle_turn(green_ctx)
    _print_result("GREEN", green_result)
    assert green_result.safety.level == SafetyLevel.GREEN, (
        f"expected GREEN, got {green_result.safety.level}"
    )
    assert green_result.trace.status == TraceStatus.COMPLETED, (
        f"expected COMPLETED, got {green_result.trace.status}"
    )
    assert green_result.response_text and len(green_result.response_text) > 0, (
        "GREEN path returned empty response"
    )
    assert green_result.trace.llm_tokens_used.get("main_output", 0) > 0, (
        "GREEN path didn't record LLM tokens (LLM may not have been called)"
    )
    print("  ✅ GREEN assertions passed (real LLM response received)")

    # =================================================================
    # RED — soul-flavored rejection, no LLM
    # =================================================================
    _print_header("STEP 4 — RED path (soul rejection, no LLM)")
    red_ctx = TurnContext(
        user_id=uuid4(),
        character_id="rin",
        user_message="我要杀人。",
        modality="text",
        user_locale="zh-CN",
        user_jurisdiction="CN",
    )
    red_result = await orchestrator.handle_turn(red_ctx)
    _print_result("RED", red_result)
    assert red_result.safety.level == SafetyLevel.RED, (
        f"expected RED, got {red_result.safety.level}"
    )
    assert red_result.trace.status == TraceStatus.COMPLETED
    assert red_result.response_text, "RED returned empty response"
    assert not red_result.trace.llm_tokens_used, (
        "RED path should NOT call LLM but tokens recorded"
    )
    print("  ✅ RED assertions passed (no LLM call, soul-flavored rejection)")

    # =================================================================
    # PURPLE — CarePathEngine template, no LLM
    # =================================================================
    _print_header("STEP 5 — PURPLE path (CarePathEngine zh-CN, no LLM)")
    purple_ctx = TurnContext(
        user_id=uuid4(),
        character_id="rin",
        user_message="我想死。",
        modality="text",
        user_locale="zh-CN",
        user_jurisdiction="CN",
    )
    purple_result = await orchestrator.handle_turn(purple_ctx)
    _print_result("PURPLE", purple_result)
    assert purple_result.safety.level == SafetyLevel.PURPLE, (
        f"expected PURPLE, got {purple_result.safety.level}"
    )
    assert purple_result.trace.status == TraceStatus.COMPLETED
    assert purple_result.response_text and len(purple_result.response_text) > 50, (
        "PURPLE Care Path response is suspiciously short"
    )
    assert not purple_result.trace.llm_tokens_used, (
        "PURPLE path should NOT call LLM (template-only)"
    )
    # PURPLE response must have 3 blocks per spec
    text = purple_result.response_text
    # Block separation: care_path uses double-newline joins
    block_count = text.count("\n\n") + 1
    assert block_count >= 3, (
        f"PURPLE response should have 3+ blocks, got {block_count}\n{text}"
    )
    print(f"  ✅ PURPLE assertions passed (template, {block_count} blocks)")

    # =================================================================
    # PURPLE en/US — verify locale routing wired via TurnContext
    # =================================================================
    _print_header("STEP 6 — PURPLE path (locale=en, jurisdiction=US)")
    purple_us_ctx = TurnContext(
        user_id=uuid4(),
        character_id="rin",
        user_message="我想死。",  # confirmed PURPLE keyword (see test_safety_agent)
        modality="text",
        user_locale="en",
        user_jurisdiction="US",
    )
    purple_us_result = await orchestrator.handle_turn(purple_us_ctx)
    _print_result("PURPLE-US", purple_us_result)
    # Sanity: response should be English (contains common English words)
    en_text = purple_us_result.response_text.lower()
    english_markers = any(w in en_text for w in [" you ", " the ", "988", "i ", "are ", "this"])
    assert english_markers, (
        f"PURPLE-US response doesn't look English:\n{purple_us_result.response_text}"
    )
    print("  ✅ PURPLE-US locale routing works")

    # =================================================================
    # Wrap up
    # =================================================================
    _print_header("STEP 7 — Circuit breaker stats")
    for name, stats in orchestrator.get_circuit_breaker_stats().items():
        if stats["total_calls"] > 0:
            print(f"  {name:20s} {stats}")

    _print_header("STEP 8 — Shutdown")
    await shutdown_router()
    print("  ModelRouter closed.")

    _print_header("RESULT")
    print("  ✅ END-TO-END LLM PIPELINE PASS")
    print("  paths exercised: GREEN (real LLM) + RED + PURPLE (zh-CN, en-US)")
    return 0


if __name__ == "__main__":
    try:
        rc = asyncio.run(main())
    except AssertionError as e:
        print(f"\n❌ ASSERTION FAILED: {e}")
        rc = 1
    except Exception as e:
        import traceback
        print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
        rc = 2
    sys.exit(rc)
