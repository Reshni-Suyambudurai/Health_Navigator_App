"""Add staff availability and appointment tables.

Revision ID: f4b7c8d9e0a1
Revises: f1a2b3c4d5e6
Create Date: 2026-10-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4b7c8d9e0a1"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("staff_availability") and inspector.has_table("appointments"):
        return

    day_of_week = sa.Enum(
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        "SATURDAY",
        "SUNDAY",
        name="day_of_week",
    )
    appointment_type = sa.Enum(
        "POST_DISCHARGE",
        "NURSE_FOLLOWUP",
        "CARE_MANAGER_CALL",
        name="appointment_type",
    )
    appointment_status = sa.Enum(
        "REQUESTED",
        "SCHEDULED",
        "CONFIRMED",
        "COMPLETED",
        "CANCELLED",
        "NO_SHOW",
        "RESCHEDULED",
        name="appointment_status",
    )
    booking_method = sa.Enum(
        "STAFF",
        "PATIENT_PORTAL",
        "EHR_INTEGRATION",
        name="booking_method",
    )

    op.create_table(
        "staff_availability",
        sa.Column("availability_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("staff_id", sa.BigInteger(), nullable=False),
        sa.Column("day_of_week", day_of_week, nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_until", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.staff_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("availability_id"),
    )
    op.create_index("ix_staff_availability_staff_id", "staff_availability", ["staff_id"])
    op.create_index("ix_staff_availability_day_of_week", "staff_availability", ["day_of_week"])
    op.create_index("ix_staff_availability_is_active", "staff_availability", ["is_active"])

    op.create_table(
        "appointments",
        sa.Column("appointment_id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("patient_id", sa.BigInteger(), nullable=False),
        sa.Column("staff_id", sa.BigInteger(), nullable=True),
        sa.Column("episode_id", sa.BigInteger(), nullable=True),
        sa.Column("appointment_type", appointment_type, nullable=False),
        sa.Column("appointment_datetime", sa.TIMESTAMP(), nullable=False),
        sa.Column("end_datetime", sa.TIMESTAMP(), nullable=False),
        sa.Column("status", appointment_status, server_default="REQUESTED", nullable=False),
        sa.Column("booking_method", booking_method, nullable=False),
        sa.Column("location_or_channel", sa.String(length=255), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.BigInteger(), nullable=False),
        sa.Column("external_fhir_appointment_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["patient_profiles.patient_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["staff_id"],
            ["staff_profiles.staff_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["episode_id"],
            ["care_navigation_episodes.episode_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.user_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("appointment_id"),
    )
    op.create_index("ix_appointments_patient_id", "appointments", ["patient_id"])
    op.create_index("ix_appointments_staff_id", "appointments", ["staff_id"])
    op.create_index("ix_appointments_episode_id", "appointments", ["episode_id"])
    op.create_index("ix_appointments_type", "appointments", ["appointment_type"])
    op.create_index("ix_appointments_datetime", "appointments", ["appointment_datetime"])
    op.create_index("ix_appointments_status", "appointments", ["status"])
    op.create_index("ix_appointments_created_by_user_id", "appointments", ["created_by_user_id"])
    op.create_index(
        "ix_appointments_external_fhir_appointment_id",
        "appointments",
        ["external_fhir_appointment_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_appointments_external_fhir_appointment_id", table_name="appointments")
    op.drop_index("ix_appointments_created_by_user_id", table_name="appointments")
    op.drop_index("ix_appointments_status", table_name="appointments")
    op.drop_index("ix_appointments_datetime", table_name="appointments")
    op.drop_index("ix_appointments_type", table_name="appointments")
    op.drop_index("ix_appointments_episode_id", table_name="appointments")
    op.drop_index("ix_appointments_staff_id", table_name="appointments")
    op.drop_index("ix_appointments_patient_id", table_name="appointments")
    op.drop_table("appointments")

    op.drop_index("ix_staff_availability_is_active", table_name="staff_availability")
    op.drop_index("ix_staff_availability_day_of_week", table_name="staff_availability")
    op.drop_index("ix_staff_availability_staff_id", table_name="staff_availability")
    op.drop_table("staff_availability")

    bind = op.get_bind()
    for enum_name in ("booking_method", "appointment_status", "appointment_type", "day_of_week"):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
