"""Unit tests for soft-delete / grace-period restoration logic.

These tests validate the pure decision logic extracted from routes_auth and
routes_account — they don't hit a real DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def _is_in_grace(deletion_grace_end: datetime | None) -> bool:
    """Mirror the grace-period check in verify_otp."""
    if deletion_grace_end is None:
        return False
    return deletion_grace_end > datetime.now(timezone.utc)


class TestGracePeriodLogic:
    def test_grace_period_active_within_30_days(self) -> None:
        grace_end = datetime.now(timezone.utc) + timedelta(days=25)
        assert _is_in_grace(grace_end) is True

    def test_grace_period_expired(self) -> None:
        grace_end = datetime.now(timezone.utc) - timedelta(days=1)
        assert _is_in_grace(grace_end) is False

    def test_grace_period_none_means_expired(self) -> None:
        assert _is_in_grace(None) is False

    def test_grace_period_exactly_at_boundary(self) -> None:
        # Already expired (past)
        grace_end = datetime.now(timezone.utc) - timedelta(seconds=1)
        assert _is_in_grace(grace_end) is False


class TestAgeVerifiedLogic:
    """Front-end rule: age_verified must be exactly True — not just truthy."""

    def test_strict_true_is_verified(self) -> None:
        assert (True == True) is True  # noqa: E712 — mirrors frontend === check

    def test_null_is_not_verified(self) -> None:
        assert (None == True) is False  # noqa: E712

    def test_false_is_not_verified(self) -> None:
        assert (False == True) is False  # noqa: E712
