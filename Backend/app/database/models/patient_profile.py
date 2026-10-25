"""
Patient Profile model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Date, ForeignKey, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum


class Gender(enum.Enum):
    """Gender enum"""
    FEMALE = "FEMALE"
    MALE = "MALE"
    NON_BINARY = "NON_BINARY"
    OTHER = "OTHER"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"
    UNKNOWN = "UNKNOWN"
    NOT_DISCLOSED = "NOT_DISCLOSED"


class ContactMethod(enum.Enum):
    """Preferred contact method enum"""
    SMS = "SMS"
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    PORTAL = "PORTAL"


class RiskTier(enum.Enum):
    """Patient risk tier enum"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


class PatientProfile(Base):
    """
    Extended profile information for patients
    """
    __tablename__ = "patient_profiles"

    patient_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    external_fhir_patient_id = Column(String(100), unique=True, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(SQLEnum(Gender, name="gender"))
    preferred_language = Column(String(50), default="en")
    preferred_contact_method = Column(SQLEnum(ContactMethod, name="contact_method"), default=ContactMethod.SMS)
    emergency_contact_name = Column(String(200))
    emergency_contact_phone = Column(String(20))
    risk_tier = Column(SQLEnum(RiskTier, name="risk_tier"), nullable=False, default=RiskTier.UNKNOWN, index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    user = relationship("User", back_populates="patient_profile")

    def __repr__(self):
        return f"<PatientProfile(id={self.patient_id}, user_id={self.user_id})>"
