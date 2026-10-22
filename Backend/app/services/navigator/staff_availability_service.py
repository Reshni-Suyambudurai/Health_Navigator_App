from datetime import date, time
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.models.staff_availability import DayOfWeek, StaffAvailability
from app.database.repositories.navigator.appointment_repository import AppointmentRepository
from app.database.repositories.navigator.staff_availability_repository import StaffAvailabilityRepository


class StaffAvailabilityService:
    def __init__(self, db: Session):
        self.appointments = AppointmentRepository(db)
        self.repository = StaffAvailabilityRepository(db)

    def list_for_user(self, user_id: int) -> list[dict[str, Any]]:
        staff_id = self._staff_id(user_id)
        return [self._serialize(item) for item in self.repository.find_for_staff(staff_id)]

    def create_for_user(
        self,
        user_id: int,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        lunch_start_time: time | None,
        lunch_end_time: time | None,
        effective_from: date,
        effective_until: date | None,
        is_active: bool,
    ) -> dict[str, Any]:
        staff_id = self._staff_id(user_id)
        self._validate_times(start_time, end_time, lunch_start_time, lunch_end_time, effective_from, effective_until)
        item = StaffAvailability(
            staff_id=staff_id,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            lunch_start_time=lunch_start_time,
            lunch_end_time=lunch_end_time,
            effective_from=effective_from,
            effective_until=effective_until,
            is_active=is_active,
        )
        return self._serialize(self.repository.save(item))

    def update_for_user(
        self,
        user_id: int,
        availability_id: int,
        day_of_week: DayOfWeek,
        start_time: time,
        end_time: time,
        lunch_start_time: time | None,
        lunch_end_time: time | None,
        effective_from: date,
        effective_until: date | None,
        is_active: bool,
    ) -> dict[str, Any]:
        staff_id = self._staff_id(user_id)
        self._validate_times(start_time, end_time, lunch_start_time, lunch_end_time, effective_from, effective_until)
        item = self.repository.find_by_id(availability_id, staff_id)
        if not item:
            raise NotFoundException("Availability record not found", "AVAILABILITY_NOT_FOUND")
        item.day_of_week = day_of_week
        item.start_time = start_time
        item.end_time = end_time
        item.lunch_start_time = lunch_start_time
        item.lunch_end_time = lunch_end_time
        item.effective_from = effective_from
        item.effective_until = effective_until
        item.is_active = is_active
        return self._serialize(self.repository.save(item))

    def _staff_id(self, user_id: int) -> int:
        staff = self.appointments.find_staff_profile_for_user(user_id)
        if not staff:
            raise AuthorizationException(
                "Only active transitional care nurses can manage availability.",
                "NURSE_ACCESS_REQUIRED",
            )
        return staff.staff_id

    @staticmethod
    def _validate_times(
        start_time: time,
        end_time: time,
        lunch_start_time: time | None,
        lunch_end_time: time | None,
        effective_from: date,
        effective_until: date | None,
    ) -> None:
        if end_time <= start_time:
            raise ValidationException("Availability end time must be after start time.", "INVALID_AVAILABILITY_RANGE")
        if (lunch_start_time is None) != (lunch_end_time is None):
            raise ValidationException("Both lunch start and lunch end are required together.", "INVALID_LUNCH_WINDOW")
        if lunch_start_time is not None and lunch_end_time is not None:
            if lunch_start_time >= lunch_end_time or lunch_start_time < start_time or lunch_end_time > end_time:
                raise ValidationException("Lunch must be inside the availability window.", "INVALID_LUNCH_WINDOW")
        if effective_until and effective_until < effective_from:
            raise ValidationException("Availability end date must not be before its start date.", "INVALID_AVAILABILITY_DATES")

    @staticmethod
    def _serialize(item: StaffAvailability) -> dict[str, Any]:
        return {
            "availability_id": item.availability_id,
            "staff_id": item.staff_id,
            "day_of_week": item.day_of_week.value,
            "start_time": item.start_time.isoformat(),
            "end_time": item.end_time.isoformat(),
            "lunch_start_time": item.lunch_start_time.isoformat() if item.lunch_start_time else None,
            "lunch_end_time": item.lunch_end_time.isoformat() if item.lunch_end_time else None,
            "effective_from": item.effective_from.isoformat(),
            "effective_until": item.effective_until.isoformat() if item.effective_until else None,
            "is_active": item.is_active,
        }
