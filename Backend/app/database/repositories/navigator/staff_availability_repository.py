from datetime import date, datetime, time, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models.role import Role, RoleName
from app.database.models.staff_availability import DayOfWeek, StaffAvailability
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User, UserStatus


class StaffAvailabilityRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_for_staff(self, staff_id: int) -> list[StaffAvailability]:
        return (
            self.db.query(StaffAvailability)
            .filter(StaffAvailability.staff_id == staff_id)
            .order_by(StaffAvailability.day_of_week, StaffAvailability.start_time)
            .all()
        )

    def find_matching_staff(self, requested_date: date, start_time: time, end_time: time) -> list[StaffProfile]:
        day = DayOfWeek[requested_date.strftime("%A").upper()]
        return (
            self.db.query(StaffProfile)
            .join(User, StaffProfile.user_id == User.user_id)
            .join(Role, User.role_id == Role.role_id)
            .join(StaffAvailability, StaffAvailability.staff_id == StaffProfile.staff_id)
            .filter(
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.TRANSITIONAL_CARE_NURSE,
                StaffAvailability.day_of_week == day,
                StaffAvailability.start_time <= start_time,
                StaffAvailability.end_time >= end_time,
                (
                    StaffAvailability.lunch_start_time.is_(None)
                    | (StaffAvailability.lunch_end_time <= start_time)
                    | (StaffAvailability.lunch_start_time >= end_time)
                ),
                StaffAvailability.effective_from <= requested_date,
                (StaffAvailability.effective_until.is_(None) | (StaffAvailability.effective_until >= requested_date)),
                StaffAvailability.is_active.is_(True),
            )
            .distinct()
            .all()
        )

    def find_active_for_date(self, requested_date: date) -> list[StaffAvailability]:
        day = DayOfWeek[requested_date.strftime("%A").upper()]
        return (
            self.db.query(StaffAvailability)
            .join(StaffProfile, StaffAvailability.staff_id == StaffProfile.staff_id)
            .join(User, StaffProfile.user_id == User.user_id)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.TRANSITIONAL_CARE_NURSE,
                StaffAvailability.day_of_week == day,
                StaffAvailability.effective_from <= requested_date,
                (StaffAvailability.effective_until.is_(None) | (StaffAvailability.effective_until >= requested_date)),
                StaffAvailability.is_active.is_(True),
            )
            .order_by(StaffAvailability.start_time, StaffAvailability.staff_id)
            .all()
        )

    def find_alternative_slots(
        self,
        requested_date: date,
        duration: timedelta,
        limit: int = 5,
    ) -> list[dict[str, datetime]]:
        day = DayOfWeek[requested_date.strftime("%A").upper()]
        rows = (
            self.db.query(StaffAvailability)
            .join(StaffProfile, StaffAvailability.staff_id == StaffProfile.staff_id)
            .join(User, StaffProfile.user_id == User.user_id)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.TRANSITIONAL_CARE_NURSE,
                StaffAvailability.day_of_week == day,
                StaffAvailability.effective_from <= requested_date,
                (StaffAvailability.effective_until.is_(None) | (StaffAvailability.effective_until >= requested_date)),
                StaffAvailability.is_active.is_(True),
            )
            .order_by(StaffAvailability.start_time)
            .all()
        )
        alternatives: list[dict[str, datetime]] = []
        for row in rows:
            start = datetime.combine(requested_date, row.start_time)
            end = datetime.combine(requested_date, row.end_time)
            candidate = start
            while candidate + duration <= end and len(alternatives) < limit:
                if (
                    row.lunch_start_time
                    and row.lunch_end_time
                    and candidate.time() < row.lunch_end_time
                    and (candidate + duration).time() > row.lunch_start_time
                ):
                    candidate = datetime.combine(requested_date, row.lunch_end_time)
                    continue
                alternatives.append({"start": candidate, "end": candidate + duration})
                candidate += timedelta(minutes=30)
        return alternatives

    def save(self, availability: StaffAvailability) -> StaffAvailability:
        self.db.add(availability)
        self.db.commit()
        self.db.refresh(availability)
        return availability

    def find_by_id(self, availability_id: int, staff_id: int) -> Optional[StaffAvailability]:
        return (
            self.db.query(StaffAvailability)
            .filter(
                StaffAvailability.availability_id == availability_id,
                StaffAvailability.staff_id == staff_id,
            )
            .first()
        )
