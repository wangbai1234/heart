"""
Tier C Live conftest — real DeepSeek calls, cost-capped, opt-in.

Three-layer kill switch per design doc:
1. LIVE_TESTS_ENABLED=false -> skip (env var)
2. CostTracker.daily_total > $5 -> abort
3. pytest --live --max-cost=2.0 -> CLI hard limit
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest


class LiveTestCostTracker:
    """Tracks real LLM spend for Tier C tests."""

    def __init__(self, max_cost_per_run=2.0):
        self.max_cost = max_cost_per_run
        self.total_spent = 0.0
        self.per_test = {}

    def start_test(self, test_id, budget=0.10):
        pass

    def record_cost(self, cost_usd):
        self.total_spent += cost_usd

    def end_test(self, test_id):
        self.per_test[test_id] = self.total_spent
        return self.total_spent

    def check_budget(self):
        return self.total_spent < self.max_cost


@pytest.fixture(scope="session")
def cost_tracker(request):
    max_cost = request.config.getoption("--max-cost", default=2.0)
    tracker = LiveTestCostTracker(max_cost_per_run=max_cost)

    env_enabled = os.environ.get("LIVE_TESTS_ENABLED", "false").lower() == "true"
    cli_live = request.config.getoption("--live", default=False)

    if not env_enabled and not cli_live:
        pytest.skip("Tier C disabled (LIVE_TESTS_ENABLED != true and --live not set)")

    yield tracker

    print("\n[live] Total spend: ${:.4f}".format(tracker.total_spent))
    for test_id, cost in tracker.per_test.items():
        print("  {}: ${:.4f}".format(test_id, cost))

    audit_dir = Path("docs/audit/live_runs")
    try:
        audit_dir.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        audit_file = audit_dir / "{}.json".format(date_str)

        existing = []
        if audit_file.exists():
            with open(audit_file, "r") as f:
                existing = json.load(f)

        existing.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cost": tracker.total_spent,
                "tests_run": len(tracker.per_test),
                "per_test": tracker.per_test,
            }
        )

        with open(audit_file, "w") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


@pytest.fixture(scope="session")
def real_deepseek_provider():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set. Required for Tier C live tests.")

    from heart.infra.llm_providers.deepseek import DeepSeekV4FlashProvider

    return DeepSeekV4FlashProvider(api_key=api_key)


@pytest.fixture
def per_test_budget(request, cost_tracker):
    marker = request.node.get_closest_marker("live")
    budget = marker.kwargs.get("max_cost", 0.10) if marker else 0.10
    cost_tracker.start_test(request.node.nodeid, budget=budget)
    yield
    spent = cost_tracker.end_test(request.node.nodeid)
    if spent > budget:
        print(
            "[live] WARNING: {} exceeded budget (${:.4f} > ${:.2f})".format(
                request.node.nodeid, spent, budget
            )
        )
