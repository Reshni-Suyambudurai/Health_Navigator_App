"""Add manual outreach creation audit action.

Revision ID: b4e6f8a0c2d4
Revises: a3d5e7f9b1c2
"""

from typing import Union

from alembic import op


revision: str = "b4e6f8a0c2d4"
down_revision: Union[str, None] = "a3d5e7f9b1c2"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'CREATE_OUTREACH_EVENTS'")


def downgrade() -> None:
    pass