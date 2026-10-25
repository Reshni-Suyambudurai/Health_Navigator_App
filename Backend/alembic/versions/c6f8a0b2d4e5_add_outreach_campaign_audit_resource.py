"""Add outreach campaign audit resource type.

Revision ID: c6f8a0b2d4e5
Revises: b4e6f8a0c2d4
"""

from typing import Union

from alembic import op


revision: str = "c6f8a0b2d4e5"
down_revision: Union[str, None] = "b4e6f8a0c2d4"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE audit_resource_type ADD VALUE IF NOT EXISTS 'OUTREACH_CAMPAIGN'")


def downgrade() -> None:
    pass