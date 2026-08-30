from heart.infra.model_health import model_status, record_model_result, reset_health_for_tests


def setup_function() -> None:
    reset_health_for_tests()


def teardown_function() -> None:
    reset_health_for_tests()


def _record(model_id: str, *, successes: int, failures: int) -> None:
    for _ in range(successes):
        record_model_result(model_id, success=True, duration_ms=1000, ttft_ms=500)
    for _ in range(failures):
        record_model_result(model_id, success=False, duration_ms=6000)


def test_unconfigured_model_is_hard_unavailable_and_not_selectable() -> None:
    status = model_status("gemini-3.1", configured=False)

    assert status["status"] == "unavailable"
    assert status["status_label"] == "暂不可用"
    assert status["selectable"] is False


def test_configured_model_without_samples_is_selectable() -> None:
    status = model_status("gemini-3.1", configured=True)

    assert status["status"] == "available"
    assert status["selectable"] is True


def test_three_consecutive_failures_are_unstable_not_unavailable() -> None:
    _record("gemini-3.1", successes=97, failures=3)

    status = model_status("gemini-3.1", configured=True)

    assert status["success_rate"] == 0.97
    assert status["status"] == "unstable"
    assert status["status_label"] == "近期波动"
    assert status["selectable"] is True


def test_low_rolling_success_rate_is_unstable_but_selectable() -> None:
    _record("gemini-3.1", successes=3, failures=2)

    status = model_status("gemini-3.1", configured=True)

    assert status["success_rate"] == 0.6
    assert status["status"] == "unstable"
    assert status["selectable"] is True


def test_healthy_model_is_smooth_and_selectable() -> None:
    _record("gemini-3.1", successes=100, failures=0)

    status = model_status("gemini-3.1", configured=True)

    assert status["status"] == "smooth"
    assert status["selectable"] is True
