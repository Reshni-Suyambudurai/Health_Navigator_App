"""Add campaign automatic outreach setting.

Revision ID: d2a4c6e8f0b1
Revises: c6f8a0b2d4e5
"""

from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2a4c6e8f0b1"
down_revision: Union[str, None] = "c6f8a0b2d4e5"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.add_column(
        "outreach_campaigns",
        sa.Column("auto_outreach_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.create_index(
        "ix_outreach_campaigns_auto_outreach_enabled",
        "outreach_campaigns",
        ["auto_outreach_enabled"],
    )
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'ENABLE_AUTO_OUTREACH'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'DISABLE_AUTO_OUTREACH'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'AUTO_CREATE_OUTREACH_EVENTS'")


def downgrade() -> None:
    op.drop_index("ix_outreach_campaigns_auto_outreach_enabled", table_name="outreach_campaigns")
    op.drop_column("outreach_campaigns", "auto_outreach_enabled")