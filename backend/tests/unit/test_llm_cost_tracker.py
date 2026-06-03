"""
Unit tests for LLM Cost Tracker.

Tests cost computation, user tracking, metrics, and alerts.
"""

from datetime import date, datetime
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest

from heart.infra.llm_cost_tracker import (
    AlertInterface,
    LLMCall,
    LLMCostTracker,
    MetricsInterface,
    UserCostStoreInterface,
)


# Test fixtures
@pytest.fixture
def mock_metrics():
    """Mock Prometheus metrics."""
    metrics = AsyncMock(spec=MetricsInterface)
    return metrics


@pytest.fixture
def mock_user_cost_store():
    """Mock Redis user cost store."""
    store = AsyncMock(spec=UserCostStoreInterface)
    store._storage = {}  # Internal storage for testing

    async def increment(user_id: str, cost: float, date_key: date):
        key = f"{user_id}:{date_key.isoformat()}"
        if key not in store._storage:
            store._storage[key] = 0.0
        store._storage[key] += cost

    async def get_daily(user_id: str, date_key: date = None):
        if date_key is None:
            date_key = date.today()
        key = f"{user_id}:{date_key.isoformat()}"
        return store._storage.get(key, 0.0)

    store.increment = increment
    store.get_daily = get_daily

    return store


@pytest.fixture
def mock_alerts():
    """Mock alert service."""
    alerts = AsyncMock(spec=AlertInterface)
    alerts.notifications = []  # Track notifications for testing

    async def notify(alert_type: str, payload: Dict[str, Any]):
        alerts.notifications.append({"type": alert_type, "payload": payload})

    alerts.notify = notify

    return alerts


@pytest.fixture
def tracker(mock_metrics, mock_user_cost_store, mock_alerts):
    """Create LLMCostTracker with mocked dependencies."""
    return LLMCostTracker(
        metrics=mock_metrics,
        user_cost_store=mock_user_cost_store,
        alerts=mock_alerts,
    )


# Tests for cost computation
class TestCostComputation:
    """Test cost computation accuracy."""

    @pytest.mark.asyncio
    async def test_deepseek_v3_cost(self, tracker):
        """Test cost computation for DeepSeek V3."""
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1_000_000,  # 1M tokens
            completion_tokens=500_000,  # 500k tokens
            user_id="test_user",
            agent_name="main_companion",
        )

        cost = tracker._compute_cost(call)

        # DeepSeek V3: $0.14 input, $0.28 output per 1M tokens
        expected_input = 1.0 * 0.14  # 1M * $0.14
        expected_output = 0.5 * 0.28  # 500k * $0.28
        expected_total = expected_input + expected_output

        assert abs(cost - expected_total) < 0.0001
        assert abs(cost - 0.28) < 0.0001  # $0.14 + $0.14 = $0.28

    @pytest.mark.asyncio
    async def test_claude_sonnet_cost(self, tracker):
        """Test cost computation for Claude Sonnet."""
        call = LLMCall(
            model="claude-sonnet-4-6",
            prompt_tokens=100_000,  # 100k tokens
            completion_tokens=50_000,  # 50k tokens
            user_id="test_user",
        )

        cost = tracker._compute_cost(call)

        # Claude Sonnet: $3.00 input, $15.00 output per 1M tokens
        expected_input = 0.1 * 3.00  # 100k * $3.00
        expected_output = 0.05 * 15.00  # 50k * $15.00
        expected_total = expected_input + expected_output

        assert abs(cost - expected_total) < 0.0001
        assert abs(cost - 1.05) < 0.0001  # $0.30 + $0.75 = $1.05

    @pytest.mark.asyncio
    async def test_deepseek_reasoner_cost(self, tracker):
        """Test cost for DeepSeek V4-pro (reasoner)."""
        call = LLMCall(
            model="deepseek-reasoner",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="test_user",
        )

        cost = tracker._compute_cost(call)

        # DeepSeek reasoner: $0.55 input, $2.19 output per 1M tokens
        expected_input = (1000 / 1_000_000) * 0.55
        expected_output = (500 / 1_000_000) * 2.19
        expected_total = expected_input + expected_output

        assert abs(cost - expected_total) < 0.000001

    @pytest.mark.asyncio
    async def test_unknown_model_cost(self, tracker):
        """Test cost computation for unknown model."""
        call = LLMCall(
            model="unknown-model-xyz",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="test_user",
        )

        cost = tracker._compute_cost(call)

        # Unknown models should return 0
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_small_token_cost_precision(self, tracker):
        """Test cost precision for small token counts."""
        call = LLMCall(
            model="deepseek-chat",
            prompt_tokens=10,
            completion_tokens=5,
            user_id="test_user",
        )

        cost = tracker._compute_cost(call)

        # DeepSeek chat: $0.14 input, $0.28 output per 1M tokens
        expected_input = (10 / 1_000_000) * 0.14
        expected_output = (5 / 1_000_000) * 0.28
        expected_total = expected_input + expected_output

        assert abs(cost - expected_total) < 0.0000001


