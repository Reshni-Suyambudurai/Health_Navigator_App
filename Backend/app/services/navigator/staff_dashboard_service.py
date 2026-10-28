"""Staff-specific pharmacist and social-worker dashboard analytics."""

from calendar import monthrange
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.database.repositories.navigator.staff_dashboard_repository import StaffDashboardRepository


class StaffDashboardService:
    ALLOWED_ROLES = {RoleName.PHARMACIST, RoleName.SOCIAL_WORKER}
    ALLOWED_PERIODS = {"TODAY", "THIS_MONTH"}

    def __init__(self, db: Session):
        self.repository = StaffDashboardRepository(db)

    def get_analytics(
        self,
        user_id: int,
        period: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        normalized_period = period.upper()
        if normalized_period not in self.ALLOWED_PERIODS:
            raise ValidationException(
                "Period must be TODAY or THIS_MONTH.",
                "INVALID_STAFF_DASHBOARD_PERIOD",
            )

        user, staff, role = self._context(user_id)
        start, end = self._period_bounds(normalized_period, from_date, to_date)
        escalations = self.repository.list_assigned_escalations(
            staff.staff_id,
            user.organization_id,
            start,
            end,
        )
        checkin_escalations = self.repository.list_checkin_escalations(
            staff.staff_id,
            user.organization_id,
            start,
            end,
        )
        appointments = self.repository.list_appointments(
            staff.staff_id,
            user.organization_id,
            start,
            end,
        )

        emergency_escalations = [
            item for item in escalations if item.escalation_type == "EMERGENCY"
        ]
        routine_escalations = [
            item for item in escalations if item.escalation_type != "EMERGENCY"
        ]
        checkin_emergency = [
            item for item in checkin_escalations if item.escalation_type == "EMERGENCY"
        ]
        checkin_routine = [
            item for item in checkin_escalations if item.escalation_type == "ROUTINE"
        ]

        return {
            "period": normalized_period,
            "from_date": from_date.isoformat() if from_date else None,
            "to_date": to_date.isoformat() if to_date else None,
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "role": role.role_name.value,
            "patients_escalated": len({item.patient_id for item in escalations}),
            "emergency_escalations": len(emergency_escalations),
            "routine_escalations": len(routine_escalations),
            "checkin_emergency_escalations": len(checkin_emergency),
            "checkin_routine_escalations": len(checkin_routine),
            "appointments_count": len(appointments),
            "details": {
                "assigned_escalations": [self._escalation_row(item) for item in escalations],
                "checkin_escalations": [self._checkin_row(item) for item in checkin_escalations],
                "appointments": [self._appointment_row(item) for item in appointments],
                "recent_emergency_escalations": [
                    self._escalation_row(item) for item in emergency_escalations[:5]
                ],
                "recent_emergency_checkins": [
                    self._checkin_row(item) for item in checkin_emergency[:5]
                ],
            },
        }

    def _context(self, user_id: int):
        result = self.repository.find_context(user_id)
        if not result:
            raise NotFoundException("Staff profile not found.", "STAFF_PROFILE_NOT_FOUND")
        user, staff, role = result
        if user.status != UserStatus.ACTIVE or role.role_name not in self.ALLOWED_ROLES:
            raise AuthorizationException(
                "Pharmacist or social worker access is required.",
                "STAFF_DASHBOARD_ACCESS_REQUIRED",
            )
        return user, staff, role

    @staticmethod
    def _period_bounds(
        period: str,
        from_date: date | None = None,
        to_date: date | None = None,
        now: datetime | None = None,
    ) -> tuple[datetime, datetime]:
        current = now or datetime.now(UTC).replace(tzinfo=None)
        if period == "TODAY":
            start = current.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, start + timedelta(days=1)

        if (from_date is None) != (to_date is None):
            raise ValidationException(
                "Both from date and to date are required.",
                "INCOMPLETE_STAFF_DASHBOARD_DATE_RANGE",
            )
        if from_date and to_date:
            if from_date > to_date:
                raise ValidationException(
                    "From date must be on or before to date.",
                    "INVALID_STAFF_DASHBOARD_DATE_RANGE",
                )
            return datetime.combine(from_date, time.min), datetime.combine(to_date + timedelta(days=1), time.min)

        start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_in_month = monthrange(start.year, start.month)[1]
        return start, start + timedelta(days=days_in_month)

    @staticmethod
    def _name(item) -> str:
        return f"{item.first_name} {item.last_name}".strip()

    def _escalation_row(self, item) -> dict[str, Any]:
        return {
            "patient": self._name(item),
            "patient_id": item.patient_id,
            "type": item.escalation_type,
            "priority": item.priority,
            "status": item.status,
            "reason": item.reason or "Not specified",
            "assigned_at": item.assigned_at.isoformat(),
        }

    def _checkin_row(self, item) -> dict[str, Any]:
        return {
            "patient": self._name(item),
            "patient_id": item.patient_id,
            "type": item.escalation_type,
            "status": item.status,
            "reason": item.reason or "Not specified",
            "response": getattr(item, "response_text", None) or "Not available",
            "trigger_source": item.trigger_source or "Not specified",
            "assigned_at": item.assigned_at.isoformat(),
        }

    def _appointment_row(self, item) -> dict[str, Any]:
        return {
            "patient": self._name(item),
            "type": item.appointment_type,
            "status": item.status,
            "date_time": item.appointment_datetime.isoformat(),
            "location_or_channel": item.location_or_channel or "Not specified",
        }
