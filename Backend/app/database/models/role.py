"""
Role model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base
import enum


class RoleName(enum.Enum):
    """Role name enum - aligned with BRD workflow roles"""
    PATIENT = "PATIENT"
    CARE_MANAGER = "CARE_MANAGER"
    TRANSITIONAL_CARE_NURSE = "TRANSITIONAL_CARE_NURSE"
    PHARMACIST = "PHARMACIST"
    SOCIAL_WORKER = "SOCIAL_WORKER"
    POPULATION_HEALTH_MANAGER = "POPULATION_HEALTH_MANAGER"
    CLINICAL_GOVERNANCE = "CLINICAL_GOVERNANCE"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class Role(Base):
    """
    User roles aligned with BRD workflow roles
    """
    __tablename__ = "roles"

    role_id = Column(BigInteger, primary_key=True, index=True)
    role_name = Column(SQLEnum(RoleName, name="role_name"), nullable=False, unique=True)
    description = Column(String(500))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())

    def __repr__(self):
        return f"<Role(id={self.role_id}, name={self.role_name})>"
