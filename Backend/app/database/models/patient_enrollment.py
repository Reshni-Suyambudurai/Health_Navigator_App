"""Patient enrollment model."""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base


class PatientEnrollment(Base):
    __tablename__ = "patient_enrollments"

    enrollment_id = Column(BigInteger, primary_key=True, index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True)
    enrollment_program = Column(String(50), nullable=False, index=True)
    enrollment_status = Column(String(30), nullable=False, index=True)
    enrollment_date = Column(TIMESTAMP, nullable=False)
    close_date = Column(TIMESTAMP)
    closed_reason = Column(String(255))
    created_by_user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())
