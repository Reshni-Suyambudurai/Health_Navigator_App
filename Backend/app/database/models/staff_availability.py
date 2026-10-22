"""Staff availability model."""

import enum
from sqlalchemy import Boolean, Column, Date, ForeignKey, BigInteger, Identity, Time, TIMESTAMP, Enum as SQLEnum
from sqlalchemy.sql import func
from app.database.connection import Base


class DayOfWeek(enum.Enum):
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class StaffAvailability(Base):
    __tablename__ = "staff_availability"

    availability_id = Column(BigInteger, Identity(), primary_key=True, index=True)
    staff_id = Column(BigInteger, ForeignKey("staff_profiles.staff_id", ondelete="CASCADE"), nullable=False, index=True)
    day_of_week = Column(SQLEnum(DayOfWeek, name="day_of_week"), nullable=False, index=True)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_until = Column(Date)
    is_active = Column(Boolean, nullable=False, server_default="true", index=True)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.current_timestamp())
    updated_at = Column(TIMESTAMP, onupdate=func.current_timestamp())
