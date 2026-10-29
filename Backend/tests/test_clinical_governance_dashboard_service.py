import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException, ValidationException
from app.database.models.clinical_guardrail_rule import (
    GuardrailActionType,
    RuleCategory,
    RuleStatus,
    UrgencyLevel,
)
from app.database.models.conversation_guardrail_hit import (
    GuardrailActionTaken,
    GuardrailHitUrgencyLevel,
)
from app.database.models.escalation import EscalationPriority, EscalationStatus, EscalationType
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.services.navigator.clinical_governance_dashboard_service import (
    ClinicalGovernanceDashboardService,
)


class ClinicalGovernanceDashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = ClinicalGovernanceDashboardService(MagicMock())
        self.service.repository = MagicMock()
        self.user = SimpleNamespace(organization_id=9, status=UserStatus.ACTIVE)
        self.role = SimpleNamespace(role_name=RoleName.CLINICAL_GOVERNANCE)
        self.service.repository.find_context.return_value = (self.user, self.role)
        for method in (
            "list_guardrail_hits",
            "list_rules",
            "list_escalations",
            "list_assignments",
            "list_actions",
            "list_audit_history",
        ):
            getattr(self.service.repository, method).return_value = []

    def test_rejects_user_without_governance_role(self):
        self.role.role_name = RoleName.CARE_MANAGER

        with self.assertRaises(AuthorizationException):
            self.service.get_analytics(4)

    def test_requires_both_custom_dates(self):
        with self.assertRaises(ValidationException):
            self.service.get_analytics(4, "custom")

    def test_counts_distinct_hits_and_open_escalations(self):
        now = datetime.now(UTC).replace(tzinfo=None)
        hit = SimpleNamespace(
            guardrail_hit_id=7,
            rule_id=3,
            hit_urgency_level=GuardrailHitUrgencyLevel.EMERGENCY,
            action_taken=GuardrailActionTaken.EMERGENCY_PROTOCOL,
            created_at=now,
        )
        rule = SimpleNamespace(
            rule_id=3,
            rule_name="Chest pain",
            rule_category=RuleCategory.EMERGENCY,
            urgency_level=UrgencyLevel.EMERGENCY,
            action_type=GuardrailActionType.EMERGENCY_PROTOCOL,
            status=RuleStatus.ACTIVE,
        )
        message = SimpleNamespace(message_text="I have chest pain")
        event = SimpleNamespace(
            emergency_instruction_sent=True,
            notified_care_team=True,
            event_status="OPEN",
        )
        self.service.repository.list_guardrail_hits.return_value = [
            (hit, rule, message, event),
            (hit, rule, message, event),
        ]
        self.service.repository.list_rules.return_value = [rule]
        escalation = SimpleNamespace(
            escalation_id=11,
            escalation_type=EscalationType.EMERGENCY,
            priority=EscalationPriority.CRITICAL,
            status=EscalationStatus.OPEN,
            resolved_at=None,
            created_at=now,
        )
        patient_user = SimpleNamespace(first_name="Jordan", last_name="Lee")
        self.service.repository.list_escalations.return_value = [
            (escalation, SimpleNamespace(), patient_user, hit)
        ]

        result = self.service.get_analytics(4)
        kpis = {metric["label"]: metric["value"] for metric in result["kpis"]}

        self.assertEqual(kpis["Emergency triggers"], 1)
        self.assertEqual(kpis["Open escalations"], 1)
        self.assertEqual(result["rule_performance"][0]["trigger_count"], 1)
        self.assertEqual(len(result["red_flag_outcomes"]), 1)

    def test_flags_missing_escalation_documentation(self):
        now = datetime.now(UTC).replace(tzinfo=None)
        escalation = SimpleNamespace(
            escalation_id=11,
            escalation_type=EscalationType.CLINICAL_REVIEW,
            priority=EscalationPriority.HIGH,
            status=EscalationStatus.IN_PROGRESS,
            resolved_at=None,
            created_at=now,
        )
        patient_user = SimpleNamespace(first_name="Jordan", last_name="Lee")
        self.service.repository.list_escalations.return_value = [
            (escalation, SimpleNamespace(), patient_user, None)
        ]

        row = self.service.get_analytics(4)["documentation"][0]

        self.assertIn("No active assignment", row["documentation_issues"])
        self.assertIn("No staff action", row["documentation_issues"])
        self.assertIn("Unresolved", row["documentation_issues"])


if __name__ == "__main__":
    unittest.main()