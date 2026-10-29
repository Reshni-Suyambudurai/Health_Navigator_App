"""Appointment model."""

import enum
from sqlalchemy import BigInteger, Column, ForeignKey, Identity, String, Text, TIMESTAMP, CheckConstraint, Index, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class AppointmentType(enum.Enum):
    ROUTINE = "ROUTINE"
    CHECK_IN = "CHECK-IN"


class AppointmentStatus(enum.Enum):
    REQUESTED = "REQUESTED"
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    NO_SHOW = "NO_SHOW"
    RESCHEDULED = "RESCHEDULED"


class BookingMethod(enum.Enum):
    STAFF = "STAFF"
    PATIENT_PORTAL = "PATIENT_PORTAL"
    EHR_INTEGRATION = "EHR_INTEGRATION"


class Appointment(Base):
    __tablename__ = "appointments"
    __table_args__ = (
        CheckConstraint("appointment_datetime < end_datetime", name="chk_appointment_time"),
        Index("ix_appointments_staff_time_range", "staff_id", "appointment_datetime", "end_datetime"),
        Index("ix_appointments_patient_datetime", "patient_id", "appointment_datetime"),
    )

    appointment_id = Column(BigInteger, Identity(), primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"), index=True)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="SET NULL"), index=True)
    source_outreach_event_id = Column(BigInteger, ForeignKey("outreach_events.outreach_event_id", ondelete="SET NULL"), index=True)
    appointment_type = Column(
        SQLEnum(
            AppointmentType,
            name="appointment_type",
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
        index=True,
    )
    appointment_datetime = Column(TIMESTAMP, nullable=False, index=True)
    end_datetime = Column(TIMESTAMP, nullable=False)
    status = Column(SQLEnum(AppointmentStatus, name="appointment_status"), nullable=False, server_default="REQUESTED", index=True)
    booking_method = Column(SQLEnum(BookingMethod, name="booking_method"), nullable=False)
    location_or_channel = Column(String(255))
    reason = Column(Text)
    cancellation_reason = Column(Text)
    rescheduled_from_appointment_id = Column(BigInteger, ForeignKey("appointments.appointment_id", ondelete="SET NULL"), index=True)
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False, index=True)
    external_fhir_appointment_id = Column(String(255), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, onupdate=func.current_timestamp())
