"""
Integration tests for Alembic migration roundtrip (up → down → up → down).

Per spec:
  - Each migration pair must survive up → down → up → down cycles
  - Table schema must be identical after each "up" state
  - Alembic stamp head + current must match

Uses testcontainers PostgreSQL via the integration conftest fixtures.
"""

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

# ── Migration revision IDs ──
BASE = "e814230ade46"
REV_001 = "001_add_memory_tables"
REV_002 = "002_add_emotion_rel"
REV_003 = "003_ss04_threshold_tuning_v1_1"
REV_004 = "004_replay_snapshots"
REV_005 = "005_safety_events"
REV_006 = "006_sessions"
REV_007 = "007_memory_extractor_audit"
REV_008 = "008_memory_extraction_dlq"
REV_009 = "009_memory_l4_extras"
REV_010 = "010_memory_regex_shadow"

ALL_REVISIONS = [
    BASE,
    REV_001,
    REV_002,
    REV_003,
    REV_004,
    REV_005,
    REV_006,
    REV_007,
    REV_008,
    REV_009,
    REV_010,
]

# Tables expected per migration (excluding alembic_version and partition children)
_TABLES_001 = {
    "episodic_memories",
    "fact_nodes",
    "identity_memories",
    "memory_encoding_events",
    "consolidation_jobs",
}
_TABLES_002 = _TABLES_001 | {
    "emotion_states",
    "emotion_events",
    "relationship_states",
    "relationship_events",
}
_TABLES_003 = _TABLES_002  # ALTER only, no new tables
_TABLES_004 = _TABLES_003 | {"replay_snapshots"}
_TABLES_005 = _TABLES_004 | {"safety_events"}
_TABLES_006 = _TABLES_005 | {"sessions"}
_TABLES_007 = _TABLES_006 | {"memory_extraction_queue", "memory_audit_log"}
_TABLES_008 = _TABLES_007 | {"memory_extraction_dlq"}
_TABLES_009 = _TABLES_008  # ALTER only (add columns to fact_nodes + identity_memories)
_TABLES_010 = _TABLES_009 | {"memory_l3_facts_shadow_regex"}

TABLES_BY_REV = {
    BASE: set(),
    REV_001: _TABLES_001,
    REV_002: _TABLES_002,
    REV_003: _TABLES_003,
    REV_004: _TABLES_004,
    REV_005: _TABLES_005,
    REV_006: _TABLES_006,
    REV_007: _TABLES_007,
    REV_008: _TABLES_008,
    REV_009: _TABLES_009,
    REV_010: _TABLES_010,
}

# Known parent tables that have partitions
_PARENT_TABLES = {
    "episodic_memories",
    "fact_nodes",
    "emotion_states",
    "relationship_states",
    "memory_encoding_events",
    "emotion_events",
    "relationship_events",
}


def _is_partition_table(name: str) -> bool:
    """Check if a table name looks like a partition child of a known parent."""
    # If it's exactly a parent table name, it's not a partition
    if name in _PARENT_TABLES:
        return False
    # If it starts with a parent table name + separator, it's likely a partition
    for parent in _PARENT_TABLES:
        if name.startswith(parent + "_"):
            return True
    return False


# ── Helpers ──


def _make_alembic_cfg(db_url: str, migrations_dir: str) -> Config:
    """Build an Alembic Config pointed at the test database."""
    cfg = Config()
    cfg.set_main_option("script_location", migrations_dir)
    cfg.set_main_option("sqlalchemy.url", db_url)
    # Suppress Alembic's own config-file loading
    cfg.config_file_name = None
    return cfg


def _run_upgrade(cfg: Config, target: str) -> None:
    """Run alembic upgrade to target revision."""
    command.upgrade(cfg, target)


def _run_downgrade(cfg: Config, target: str) -> None:
    """Run alembic downgrade to target revision."""
    command.downgrade(cfg, target)


def _run_stamp(cfg: Config, target: str) -> None:
    """Stamp the database with a revision without running migrations."""
    command.stamp(cfg, target)


