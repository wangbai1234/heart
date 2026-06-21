"""Add L4 promotion extras to fact_nodes and identity_memories.

Revision ID: 009_memory_l4_extras
Revises: 008_memory_extraction_dlq
Create Date: 2026-06-19 18:00:00.000000

Schema: PostgreSQL 15+
Purpose: Support L3→L4 Promoter (INV-M-15).
  - fact_nodes: add was_l4, previously_l4_id for demotion tracking
  - identity_memories: add demoted_at, demotion_reason for demotion shadowing
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "009_memory_l4_extras"
down_revision = "008_memory_extraction_dlq"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # fact_nodes: demotion tracking columns
    op.add_column("fact_nodes", sa.Column("was_l4", Boolean, nullable=False, server_default="false"))
    op.add_column(
        "fact_nodes",
        sa.Column("previously_l4_id", PG_UUID(as_uuid=True), nullable=True),
    )

    # identity_memories: demotion shadow columns
    op.add_column(
        "identity_memories",
        sa.Column("demoted_at", DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "identity_memories",
        sa.Column("demotion_reason", Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("identity_memories", "demotion_reason")
    op.drop_column("identity_memories", "demoted_at")
    op.drop_column("fact_nodes", "previously_l4_id")
    op.drop_column("fact_nodes", "was_l4")