# Tests for recording and tracking
class TestRecordAndTracking:
    """Test cost recording and user tracking."""

    @pytest.mark.asyncio
    async def test_record_updates_user_cost(self, tracker, mock_user_cost_store):
        """Test that recording updates per-user daily cost."""
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="user_123",
        )

        await tracker.record(call)

        # Check user cost was incremented
        today = date.today()
        user_cost = await mock_user_cost_store.get_daily("user_123", today)

        assert user_cost > 0
        expected_cost = tracker._compute_cost(call)
        assert abs(user_cost - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_record_emits_metrics(self, tracker, mock_metrics):
        """Test that recording emits Prometheus metrics."""
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="user_123",
            agent_name="main_companion",
            provider="deepseek",
        )

        await tracker.record(call)

        # Verify metrics were emitted
        assert mock_metrics.observe.call_count == 2  # cost + tokens

        # Check cost metric
        cost_call = mock_metrics.observe.call_args_list[0]
        assert cost_call[0][0] == "llm.cost"
        assert cost_call[1]["labels"]["model"] == "deepseek-v3"
        assert cost_call[1]["labels"]["agent"] == "main_companion"
        assert cost_call[1]["labels"]["provider"] == "deepseek"

        # Check token metric
        token_call = mock_metrics.observe.call_args_list[1]
        assert token_call[0][0] == "llm.tokens"
        assert token_call[0][1] == 1500.0  # 1000 + 500

    @pytest.mark.asyncio
    async def test_record_returns_cost(self, tracker):
        """Test that record() returns the computed cost."""
        call = LLMCall(
            model="deepseek-chat",
            prompt_tokens=100,
            completion_tokens=50,
            user_id="user_123",
        )

        cost = await tracker.record(call)

        expected_cost = tracker._compute_cost(call)
        assert abs(cost - expected_cost) < 0.0001

    @pytest.mark.asyncio
    async def test_multiple_calls_accumulate(self, tracker, mock_user_cost_store):
        """Test that multiple calls accumulate daily cost."""
        user_id = "user_456"

        # Make 3 calls
        for _i in range(3):
            call = LLMCall(
                model="deepseek-v3",
                prompt_tokens=1000,
                completion_tokens=500,
                user_id=user_id,
            )
            await tracker.record(call)

        # Check total cost
        today = date.today()
        total_cost = await mock_user_cost_store.get_daily(user_id, today)

        expected_cost = tracker._compute_cost(call) * 3
        assert abs(total_cost - expected_cost) < 0.0001


# Tests for alerts
class TestAlerts:
    """Test cost threshold alerts."""

    @pytest.mark.asyncio
    async def test_alert_triggered_when_limit_exceeded(self, tracker, mock_alerts):
        """Test that alert is triggered when user exceeds daily limit."""
        user_id = "expensive_user"

        # Make expensive call that exceeds $1 limit
        call = LLMCall(
            model="claude-sonnet-4-6",
            prompt_tokens=100_000,  # This will cost > $1
            completion_tokens=50_000,
            user_id=user_id,
        )

        await tracker.record(call)

        # Verify alert was sent
        assert len(mock_alerts.notifications) == 1
        alert = mock_alerts.notifications[0]

        assert alert["type"] == "user.cost.exceeded"
        assert alert["payload"]["user_id"] == user_id
        assert alert["payload"]["daily_cost"] > tracker.USER_DAILY_LIMIT

    @pytest.mark.asyncio
    async def test_no_alert_when_under_limit(self, tracker, mock_alerts):
        """Test that no alert is triggered when under limit."""
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="cheap_user",
        )

        await tracker.record(call)

        # Verify no alert was sent
        assert len(mock_alerts.notifications) == 0


