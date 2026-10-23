from datetime import date, datetime, time, timedelta
from typing import Any

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.appointment import Appointment, AppointmentStatus, AppointmentType, BookingMethod
from app.database.repositories.navigator.appointment_repository import AppointmentRepository
from app.database.repositories.navigator.patient_profile_repository import PatientProfileRepository
from app.database.repositories.navigator.staff_availability_repository import StaffAvailabilityRepository
from sqlalchemy.orm import Session


class AppointmentService:
    TRANSITIONAL_CARE_NURSE_ROLE_ID = 3

    def __init__(self, db: Session):
        self.db = db
        self.appointments = AppointmentRepository(db)
        self.patients = PatientProfileRepository(db)
        self.availability = StaffAvailabilityRepository(db)

    def get_nurse_appointments(self, user_id: int, upcoming: bool) -> list[dict[str, Any]]:
        staff = self._get_nurse_staff(user_id)
        return self.appointments.find_for_staff(staff.staff_id, upcoming=upcoming)

    def get_nurse_appointment_details(self, user_id: int, appointment_id: int) -> dict[str, Any]:
        staff = self._get_nurse_staff(user_id)
        appointment = self.appointments.find_details_by_id(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment not found", "APPOINTMENT_NOT_FOUND")
        if appointment["staff_id"] != staff.staff_id:
            raise AuthorizationException(
                "Only the assigned nurse can view this appointment.",
                "APPOINTMENT_VIEW_ACCESS_REQUIRED",
            )
        return appointment

    def get_patient_appointments(self, user_id: int, upcoming: bool) -> list[dict[str, Any]]:
        patient = self.patients.find_by_user_id(user_id)
        if not patient:
            raise NotFoundException("Patient profile not found", "PATIENT_NOT_FOUND")
        return self.appointments.find_for_patient(patient.patient_id, upcoming=upcoming)

    def get_reassignment_options(self, user_id: int, appointment_id: int) -> list[dict[str, Any]]:
        current_staff = self._get_nurse_staff(user_id)
        appointment = self.appointments.find_by_id(appointment_id)
        if not appointment:
            raise NotFoundException("Appointment not found", "APPOINTMENT_NOT_FOUND")
        if appointment.staff_id != current_staff.staff_id:
            raise AuthorizationException(
                "Only the assigned nurse can reassign this appointment.",
                "APPOINTMENT_UPDATE_ACCESS_REQUIRED",
            )

        return self.appointments.find_active_staff_by_role_id(
            self.TRANSITIONAL_CARE_NURSE_ROLE_ID,
            excluded_staff_id=current_staff.staff_id,
        )

    def update_nurse_appointment(
        self,
        user_id: int,
        appointment_id: int,
        new_status: AppointmentStatus,
        staff_id: int | None,
    ) -> dict[str, Any]:
        with self.db.begin():
            current_staff = self._get_nurse_staff(user_id)
            appointment = self.appointments.lock_appointment(appointment_id)
            if not appointment:
                raise NotFoundException("Appointment not found", "APPOINTMENT_NOT_FOUND")
            if appointment.staff_id != current_staff.staff_id:
                raise AuthorizationException(
                    "Only the assigned nurse can update this appointment.",
                    "APPOINTMENT_UPDATE_ACCESS_REQUIRED",
                )

            if staff_id and staff_id != current_staff.staff_id:
                staff_options = self.appointments.find_active_staff_by_role_id(
                    self.TRANSITIONAL_CARE_NURSE_ROLE_ID,
                    excluded_staff_id=current_staff.staff_id,
                )
                if staff_id not in {option["staff_id"] for option in staff_options}:
                    raise ValidationException(
                        "Select an active transitional care nurse.",
                        "INVALID_REASSIGNMENT_STAFF",
                    )
                target_staff = self.appointments.lock_staff_for_booking(staff_id)
                if not target_staff:
                    raise NotFoundException("Selected nurse not found", "STAFF_NOT_FOUND")
                appointment.staff_id = staff_id

            appointment.status = new_status

            saved = self.appointments.save(appointment)
            result = {
                "appointment_id": saved.appointment_id,
                "staff_id": saved.staff_id,
                "status": saved.status.value,
            }

        return result

    def get_available_slots(
        self,
        user_id: int,
        requested_date: date,
        duration_minutes: int,
    ) -> list[dict[str, str]]:
        self._validate_duration(duration_minutes)
        if requested_date < datetime.utcnow().date():
            raise ValidationException("Appointment date cannot be in the past.", "APPOINTMENT_DATE_IN_PAST")
        if not self.patients.find_by_user_id(user_id):
            raise NotFoundException("Patient profile not found", "PATIENT_NOT_FOUND")

        duration = timedelta(minutes=duration_minutes)
        windows = self.availability.find_active_for_date(requested_date)
        staff_ids = list({window.staff_id for window in windows})
        day_start = datetime.combine(requested_date, time.min)
        day_end = day_start + timedelta(days=1)
        busy_ranges = self.appointments.find_busy_ranges(staff_ids, day_start, day_end)
        busy_by_staff: dict[int, list[tuple[datetime, datetime]]] = {}
        for staff_id, busy_start, busy_end in busy_ranges:
            busy_by_staff.setdefault(staff_id, []).append((busy_start, busy_end))

        now = datetime.utcnow()
        slots: set[tuple[datetime, datetime]] = set()
        for window in windows:
            candidate = datetime.combine(requested_date, window.start_time)
            window_end = datetime.combine(requested_date, window.end_time)
            lunch_start = (
                datetime.combine(requested_date, window.lunch_start_time)
                if window.lunch_start_time
                else None
            )
            lunch_end = (
                datetime.combine(requested_date, window.lunch_end_time)
                if window.lunch_end_time
                else None
            )

            while candidate + duration <= window_end:
                candidate_end = candidate + duration
                overlaps_lunch = bool(
                    lunch_start
                    and lunch_end
                    and candidate < lunch_end
                    and candidate_end > lunch_start
                )
                overlaps_booking = any(
                    busy_start < candidate_end and busy_end > candidate
                    for busy_start, busy_end in busy_by_staff.get(window.staff_id, [])
                )
                if candidate > now and not overlaps_lunch and not overlaps_booking:
                    slots.add((candidate, candidate_end))
                candidate += timedelta(minutes=30)

        return [
            {"start": start.isoformat(), "end": end.isoformat()}
            for start, end in sorted(slots)
        ]

    def book_routine_appointment(
        self,
        patient_id: int,
        created_by_user_id: int,
        appointment_type: AppointmentType,
        appointment_datetime: datetime,
        end_datetime: datetime,
        reason: str | None,
        location_or_channel: str | None,
    ) -> dict[str, Any]:
        if end_datetime <= appointment_datetime:
            raise ValidationException("Appointment end time must be after its start time.", "INVALID_APPOINTMENT_RANGE")
        if appointment_datetime <= datetime.utcnow():
            raise ValidationException("Appointments must be scheduled in the future.", "APPOINTMENT_IN_PAST")
        duration_minutes = int((end_datetime - appointment_datetime).total_seconds() // 60)
        self._validate_duration(duration_minutes)

        with self.db.begin():
            patient = self.patients.find_by_user_id(created_by_user_id)
            if not patient or patient.patient_id != patient_id:
                raise AuthorizationException(
                    "You can only book appointments for your own patient profile.",
                    "PATIENT_BOOKING_ACCESS_REQUIRED",
                )

            candidates = self.availability.find_matching_staff(
                appointment_datetime.date(),
                appointment_datetime.time(),
                end_datetime.time(),
            )
            now = datetime.utcnow()
            ordered_candidates = sorted(
                candidates,
                key=lambda staff: (
                    self.appointments.count_upcoming(staff.staff_id, now),
                    staff.staff_id,
                ),
            )

            selected = None
            for candidate in ordered_candidates:
                locked_staff = self.appointments.lock_staff_for_booking(candidate.staff_id)
                if locked_staff and not self.appointments.has_overlap(
                    locked_staff.staff_id,
                    appointment_datetime,
                    end_datetime,
                ):
                    selected = locked_staff
                    break

            if not selected:
                raise ConflictException(
                    "This slot is no longer available. Please choose another available time.",
                    "NO_ELIGIBLE_NURSE",
                )

            saved = self.appointments.save(Appointment(
                patient_id=patient_id,
                staff_id=selected.staff_id,
                appointment_type=appointment_type,
                appointment_datetime=appointment_datetime,
                end_datetime=end_datetime,
                status=AppointmentStatus.REQUESTED,
                booking_method=BookingMethod.PATIENT_PORTAL,
                location_or_channel=location_or_channel,
                reason=reason,
                created_by_user_id=created_by_user_id,
            ))
            result = {
                "appointment_id": saved.appointment_id,
                "patient_id": saved.patient_id,
                "staff_id": saved.staff_id,
                "appointment_datetime": saved.appointment_datetime.isoformat(),
                "end_datetime": saved.end_datetime.isoformat(),
                "status": saved.status.value,
            }

        return result

    def _get_nurse_staff(self, user_id: int):
        staff = self.appointments.find_staff_profile_for_user(user_id)
        if not staff:
            raise AuthorizationException(
                "Only active transitional care nurses can access nurse appointments.",
                "NURSE_ACCESS_REQUIRED",
            )
        return staff

    @staticmethod
    def _validate_duration(duration_minutes: int) -> None:
        if duration_minutes not in {30, 45, 60}:
            raise ValidationException(
                "Appointment duration must be 30, 45, or 60 minutes.",
                "INVALID_APPOINTMENT_DURATION",
            )
