"""Care-manager analytics assembled from existing operational tables."""

from collections import Counter
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, NotFoundException
from app.database.models.appointment import AppointmentStatus
from app.database.models.appointment_action import AppointmentResolutionStatus
from app.database.models.care_navigation_episode import EpisodeStatus
from app.database.models.checkin_session import CheckinSessionStatus
from app.database.models.escalation import EscalationStatus
from app.database.models.follow_up_task import FollowUpTaskStatus
from app.database.models.outreach_event import DeliveryStatus, OutreachEventStatus
from app.database.models.patient_profile import RiskTier
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.database.repositories.navigator.care_manager_dashboard_repository import (
    CareManagerDashboardRepository,
)


class CareManagerDashboardService:
    def __init__(self, db: Session):
        self.repository = CareManagerDashboardRepository(db)

    def get_analytics(self, user_id: int) -> dict[str, Any]:
        user, staff = self._context(user_id)
        now = datetime.now(UTC).replace(tzinfo=None)
        assigned = self.repository.list_assigned_episodes(staff.staff_id)
        enrollments = self.repository.list_enrollments(user.organization_id)
        episodes = self.repository.list_episodes(user.organization_id)
        appointment_rows = self.repository.list_appointments(user.organization_id)
        appointment_actions = self.repository.list_appointment_actions(user.organization_id)
        outreach_rows = self.repository.list_outreach(user.organization_id)
        checkins = self.repository.list_checkins(user.organization_id)
        escalation_rows = self.repository.list_escalations(user.organization_id)
        escalation_ids = [row[0].escalation_id for row in escalation_rows]
        assignments = self.repository.list_assignments(escalation_ids)
        escalation_actions = self.repository.list_escalation_actions(escalation_ids)
        follow_up_rows = self.repository.list_follow_ups(staff.staff_id)

        active_episode_statuses = {EpisodeStatus.OPEN, EpisodeStatus.IN_PROGRESS, EpisodeStatus.ON_HOLD}
        open_escalation_statuses = {
            EscalationStatus.OPEN,
            EscalationStatus.ASSIGNED,
            EscalationStatus.IN_PROGRESS,
        }
        incomplete_task_statuses = {FollowUpTaskStatus.OPEN, FollowUpTaskStatus.IN_PROGRESS}
        active_assigned = [row for row in assigned if row[0].status in active_episode_statuses]
        open_escalations = [row for row in escalation_rows if row[0].status in open_escalation_statuses]
        tasks = [row[0] for row in follow_up_rows]
        appointments = appointment_rows
        outreach_events = [row[0] for row in outreach_rows]

        appointment_counts = self._counts(appointments, "status")
        delivery_counts = self._counts(outreach_events, "delivery_status")
        event_counts = self._counts(outreach_events, "event_status")
        checkin_counts = self._counts(checkins, "session_status")
        enrollment_counts = self._counts(enrollments, "enrollment_status")
        episode_counts = self._counts(episodes, "status")
        task_counts = self._counts(tasks, "status")
        assigned_ids = {item.escalation_id for item in assignments}
        action_ids = {item.escalation_id for item in escalation_actions}
        latest_actions = self._latest_appointment_actions(appointment_actions)

        due_today = sum(
            1 for task in tasks
            if task.status in incomplete_task_statuses and task.due_at and task.due_at.date() == now.date()
        )
        overdue = sum(
            1 for task in tasks
            if task.status in incomplete_task_statuses and task.due_at and task.due_at < now
        )
        high_risk_rows = []
        high_risk_patient_ids = set()
        for row in active_assigned:
            patient_id = row[1].patient_id
            if (
                row[1].risk_tier in {RiskTier.HIGH, RiskTier.CRITICAL}
                and patient_id not in high_risk_patient_ids
            ):
                high_risk_patient_ids.add(patient_id)
                high_risk_rows.append(row)
        overdue_follow_up_rows = [
            row
            for row in follow_up_rows
            if row[0].status in incomplete_task_statuses
            and row[0].due_at
            and row[0].due_at < now
        ]
        follow_up_required = sum(
            1 for action in appointment_actions
            if action.follow_up_required
            or action.resolution_status == AppointmentResolutionStatus.FOLLOW_UP_REQUIRED
        )
        completed_tasks = task_counts.get(FollowUpTaskStatus.COMPLETED.value, 0)
        completion_eligible_tasks = sum(
            count
            for status, count in task_counts.items()
            if status != FollowUpTaskStatus.CANCELLED.value
        )
        resolved = [row[0] for row in escalation_rows if row[0].resolved_at]

        return {
            "generated_at": now.isoformat(),
            "dashboard": {
                "metrics": [
                    self._metric("Active care episodes", len(active_assigned)),
                    self._metric("High-risk patients", len(high_risk_rows), "warning"),
                    self._metric("Open escalations", len(open_escalations), "critical"),
                    self._metric("Overdue follow-ups", overdue, "warning"),
                ],
                "rows": [],
                "detail_groups": {
                    "active_care_episodes": [{
                        "patient": self._name(row[3]),
                        "risk_tier": row[1].risk_tier.value,
                        "enrollment_status": row[2].enrollment_status.value,
                        "episode_type": row[0].episode_type.value,
                        "episode_status": row[0].status.value,
                        "opened_at": row[0].opened_at.isoformat(),
                        "duration": f"{max((now - row[0].opened_at).days, 0)} days",
                    } for row in active_assigned],
                    "high_risk_patients": [{
                        "patient": self._name(row[3]),
                        "risk_tier": row[1].risk_tier.value,
                        "enrollment_status": row[2].enrollment_status.value,
                        "episode_type": row[0].episode_type.value,
                        "episode_status": row[0].status.value,
                        "duration": f"{max((now - row[0].opened_at).days, 0)} days",
                    } for row in high_risk_rows],
                    "open_escalations": [{
                        "patient": self._name(row[2]),
                        "type": row[0].escalation_type.value,
                        "priority": row[0].priority.value,
                        "status": row[0].status.value,
                        "assigned": "Yes" if row[0].escalation_id in assigned_ids else "No",
                        "guardrail_urgency": row[3].hit_urgency_level.value if row[3] else "Not linked",
                        "created_at": row[0].created_at.isoformat(),
                    } for row in open_escalations],
                    "overdue_follow_ups": [{
                        "patient": self._name(row[2]),
                        "title": row[0].title,
                        "task_type": row[0].task_type.value,
                        "priority": row[0].priority.value,
                        "status": row[0].status.value,
                        "due_at": row[0].due_at.isoformat(),
                        "linked_case": (
                            f"Escalation {row[0].escalation_id}" if row[0].escalation_id
                            else f"Appointment {row[0].appointment_id}" if row[0].appointment_id
                            else "General follow-up"
                        ),
                    } for row in overdue_follow_up_rows],
                },
            },
            "caseload": {
                "metrics": [
                    self._metric("Assigned patients", len({row[1].patient_id for row in active_assigned})),
                    self._metric("High risk", sum(1 for row in active_assigned if row[1].risk_tier == RiskTier.HIGH), "warning"),
                    self._metric("Critical risk", sum(1 for row in active_assigned if row[1].risk_tier == RiskTier.CRITICAL), "critical"),
                ],
                "rows": [{
                    "patient": self._name(row[3]),
                    "risk_tier": row[1].risk_tier.value,
                    "enrollment_status": row[2].enrollment_status.value,
                    "episode_status": row[0].status.value,
                    "episode_type": row[0].episode_type.value,
                    "duration": f"{max((now - row[0].opened_at).days, 0)} days",
                } for row in active_assigned],
            },
            "appointments": {
                "metrics": [
                    self._metric("Upcoming", sum(
                        1 for item in appointments
                        if item.appointment_datetime >= now
                            and item.status in {
                                AppointmentStatus.REQUESTED.value,
                                AppointmentStatus.SCHEDULED.value,
                                AppointmentStatus.CONFIRMED.value,
                            }
                        )),
                    self._metric("Completed", appointment_counts.get("COMPLETED", 0), "positive"),
                    self._metric("Cancelled", appointment_counts.get("CANCELLED", 0)),
                    self._metric("Rescheduled", appointment_counts.get("RESCHEDULED", 0)),
                    self._metric("No-show", appointment_counts.get("NO_SHOW", 0), "warning"),
                ],
                "rows": [{
                    "patient": f"{row.first_name} {row.last_name}".strip(),
                    "appointment_type": row.appointment_type,
                    "date_time": row.appointment_datetime.isoformat(),
                    "status": row.status,
                    "channel": row.location_or_channel or "Not specified",
                    "latest_resolution": (
                        latest_actions[row.appointment_id].resolution_status.value
                        if row.appointment_id in latest_actions else "NO_ACTION"
                    ),
                } for row in appointment_rows],
            },
            "outreach": {
                "metrics": [
                    self._metric("Scheduled", event_counts.get("PENDING", 0)),
                    self._metric("Delivered", delivery_counts.get("DELIVERED", 0), "positive"),
                    self._metric("Failed", delivery_counts.get("FAILED", 0), "critical"),
                    self._metric("Responded", delivery_counts.get("RESPONDED", 0), "positive"),
                    self._metric("Completed", event_counts.get("COMPLETED", 0), "positive"),
                    self._metric("Check-ins completed", checkin_counts.get(CheckinSessionStatus.COMPLETED.value, 0)),
                    self._metric(
                        "Check-ins expired",
                        checkin_counts.get("EXPIRED", 0)
                        + checkin_counts.get(CheckinSessionStatus.ABANDONED.value, 0),
                        "warning",
                    ),
                    self._metric("Check-in responses", self.repository.count_checkin_responses(user.organization_id)),
                ],
                "rows": [{
                    "patient": self._name(row[4]),
                    "campaign": row[1].campaign_name,
                    "workflow": row[2].step_name,
                    "channel": row[0].channel.value,
                    "delivery": row[0].delivery_status.value,
                    "status": row[0].event_status.value,
                    "scheduled_at": row[0].scheduled_at.isoformat(),
                } for row in outreach_rows],
            },
            "escalations": {
                "metrics": [
                    self._metric("Open cases", len(open_escalations), "critical"),
                    *[
                        self._metric(f"{priority.title()} priority", count)
                        for priority, count in sorted(self._counts([row[0] for row in open_escalations], "priority").items())
                    ],
                    self._metric("Unassigned cases", sum(1 for row in open_escalations if row[0].escalation_id not in assigned_ids), "warning"),
                    self._metric("Average resolution time", f"{self._average_resolution_hours(resolved)} hrs"),
                    self._metric("Pending actions", sum(1 for row in open_escalations if row[0].escalation_id not in action_ids)),
                ],
                "rows": [{
                    "patient": self._name(row[2]),
                    "type": row[0].escalation_type.value,
                    "priority": row[0].priority.value,
                    "status": row[0].status.value,
                    "assigned": "Yes" if row[0].escalation_id in assigned_ids else "No",
                    "guardrail_urgency": row[3].hit_urgency_level.value if row[3] else "Not linked",
                    "created_at": row[0].created_at.isoformat(),
                } for row in escalation_rows],
            },
            "follow_up": {
                "metrics": [
                    self._metric("Tasks due today", due_today),
                    self._metric("Overdue tasks", overdue, "warning"),
                    self._metric("Follow-up-required cases", follow_up_required),
                    self._metric("Task completion rate", f"{self._percentage(completed_tasks, completion_eligible_tasks)}%", "positive"),
                ],
                "rows": [{
                    "patient": self._name(row[2]),
                    "title": row[0].title,
                    "task_type": row[0].task_type.value,
                    "priority": row[0].priority.value,
                    "status": row[0].status.value,
                    "due_at": row[0].due_at.isoformat() if row[0].due_at else "No due date",
                    "linked_case": (
                        f"Escalation {row[0].escalation_id}" if row[0].escalation_id
                        else f"Appointment {row[0].appointment_id}" if row[0].appointment_id
                        else "General follow-up"
                    ),
                } for row in follow_up_rows],
            },
            "program_performance": {
                "metrics": [
                    *[
                        self._metric(f"{status.title()} enrollments", count)
                        for status, count in sorted(enrollment_counts.items())
                    ],
                    self._metric("Completed episodes", episode_counts.get("COMPLETED", 0)),
                    self._metric(
                        "Outreach response rate",
                        f"{self._percentage(delivery_counts.get('RESPONDED', 0), delivery_counts.get('DELIVERED', 0) + delivery_counts.get('RESPONDED', 0))}%",
                        "positive",
                    ),
                    self._metric(
                        "Appointment completion rate",
                        f"{self._percentage(appointment_counts.get('COMPLETED', 0), sum(
                            appointment_counts.get(status, 0)
                            for status in ('COMPLETED', 'CANCELLED', 'NO_SHOW', 'RESCHEDULED')
                        ))}%",
                        "positive",
                    ),
                ],
                "rows": [],
            },
        }

    def _context(self, user_id: int):
        result = self.repository.find_context(user_id)
        if not result:
            raise NotFoundException("Care manager profile not found.", "CARE_MANAGER_NOT_FOUND")
        user, staff, role = result
        if user.status != UserStatus.ACTIVE or role.role_name != RoleName.CARE_MANAGER:
            raise AuthorizationException("Care manager access is required.", "CARE_MANAGER_ACCESS_REQUIRED")
        return user, staff

    @staticmethod
    def _metric(label: str, value: Any, tone: str = "default") -> dict[str, Any]:
        return {"label": label, "value": value, "tone": tone}

    @staticmethod
    def _name(user) -> str:
        return f"{user.first_name} {user.last_name}".strip()

    @staticmethod
    def _counts(items, attribute: str) -> dict[str, int]:
        values = (getattr(item, attribute) for item in items)
        return dict(Counter(value.value if hasattr(value, "value") else value for value in values))

    @staticmethod
    def _latest_appointment_actions(actions):
        latest = {}
        for action in actions:
            current = latest.get(action.appointment_id)
            if current is None or action.created_at > current.created_at:
                latest[action.appointment_id] = action
        return latest

    @staticmethod
    def _average_resolution_hours(escalations) -> float:
        hours = [(item.resolved_at - item.created_at).total_seconds() / 3600 for item in escalations]
        return round(sum(hours) / len(hours), 1) if hours else 0

    @staticmethod
    def _percentage(numerator: int, denominator: int) -> float:
        return round(numerator / denominator * 100, 1) if denominator else 0