# Tests for utility methods
class TestUtilityMethods:
    """Test utility methods."""

    def test_user_id_bucketing(self, tracker):
        """Test user ID bucketing for privacy."""
        user_id_1 = "user_123"
        user_id_2 = "user_456"

        bucket_1 = tracker._bucket_user_id(user_id_1)
        bucket_2 = tracker._bucket_user_id(user_id_2)

        # Buckets should be in format "bucket_N"
        assert bucket_1.startswith("bucket_")
        assert bucket_2.startswith("bucket_")

        # Same user should always get same bucket
        assert tracker._bucket_user_id(user_id_1) == bucket_1

        # Different users might get different buckets
        # (not guaranteed due to hash collisions, but likely)

    @pytest.mark.asyncio
    async def test_get_user_daily_cost(self, tracker, mock_user_cost_store):
        """Test getting user's daily cost."""
        user_id = "user_789"

        # Record some calls
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id=user_id,
        )

        cost1 = await tracker.record(call)
        cost2 = await tracker.record(call)

        # Get daily cost
        today = date.today()
        daily_cost = await tracker.get_user_daily_cost(user_id, today)

        expected_total = cost1 + cost2
        assert abs(daily_cost - expected_total) < 0.0001

    @pytest.mark.asyncio
    async def test_get_user_daily_cost_defaults_to_today(self, tracker, mock_user_cost_store):
        """Test that get_user_daily_cost defaults to today."""
        user_id = "user_current"

        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id=user_id,
        )

        await tracker.record(call)

        # Get without specifying date
        daily_cost = await tracker.get_user_daily_cost(user_id)

        assert daily_cost > 0

    def test_estimate_call_cost(self, tracker):
        """Test cost estimation for future calls."""
        cost = tracker.estimate_call_cost(
            model="deepseek-v3",
            prompt_tokens=1000,
            estimated_completion_tokens=500,
        )

        # Should match _compute_cost for same parameters
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=1000,
            completion_tokens=500,
            user_id="dummy",
        )

        expected_cost = tracker._compute_cost(call)
        assert abs(cost - expected_cost) < 0.0001

    def test_estimate_call_cost_unknown_model(self, tracker):
        """Test cost estimation for unknown model."""
        cost = tracker.estimate_call_cost(
            model="unknown-model",
            prompt_tokens=1000,
            estimated_completion_tokens=500,
        )

        assert cost == 0.0

    @pytest.mark.asyncio
    @pytest.mark.xfail(reason="Metrics structure not yet implemented")
    async def test_get_aggregated_metrics(self, tracker):
        """Test get_aggregated_metrics returns structure."""
        metrics = await tracker.get_aggregated_metrics()

        # Should return a dict with expected keys
        assert isinstance(metrics, dict)
        assert "status" in metrics
        assert "total_calls" in metrics
        assert "total_cost_usd" in metrics
        assert "by_model" in metrics


# Tests for LLMCall dataclass
class TestLLMCall:
    """Test LLMCall dataclass."""

    def test_llm_call_creation(self):
        """Test creating an LLMCall instance."""
        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=100,
            completion_tokens=50,
            user_id="user_123",
            agent_name="companion",
            provider="deepseek",
        )

        assert call.model == "deepseek-v3"
        assert call.prompt_tokens == 100
        assert call.completion_tokens == 50
        assert call.total_tokens == 150
        assert call.user_id == "user_123"

    def test_llm_call_defaults(self):
        """Test LLMCall defaults."""
        call = LLMCall(
            model="test-model",
            prompt_tokens=10,
            completion_tokens=5,
            user_id="user",
        )

        assert call.agent_name == ""
        assert call.provider == ""
        assert isinstance(call.created_at, datetime)
        assert call.metadata == {}


# Integration-style tests
class TestIntegration:
    """Integration tests for common usage patterns."""

    @pytest.mark.asyncio
    async def test_typical_usage_flow(self, tracker, mock_user_cost_store):
        """Test typical usage pattern."""
        user_id = "alice"

        # User has a conversation with 3 exchanges
        for i in range(3):
            call = LLMCall(
                model="deepseek-reasoner",
                prompt_tokens=500 + i * 100,
                completion_tokens=250 + i * 50,
                user_id=user_id,
                agent_name="main_companion",
            )

            cost = await tracker.record(call)
            assert cost > 0

        # Check total daily cost
        today = date.today()
        total_cost = await tracker.get_user_daily_cost(user_id, today)

        assert total_cost > 0
        # Should be under $1 limit for these small calls
        assert total_cost < tracker.USER_DAILY_LIMIT

    @pytest.mark.asyncio
    async def test_cost_aware_model_selection(self, tracker):
        """Test using cost estimation for model selection."""
        prompt_tokens = 1000
        completion_tokens = 500

        # Estimate costs for different models
        deepseek_cost = tracker.estimate_call_cost("deepseek-v3", prompt_tokens, completion_tokens)

        claude_cost = tracker.estimate_call_cost(
            "claude-sonnet-4-6", prompt_tokens, completion_tokens
        )

        gpt4_cost = tracker.estimate_call_cost("gpt-4o", prompt_tokens, completion_tokens)

        # DeepSeek should be cheapest
        assert deepseek_cost < claude_cost
        assert deepseek_cost < gpt4_cost


# Tests for no-op implementations
class TestNoOpImplementations:
    """Test no-op fallback implementations."""

    @pytest.mark.asyncio
    async def test_tracker_works_without_dependencies(self):
        """Test that tracker works with no-op dependencies."""
        # Create tracker without injecting dependencies
        tracker = LLMCostTracker()

        call = LLMCall(
            model="deepseek-v3",
            prompt_tokens=100,
            completion_tokens=50,
            user_id="user_123",
        )

        # Should work without errors
        cost = await tracker.record(call)
        assert cost > 0

        # Can retrieve user cost
        daily_cost = await tracker.get_user_daily_cost("user_123")
        assert daily_cost > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
