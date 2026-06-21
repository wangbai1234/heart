"""
SS02 Memory LLM Extractor — Cost Guard

Wraps CostTracker; enforces per-run cost cap.
Raises CostCapExceeded before LLM call when projected cost > cap.

Author: 心屿团队
"""

from __future__ import annotations

import structlog

from heart.core.config import settings

logger = structlog.get_logger()

# Default cost cap from settings
_DEFAULT_COST_CAP_USD = 0.05


class CostCapExceeded(Exception):
    """Raised when projected LLM cost exceeds per-run cost cap."""

    def __init__(self, projected_cost: float, cap: float, run_id: str):
        self.projected_cost = projected_cost
        self.cap = cap
        self.run_id = run_id
        super().__init__(
            f"Projected cost ${projected_cost:.6f} exceeds cap ${cap:.6f} "
            f"for extractor_run_id={run_id}"
        )


class CostGuard:
    """Enforces per-run cost cap for the Memory Extractor.

    Usage:
        guard = CostGuard()
        guard.check_before_call(run_id, estimated_input_tokens, estimated_output_tokens)
        # ... LLM call ...
        guard.record_actual(run_id, actual_cost_usd)
    """

    def __init__(self, cost_cap_usd: float | None = None):
        if cost_cap_usd is not None:
            self._cap = cost_cap_usd
        else:
            self._cap = getattr(settings, "memory_extractor_cost_cap_usd", _DEFAULT_COST_CAP_USD)
        self._run_costs: dict[str, float] = {}

    @property
    def cap(self) -> float:
        return self._cap

    def check_before_call(
        self,
        run_id: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
        input_price_per_mtok: float = 0.30,
        output_price_per_mtok: float = 1.20,
    ) -> None:
        """Check if projected cost exceeds cap before making LLM call.

        Args:
            run_id: Extractor run ID for logging
            estimated_input_tokens: Estimated input token count
            estimated_output_tokens: Estimated output token count
            input_price_per_mtok: Input price per million tokens (conservative default)
            output_price_per_mtok: Output price per million tokens (conservative default)

        Raises:
            CostCapExceeded: If projected cost > cap
        """
        projected_input_cost = (estimated_input_tokens / 1_000_000) * input_price_per_mtok
        projected_output_cost = (estimated_output_tokens / 1_000_000) * output_price_per_mtok
        projected_total = projected_input_cost + projected_output_cost

        # Add any prior cost from this run (e.g. retry)
        prior_cost = self._run_costs.get(run_id, 0.0)
        total_projected = prior_cost + projected_total

        if total_projected > self._cap:
            logger.warning(
                "cost_cap_exceeded_before_call",
                run_id=run_id,
                projected_usd=f"{total_projected:.6f}",
                cap_usd=f"{self._cap:.6f}",
                prior_cost_usd=f"{prior_cost:.6f}",
            )
            raise CostCapExceeded(total_projected, self._cap, run_id)

        logger.debug(
            "cost_guard_check_passed",
            run_id=run_id,
            projected_usd=f"{total_projected:.6f}",
            cap_usd=f"{self._cap:.6f}",
        )

    def record_actual(self, run_id: str, actual_cost_usd: float) -> float:
        """Record actual cost for a run and return cumulative cost.

        Args:
            run_id: Extractor run ID
            actual_cost_usd: Actual cost in USD

        Returns:
            Cumulative cost for this run
        """
        prior = self._run_costs.get(run_id, 0.0)
        cumulative = prior + actual_cost_usd
        self._run_costs[run_id] = cumulative

        if cumulative > self._cap:
            logger.warning(
                "cost_cap_exceeded_after_call",
                run_id=run_id,
                cumulative_usd=f"{cumulative:.6f}",
                cap_usd=f"{self._cap:.6f}",
            )
            raise CostCapExceeded(cumulative, self._cap, run_id)

        return cumulative

    def get_run_cost(self, run_id: str) -> float:
        """Get cumulative cost for a run."""
        return self._run_costs.get(run_id, 0.0)

    def reset(self) -> None:
        """Reset all tracked costs."""
        self._run_costs.clear()
