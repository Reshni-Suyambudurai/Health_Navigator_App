from datetime import datetime
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment, AppointmentStatus
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role, RoleName
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User, UserStatus


class AppointmentRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_staff_profile_for_user(self, user_id: int) -> Optional[StaffProfile]:
        return (
            self.db.query(StaffProfile)
            .join(User, StaffProfile.user_id == User.user_id)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                StaffProfile.user_id == user_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.TRANSITIONAL_CARE_NURSE,
            )
            .first()
        )

    def patient_exists(self, patient_id: int) -> bool:
        return (
            self.db.query(PatientProfile.patient_id)
            .filter(PatientProfile.patient_id == patient_id)
            .first()
            is not None
        )

    def lock_staff_for_booking(self, staff_id: int) -> Optional[StaffProfile]:
        return (
            self.db.query(StaffProfile)
            .filter(StaffProfile.staff_id == staff_id)
            .with_for_update()
            .one_or_none()
        )

    def find_by_id(self, appointment_id: int) -> Optional[Appointment]:
        return (
            self.db.query(Appointment)
            .filter(Appointment.appointment_id == appointment_id)
            .first()
        )

    def find_details_by_id(self, appointment_id: int) -> Optional[dict[str, Any]]:
        row = (
            self.db.query(Appointment, PatientProfile, User)
            .join(PatientProfile, Appointment.patient_id == PatientProfile.patient_id)
            .join(User, PatientProfile.user_id == User.user_id)
            .filter(Appointment.appointment_id == appointment_id)
            .first()
        )
        if not row:
            return None

        appointment, patient, user = row
        return {
            **self._serialize_row(appointment, patient, user),
            "external_fhir_patient_id": patient.external_fhir_patient_id,
        }

    def lock_appointment(self, appointment_id: int) -> Optional[Appointment]:
        return (
            self.db.query(Appointment)
            .filter(Appointment.appointment_id == appointment_id)
            .with_for_update()
            .one_or_none()
        )

    def find_staff_options(self, staff_ids: list[int]) -> list[dict[str, Any]]:
        if not staff_ids:
            return []
        rows = (
            self.db.query(StaffProfile, User)
            .join(User, StaffProfile.user_id == User.user_id)
            .filter(StaffProfile.staff_id.in_(staff_ids))
            .order_by(User.first_name, User.last_name)
            .all()
        )
        return [
            {
                "staff_id": staff.staff_id,
                "staff_name": f"{user.first_name} {user.last_name}",
            }
            for staff, user in rows
        ]

    def find_active_staff_by_role_id(
        self,
        role_id: int,
        excluded_staff_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            self.db.query(StaffProfile, User)
            .join(User, StaffProfile.user_id == User.user_id)
            .filter(
                User.role_id == role_id,
                User.status == UserStatus.ACTIVE,
            )
        )
        if excluded_staff_id is not None:
            query = query.filter(StaffProfile.staff_id != excluded_staff_id)

        rows = query.order_by(User.first_name, User.last_name).all()
        return [
            {
                "staff_id": staff.staff_id,
                "staff_name": f"{user.first_name} {user.last_name}",
            }
            for staff, user in rows
        ]

    def find_for_staff(self, staff_id: int, upcoming: bool) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        query = (
            self.db.query(Appointment, PatientProfile, User)
            .join(PatientProfile, Appointment.patient_id == PatientProfile.patient_id)
            .join(User, PatientProfile.user_id == User.user_id)
            .filter(Appointment.staff_id == staff_id)
        )

        if upcoming:
            query = query.filter(
                Appointment.appointment_datetime >= now,
                Appointment.status.in_([
                    AppointmentStatus.REQUESTED,
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.RESCHEDULED,
                ]),
            )
        else:
            query = query.filter(
                or_(
                    Appointment.appointment_datetime < now,
                    Appointment.status.in_([
                        AppointmentStatus.COMPLETED,
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.NO_SHOW,
                    ]),
                )
            )

        rows = query.order_by(Appointment.appointment_datetime.asc()).all()
        return [self._serialize_row(appointment, patient, user) for appointment, patient, user in rows]

    def find_for_patient(self, patient_id: int, upcoming: bool) -> list[dict[str, Any]]:
        now = datetime.utcnow()
        query = (
            self.db.query(Appointment, StaffProfile, User)
            .outerjoin(StaffProfile, Appointment.staff_id == StaffProfile.staff_id)
            .outerjoin(User, StaffProfile.user_id == User.user_id)
            .filter(Appointment.patient_id == patient_id)
        )

        if upcoming:
            query = query.filter(
                Appointment.appointment_datetime >= now,
                Appointment.status.in_([
                    AppointmentStatus.REQUESTED,
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.RESCHEDULED,
                ]),
            )
        else:
            query = query.filter(
                or_(
                    Appointment.appointment_datetime < now,
                    Appointment.status.in_([
                        AppointmentStatus.COMPLETED,
                        AppointmentStatus.CANCELLED,
                        AppointmentStatus.NO_SHOW,
                    ]),
                )
            )

        rows = query.order_by(
            Appointment.appointment_datetime.asc() if upcoming else Appointment.appointment_datetime.desc()
        ).all()
        return [
            {
                "appointment_id": appointment.appointment_id,
                "patient_id": appointment.patient_id,
                "staff_id": appointment.staff_id,
                "staff_name": (
                    f"{staff_user.first_name} {staff_user.last_name}"
                    if staff_user
                    else "Care team"
                ),
                "appointment_type": appointment.appointment_type.value,
                "appointment_datetime": appointment.appointment_datetime.isoformat(),
                "end_datetime": appointment.end_datetime.isoformat(),
                "status": appointment.status.value,
                "booking_method": appointment.booking_method.value,
                "location_or_channel": appointment.location_or_channel,
                "reason": appointment.reason,
            }
            for appointment, _staff, staff_user in rows
        ]

    def has_overlap(self, staff_id: int, start: datetime, end: datetime) -> bool:
        return (
            self.db.query(Appointment.appointment_id)
            .filter(
                Appointment.staff_id == staff_id,
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED,
                    AppointmentStatus.NO_SHOW,
                ]),
                Appointment.appointment_datetime < end,
                Appointment.end_datetime > start,
            )
            .first()
            is not None
        )

    def count_upcoming(self, staff_id: int, now: datetime) -> int:
        return (
            self.db.query(func.count(Appointment.appointment_id))
            .filter(
                Appointment.staff_id == staff_id,
                Appointment.appointment_datetime >= now,
                Appointment.status.in_([
                    AppointmentStatus.REQUESTED,
                    AppointmentStatus.SCHEDULED,
                    AppointmentStatus.CONFIRMED,
                    AppointmentStatus.RESCHEDULED,
                ]),
            )
            .scalar()
            or 0
        )

    def find_busy_ranges(
        self,
        staff_ids: list[int],
        range_start: datetime,
        range_end: datetime,
    ) -> list[tuple[int, datetime, datetime]]:
        if not staff_ids:
            return []

        return (
            self.db.query(
                Appointment.staff_id,
                Appointment.appointment_datetime,
                Appointment.end_datetime,
            )
            .filter(
                Appointment.staff_id.in_(staff_ids),
                Appointment.status.notin_([
                    AppointmentStatus.CANCELLED,
                    AppointmentStatus.NO_SHOW,
                ]),
                Appointment.appointment_datetime < range_end,
                Appointment.end_datetime > range_start,
            )
            .all()
        )

    def save(self, appointment: Appointment) -> Appointment:
        self.db.add(appointment)
        self.db.flush()
        return appointment

    def _serialize_row(
        self,
        appointment: Appointment,
        patient: PatientProfile,
        user: User,
    ) -> dict[str, Any]:
        return {
            "appointment_id": appointment.appointment_id,
            "patient_id": appointment.patient_id,
            "patient_name": f"{user.first_name} {user.last_name}",
            "appointment_type": appointment.appointment_type.value,
            "appointment_datetime": appointment.appointment_datetime.isoformat(),
            "end_datetime": appointment.end_datetime.isoformat(),
            "status": appointment.status.value,
            "booking_method": appointment.booking_method.value,
            "location_or_channel": appointment.location_or_channel,
            "reason": appointment.reason,
            "staff_id": appointment.staff_id,
        }
