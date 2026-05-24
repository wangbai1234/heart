"""Pytest conftest for property-based invariant tests.

Sets up:
- Hypothesis profile for CI (fast) vs deep fuzz (thorough)
- Registry repopulation between tests to avoid cross-test pollution

Constraint: Full suite must complete in < 30s.
"""

from __future__ import annotations

import importlib
import pytest
from hypothesis import settings, HealthCheck

from heart.infra.invariants import InvariantRegistry
import heart.infra.invariant_predicates as predicates_module


# ── Hypothesis profile ───────────────────────────────────────────

settings.register_profile(
    "ci",
    max_examples=200,
    deadline=2000,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.register_profile(
    "deep",
    max_examples=2000,
    deadline=5000,
    suppress_health_check=[HealthCheck.too_slow],
)

settings.load_profile("ci")


# ── Fixtures ─────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_registry():
    """Reset and repopulate registry between tests."""
    InvariantRegistry.reset()
    # Re-import to re-register predicates
    importlib.reload(predicates_module)
    yield
    InvariantRegistry.reset()
