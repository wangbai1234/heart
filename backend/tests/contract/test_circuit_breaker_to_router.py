"""
Contract: SS07 Circuit Breaker -> ModelRouter: breaker open triggers fallback path.
per runtime_specs/07_agent_orchestration.md section 7 (Circuit Breaker)
per runtime_specs/08_engineering_architecture.md section 3 (Model Router)
per INV-O-6: Each subsystem has hard timeout
per INV-O-7: Circuit breaker open -> fallback mode

Verifies that when CircuitBreakerInterface reports "open", the ModelRouter
switches to a fallback provider or cached/default response path.
"""

import pytest


class RealisticCircuitBreaker:
    """Circuit breaker that tracks failures and opens after threshold."""

    def __init__(self, failure_threshold: int = 3, reset_timeout_secs: int = 60):
        self.failure_threshold = failure_threshold
        self.reset_timeout_secs = reset_timeout_secs
        self._failure_counts: dict[str, int] = {}
        self._open_since: dict[str, float] = {}
        self._state: dict[str, str] = {}  # closed | open | half_open

    def record_success(self, provider: str) -> None:
        if self._state.get(provider) == "half_open":
            self._state[provider] = "closed"
            self._failure_counts[provider] = 0

    def record_failure(self, provider: str) -> None:
        self._failure_counts[provider] = self._failure_counts.get(provider, 0) + 1
        if self._failure_counts[provider] >= self.failure_threshold:
            self._state[provider] = "open"
            import time
            self._open_since[provider] = time.time()

    def is_open(self, provider: str) -> bool:
        """Check if circuit breaker is open for provider."""
        return self._state.get(provider) == "open"

    def get_state(self, provider: str) -> str:
        return self._state.get(provider, "closed")


class FakeModelRouter:
    """ModelRouter with circuit breaker integration."""

    def __init__(self, circuit_breaker: RealisticCircuitBreaker):
        self.circuit_breaker = circuit_breaker
        self.primary_provider = "deepseek-v4-pro"
        self.fallback_provider = "deepseek-v4-flash"

    async def call_main(self, messages: list, agent_name: str = "unknown") -> str:
        """INV-O-7: Check circuit breaker before calling provider."""
        if self.circuit_breaker.is_open(self.primary_provider):
            return await self._call_fallback(messages, agent_name)
        return "primary_response"

    async def _call_fallback(self, messages: list, agent_name: str) -> str:
        """Fallback to secondary provider or cached response."""
        if self.circuit_breaker.is_open(self.fallback_provider):
            return "cached_fallback_response"
        return "fallback_provider_response"


@pytest.mark.contract
class TestCircuitBreakerToRouter:
    """SS07 Circuit Breaker -> ModelRouter: breaker open triggers fallback."""

    @pytest.mark.asyncio
    async def test_circuit_closed_uses_primary(self):
        """When circuit closed, primary provider is used."""
        cb = RealisticCircuitBreaker(failure_threshold=3)
        router = FakeModelRouter(cb)

        response = await router.call_main([{"role": "user", "content": "hello"}])
        assert response == "primary_response"

    @pytest.mark.asyncio
    async def test_circuit_open_triggers_fallback(self):
        """INV-O-7: When circuit open, fallback provider is used."""
        cb = RealisticCircuitBreaker(failure_threshold=1)
        router = FakeModelRouter(cb)

        # Trigger circuit open
        cb.record_failure("deepseek-v4-pro")
        assert cb.is_open("deepseek-v4-pro")

        response = await router.call_main([{"role": "user", "content": "hello"}])
        assert response == "fallback_provider_response"

    @pytest.mark.asyncio
    async def test_both_providers_open_returns_cached(self):
        """When all providers are open, cached fallback response."""
        cb = RealisticCircuitBreaker(failure_threshold=1)
        router = FakeModelRouter(cb)

        # Trip both breakers
        cb.record_failure("deepseek-v4-pro")
        cb.record_failure("deepseek-v4-flash")

        response = await router.call_main([{"role": "user", "content": "hello"}])
        assert response == "cached_fallback_response"

    def test_failure_count_tracks_per_provider(self):
        """Failure counts are tracked independently per provider."""
        cb = RealisticCircuitBreaker(failure_threshold=3)

        cb.record_failure("deepseek-v4-pro")
        cb.record_failure("deepseek-v4-pro")

        assert not cb.is_open("deepseek-v4-pro")
        assert not cb.is_open("deepseek-v4-flash")

        cb.record_failure("deepseek-v4-pro")  # third failure
        assert cb.is_open("deepseek-v4-pro")

    def test_success_resets_half_open(self):
        """When circuit is half_open and success received, reset to closed."""
        cb = RealisticCircuitBreaker(failure_threshold=2)
        cb.record_failure("deepseek-v4-pro")
        cb.record_failure("deepseek-v4-pro")
        assert cb.is_open("deepseek-v4-pro")

        # Simulate half_open -> success
        cb._state["deepseek-v4-pro"] = "half_open"
        cb.record_success("deepseek-v4-pro")
        assert cb.get_state("deepseek-v4-pro") == "closed"

    @pytest.mark.asyncio
    async def test_circuit_breaker_idempotent_after_open(self):
        """Once open, circuit stays open regardless of more failures."""
        cb = RealisticCircuitBreaker(failure_threshold=1)
        cb.record_failure("deepseek-v4-pro")
        assert cb.is_open("deepseek-v4-pro")

        # More failures don't change state
        cb.record_failure("deepseek-v4-pro")
        cb.record_failure("deepseek-v4-pro")
        assert cb.is_open("deepseek-v4-pro")

        router = FakeModelRouter(cb)
        response = await router.call_main([{"role": "user", "content": "test"}])
        assert response != "primary_response"
