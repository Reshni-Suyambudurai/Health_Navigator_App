"""Add outreach event audit resource type.

Revision ID: f8a9b0c1d2e3
Revises: f7a8b9c0d1e2
"""

from typing import Union

from alembic import op


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_resource_type ADD VALUE IF NOT EXISTS 'OUTREACH_EVENT'")


def downgrade() -> None:
    # PostgreSQL does not support removing an enum value safely.
    pass
