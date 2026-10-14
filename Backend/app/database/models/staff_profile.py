"""
Staff Profile model for Patient AI Health Navigator
"""

from sqlalchemy import Column, BigInteger, String, ForeignKey, TIMESTAMP
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database.connection import Base


class StaffProfile(Base):
    """
    Extended profile information for healthcare staff
    """
    __tablename__ = "staff_profiles"

    staff_id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    employee_id = Column(String(50), index=True)
    license_number = Column(String(100))
    license_type = Column(String(100))
    department = Column(String(100))
    specialization = Column(String(200))
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    user = relationship("User", back_populates="staff_profile")

    def __repr__(self):
        return f"<StaffProfile(id={self.staff_id}, user_id={self.user_id}, employee_id='{self.employee_id}')>"
