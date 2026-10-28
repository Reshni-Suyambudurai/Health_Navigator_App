"""Database access for staff-specific dashboard analytics."""

from datetime import datetime

from sqlalchemy import String, cast
from sqlalchemy.orm import Session

from app.database.models.appointment import Appointment
from app.database.models.checkin_escalation import CheckinEscalation
from app.database.models.checkin_response import CheckinResponse
from app.database.models.checkin_session import CheckinSession
from app.database.models.escalation import Escalation
from app.database.models.escalation_assignment import EscalationAssignment
from app.database.models.patient_profile import PatientProfile
from app.database.models.role import Role
from app.database.models.staff_profile import StaffProfile
from app.database.models.user import User


class StaffDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_context(self, user_id: int):
        return (
            self.db.query(User, StaffProfile, Role)
            .join(StaffProfile, StaffProfile.user_id == User.user_id)
            .join(Role, Role.role_id == User.role_id)
            .filter(User.user_id == user_id)
            .first()
        )

    def list_assigned_escalations(self, staff_id: int, organization_id: int, start: datetime, end: datetime):
        return (
            self.db.query(
                Escalation.escalation_id.label("escalation_id"),
                Escalation.patient_id.label("patient_id"),
                cast(Escalation.escalation_type, String).label("escalation_type"),
                cast(Escalation.priority, String).label("priority"),
                cast(Escalation.status, String).label("status"),
                Escalation.reason.label("reason"),
                Escalation.created_at.label("created_at"),
                EscalationAssignment.assigned_at.label("assigned_at"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
            )
            .join(EscalationAssignment, EscalationAssignment.escalation_id == Escalation.escalation_id)
            .join(PatientProfile, PatientProfile.patient_id == Escalation.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                EscalationAssignment.assigned_to_staff_id == staff_id,
                EscalationAssignment.is_active.is_(True),
                EscalationAssignment.assigned_at >= start,
                EscalationAssignment.assigned_at < end,
                User.organization_id == organization_id,
            )
            .order_by(EscalationAssignment.assigned_at.desc())
            .all()
        )

    def list_checkin_escalations(self, staff_id: int, organization_id: int, start: datetime, end: datetime):
        return (
            self.db.query(
                CheckinEscalation.checkin_escalation_id.label("checkin_escalation_id"),
                CheckinSession.patient_id.label("patient_id"),
                cast(CheckinEscalation.escalation_type, String).label("escalation_type"),
                cast(CheckinEscalation.escalation_status, String).label("status"),
                CheckinEscalation.escalation_reason.label("reason"),
                CheckinResponse.answer_text.label("response_text"),
                CheckinEscalation.trigger_source.label("trigger_source"),
                CheckinEscalation.assigned_at.label("assigned_at"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
            )
            .join(CheckinSession, CheckinSession.checkin_session_id == CheckinEscalation.checkin_session_id)
            .outerjoin(CheckinResponse, CheckinResponse.response_id == CheckinEscalation.response_id)
            .join(PatientProfile, PatientProfile.patient_id == CheckinSession.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                CheckinEscalation.assigned_to_staff_id == staff_id,
                CheckinEscalation.assigned_at >= start,
                CheckinEscalation.assigned_at < end,
                User.organization_id == organization_id,
            )
            .order_by(CheckinEscalation.assigned_at.desc())
            .all()
        )

    def list_appointments(self, staff_id: int, organization_id: int, start: datetime, end: datetime):
        return (
            self.db.query(
                Appointment.appointment_id.label("appointment_id"),
                Appointment.patient_id.label("patient_id"),
                cast(Appointment.appointment_type, String).label("appointment_type"),
                cast(Appointment.status, String).label("status"),
                Appointment.appointment_datetime.label("appointment_datetime"),
                Appointment.location_or_channel.label("location_or_channel"),
                User.first_name.label("first_name"),
                User.last_name.label("last_name"),
            )
            .join(PatientProfile, PatientProfile.patient_id == Appointment.patient_id)
            .join(User, User.user_id == PatientProfile.user_id)
            .filter(
                Appointment.staff_id == staff_id,
                Appointment.appointment_datetime >= start,
                Appointment.appointment_datetime < end,
                User.organization_id == organization_id,
            )
            .order_by(Appointment.appointment_datetime.asc())
            .all()
        )