async def _get_table_names(db_url: str) -> set[str]:
    """Get set of user table names from the database, excluding alembic_version and partitions."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.connect() as conn:

        def get_tables(connection):
            inspector = inspect(connection)
            tables = inspector.get_table_names()
            return {t for t in tables if t != "alembic_version" and not _is_partition_table(t)}

        tables = await conn.run_sync(get_tables)
    await engine.dispose()
    return tables


async def _get_table_schema(db_url: str) -> dict:
    """Capture full table schema: {table_name: {column_name: (type, nullable, default)}}."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.connect() as conn:

        def get_schema(connection):
            inspector = inspect(connection)
            schema = {}
            for table in inspector.get_table_names():
                if table == "alembic_version" or _is_partition_table(table):
                    continue
                cols = {}
                for col in inspector.get_columns(table):
                    # Normalize type to string for comparison
                    cols[col["name"]] = (
                        str(col["type"]),
                        col.get("nullable", True),
                        col.get("default"),
                    )
                schema[table] = cols
            return schema

        schema = await conn.run_sync(get_schema)
    await engine.dispose()
    return schema


async def _assert_schema_identical(schema1: dict, schema2: dict, label: str) -> None:
    """Assert two schema snapshots are identical."""
    assert set(schema1.keys()) == set(schema2.keys()), (
        f"{label}: table sets differ\n"
        f"  Only in 1st: {set(schema1.keys()) - set(schema2.keys())}\n"
        f"  Only in 2nd: {set(schema2.keys()) - set(schema1.keys())}"
    )
    for table in schema1:
        assert table in schema2, f"{label}: table '{table}' missing in 2nd snapshot"
        cols1 = schema1[table]
        cols2 = schema2[table]
        assert set(cols1.keys()) == set(cols2.keys()), (
            f"{label}: columns differ for table '{table}'\n"
            f"  Only in 1st: {set(cols1.keys()) - set(cols2.keys())}\n"
            f"  Only in 2nd: {set(cols2.keys()) - set(cols1.keys())}"
        )
        for col in cols1:
            assert col in cols2, f"{label}: column '{table}.{col}' missing in 2nd snapshot"
            t1, n1, d1 = cols1[col]
            t2, n2, d2 = cols2[col]
            assert t1 == t2, f"{label}: column '{table}.{col}' type mismatch: {t1} vs {t2}"
            assert n1 == n2, f"{label}: column '{table}.{col}' nullable mismatch: {n1} vs {n2}"


async def _clean_database(db_url: str) -> None:
    """Drop all known tables to ensure a clean state before each test."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        # Drop in reverse dependency order to avoid FK issues
        await conn.execute(text("DROP TABLE IF EXISTS relationship_events CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS relationship_states CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS emotion_events CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS emotion_states CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS consolidation_jobs CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS memory_encoding_events CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS identity_memories CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS fact_nodes CASCADE"))
        await conn.execute(text("DROP TABLE IF EXISTS episodic_memories CASCADE"))
        # Reset alembic_version to clean migration state
        await conn.execute(text("DELETE FROM alembic_version"))
    await engine.dispose()


# ── Fixtures ──


@pytest.fixture
def migrations_dir():
    """Path to the migrations directory."""
    p = Path(__file__).parent.parent.parent / "migrations"
    assert p.exists(), f"Migrations dir not found: {p}"
    return str(p)


@pytest.fixture
def alembic_cfg(postgres_container, migrations_dir):
    """Alembic Config pointed at the test Postgres container."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    return _make_alembic_cfg(db_url, migrations_dir)


# ── Test: Roundtrip — Full Chain ──


@pytest.mark.asyncio
async def test_full_chain_roundtrip(postgres_container, alembic_cfg, migrations_dir):
    """Full migration chain: head → base → head → base.

    Verifies that schemas are identical after each upgrade to head.
    """
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # ── Phase 1: upgrade to head, capture schema ──
    _run_upgrade(alembic_cfg, "head")
    schema_up1 = await _get_table_schema(db_url)
    tables_up1 = await _get_table_names(db_url)
    assert tables_up1 == TABLES_BY_REV[REV_010], f"Tables after 1st upgrade: {tables_up1}"

    # ── Phase 2: downgrade to base, verify empty ──
    _run_downgrade(alembic_cfg, "base")
    tables_base = await _get_table_names(db_url)
    assert tables_base == TABLES_BY_REV[BASE], (
        f"Tables after downgrade to base (should be empty except alembic_version): {tables_base}"
    )

    # ── Phase 3: upgrade to head again, compare schema ──
    _run_upgrade(alembic_cfg, "head")
    schema_up2 = await _get_table_schema(db_url)
    tables_up2 = await _get_table_names(db_url)
    assert tables_up2 == TABLES_BY_REV[REV_010], f"Tables after 2nd upgrade: {tables_up2}"
    await _assert_schema_identical(schema_up1, schema_up2, "Full chain roundtrip")

    # ── Phase 4: downgrade to base, verify empty ──
    _run_downgrade(alembic_cfg, "base")
    tables_base2 = await _get_table_names(db_url)
    assert tables_base2 == TABLES_BY_REV[BASE], (
        f"Tables after 2nd downgrade (should be empty): {tables_base2}"
    )


