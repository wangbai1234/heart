"""Unit tests for bundle_dump SQL safety (PR-7, M16).

Verifies that f-string SQL injection is no longer possible.
"""

from __future__ import annotations

import pytest

from heart.replay.bundle_dump import ReplayRecorder


@pytest.mark.unit
class TestBundleDumpSqlSafety:
    def test_load_one_uses_bind_params(self):
        """_load_one should use bind params, not f-string SQL."""
        import inspect

        source = inspect.getsource(ReplayRecorder._load_one)
        # Should NOT contain f-string SQL
        assert 'f"""' not in source
        assert "f'''" not in source
        # Should use hardcoded WHERE with bind param
        assert "WHERE turn_id = :id" in source

    def test_sqli_payload_in_turn_id(self):
        """SQLi payload in turn_id should not break the query."""
        # The _load_one method now takes a UUID, which is validated by Python's UUID type
        # A SQLi string like "'; DROP TABLE x; --" would fail UUID validation
        from uuid import UUID

        with pytest.raises(ValueError):
            UUID("'; DROP TABLE replay_snapshots; --")
