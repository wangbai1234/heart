"""Initial empty schema — stub for migration chain compatibility.

Revision ID: e814230ade46
Revises:
Create Date: 2026-05-16

This is a zero-op migration that serves as the initial root for the chain.
"""

revision: str = "e814230ade46"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
