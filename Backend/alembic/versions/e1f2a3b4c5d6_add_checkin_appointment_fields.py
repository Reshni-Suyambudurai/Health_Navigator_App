"""Add appointment fields to check-in templates and sessions.

Revision ID: e1f2a3b4c5d6
Revises: d9e1f2a3b4c5
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d9e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "checkin_templates",
        sa.Column("appointment_required", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    appointment_status = postgresql.ENUM(
        "REQUESTED",
        "SCHEDULED",
        "CONFIRMED",
        "COMPLETED",
        "CANCELLED",
        "NO_SHOW",
        "RESCHEDULED",
        name="appointment_status",
        create_type=False,
    )
    op.add_column("checkin_sessions", sa.Column("appointment_id", sa.BigInteger(), nullable=True))
    op.add_column("checkin_sessions", sa.Column("appointment_status", appointment_status, nullable=True))
    op.create_index(
        "ix_checkin_sessions_appointment_id",
        "checkin_sessions",
        ["appointment_id"],
    )
    op.create_foreign_key(
        "fk_checkin_sessions_appointment_id",
        "checkin_sessions",
        "appointments",
        ["appointment_id"],
        ["appointment_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_checkin_sessions_appointment_id", "checkin_sessions", type_="foreignkey")
    op.drop_index("ix_checkin_sessions_appointment_id", table_name="checkin_sessions")
    op.drop_column("checkin_sessions", "appointment_status")
    op.drop_column("checkin_sessions", "appointment_id")
    op.drop_column("checkin_templates", "appointment_required")
