"""
User model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Boolean, ForeignKey, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base
import enum


class UserStatus(enum.Enum):
    """User status enum"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class User(Base):
    """
    User accounts for all system users (patients, staff, administrators)
    """
    __tablename__ = "users"

    user_id = Column(BigInteger, primary_key=True, index=True)
    organization_id = Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="RESTRICT"), nullable=False, index=True)
    role_id = Column(BigInteger, ForeignKey("roles.role_id", ondelete="RESTRICT"), nullable=False, index=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    phone = Column(String(20))
    status = Column(SQLEnum(UserStatus, name="user_status"), nullable=False, default=UserStatus.ACTIVE, index=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    last_login_at = Column(TIMESTAMP)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    organization = relationship("Organization")
    role = relationship("Role")
    patient_profile = relationship("PatientProfile", back_populates="user", uselist=False)
    staff_profile = relationship("StaffProfile", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.user_id}, email='{self.email}', role_id={self.role_id})>"
