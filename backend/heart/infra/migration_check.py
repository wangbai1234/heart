"""Migration drift check — compare DB alembic_version against on-disk migration heads.

Goal: prevent silent "code deployed, migration not applied" incidents. On startup
we scan `backend/migrations/versions/*.py` for revision heads and compare with
the row(s) in `alembic_version`. Any drift is logged at ERROR level.

The check is best-effort — a failure to introspect never blocks startup, since
missing tables can also indicate a fresh (never-migrated) DB.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_REV_RE = re.compile(r'^\s*revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DOWN_RE = re.compile(r'^\s*down_revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _discover_migration_heads(versions_dir: Path) -> set[str]:
    """Return the set of head revisions (those with no children) on disk."""
    revisions: dict[str, str | None] = {}
    for py in versions_dir.glob("*.py"):
        try:
            src = py.read_text(encoding="utf-8")
        except OSError:
            continue
        rev_m = _REV_RE.search(src)
        if not rev_m:
            continue
        rev = rev_m.group(1)
        down_m = _DOWN_RE.search(src)
        revisions[rev] = down_m.group(1) if down_m else None
    children: set[str] = set()
    for _rev, down in revisions.items():
        if down:
            children.add(down)
    return set(revisions.keys()) - children


async def check_migration_drift(engine: Any) -> None:
    """Compare DB alembic_version rows against on-disk migration heads."""
    versions_dir = Path(__file__).resolve().parents[2] / "migrations" / "versions"
    if not versions_dir.is_dir():
        logger.debug("migration_check_skipped", reason="no_versions_dir")
        return

    disk_heads = _discover_migration_heads(versions_dir)
    if not disk_heads:
        logger.debug("migration_check_skipped", reason="no_migrations_found")
        return

    try:
        from sqlalchemy import text as sql_text

        async with engine.connect() as conn:
            result = await conn.execute(sql_text("SELECT version_num FROM alembic_version"))
            db_rows = {row[0] for row in result.fetchall()}
    except Exception as exc:
        logger.warning("migration_check_query_failed", error=str(exc))
        return

    if db_rows == disk_heads:
        logger.info("migration_check_ok", heads=sorted(disk_heads))
        return

    missing_in_db = disk_heads - db_rows
    extra_in_db = db_rows - disk_heads
    logger.error(
        "migration_drift_detected",
        disk_heads=sorted(disk_heads),
        db_heads=sorted(db_rows),
        missing_in_db=sorted(missing_in_db),
        extra_in_db=sorted(extra_in_db),
        hint="Run `alembic upgrade <head>` for each head under versions/",
    )
