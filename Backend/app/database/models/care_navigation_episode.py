"""Care navigation episode model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class EpisodeType(enum.Enum):
    POST_DISCHARGE_30_DAY = "POST_DISCHARGE_30_DAY"
    MEDICATION_SUPPORT = "MEDICATION_SUPPORT"
    CHRONIC_CARE_FOLLOWUP = "CHRONIC_CARE_FOLLOWUP"
    APPOINTMENT_FOLLOWUP = "APPOINTMENT_FOLLOWUP"
    GENERAL_NAVIGATION = "GENERAL_NAVIGATION"
    # Legacy values retained for compatibility.
    POST_DISCHARGE = "POST_DISCHARGE"
    CHRONIC_CARE = "CHRONIC_CARE"


class TriggerType(enum.Enum):
    DISCHARGE = "DISCHARGE"
    PATIENT_REQUEST = "PATIENT_REQUEST"
    MEDICATION_CONCERN = "MEDICATION_CONCERN"
    SCHEDULED_OUTREACH = "SCHEDULED_OUTREACH"
    STAFF_REFERRAL = "STAFF_REFERRAL"
    # Legacy values retained for compatibility.
    FHIR_ENCOUNTER = "FHIR_ENCOUNTER"
    FHIR_OBSERVATION = "FHIR_OBSERVATION"
    MANUAL = "MANUAL"
    CAMPAIGN = "CAMPAIGN"


class EpisodeStatus(enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    ON_HOLD = "ON_HOLD"
    COMPLETED = "COMPLETED"
    CLOSED = "CLOSED"


class CareNavigationEpisode(Base):
    __tablename__ = "care_navigation_episodes"

    episode_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    enrollment_id = Column(BigInteger, ForeignKey("patient_enrollments.enrollment_id", ondelete="CASCADE"), nullable=False, index=True)
    episode_type = Column(SQLEnum(EpisodeType, name="episode_type"), nullable=False, index=True)
    trigger_type = Column(SQLEnum(TriggerType, name="trigger_type"), nullable=False)
    trigger_reference = Column(String(255))
    status = Column(SQLEnum(EpisodeStatus, name="episode_status"), nullable=False, index=True)
    opened_at = Column(TIMESTAMP, nullable=False)
    closed_at = Column(TIMESTAMP)
    owner_staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
