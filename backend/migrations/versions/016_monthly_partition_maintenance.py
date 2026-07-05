"""Pre-create monthly partitions for range-partitioned event tables.

Revision ID: 016_monthly_parts
Revises: 015_rel_event_parts
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "016_monthly_parts"
down_revision = "015_rel_event_parts"
branch_labels = None
depends_on = None


def _create_monthly_partitions(parent_table: str, prefix: str, start_date: str) -> None:
    op.execute(
        f"""
        DO $$
        DECLARE
            month_start date := DATE '{start_date}';
            month_end date;
            partition_name text;
            cutoff date := (date_trunc('month', CURRENT_DATE) + INTERVAL '12 months')::date;
        BEGIN
            WHILE month_start <= cutoff LOOP
                month_end := (month_start + INTERVAL '1 month')::date;
                partition_name := format('{prefix}_%s', to_char(month_start, 'YYYY_MM'));

                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF {parent_table} FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    month_start,
                    month_end
                );

                month_start := month_end;
            END LOOP;
        END
        $$;
        """
    )


def upgrade() -> None:
    _create_monthly_partitions("memory_encoding_events", "memory_encoding_events", "2026-05-01")
    _create_monthly_partitions("emotion_events", "emotion_events", "2026-05-01")
    _create_monthly_partitions("relationship_events", "relationship_events", "2026-05-01")


def downgrade() -> None:
    # Keep partitions in place on downgrade; dropping them risks deleting audit history.
    pass
