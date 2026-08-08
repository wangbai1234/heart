"""Unit tests for migration drift check."""

from __future__ import annotations

from pathlib import Path

from heart.infra.migration_check import _discover_migration_heads


def test_discover_heads_finds_actual_migrations():
    """Should find at least one head from the real backend/migrations/versions dir."""
    versions_dir = Path(__file__).resolve().parents[3] / "migrations" / "versions"
    heads = _discover_migration_heads(versions_dir)
    assert len(heads) >= 1
    # Real repo currently has both 022_identity_narrative_backfill and 025_voice_tables as heads
    for head in heads:
        assert isinstance(head, str)
        assert len(head) > 3


def test_discover_heads_empty_dir(tmp_path):
    """Empty dir returns empty set."""
    heads = _discover_migration_heads(tmp_path)
    assert heads == set()


def test_discover_heads_linear_chain(tmp_path):
    """A → B → C should find only C as head."""
    (tmp_path / "a.py").write_text('revision = "a"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text('revision = "b"\ndown_revision = "a"\n')
    (tmp_path / "c.py").write_text('revision = "c"\ndown_revision = "b"\n')
    heads = _discover_migration_heads(tmp_path)
    assert heads == {"c"}


def test_discover_heads_multi_head(tmp_path):
    """A → B, A → C should find both B and C as heads."""
    (tmp_path / "a.py").write_text('revision = "a"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text('revision = "b"\ndown_revision = "a"\n')
    (tmp_path / "c.py").write_text('revision = "c"\ndown_revision = "a"\n')
    heads = _discover_migration_heads(tmp_path)
    assert heads == {"b", "c"}


def test_discover_heads_merge_migration_tuple(tmp_path):
    """A merge migration (down_revision = tuple) collapses two heads into one.

    Regression: a tuple down_revision must register BOTH parents as children,
    else B and C are mis-reported as heads and startup logs a false
    migration_drift_detected even though the DB is on the single real head D.
    """
    (tmp_path / "a.py").write_text('revision = "a"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text('revision = "b"\ndown_revision = "a"\n')
    (tmp_path / "c.py").write_text('revision = "c"\ndown_revision = "a"\n')
    (tmp_path / "d.py").write_text('revision = "d"\ndown_revision = ("b", "c")\n')
    heads = _discover_migration_heads(tmp_path)
    assert heads == {"d"}


def test_discover_heads_annotated_form(tmp_path):
    """Alembic autogenerate emits type-annotated `revision`/`down_revision`.

    Regression: `revision: str = "b"` / `down_revision: Union[...] = "a"` (the
    autogenerate template form) must parse the same as the bare form. Missing it
    left the annotated child unparsed, so its parent A was never recorded as
    having a child and got mis-detected as a head — a false migration_drift_detected
    (058_chat_messages_channel, via autogen child 88a95a36ffcb_voice_call_quotas).
    """
    (tmp_path / "a.py").write_text('revision = "a"\ndown_revision = None\n')
    (tmp_path / "b.py").write_text(
        "from typing import Sequence, Union\n"
        'revision: str = "b"\n'
        'down_revision: Union[str, Sequence[str], None] = "a"\n'
    )
    heads = _discover_migration_heads(tmp_path)
    assert heads == {"b"}


def test_discover_heads_ignores_non_python_files(tmp_path):
    """Files without .py extension are skipped."""
    (tmp_path / "a.py").write_text('revision = "a"\ndown_revision = None\n')
    (tmp_path / "b.txt").write_text('revision = "b"\ndown_revision = None\n')
    heads = _discover_migration_heads(tmp_path)
    assert heads == {"a"}
