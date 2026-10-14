"""
Audit Log model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Text, ForeignKey, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum


class AuditAction(enum.Enum):
    """Audit action enum"""
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    VIEW_PATIENT = "VIEW_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    VIEW_MEDICATION = "VIEW_MEDICATION"
    VIEW_CONVERSATION = "VIEW_CONVERSATION"
    CREATE_ESCALATION = "CREATE_ESCALATION"
    UPDATE_ESCALATION = "UPDATE_ESCALATION"
    CLOSE_ESCALATION = "CLOSE_ESCALATION"
    VIEW_CARE_PLAN = "VIEW_CARE_PLAN"
    UPDATE_CARE_PLAN = "UPDATE_CARE_PLAN"
    VIEW_APPOINTMENT = "VIEW_APPOINTMENT"
    UPDATE_APPOINTMENT = "UPDATE_APPOINTMENT"
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DISABLE_USER = "DISABLE_USER"
    ENABLE_USER = "ENABLE_USER"


class AuditResourceType(enum.Enum):
    """Audit resource type enum"""
    USER = "USER"
    PATIENT = "PATIENT"
    MEDICATION = "MEDICATION"
    CONVERSATION = "CONVERSATION"
    ESCALATION = "ESCALATION"
    CARE_PLAN = "CARE_PLAN"
    APPOINTMENT = "APPOINTMENT"
    ORGANIZATION = "ORGANIZATION"


class AuditLog(Base):
    """
    Audit trail for all significant system actions
    """
    __tablename__ = "audit_logs"

    audit_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="SET NULL"), index=True)
    action = Column(SQLEnum(AuditAction, name="audit_action"), nullable=False, index=True)
    resource_type = Column(SQLEnum(AuditResourceType, name="audit_resource_type"), nullable=False)
    resource_id = Column(BigInteger)
    details = Column(Text)
    ip_address = Column(String(45))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self):
        return f"<AuditLog(id={self.audit_id}, action={self.action}, resource={self.resource_type})>"