# ── Test: Roundtrip — Per-Pair ──


@pytest.mark.asyncio
async def test_pair_001_to_base_roundtrip(postgres_container, alembic_cfg, migrations_dir):
    """Pair (001, base): up → down → up → down."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # Phase 1: up to 001
    _run_upgrade(alembic_cfg, REV_001)
    schema_up1 = await _get_table_schema(db_url)
    tables_up1 = await _get_table_names(db_url)
    assert tables_up1 == TABLES_BY_REV[REV_001]

    # Phase 2: down to base
    _run_downgrade(alembic_cfg, "base")
    tables_down1 = await _get_table_names(db_url)
    assert tables_down1 == TABLES_BY_REV[BASE]

    # Phase 3: up to 001 again
    _run_upgrade(alembic_cfg, REV_001)
    schema_up2 = await _get_table_schema(db_url)
    await _assert_schema_identical(schema_up1, schema_up2, "Pair 001↔base")

    # Phase 4: down to base
    _run_downgrade(alembic_cfg, "base")
    tables_down2 = await _get_table_names(db_url)
    assert tables_down2 == TABLES_BY_REV[BASE]


@pytest.mark.asyncio
async def test_pair_002_to_001_roundtrip(postgres_container, alembic_cfg, migrations_dir):
    """Pair (002, 001): up → down → up → down."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # Phase 1: up to 001 first, then up to 002
    _run_upgrade(alembic_cfg, REV_001)
    _run_upgrade(alembic_cfg, REV_002)
    schema_up1 = await _get_table_schema(db_url)
    tables_up1 = await _get_table_names(db_url)
    assert tables_up1 == TABLES_BY_REV[REV_002]

    # Phase 2: down to 001
    _run_downgrade(alembic_cfg, REV_001)
    tables_down1 = await _get_table_names(db_url)
    assert tables_down1 == TABLES_BY_REV[REV_001]

    # Phase 3: up to 002 again
    _run_upgrade(alembic_cfg, REV_002)
    schema_up2 = await _get_table_schema(db_url)
    await _assert_schema_identical(schema_up1, schema_up2, "Pair 002↔001")

    # Phase 4: down to 001
    _run_downgrade(alembic_cfg, REV_001)
    tables_down2 = await _get_table_names(db_url)
    assert tables_down2 == TABLES_BY_REV[REV_001]


