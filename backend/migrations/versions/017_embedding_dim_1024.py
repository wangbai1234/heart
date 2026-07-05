"""Widen semantic_vector 768 → 1024 to match BAAI/bge-m3.

The embedding write path never populated semantic_vector (confirmed zero
assignment sites before PR4), so every value is NULL and dropping/recreating
the column at the new dimension loses no data. HNSW indexes are dimension-bound,
so they are dropped and recreated around the type change.

emotional_vector (256-dim) is unrelated to semantic recall and left unchanged.

Revision ID: 017_embed_dim_1024
Revises: 016_monthly_parts
Create Date: 2026-07-06
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "017_embed_dim_1024"
down_revision = "016_monthly_parts"
branch_labels = None
depends_on = None


_TARGETS = (
    # (table, hnsw index name)
    ("episodic_memories", "idx_episodic_semantic"),
    ("fact_nodes", "idx_fact_semantic"),
)


def _reshape(dim: int) -> None:
    for table, index_name in _TARGETS:
        op.execute(f"DROP INDEX IF EXISTS {index_name}")
        # All values are NULL, so drop+add is a safe, dimension-agnostic swap.
        op.execute(f"ALTER TABLE {table} DROP COLUMN IF EXISTS semantic_vector")
        op.execute(f"ALTER TABLE {table} ADD COLUMN semantic_vector vector({dim})")
        op.execute(
            f"CREATE INDEX {index_name} ON {table} "
            f"USING hnsw (semantic_vector vector_cosine_ops)"
        )


def upgrade() -> None:
    _reshape(1024)


def downgrade() -> None:
    _reshape(768)
