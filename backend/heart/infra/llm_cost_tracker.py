"""
LLM Cost Tracker - Records and tracks LLM API costs.

Per SS08 §6.2 - Tracks per-user daily costs, emits metrics, and provides alerts.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Protocol
from datetime import date, datetime


@dataclass
class LLMCall:
    """
    Record of an LLM API call with cost information.

    This can be constructed from LLMResponse or created manually.
    """

    model: str
    prompt_tokens: int
    completion_tokens: int
    user_id: str
    agent_name: str = ""
    provider: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.prompt_tokens + self.completion_tokens


class MetricsInterface(Protocol):
    """Interface for Prometheus-style metrics."""

    async def observe(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
    ) -> None:
        """Record a metric observation."""
        ...


class UserCostStoreInterface(Protocol):
    """Interface for per-user cost storage (Redis)."""

    async def increment(
        self,
        user_id: str,
        cost: float,
        date_key: date,
    ) -> None:
        """Increment user's daily cost."""
        ...

    async def get_daily(
        self,
        user_id: str,
        date_key: Optional[date] = None,
    ) -> float:
        """Get user's cost for a specific day."""
        ...


class AlertInterface(Protocol):
    """Interface for cost alerts."""

    async def notify(
        self,
        alert_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Send an alert notification."""
        ...


class LLMCostTracker:
    """
    Tracks LLM API costs per user, model, and agent.

    Features:
    - Per-call cost computation based on token usage
    - Per-user daily cost aggregation (Redis)
    - Prometheus metric export
    - Cost threshold alerts

    Usage:
        tracker = LLMCostTracker(
            metrics=prometheus_client,
            user_cost_store=redis_store,
            alerts=alert_service,
        )

        # After each LLM call:
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=100,
            completion_tokens=50,
            user_id="user_123",
            agent_name="main_companion",
        )

        await tracker.record(call)
    """

    # Pricing per 1M tokens (USD)
    # Source: SS08 §6.2
    PRICING = {
        "claude-sonnet-4-6": {
            "input_per_1m": 3.00,
            "output_per_1m": 15.00,
        },
        "claude-haiku-4-5": {
            "input_per_1m": 0.80,
            "output_per_1m": 4.00,
        },
        "deepseek-v3": {
            "input_per_1m": 0.14,
            "output_per_1m": 0.28,
        },
        "deepseek-reasoner": {  # V4-pro (from existing implementation)
            "input_per_1m": 0.55,
            "output_per_1m": 2.19,
        },
        "deepseek-chat": {  # V4-flash (from existing implementation)
            "input_per_1m": 0.14,
            "output_per_1m": 0.28,
        },
        "gpt-4o": {
            "input_per_1m": 2.50,
            "output_per_1m": 10.00,
        },
        # V2: Self-hosted companion model (amortized cost)
        "companion-llm-v2": {
            "input_per_1m": 0.50,
            "output_per_1m": 1.00,
        },
    }

    # Daily cost limit per user (USD)
    # After this threshold, alerts are triggered
    USER_DAILY_LIMIT = 1.00  # $1/day max per user

    def __init__(
        self,
        metrics: Optional[MetricsInterface] = None,
        user_cost_store: Optional[UserCostStoreInterface] = None,
        alerts: Optional[AlertInterface] = None,
    ):
        """
        Initialize LLM Cost Tracker.

        Args:
            metrics: Prometheus-style metrics interface
            user_cost_store: Redis-backed user cost store
            alerts: Alert notification interface
        """
        self.metrics = metrics or NoOpMetrics()
        self.user_cost_store = user_cost_store or NoOpUserCostStore()
        self.alerts = alerts or NoOpAlerts()

        # In-memory accumulators for aggregated metrics
        self._total_calls: int = 0
        self._total_cost: float = 0.0
        self._calls_by_model: Dict[str, int] = {}
        self._cost_by_model: Dict[str, float] = {}

    def _compute_cost(self, call: LLMCall) -> float:
        """
        Compute cost for an LLM call.

        Args:
            call: LLM call record

        Returns:
            Cost in USD
        """
        pricing = self.PRICING.get(call.model)

        if not pricing:
            # Unknown model - return 0 and log warning
            # In production, this should log to monitoring
            return 0.0

        # Calculate cost based on tokens
        # Pricing is per 1M tokens, so divide by 1,000,000
        input_cost = (call.prompt_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (call.completion_tokens / 1_000_000) * pricing["output_per_1m"]

        total_cost = input_cost + output_cost

        return float(total_cost)

    def _bucket_user_id(self, user_id: str) -> str:
        """
        Bucket user IDs for privacy in metrics.

        Groups users into buckets to avoid exposing individual user IDs
        in monitoring dashboards.

        Args:
            user_id: User ID

        Returns:
            Bucketed user ID (e.g., "bucket_0", "bucket_1", ...)
        """
        # Simple hash-based bucketing (100 buckets)
        bucket = hash(user_id) % 100
        return f"bucket_{bucket}"

    async def record(self, call: LLMCall) -> float:
        """
        Record an LLM call and its cost.

        This method:
        1. Computes the cost based on token usage
        2. Emits Prometheus metrics
        3. Increments per-user daily cost in Redis
        4. Checks for cost threshold alerts

        Args:
            call: LLM call record

        Returns:
            Cost in USD
        """
        # Compute cost
        cost = self._compute_cost(call)

        # Emit metrics to Prometheus
        await self.metrics.observe(
            "llm.cost",
            cost,
            labels={
                "model": call.model,
                "user_id_bucket": self._bucket_user_id(call.user_id),
                "agent": call.agent_name,
                "provider": call.provider,
            },
        )

        # Also emit token count metrics
        await self.metrics.observe(
            "llm.tokens",
            float(call.total_tokens),
            labels={
                "model": call.model,
                "token_type": "total",
                "agent": call.agent_name,
            },
        )

        # Aggregate per-user daily cost
        today = date.today()
        await self.user_cost_store.increment(
            call.user_id,
            cost,
            date_key=today,
        )

        # Check if user exceeded daily limit
        user_daily_cost = await self.user_cost_store.get_daily(call.user_id, today)

        if user_daily_cost > self.USER_DAILY_LIMIT:
            await self.alerts.notify(
                "user.cost.exceeded",
                {
                    "user_id": call.user_id,
                    "daily_cost": user_daily_cost,
                    "limit": self.USER_DAILY_LIMIT,
                    "date": today.isoformat(),
                },
            )

        # Accumulate in-memory metrics
        self._total_calls += 1
        self._total_cost += cost
        self._calls_by_model[call.model] = self._calls_by_model.get(call.model, 0) + 1
        self._cost_by_model[call.model] = self._cost_by_model.get(call.model, 0.0) + cost

        return cost

    async def get_user_daily_cost(
        self,
        user_id: str,
        date_key: Optional[date] = None,
    ) -> float:
        """
        Get a user's total cost for a specific day.

        Args:
            user_id: User ID
            date_key: Date to query (defaults to today)

        Returns:
            Total cost in USD for that day
        """
        if date_key is None:
            date_key = date.today()

        return await self.user_cost_store.get_daily(user_id, date_key)

    async def get_aggregated_metrics(self) -> Dict[str, Any]:
        """
        Get aggregated cost metrics.

        This is a placeholder for production implementation.
        In production, this would query:
        - Prometheus for time-series metrics
        - ClickHouse for detailed analytics
        - Redis for per-user aggregates

        Returns:
            Aggregated metrics dictionary
        """
        # In production, this would query from Prometheus/ClickHouse
        # For now, return a structure that shows what data is available

        return {
            "status": "active",
            "total_calls": self._total_calls,
            "total_cost_usd": round(self._total_cost, 6),
            "by_model": {
                model: {
                    "calls": self._calls_by_model.get(model, 0),
                    "cost_usd": round(self._cost_by_model.get(model, 0.0), 6),
                }
                for model in self._calls_by_model
            },
            "pricing_used": {
                k: v for k, v in self.PRICING.items()
                if k in self._calls_by_model
            },
            "data_sources": {
                "in_memory": "Current session accumulators",
                "prometheus": "Time-series metrics",
                "redis": "Per-user daily costs",
            },
        }

    def estimate_call_cost(
        self,
        model: str,
        prompt_tokens: int,
        estimated_completion_tokens: int,
    ) -> float:
        """
        Estimate cost for a future LLM call.

        Useful for cost-aware model selection.

        Args:
            model: Model name
            prompt_tokens: Input token count
            estimated_completion_tokens: Estimated output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = self.PRICING.get(model)

        if not pricing:
            return 0.0

        input_cost = (prompt_tokens / 1_000_000) * pricing["input_per_1m"]
        output_cost = (estimated_completion_tokens / 1_000_000) * pricing["output_per_1m"]

        return float(input_cost + output_cost)


# No-op implementations for testing and optional dependencies
class NoOpMetrics:
    """No-op metrics implementation."""

    async def observe(
        self,
        metric_name: str,
        value: float,
        labels: Dict[str, str],
    ) -> None:
        pass


class NoOpUserCostStore:
    """No-op user cost store implementation."""

    def __init__(self):
        self._store: Dict[str, float] = {}

    async def increment(
        self,
        user_id: str,
        cost: float,
        date_key: date,
    ) -> None:
        key = f"{user_id}:{date_key.isoformat()}"
        self._store[key] = self._store.get(key, 0.0) + cost

    async def get_daily(
        self,
        user_id: str,
        date_key: Optional[date] = None,
    ) -> float:
        if date_key is None:
            date_key = date.today()

        key = f"{user_id}:{date_key.isoformat()}"
        return self._store.get(key, 0.0)


class NoOpAlerts:
    """No-op alerts implementation."""

    async def notify(
        self,
        alert_type: str,
        payload: Dict[str, Any],
    ) -> None:
        pass
