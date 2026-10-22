"""Add lunch windows and availability checks.

Revision ID: a7c8d9e0f1b2
Revises: f4b7c8d9e0a1
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c8d9e0f1b2"
down_revision: Union[str, None] = "f4b7c8d9e0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("staff_availability", sa.Column("lunch_start_time", sa.Time(), nullable=True))
    op.add_column("staff_availability", sa.Column("lunch_end_time", sa.Time(), nullable=True))
    op.create_check_constraint(
        "chk_availability_time",
        "staff_availability",
        "start_time < end_time",
    )
    op.create_check_constraint(
        "chk_lunch_time",
        "staff_availability",
        "(lunch_start_time IS NULL AND lunch_end_time IS NULL) OR "
        "(lunch_start_time IS NOT NULL AND lunch_end_time IS NOT NULL AND "
        "lunch_start_time < lunch_end_time AND lunch_start_time >= start_time AND "
        "lunch_end_time <= end_time)",
    )


def downgrade() -> None:
    op.drop_constraint("chk_lunch_time", "staff_availability", type_="check")
    op.drop_constraint("chk_availability_time", "staff_availability", type_="check")
    op.drop_column("staff_availability", "lunch_end_time")
    op.drop_column("staff_availability", "lunch_start_time")
