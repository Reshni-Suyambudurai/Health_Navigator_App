"""Campaign-based TCM tracker business logic."""

from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.models.appointment import AppointmentStatus, AppointmentType
from app.database.models.care_navigation_episode import EpisodeStatus, TriggerType
from app.database.models.checkin_escalation import CheckinEscalationStatus, CheckinEscalationType
from app.database.models.checkin_session import CheckinSessionStatus
from app.database.models.outreach_campaign import OutreachCampaign
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.database.repositories.navigator.tcm_tracker_repository import TcmTrackerRepository
from app.database.repositories.patientFHIR.patient_fhir_repository import PatientFHIRRepository


class TcmTrackerService:
    ALLOWED_ROLES = {RoleName.CARE_MANAGER, RoleName.TRANSITIONAL_CARE_NURSE}
    CATEGORIES = {
        "ACTIVE",
        "NEEDS_ATTENTION",
        "APPOINTMENT_ATTENTION",
        "REGULAR_APPOINTMENTS",
        "COMPLETE",
    }
    ACTIVE_EPISODE_STATUSES = {EpisodeStatus.OPEN, EpisodeStatus.IN_PROGRESS, EpisodeStatus.ON_HOLD}
    ACTIVE_ESCALATION_STATUSES = {
        CheckinEscalationStatus.OPEN,
        CheckinEscalationStatus.ASSIGNED,
        CheckinEscalationStatus.IN_PROGRESS,
    }
    BOOKED_APPOINTMENT_STATUSES = {
        AppointmentStatus.REQUESTED,
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
    }
    APPOINTMENT_ATTENTION_STATUSES = {
        AppointmentStatus.REQUESTED,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
        AppointmentStatus.RESCHEDULED,
    }
    ROUTINE_TRACKING_STATUSES = {
        AppointmentStatus.REQUESTED,
        AppointmentStatus.SCHEDULED,
        AppointmentStatus.CONFIRMED,
        AppointmentStatus.RESCHEDULED,
    }

    def __init__(self, db: Session, fhir_db: Session | None = None):
        self.repository = TcmTrackerRepository(db)
        self.fhir_repository = PatientFHIRRepository(fhir_db) if fhir_db is not None else None

    def list_campaigns(self, user_id: int) -> dict[str, Any]:
        user, staff, role = self._context(user_id)
        campaigns = self.repository.list_campaigns(user.organization_id)
        return {
            "scope": self._scope(role.role_name),
            "campaigns": [self._campaign_result(campaign) for campaign in campaigns],
        }

    def get_summary(
        self,
        user_id: int,
        campaign_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        snapshot = self._snapshot(user_id, campaign_id, from_date, to_date)
        records = snapshot["records"]
        eligible_workflows = [state for record in records for state in record["workflows"] if state["eligible"]]
        completed_workflows = [state for state in eligible_workflows if state["complete"]]
        categories = {category: 0 for category in self.CATEGORIES}
        for record in records:
            categories[record["category"]] += 1
        return {
            "scope": snapshot["scope"],
            "eligible_patients": len(records),
            "active_episodes": sum(record["episode_status"] in self.ACTIVE_EPISODE_STATUSES for record in records),
            "workflow_completion_rate": self._percentage(len(completed_workflows), len(eligible_workflows)),
            "overdue_activities": sum(
                state["eligible"] and state["overdue"] and not state["complete"]
                for record in records
                for state in record["workflows"]
            ),
            "patient_categories": {
                "active": categories["ACTIVE"],
                "needs_attention": categories["NEEDS_ATTENTION"],
                "appointment_attention": categories["APPOINTMENT_ATTENTION"],
                "regular_appointments": categories["REGULAR_APPOINTMENTS"],
                "complete": categories["COMPLETE"],
            },
        }

    def get_workflow_progress(
        self,
        user_id: int,
        campaign_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        snapshot = self._snapshot(user_id, campaign_id, from_date, to_date)
        grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
        for record in snapshot["records"]:
            for state in record["workflows"]:
                if state["eligible"]:
                    grouped[(record["campaign_id"], state["workflow_id"])].append(state)
        workflows = []
        for campaign in snapshot["campaigns"]:
            for workflow, template in snapshot["workflows_by_campaign"].get(campaign.campaign_id, []):
                states = grouped.get((campaign.campaign_id, workflow.workflow_id), [])
                eligible = len(states)
                checkin_completed = sum(state["checkin_completed"] for state in states)
                appointment_required = bool(template and template.appointment_required)
                appointment_eligible = sum(state["appointment_eligible"] for state in states)
                appointment_booked = sum(state["appointment_booked"] for state in states)
                appointment_completed = sum(state["appointment_completed"] for state in states)
                workflows.append({
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.campaign_name,
                    "workflow_id": workflow.workflow_id,
                    "workflow_name": workflow.step_name,
                    "step_order": workflow.step_order,
                    "appointment_required": appointment_required,
                    "eligible_count": eligible,
                    "checkin": {
                        "completed": checkin_completed,
                        "pending": eligible - checkin_completed,
                        "completion_percentage": self._percentage(checkin_completed, eligible),
                    },
                    "appointment": ({
                        "eligible": appointment_eligible,
                        "booked": appointment_booked,
                        "completed": appointment_completed,
                        "pending_booking": appointment_eligible - appointment_booked,
                        "pending_completion": appointment_booked - appointment_completed,
                        "booking_percentage": self._percentage(appointment_booked, appointment_eligible),
                        "completion_percentage": self._percentage(appointment_completed, appointment_booked),
                    } if appointment_required else None),
                })
        return {"scope": snapshot["scope"], "workflows": workflows}

    def list_patients(
        self,
        user_id: int,
        category: str,
        campaign_id: int | None = None,
        page: int = 1,
        page_size: int = 10,
        from_date: date | None = None,
        to_date: date | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        normalized_category = category.upper()
        if normalized_category not in self.CATEGORIES:
            raise ValidationException("Unsupported TCM patient category", "INVALID_TCM_CATEGORY")
        if page < 1 or page_size < 1 or page_size > 100:
            raise ValidationException("Invalid pagination values", "INVALID_PAGINATION")
        snapshot = self._snapshot(user_id, campaign_id, from_date, to_date)
        records = [record for record in snapshot["records"] if record["category"] == normalized_category]
        if search:
            normalized_search = search.strip().lower()
            records = [record for record in records if normalized_search in record["patient_name"].lower()]
        total = len(records)
        start = (page - 1) * page_size
        patients = [self._patient_result(record) for record in records[start:start + page_size]]
        return {
            "scope": snapshot["scope"],
            "category": normalized_category,
            "total": total,
            "page": page,
            "page_size": page_size,
            "patients": patients,
        }

    def get_patient_details(self, user_id: int, campaign_id: int, episode_id: int) -> dict[str, Any]:
        snapshot = self._snapshot(user_id, campaign_id, None, None)
        record = next((item for item in snapshot["records"] if item["episode_id"] == episode_id), None)
        if record is None:
            raise NotFoundException("TCM episode was not found", "TCM_EPISODE_NOT_FOUND")
        result = self._patient_result(record)
        result["workflows"] = [self._workflow_detail(state) for state in record["workflows"]]
        result["appointments"] = [self._appointment_result(item) for item in record["appointments"]]
        result["escalations"] = [self._escalation_result(item) for item in record["escalations"]]
        activity = []
        for state in record["workflows"]:
            if state["event"]:
                activity.append({"type": "OUTREACH", "label": state["workflow_name"], "timestamp": self._iso(state["event"].created_at)})
            if state["session"]:
                activity.append({"type": "CHECK_IN", "label": state["session"].session_status.value, "timestamp": self._iso(state["session"].updated_at or state["session"].created_at)})
        for appointment in record["appointments"]:
            activity.append({"type": "APPOINTMENT", "label": appointment.status.value, "timestamp": self._iso(appointment.updated_at or appointment.created_at)})
        result["recent_activity"] = sorted(activity, key=lambda item: item["timestamp"] or "", reverse=True)
        return result

    def _snapshot(
        self,
        user_id: int,
        campaign_id: int | None,
        from_date: date | None,
        to_date: date | None,
    ) -> dict[str, Any]:
        user, staff, role = self._context(user_id)
        campaigns = self.repository.list_campaigns(user.organization_id)
        if campaign_id is not None:
            campaigns = [campaign for campaign in campaigns if campaign.campaign_id == campaign_id]
            if not campaigns:
                raise NotFoundException("TCM campaign was not found", "TCM_CAMPAIGN_NOT_FOUND")
        campaign_ids = [campaign.campaign_id for campaign in campaigns]
        workflow_rows = self.repository.list_workflows(campaign_ids)
        workflows_by_campaign: dict[int, list] = defaultdict(list)
        for workflow_row in workflow_rows:
            workflow, _ = workflow_row
            workflows_by_campaign[workflow.campaign_id].append(workflow_row)
        owner_staff_id = staff.staff_id if role.role_name == RoleName.TRANSITIONAL_CARE_NURSE else None
        start, end = self._date_bounds(from_date, to_date)
        episode_records = []
        for campaign in campaigns:
            for episode in self.repository.list_eligible_episodes(campaign, owner_staff_id, start, end):
                episode_records.append((campaign, episode))
        episode_ids = list({episode.episode_id for _, episode in episode_records})
        events = self.repository.list_events(campaign_ids, episode_ids)
        event_ids = [event.outreach_event_id for event in events]
        sessions = self.repository.list_sessions(event_ids)
        appointments = self.repository.list_appointments(episode_ids)
        session_ids = [session.checkin_session_id for session in sessions]
        escalations = self.repository.list_escalations(session_ids)
        event_map = {(event.campaign_id, event.workflow_id, event.episode_id): event for event in events}
        session_by_event = {session.outreach_event_id: session for session in sessions}
        appointment_by_id = {appointment.appointment_id: appointment for appointment in appointments}
        appointments_by_episode: dict[int, list] = defaultdict(list)
        for appointment in appointments:
            appointments_by_episode[appointment.episode_id].append(appointment)
        escalation_by_session: dict[int, list] = defaultdict(list)
        for escalation_row in escalations:
            escalation_by_session[escalation_row[0].checkin_session_id].append(escalation_row)
        now = datetime.now(UTC).replace(tzinfo=None)
        records = []
        for campaign, episode in episode_records:
            states = []
            previous_complete = True
            for workflow, template in workflows_by_campaign.get(campaign.campaign_id, []):
                due_at = episode.opened_at + timedelta(hours=workflow.trigger_offset_hours)
                eligible = previous_complete and due_at <= now
                event = event_map.get((campaign.campaign_id, workflow.workflow_id, episode.episode_id))
                session = session_by_event.get(event.outreach_event_id) if event else None
                appointment = appointment_by_id.get(session.appointment_id) if session and session.appointment_id else None
                checkin_completed = bool(session and session.session_status == CheckinSessionStatus.COMPLETED)
                appointment_required = bool(template and template.appointment_required)
                appointment_eligible = appointment_required and checkin_completed
                appointment_booked = appointment_eligible and bool(
                    appointment and appointment.status in self.BOOKED_APPOINTMENT_STATUSES | {AppointmentStatus.COMPLETED}
                )
                appointment_completed = appointment_eligible and bool(
                    appointment and appointment.status == AppointmentStatus.COMPLETED
                )
                complete = checkin_completed and (not appointment_required or appointment_completed)
                states.append({
                    "workflow_id": workflow.workflow_id,
                    "workflow_name": workflow.step_name,
                    "step_order": workflow.step_order,
                    "appointment_required": appointment_required,
                    "eligible": eligible,
                    "due_at": due_at,
                    "overdue": due_at < now,
                    "event": event,
                    "session": session,
                    "appointment": appointment,
                    "checkin_completed": checkin_completed,
                    "appointment_eligible": appointment_eligible,
                    "appointment_booked": appointment_booked,
                    "appointment_completed": appointment_completed,
                    "complete": complete,
                })
                previous_complete = eligible and complete
            episode_appointments = appointments_by_episode.get(episode.episode_id, [])
            episode_escalations = [
                escalation
                for state in states
                if state["session"]
                for escalation in escalation_by_session.get(state["session"].checkin_session_id, [])
            ]
            records.append({
                "campaign_id": campaign.campaign_id,
                "campaign_name": campaign.campaign_name,
                "episode_id": episode.episode_id,
                "patient_id": episode.patient_id,
                "patient_name": f"{episode.first_name} {episode.last_name}".strip(),
                "external_fhir_patient_id": episode.external_fhir_patient_id,
                "condition": None,
                "discharge_date": episode.opened_at if episode.trigger_type == TriggerType.DISCHARGE else None,
                "episode_status": episode.episode_status,
                "closed_at": episode.closed_at,
                "owner_staff_id": episode.owner_staff_id,
                "workflows": states,
                "appointments": episode_appointments,
                "escalations": episode_escalations,
            })
        for record in records:
            record["category"] = self._category(record, now)
        self._add_conditions(records)
        return {
            "scope": self._scope(role.role_name),
            "campaigns": campaigns,
            "workflows_by_campaign": workflows_by_campaign,
            "records": records,
        }

    def _add_conditions(self, records: list[dict[str, Any]]) -> None:
        if self.fhir_repository is None:
            return
        fhir_ids = list({
            record["external_fhir_patient_id"]
            for record in records
            if record["external_fhir_patient_id"]
        })
        try:
            conditions = self.fhir_repository.get_primary_active_conditions(fhir_ids)
        except Exception:
            return
        for record in records:
            record["condition"] = conditions.get(record["external_fhir_patient_id"])

    def _category(self, record: dict[str, Any], now: datetime) -> str:
        if any(
            escalation.escalation_type == CheckinEscalationType.EMERGENCY
            and escalation.escalation_status in self.ACTIVE_ESCALATION_STATUSES
            for escalation, _, _, _ in record["escalations"]
        ):
            return "NEEDS_ATTENTION"
        if any(
            state["appointment_eligible"]
            and (
                state["appointment"] is None
                or state["appointment"].status in self.APPOINTMENT_ATTENTION_STATUSES
            )
            for state in record["workflows"]
        ):
            return "APPOINTMENT_ATTENTION"
        if any(
            appointment.appointment_type == AppointmentType.ROUTINE
            and appointment.status in self.ROUTINE_TRACKING_STATUSES
            and appointment.appointment_datetime >= now
            for appointment in record["appointments"]
        ):
            return "REGULAR_APPOINTMENTS"
        workflows = record["workflows"]
        if (
            record["episode_status"] in {EpisodeStatus.COMPLETED, EpisodeStatus.CLOSED}
            and workflows
            and all(state["complete"] for state in workflows)
        ):
            return "COMPLETE"
        return "ACTIVE"

    def _context(self, user_id: int):
        context = self.repository.find_context(user_id)
        if context is None:
            raise NotFoundException("Staff user was not found", "TCM_STAFF_NOT_FOUND")
        user, staff, role = context
        if user.status != UserStatus.ACTIVE or role.role_name not in self.ALLOWED_ROLES:
            raise AuthorizationException("TCM tracker access is not allowed", "TCM_TRACKER_ACCESS_DENIED")
        return user, staff, role

    @staticmethod
    def _scope(role_name: RoleName) -> str:
        return "ASSIGNED_PATIENTS" if role_name == RoleName.TRANSITIONAL_CARE_NURSE else "ORGANIZATION"

    @staticmethod
    def _campaign_result(campaign: OutreachCampaign) -> dict[str, Any]:
        return {
            "campaign_id": campaign.campaign_id,
            "campaign_name": campaign.campaign_name,
            "status": campaign.status.value,
        }

    @staticmethod
    def _date_bounds(from_date: date | None, to_date: date | None):
        if from_date and to_date and from_date > to_date:
            raise ValidationException("From date must be on or before to date", "INVALID_TCM_DATE_RANGE")
        start = datetime.combine(from_date, time.min) if from_date else None
        end = datetime.combine(to_date + timedelta(days=1), time.min) if to_date else None
        return start, end

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float:
        return round((numerator / denominator) * 100, 2) if denominator else 0.0

    def _patient_result(self, record: dict[str, Any]) -> dict[str, Any]:
        current = next((state for state in record["workflows"] if state["eligible"] and not state["complete"]), None)
        latest_escalation = record["escalations"][0] if record["escalations"] else None
        checkin_appointment = next(
            (item for item in record["appointments"] if item.appointment_type == AppointmentType.CHECK_IN),
            None,
        )
        routine_appointment = next(
            (item for item in record["appointments"] if item.appointment_type == AppointmentType.ROUTINE),
            None,
        )
        return {
            "campaign_id": record["campaign_id"],
            "campaign_name": record["campaign_name"],
            "episode_id": record["episode_id"],
            "patient_id": record["patient_id"],
            "patient_name": record["patient_name"],
            "condition": record["condition"],
            "discharge_date": self._iso(record["discharge_date"]),
            "episode_status": record["episode_status"].value,
            "category": record["category"],
            "current_workflow": current["workflow_name"] if current else None,
            "checkin_status": current["session"].session_status.value if current and current["session"] else "PENDING",
            "appointment_status": (
                checkin_appointment.status.value if checkin_appointment else
                ("NOT_REQUIRED" if current and not current["appointment_required"] else "NOT_YET_BOOKED")
            ),
            "next_due_at": self._iso(current["due_at"]) if current else None,
            "checkin_session_id": current["session"].checkin_session_id if current and current["session"] else None,
            "appointment": self._appointment_result(checkin_appointment or routine_appointment),
            "escalation": self._escalation_result(latest_escalation),
            "completed_at": self._iso(record["closed_at"]),
        }

    def _workflow_detail(self, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "workflow_id": state["workflow_id"],
            "workflow_name": state["workflow_name"],
            "step_order": state["step_order"],
            "eligible": state["eligible"],
            "due_at": self._iso(state["due_at"]),
            "complete": state["complete"],
            "appointment_required": state["appointment_required"],
            "checkin_session_id": state["session"].checkin_session_id if state["session"] else None,
            "checkin_status": state["session"].session_status.value if state["session"] else None,
            "checkin_completed_at": self._iso(state["session"].completed_at) if state["session"] else None,
            "appointment": self._appointment_result(state["appointment"]),
        }

    @staticmethod
    def _appointment_result(appointment) -> dict[str, Any] | None:
        if appointment is None:
            return None
        return {
            "appointment_id": appointment.appointment_id,
            "appointment_type": appointment.appointment_type.value,
            "status": appointment.status.value,
            "staff_id": appointment.staff_id,
            "appointment_datetime": TcmTrackerService._iso(appointment.appointment_datetime),
            "created_at": TcmTrackerService._iso(appointment.created_at),
            "location_or_channel": appointment.location_or_channel,
        }

    @staticmethod
    def _escalation_result(escalation_row) -> dict[str, Any] | None:
        if escalation_row is None:
            return None
        escalation, assignment, _, user = escalation_row
        return {
            "checkin_escalation_id": escalation.checkin_escalation_id,
            "type": escalation.escalation_type.value,
            "status": escalation.escalation_status.value,
            "reason": escalation.escalation_reason,
            "assigned_staff": (
                f"{user.first_name} {user.last_name}".strip() if user else None
            ),
            "assigned_at": TcmTrackerService._iso(assignment.assigned_at) if assignment else None,
            "action_taken": escalation.action_taken,
            "resolution_notes": escalation.resolution_notes,
        }

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return value.isoformat() if value else None