"""Nurse action and outcome recorded against an appointment."""

import enum

from sqlalchemy import BigInteger, Boolean, Column, Enum as SQLEnum, ForeignKey, Identity, Index, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class ContactMethod(enum.Enum):
    PHONE = "PHONE"
    PORTAL = "PORTAL"
    SMS = "SMS"
    VIDEO = "VIDEO"
    IN_PERSON = "IN_PERSON"
    INTERNAL_REVIEW = "INTERNAL_REVIEW"


class AppointmentActionType(enum.Enum):
    REVIEWED = "REVIEWED"
    CALL_ATTEMPT = "CALL_ATTEMPT"
    PATIENT_CONTACTED = "PATIENT_CONTACTED"
    GUIDANCE_PROVIDED = "GUIDANCE_PROVIDED"
    REFERRED = "REFERRED"
    OTHER = "OTHER"


class AppointmentOutcome(enum.Enum):
    REACHED = "REACHED"
    NO_ANSWER = "NO_ANSWER"
    ISSUE_ADDRESSED = "ISSUE_ADDRESSED"
    ISSUE_UNRESOLVED = "ISSUE_UNRESOLVED"
    REFERRED = "REFERRED"
    OTHER = "OTHER"


class AppointmentResolutionStatus(enum.Enum):
    PENDING = "PENDING"
    RESOLVED = "RESOLVED"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    UNABLE_TO_REACH = "UNABLE_TO_REACH"


class AppointmentAction(Base):
    __tablename__ = "appointment_actions"
    __table_args__ = (
        Index("ix_appointment_actions_appointment_created", "appointment_id", "created_at"),
        Index("ix_appointment_actions_patient_episode", "patient_id", "episode_id"),
        Index("ix_appointment_actions_resolution_due", "resolution_status", "follow_up_due_at"),
    )

    appointment_action_id = Column(BigInteger, Identity(), primary_key=True)
    appointment_id = Column(BigInteger, ForeignKey("appointments.appointment_id", ondelete="CASCADE"), nullable=False)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="SET NULL"))
    action_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT"), nullable=False)
    contact_datetime = Column(TIMESTAMP)
    contact_method = Column(SQLEnum(ContactMethod, name="appointment_contact_method"))
    action_taken = Column(SQLEnum(AppointmentActionType, name="appointment_action_type"), nullable=False)
    outcome = Column(SQLEnum(AppointmentOutcome, name="appointment_outcome"))
    action_notes = Column(Text)
    resolution_status = Column(SQLEnum(AppointmentResolutionStatus, name="appointment_resolution_status"), nullable=False, server_default="PENDING")
    follow_up_required = Column(Boolean, nullable=False, server_default="false")
    follow_up_notes = Column(Text)
    follow_up_due_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())