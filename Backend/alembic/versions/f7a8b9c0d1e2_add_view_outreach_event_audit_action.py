"""Add outreach event detail audit action.

Revision ID: f7a8b9c0d1e2
Revises: d2a4c6e8f0b1
"""

from typing import Union

from alembic import op


revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "d2a4c6e8f0b1"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'VIEW_OUTREACH_EVENT'")


def downgrade() -> None:
    # PostgreSQL does not support removing a value from an enum safely.
    pass
