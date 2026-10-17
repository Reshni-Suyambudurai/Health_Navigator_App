"""
Audit Log model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class AuditLog(Base):
    """
    Audit trail for all significant system actions
    """
    __tablename__ = "audit_logs"

    audit_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    patient_id = Column(BigInteger, ForeignKey("patient_profiles.patient_id", ondelete="SET NULL"), index=True)
    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(BigInteger)
    details = Column(Text)
    ip_address = Column(String(45))
    correlation_id = Column(String(100), index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    patient = relationship("PatientProfile")

    def __repr__(self):
        return f"<AuditLog(id={self.audit_id}, action={self.action}, resource={self.resource_type})>"
