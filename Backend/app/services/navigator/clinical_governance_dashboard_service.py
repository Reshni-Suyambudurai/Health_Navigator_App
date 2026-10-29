"""Clinical-governance analytics assembled from existing operational tables."""

from collections import Counter, defaultdict
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.models.escalation import EscalationStatus
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.database.repositories.navigator.clinical_governance_dashboard_repository import (
    ClinicalGovernanceDashboardRepository,
)


class ClinicalGovernanceDashboardService:
    VALID_PERIODS = {"today", "month", "custom"}

    def __init__(self, db: Session):
        self.repository = ClinicalGovernanceDashboardRepository(db)

    def get_analytics(
        self,
        user_id: int,
        period: str = "today",
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        user = self._context(user_id)
        start_at, end_at = self._date_range(period, start_date, end_date)
        hit_rows = self.repository.list_guardrail_hits(user.organization_id, start_at, end_at)
        rules = self.repository.list_rules()
        escalation_rows = self.repository.list_escalations(user.organization_id, start_at, end_at)
        escalation_ids = [row[0].escalation_id for row in escalation_rows]
        assignments = self.repository.list_assignments(escalation_ids)
        actions = self.repository.list_actions(escalation_ids)
        audit_rows = self.repository.list_audit_history(user.organization_id, start_at, end_at)

        hits = self._distinct_hits(hit_rows)
        escalations = self._distinct_escalations(escalation_rows)
        urgency_counts = Counter(self._value(row[0].hit_urgency_level) for row in hits)
        status_counts = Counter(self._value(row[0].status) for row in escalations)
        open_statuses = {"OPEN", "ASSIGNED", "IN_PROGRESS"}
        open_escalations = sum(count for status, count in status_counts.items() if status in open_statuses)

        actions_by_escalation: dict[int, list[Any]] = defaultdict(list)
        for action in actions:
            actions_by_escalation[action.escalation_id].append(action)
        assigned_ids = {assignment.escalation_id for assignment in assignments}
        documentation_rows = self._documentation_rows(
            escalations,
            actions_by_escalation,
            assigned_ids,
        )
        hits_by_rule = Counter(row[0].rule_id for row in hits)
        latest_hit_by_rule = {}
        for hit, *_ in hits:
            latest = latest_hit_by_rule.get(hit.rule_id)
            if latest is None or hit.created_at > latest:
                latest_hit_by_rule[hit.rule_id] = hit.created_at

        return {
            "generated_at": datetime.now(UTC).replace(tzinfo=None).isoformat(),
            "period": {
                "key": period,
                "start_date": start_at.date().isoformat(),
                "end_date": (end_at.date() - timedelta(days=1)).isoformat(),
            },
            "kpis": [
                self._metric("Emergency triggers", urgency_counts.get("EMERGENCY", 0), "critical"),
                self._metric("Same-day triggers", urgency_counts.get("SAME_DAY", 0), "warning"),
                self._metric("Routine triggers", urgency_counts.get("ROUTINE", 0)),
                self._metric("Open escalations", open_escalations, "critical"),
            ],
            "escalation_summary": {
                "metrics": [
                    self._metric("Emergency triggers", urgency_counts.get("EMERGENCY", 0), "critical"),
                    self._metric("Same-day triggers", urgency_counts.get("SAME_DAY", 0), "warning"),
                    self._metric("Routine triggers", urgency_counts.get("ROUTINE", 0)),
                    self._metric("Total escalations", len(escalations)),
                    self._metric("Open", status_counts.get("OPEN", 0), "critical"),
                    self._metric("In progress", status_counts.get("IN_PROGRESS", 0), "warning"),
                    self._metric(
                        "Resolved",
                        status_counts.get("RESOLVED", 0) + status_counts.get("CLOSED", 0),
                        "positive",
                    ),
                ],
            },
            "red_flag_outcomes": [self._red_flag_row(row) for row in hits],
            "rule_performance": [{
                "rule": rule.rule_name,
                "category": self._value(rule.rule_category),
                "urgency": self._value(rule.urgency_level),
                "action": self._value(rule.action_type),
                "status": self._value(rule.status),
                "trigger_count": hits_by_rule.get(rule.rule_id, 0),
                "last_triggered_at": self._iso(latest_hit_by_rule.get(rule.rule_id)),
            } for rule in rules],
            "documentation": documentation_rows,
            "audit_history": [self._audit_row(row) for row in audit_rows],
            "detection_accuracy": {
                "available": False,
                "message": (
                    "Detection accuracy requires reviewed expected-versus-actual test or audit results. "
                    "Guardrail hits alone cannot identify missed or incorrect triggers."
                ),
            },
        }

    def _context(self, user_id: int):
        result = self.repository.find_context(user_id)
        if not result:
            raise NotFoundException("Clinical governance user not found.", "GOVERNANCE_USER_NOT_FOUND")
        user, role = result
        if user.status != UserStatus.ACTIVE or role.role_name not in {
            RoleName.CLINICAL_GOVERNANCE,
            RoleName.SYSTEM_ADMIN,
        }:
            raise AuthorizationException(
                "Clinical governance access is required.",
                "GOVERNANCE_ACCESS_REQUIRED",
            )
        return user

    @classmethod
    def _date_range(
        cls,
        period: str,
        start_date: date | None,
        end_date: date | None,
    ) -> tuple[datetime, datetime]:
        if period not in cls.VALID_PERIODS:
            raise ValidationException("Invalid dashboard period.", "GOVERNANCE_PERIOD_INVALID")
        today = datetime.now(UTC).date()
        if period == "today":
            first_day = last_day = today
        elif period == "month":
            first_day, last_day = today.replace(day=1), today
        else:
            if start_date is None or end_date is None:
                raise ValidationException(
                    "Start and end dates are required for a custom range.",
                    "GOVERNANCE_DATES_REQUIRED",
                )
            if start_date > end_date:
                raise ValidationException(
                    "Start date cannot be after end date.",
                    "GOVERNANCE_DATE_RANGE_INVALID",
                )
            first_day, last_day = start_date, end_date
        return datetime.combine(first_day, time.min), datetime.combine(last_day + timedelta(days=1), time.min)

    @staticmethod
    def _distinct_hits(rows):
        return list({row[0].guardrail_hit_id: row for row in rows}.values())

    @staticmethod
    def _distinct_escalations(rows):
        return list({row[0].escalation_id: row for row in rows}.values())

    def _red_flag_row(self, row) -> dict[str, Any]:
        hit, rule, message, event = row
        return {
            "triggered_at": self._iso(hit.created_at),
            "rule": rule.rule_name,
            "patient_message": message.message_text,
            "urgency": self._value(hit.hit_urgency_level),
            "action_taken": self._value(hit.action_taken),
            "emergency_instruction_sent": self._yes_no(event.emergency_instruction_sent) if event else "Not applicable",
            "care_team_notified": self._yes_no(event.notified_care_team) if event else "Not applicable",
            "event_status": self._value(event.event_status) if event else "Not applicable",
        }

    def _documentation_rows(self, rows, actions_by_escalation, assigned_ids) -> list[dict[str, Any]]:
        result = []
        for escalation, _, patient_user, _ in rows:
            actions = actions_by_escalation.get(escalation.escalation_id, [])
            has_notes = any((action.action_notes or "").strip() for action in actions)
            is_resolved = self._value(escalation.status) in {"RESOLVED", "CLOSED"}
            resolution_complete = not is_resolved or bool(escalation.resolved_at)
            issues = []
            if escalation.escalation_id not in assigned_ids:
                issues.append("No active assignment")
            if not actions:
                issues.append("No staff action")
            if not has_notes:
                issues.append("Missing action notes")
            if not resolution_complete:
                issues.append("Missing resolution timestamp")
            if not is_resolved:
                issues.append("Unresolved")
            if issues:
                result.append({
                    "escalation_id": escalation.escalation_id,
                    "patient": f"{patient_user.first_name} {patient_user.last_name}".strip(),
                    "type": self._value(escalation.escalation_type),
                    "priority": self._value(escalation.priority),
                    "status": self._value(escalation.status),
                    "action_count": len(actions),
                    "documentation_issues": ", ".join(issues),
                    "created_at": self._iso(escalation.created_at),
                })
        return result

    def _audit_row(self, row) -> dict[str, Any]:
        audit, actor = row
        return {
            "created_at": self._iso(audit.created_at),
            "action": audit.action,
            "resource_type": audit.resource_type,
            "resource_id": audit.resource_id,
            "actor": f"{actor.first_name} {actor.last_name}".strip() if actor else "System",
            "details": audit.details or "No details recorded",
        }

    @staticmethod
    def _metric(label: str, value: int, tone: str = "default") -> dict[str, Any]:
        return {"label": label, "value": value, "tone": tone}

    @staticmethod
    def _value(value: Any) -> str:
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _iso(value: Any) -> str | None:
        return value.isoformat() if value is not None else None

    @staticmethod
    def _yes_no(value: bool) -> str:
        return "Yes" if value else "No"