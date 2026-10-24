"""Unresolved patient follow-up work item model."""

import enum

from sqlalchemy import BigInteger, Column, Enum as SQLEnum, ForeignKey, Identity, Index, String, Text, TIMESTAMP
from sqlalchemy.sql import func

from app.database.connection import Base


class FollowUpTaskType(enum.Enum):
    PATIENT_CONTACT = "PATIENT_CONTACT"
    MEDICATION_FOLLOWUP = "MEDICATION_FOLLOWUP"
    APPOINTMENT_BOOKING = "APPOINTMENT_BOOKING"
    CLINICAL_REVIEW = "CLINICAL_REVIEW"
    OTHER = "OTHER"


class FollowUpPriority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FollowUpTaskStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class FollowUpTask(Base):
    __tablename__ = "follow_up_tasks"
    __table_args__ = (
        Index("ix_follow_up_tasks_status_due", "status", "due_at"),
        Index("ix_follow_up_tasks_assignee_status_due", "assigned_to_staff_id", "status", "due_at"),
        Index("ix_follow_up_tasks_patient_episode", "patient_id", "episode_id"),
    )

    follow_up_task_id = Column(BigInteger, Identity(), primary_key=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False)
    episode_id = Column(BigInteger, ForeignKey("care_navigation_episodes.episode_id", ondelete="SET NULL"))
    appointment_id = Column(BigInteger, ForeignKey("appointments.appointment_id", ondelete="SET NULL"))
    escalation_id = Column(BigInteger, ForeignKey("escalations.escalation_id", ondelete="SET NULL"))
    task_type = Column(SQLEnum(FollowUpTaskType, name="follow_up_task_type"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    assigned_to_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"))
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"))
    due_at = Column(TIMESTAMP)
    priority = Column(SQLEnum(FollowUpPriority, name="follow_up_priority"), nullable=False, server_default="MEDIUM")
    status = Column(SQLEnum(FollowUpTaskStatus, name="follow_up_task_status"), nullable=False, server_default="OPEN")
    completed_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"))
    completed_at = Column(TIMESTAMP)
    completion_notes = Column(Text)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())