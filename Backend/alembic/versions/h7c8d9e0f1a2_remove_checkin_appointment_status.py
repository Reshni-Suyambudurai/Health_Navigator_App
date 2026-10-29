"""Remove duplicated appointment status from check-in sessions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "h7c8d9e0f1a2"
down_revision: Union[str, None] = "g6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("checkin_sessions", "appointment_status")


def downgrade() -> None:
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
    op.add_column(
        "checkin_sessions",
        sa.Column("appointment_status", appointment_status, nullable=True),
    )