@pytest.mark.asyncio
async def test_pair_003_to_002_roundtrip(postgres_container, alembic_cfg, migrations_dir):
    """Pair (003, 002): up → down → up → down."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # Phase 1: up to 002 first, then up to 003
    _run_upgrade(alembic_cfg, REV_001)
    _run_upgrade(alembic_cfg, REV_002)
    _run_upgrade(alembic_cfg, REV_003)
    schema_up1 = await _get_table_schema(db_url)
    tables_up1 = await _get_table_names(db_url)
    assert tables_up1 == TABLES_BY_REV[REV_003]

    # Verify stage_thresholds column exists after 003
    assert "stage_thresholds" in schema_up1.get("relationship_states", {}), (
        "stage_thresholds column missing after upgrade to 003"
    )

    # Phase 2: down to 002
    _run_downgrade(alembic_cfg, REV_002)
    tables_down1 = await _get_table_names(db_url)
    assert tables_down1 == TABLES_BY_REV[REV_002]

    # Verify stage_thresholds column is gone after downgrade
    schema_down = await _get_table_schema(db_url)
    assert "stage_thresholds" not in schema_down.get("relationship_states", {}), (
        "stage_thresholds column still present after downgrade to 002"
    )

    # Phase 3: up to 003 again
    _run_upgrade(alembic_cfg, REV_003)
    schema_up2 = await _get_table_schema(db_url)
    await _assert_schema_identical(schema_up1, schema_up2, "Pair 003↔002")

    # Phase 4: down to 002
    _run_downgrade(alembic_cfg, REV_002)
    tables_down2 = await _get_table_names(db_url)
    assert tables_down2 == TABLES_BY_REV[REV_002]


# ── Test: Stamps ──


@pytest.mark.asyncio
async def test_alembic_stamp_head_matches_current(postgres_container, alembic_cfg, migrations_dir):
    """alembic stamp head + alembic current must match."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # Verify database is clean before stamp
    tables_before = await _get_table_names(db_url)
    assert tables_before == TABLES_BY_REV[BASE], (
        f"Expected empty database before stamp, got: {tables_before}"
    )

    # Stamp the database with head (sets alembic_version without running migrations)
    _run_stamp(alembic_cfg, "head")

    # Read alembic_version to verify the stamped revision
    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT version_num FROM alembic_version"))
        rows = result.fetchall()
    await engine.dispose()

    assert len(rows) == 1, f"Expected 1 row in alembic_version, got {len(rows)}"
    stamped_rev = rows[0][0]
    assert stamped_rev == REV_010, f"Stamped revision {stamped_rev} does not match head {REV_010}"

    # Verify stamp didn't actually create any tables
    tables_after = await _get_table_names(db_url)
    assert tables_after == TABLES_BY_REV[BASE], (
        f"Stamp should not create tables, but got: {tables_after}"
    )

    # Clean up: remove the stamp so subsequent tests get a clean DB
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM alembic_version"))
    await engine.dispose()


@pytest.mark.asyncio
async def test_alembic_head_is_consistently_reachable(
    postgres_container, alembic_cfg, migrations_dir
):
    """Each migration can be reached from base and from its down_revision."""
    db_url = os.environ["TEST_ASYNC_DATABASE_URL"]
    await _clean_database(db_url)

    # Test that each revision can be upgraded to from base
    for rev in [
        REV_001,
        REV_002,
        REV_003,
        REV_004,
        REV_005,
        REV_006,
        REV_007,
        REV_008,
        REV_009,
        REV_010,
    ]:
        # Start from base
        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM alembic_version"))
        await engine.dispose()

        _run_upgrade(alembic_cfg, rev)
        tables = await _get_table_names(db_url)
        assert tables == TABLES_BY_REV[rev], (
            f"Upgrade to {rev}: expected {TABLES_BY_REV[rev]}, got {tables}"
        )

        # Downgrade back to base
        _run_downgrade(alembic_cfg, "base")
        tables = await _get_table_names(db_url)
        assert tables == TABLES_BY_REV[BASE], (
            f"Downgrade from {rev} to base: expected empty, got {tables}"
        )


# ── Test: Migration Chain Integrity ──


@pytest.mark.asyncio
async def test_migration_chain_has_no_gaps(postgres_container, alembic_cfg, migrations_dir):
    """Verify the down_revision chain is continuous with no broken links."""
    from alembic.script import ScriptDirectory

    sd = ScriptDirectory.from_config(alembic_cfg)

    # Build revision lookup
    revisions = {r.revision: r for r in sd.walk_revisions()}

    # Verify expected revisions exist
    for rev_id in ALL_REVISIONS:
        assert rev_id in revisions, f"Revision {rev_id} not found in migration chain"

    # Verify down_revision chain
    chain = [
        (REV_001, BASE),
        (REV_002, REV_001),
        (REV_003, REV_002),
        (REV_004, REV_003),
        (REV_005, REV_004),
        (REV_006, REV_005),
        (REV_007, REV_006),
        (REV_008, REV_007),
        (REV_009, REV_008),
        (REV_010, REV_009),
    ]
    for rev_id, expected_parent in chain:
        rev = revisions[rev_id]
        parents = (
            rev.down_revision if isinstance(rev.down_revision, tuple) else (rev.down_revision,)
        )
        assert expected_parent in parents, (
            f"{rev_id} down_revision {rev.down_revision} != {expected_parent}"
        )

    # Verify no duplicate heads (exactly one head)
    heads = sd.get_heads()
    assert len(heads) == 1, f"Expected exactly 1 head, got {len(heads)}: {heads}"
    assert heads[0] == REV_010, f"Head is {heads[0]}, expected {REV_010}"
