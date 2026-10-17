"""Patient consent record model."""

import enum
from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class ConsentType(enum.Enum):
    AI_DISCLOSURE = "AI_DISCLOSURE"
    AI_INTERACTION = "AI_INTERACTION"
    OUTREACH = "OUTREACH"
    DATA_USE = "DATA_USE"


class ConsentStatus(enum.Enum):
    ACCEPTED = "ACCEPTED"
    DECLINED = "DECLINED"
    REVOKED = "REVOKED"
    PENDING = "PENDING"


class CapturedChannel(enum.Enum):
    PORTAL = "PORTAL"
    SMS = "SMS"
    PHONE = "PHONE"
    IN_PERSON = "IN_PERSON"


class PatientConsentRecord(Base):
    __tablename__ = "patient_consent_records"

    consent_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(String(50), nullable=False, index=True)
    consent_status = Column(String(30), nullable=False, index=True)
    consent_text_version = Column(String(50), nullable=False)
    effective_at = Column(TIMESTAMP, nullable=False)
    revoked_at = Column(TIMESTAMP)
    captured_channel = Column(String(30), nullable=False)
    captured_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
