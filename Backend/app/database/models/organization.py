"""
Organization model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, Enum as SQLEnum, TIMESTAMP
from sqlalchemy.sql import func
from app.database.connection import Base
import enum


class OrganizationStatus(enum.Enum):
    """Organization status enum"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class OrganizationType(enum.Enum):
    """Organization type enum"""
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    HEALTHCARE_GROUP = "HEALTHCARE_GROUP"
    PAYER = "PAYER"
    ACO = "ACO"


class Organization(Base):
    """
    Healthcare organizations using the Patient AI Health Navigator
    """
    __tablename__ = "organizations"

    organization_id = Column(BigInteger, primary_key=True, index=True)
    organization_name = Column(String(255), nullable=False, unique=True)
    organization_type = Column(SQLEnum(OrganizationType, name="organization_type"), nullable=False)
    npi_number = Column(String(20), index=True)
    address = Column(String(500))
    phone = Column(String(20))
    status = Column(SQLEnum(OrganizationStatus, name="organization_status"), nullable=False, default=OrganizationStatus.ACTIVE)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    def __repr__(self):
        return f"<Organization(id={self.organization_id}, name='{self.organization_name}', type={self.organization_type})>"
