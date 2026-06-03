"""Voice Drift Regression Tests — Tier C (live).

Per docs/design/soul_drift_regression.md §3.
Requires: --live flag, DEEPSEEK_API_KEY, baseline JSONL.

Run:
  pytest backend/tests/live/test_voice_drift.py --live -v
"""

import json
from pathlib import Path

import pytest
import yaml

pytestmark = [pytest.mark.live, pytest.mark.drift]


def _load_thresholds() -> dict:
    """Load drift thresholds from config."""
    cfg_path = Path(__file__).parent.parent.parent / "config" / "voice_drift" / "thresholds.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_baseline(character: str) -> list[dict]:
    """Load baseline JSONL for a character."""
    baseline_path = (
        Path(__file__).parent.parent.parent
        / "config"
        / "voice_drift"
        / "baselines"
        / f"{character}_baseline.jsonl"
    )
    if not baseline_path.exists():
        pytest.skip(f"Baseline not found: {baseline_path}")

    entries = []
    with open(baseline_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                entries.append(json.loads(line))
    return entries


@pytest.mark.asyncio
async def test_voice_drift_rin_baseline_exists():
    """Verify Rin baseline JSONL exists and has expected structure."""
    entries = _load_baseline("rin")
    assert len(entries) > 0, "Rin baseline is empty"
    # Should have 90 entries (30 prompts × 3 runs)
    assert len(entries) >= 30, f"Expected ≥ 30 entries, got {len(entries)}"

    # Verify schema
    for entry in entries[:3]:
        assert "prompt_id" in entry
        assert "response" in entry
        assert entry["character"] == "rin"


@pytest.mark.asyncio
async def test_voice_drift_dorothy_baseline_exists():
    """Verify Dorothy baseline JSONL exists and has expected structure."""
    entries = _load_baseline("dorothy")
    assert len(entries) > 0, "Dorothy baseline is empty"
    assert len(entries) >= 30, f"Expected ≥ 30 entries, got {len(entries)}"

    for entry in entries[:3]:
        assert entry["character"] == "dorothy"


@pytest.mark.asyncio
async def test_voice_drift_canonical_prompts_loadable():
    """Verify canonical_prompts.yaml loads and has 30 prompts."""
    cfg_path = (
        Path(__file__).parent.parent.parent / "config" / "voice_drift" / "canonical_prompts.yaml"
    )
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    prompts = cfg.get("prompts", [])
    assert len(prompts) == 30, f"Expected 30 prompts, got {len(prompts)}"

    categories = {p["category"] for p in prompts}
    assert "golden_replay" in categories
    assert "smalltalk" in categories
    assert "intimate" in categories
    assert "conflict" in categories
    assert "meta" in categories


@pytest.mark.asyncio
async def test_voice_drift_thresholds_loadable():
    """Verify thresholds.yaml loads with expected values."""
    cfg = _load_thresholds()
    assert "drift_threshold" in cfg
    assert "anti_pattern_tolerance" in cfg
    assert cfg["anti_pattern_tolerance"] == 0
    assert "dimension_weights" in cfg

    weights = cfg["dimension_weights"]
    total = sum(weights.values())
    assert abs(total - 1.0) < 0.01, f"Dimension weights sum to {total}, expected 1.0"


@pytest.mark.asyncio
async def test_voice_drift_regression_rin():
    """Run full regression for Rin vs baseline.

    This is the main Tier C drift gate.
    Fails if drift_score > threshold or any anti_pattern hit.
    """
    from heart.core.config import settings
    from heart.infra.llm import get_model_router, initialize_router
    from heart.qa.regression_runner import RegressionRunner

    entries = _load_baseline("rin")
    if not entries:
        pytest.skip("No Rin baseline found")

    cfg = _load_thresholds()
    threshold = cfg["drift_threshold"]
    anti_tolerance = cfg["anti_pattern_tolerance"]

    # Initialize router
    llm_config = settings.get_llm_config()
    initialize_router(llm_config)
    router = get_model_router()

    runner = RegressionRunner(model_router=router)
    result = await runner.regress("rin")

    print(f"\n[Rin] drift_score={result.drift_score:.4f} threshold={threshold}")
    print(f"[Rin] anti_pattern_hits={result.total_anti_pattern_hits}")
    print(f"[Rin] verdict={result.verdict}")

    # Assertions
    assert result.total_anti_pattern_hits <= anti_tolerance, (
        f"Rin has {result.total_anti_pattern_hits} anti_pattern hits (tolerance: {anti_tolerance})"
    )
    assert result.drift_score <= threshold, (
        f"Rin drift_score {result.drift_score:.4f} exceeds threshold {threshold}"
    )


@pytest.mark.asyncio
async def test_voice_drift_regression_dorothy():
    """Run full regression for Dorothy vs baseline."""
    from heart.core.config import settings
    from heart.infra.llm import get_model_router, initialize_router
    from heart.qa.regression_runner import RegressionRunner

    entries = _load_baseline("dorothy")
    if not entries:
        pytest.skip("No Dorothy baseline found")

    cfg = _load_thresholds()
    threshold = cfg["drift_threshold"]
    anti_tolerance = cfg["anti_pattern_tolerance"]

    llm_config = settings.get_llm_config()
    initialize_router(llm_config)
    router = get_model_router()

    runner = RegressionRunner(model_router=router)
    result = await runner.regress("dorothy")

    print(f"\n[Dorothy] drift_score={result.drift_score:.4f} threshold={threshold}")
    print(f"[Dorothy] anti_pattern_hits={result.total_anti_pattern_hits}")
    print(f"[Dorothy] verdict={result.verdict}")

    assert result.total_anti_pattern_hits <= anti_tolerance
    assert result.drift_score <= threshold
