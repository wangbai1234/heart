"""Extend relationship_events monthly partitions.

Revision ID: 015_rel_event_parts
Revises: 014_chat_messages
Create Date: 2026-07-05
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "015_rel_event_parts"
down_revision = "014_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            month_start date := DATE '2026-05-01';
            month_end date;
            partition_name text;
            cutoff date := (date_trunc('month', CURRENT_DATE) + INTERVAL '12 months')::date;
        BEGIN
            WHILE month_start <= cutoff LOOP
                month_end := (month_start + INTERVAL '1 month')::date;
                partition_name := format('relationship_events_%s', to_char(month_start, 'YYYY_MM'));

                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF relationship_events FOR VALUES FROM (%L) TO (%L)',
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


def downgrade() -> None:
    # Keep partitions in place on downgrade; dropping them risks deleting audit history.
    pass
