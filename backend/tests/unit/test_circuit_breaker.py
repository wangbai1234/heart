"""
Unit tests: SS07 CircuitBreaker three-state machine.

Covers:
- closed → open transition on threshold
- open → half_open after reset timeout
- half_open → closed on success
- half_open → open on failure
- sliding window reset
- BreakerRegistry per-service isolation
"""

import time

from heart.ss07_orchestration.circuit_breaker import BreakerRegistry, CircuitBreaker


class TestCircuitBreakerStateMachine:
    """Three-state transition: closed → open → half_open → closed."""

    def test_initial_state_closed(self):
        cb = CircuitBreaker(name="test")
        assert not cb.is_open()
        assert cb.state == "closed"

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(name="test", threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert not cb.is_open()

        cb.record_failure()
        assert cb.is_open()
        assert cb.state == "open"

    def test_opens_on_first_failure_with_threshold_1(self):
        cb = CircuitBreaker(name="test", threshold=1)
        assert not cb.is_open()
        cb.record_failure()
        assert cb.is_open()

    def test_success_does_nothing_when_closed(self):
        cb = CircuitBreaker(name="test", threshold=2)
        cb.record_success()
        assert cb.state == "closed"
        assert not cb.is_open()

    def test_half_open_success_resets_to_closed(self):
        cb = CircuitBreaker(name="test", threshold=1, open_sec=1)
        cb.record_failure()
        assert cb.is_open()

        # Manually simulate half_open (normally auto-transition after open_sec)
        cb._state = "half_open"
        cb.record_success()
        assert cb.state == "closed"
        assert not cb.is_open()

    def test_half_open_failure_goes_back_to_open(self):
        cb = CircuitBreaker(name="test", threshold=1, open_sec=1)
        cb.record_failure()
        assert cb.is_open()

        cb._state = "half_open"
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_open()

    def test_auto_transition_to_half_open(self):
        cb = CircuitBreaker(name="test", threshold=1, open_sec=0)
        cb.record_failure()
        # open_sec=0 means auto-transition happens immediately
        # within is_open() itself
        assert not cb.is_open()
        assert cb.state == "half_open"


class TestCircuitBreakerWindow:
    """Sliding window resets failure count when expired."""

    def test_failures_expire_after_window(self):
        cb = CircuitBreaker(name="test", threshold=3, window_sec=0)
        cb.record_failure()
        cb.record_failure()

        # Window has 0 duration, so next failure starts a new window
        cb.record_failure()
        assert not cb.is_open()

    def test_many_failures_over_time_dont_open(self):
        """Failures spread over time should not trigger breaker."""
        cb = CircuitBreaker(name="test", threshold=3, window_sec=0.001)
        cb.record_failure()
        time.sleep(0.002)
        cb.record_failure()
        time.sleep(0.002)
        cb.record_failure()
        # Each failure resets window, so never hits threshold
        assert not cb.is_open()


class TestCircuitBreakerIdempotent:
    """Once open, stays open regardless of more failures."""

    def test_open_stays_open_on_more_failures(self):
        cb = CircuitBreaker(name="test", threshold=1)
        cb.record_failure()
        assert cb.is_open()

        for _ in range(5):
            cb.record_failure()
        assert cb.is_open()

    def test_repeated_success_does_not_reopen(self):
        cb = CircuitBreaker(name="test", threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.is_open()

        cb._state = "half_open"
        cb.record_success()
        assert cb.state == "closed"

        # Successes in closed state are harmless
        for _ in range(10):
            cb.record_success()
        assert cb.state == "closed"


class TestBreakerRegistry:
    """BreakerRegistry provides isolated per-service breakers."""

    def test_get_returns_same_breaker_for_same_name(self):
        registry = BreakerRegistry()
        b1 = registry.get("safety")
        b2 = registry.get("safety")
        assert b1 is b2

    def test_breakers_are_isolated(self):
        registry = BreakerRegistry()
        safety = registry.get("safety")
        composer = registry.get("composer")

        # Open safety, composer should stay closed
        for _ in range(5):
            safety.record_failure()
        assert safety.is_open()
        assert not composer.is_open()

    def test_lazy_create_unknown_service(self):
        registry = BreakerRegistry()
        unknown = registry.get("new_service")
        assert unknown.name == "new_service"
        assert unknown.state == "closed"

    def test_get_all_returns_all_registered(self):
        registry = BreakerRegistry()
        all_breakers = registry.get_all()
        assert "safety" in all_breakers
        assert "composer" in all_breakers
        assert "llm" in all_breakers

    def test_registry_is_singleton(self):
        r1 = BreakerRegistry()
        r2 = BreakerRegistry()
        assert r1 is r2
