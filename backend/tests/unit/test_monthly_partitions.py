from datetime import datetime, timezone

from heart.infra.partitions import month_bounds


def test_month_bounds_handles_timezone_aware_datetime():
    start, end = month_bounds(datetime(2026, 7, 5, 9, 55, tzinfo=timezone.utc))

    assert start == datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)


def test_month_bounds_handles_naive_datetime_as_utc():
    start, end = month_bounds(datetime(2026, 12, 31, 23, 59))

    assert start == datetime(2026, 12, 1, 0, 0, tzinfo=timezone.utc)
    assert end == datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)
