import unittest
from datetime import date
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException, ConflictException, ValidationException
from app.database.models.notification import NotificationPriority, NotificationStatus, NotificationType
from app.services.clinical_guardrail_service import ClinicalGuardrailService


class ClinicalGuardrailServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = ClinicalGuardrailService(MagicMock())
        self.service.repository = MagicMock()
        self.care_manager = {
            "user_id": 11,
            "organization_id": 7,
            "role_name": "CARE_MANAGER",
            "display_name": "Case Manager",
        }
        self.reviewer = {
            "user_id": 22,
            "organization_id": 7,
            "role_name": "CLINICAL_GOVERNANCE",
            "display_name": "Clinical Reviewer",
        }
        self.service.repository.find_actor.side_effect = self.find_actor

    def find_actor(self, user_id):
        return {11: self.care_manager, 22: self.reviewer}.get(user_id)

    @staticmethod
    def rule(approval_status="DRAFT", status="DRAFT", creator=11):
        return {
            "rule_id": 101,
            "guardrail_id": 51,
            "guardrail_name": "Medication Safety",
            "description": "Medication safety rules",
            "rule_name": "High-risk interaction",
            "category": "MEDICATION",
            "urgency": "HIGH",
            "handler_role_id": None,
            "action_type": "ESCALATE",
            "status": status,
            "approval_status": approval_status,
            "patient_response_template": "A clinician will review this.",
            "target_queue_type": "MEDICATION",
            "escalation_type": "MEDICATION",
            "escalation_priority": "HIGH",
            "created_by_user_id": creator,
            "approved_by_user_id": None,
            "approved_at": None,
            "effective_from": None,
            "rejection_reason": None,
        }

    def test_submit_transitions_owned_draft_and_notifies_same_org_reviewers(self):
        self.service.repository.find_rule.return_value = self.rule()
        self.service.repository.list_governance_users.return_value = [
            {"user_id": 22, "organization_id": 7}
        ]

        result = self.service.submit_rules(11, [101])

        self.service.repository.set_pending.assert_called_once_with(101)
        notification = self.service.repository.stage_notifications.call_args.args[0][0]
        self.assertEqual(notification.recipient_user_id, 22)
        self.assertEqual(notification.notification_type, NotificationType.SYSTEM_ALERT)
        self.assertEqual(notification.priority, NotificationPriority.HIGH)
        self.assertEqual(notification.status, NotificationStatus.UNREAD)
        self.assertIn("Rule ID: 101", notification.message)
        self.service.repository.commit.assert_called_once()
        self.assertEqual(result["notified_reviewers"], 1)

    def test_submit_rejects_rule_owned_by_another_care_manager_and_rolls_back(self):
        self.service.repository.find_rule.return_value = self.rule(creator=99)
        self.service.repository.list_governance_users.return_value = [
            {"user_id": 22, "organization_id": 7}
        ]

        with self.assertRaises(AuthorizationException):
            self.service.submit_rules(11, [101])

        self.service.repository.set_pending.assert_not_called()
        self.service.repository.commit.assert_not_called()
        self.service.repository.rollback.assert_called_once()

    def test_submit_requires_active_governance_reviewer(self):
        self.service.repository.list_governance_users.return_value = []

        with self.assertRaisesRegex(ValidationException, "No active Clinical Governance reviewer"):
            self.service.submit_rules(11, [101])

        self.service.repository.set_pending.assert_not_called()
        self.service.repository.commit.assert_not_called()
        self.service.repository.rollback.assert_called_once()

    def test_approval_records_reason_activates_and_notifies_creator(self):
        pending = self.rule(approval_status="PENDING")
        self.service.repository.find_rule.return_value = pending

        result = self.service.approve_rule(101, 22, "Clinically appropriate", date(2026, 11, 3))

        self.service.repository.approve.assert_called_once_with(101, 22, date(2026, 11, 3))
        audit_call = self.service.repository.stage_audit.call_args.kwargs
        self.assertEqual(audit_call["details"]["reason"], "Clinically appropriate")
        self.assertEqual(audit_call["details"]["approval_status"], "APPROVED")
        notification = self.service.repository.stage_notifications.call_args.args[0][0]
        self.assertEqual(notification.recipient_user_id, 11)
        self.assertIn("approved", notification.message)
        self.service.repository.commit.assert_called_once()
        self.assertEqual(result, {"rule_id": 101})

    def test_reviewer_cannot_approve_rule_they_created(self):
        self.service.repository.find_rule.return_value = self.rule(
            approval_status="PENDING",
            creator=22,
        )

        with self.assertRaises(AuthorizationException):
            self.service.approve_rule(101, 22, "Looks good", date(2026, 11, 3))

        self.service.repository.approve.assert_not_called()
        self.service.repository.commit.assert_not_called()
        self.service.repository.rollback.assert_called_once()

    def test_duplicate_approval_is_rejected_and_rolls_back(self):
        self.service.repository.find_rule.return_value = self.rule(
            approval_status="APPROVED",
            status="ACTIVE",
        )

        with self.assertRaises(ConflictException):
            self.service.approve_rule(101, 22, "Again", date(2026, 11, 3))

        self.service.repository.approve.assert_not_called()
        self.service.repository.rollback.assert_called_once()

    def test_rejection_persists_reason_and_notifies_creator(self):
        self.service.repository.find_rule.return_value = self.rule(approval_status="PENDING")

        self.service.reject_rule(101, 22, "Clarify the trigger")

        self.service.repository.reject.assert_called_once_with(101, "Clarify the trigger")
        audit_call = self.service.repository.stage_audit.call_args.kwargs
        self.assertEqual(audit_call["details"]["approval_status"], "REJECTED")
        self.assertEqual(audit_call["details"]["reason"], "Clarify the trigger")
        notification = self.service.repository.stage_notifications.call_args.args[0][0]
        self.assertIn("Clarify the trigger", notification.message)

    def test_only_approved_active_rule_can_be_deactivated(self):
        self.service.repository.find_rule.return_value = self.rule(
            approval_status="PENDING",
            status="DRAFT",
        )

        with self.assertRaises(ConflictException):
            self.service.deactivate_rule(101, 22, "Needs revision")

        self.service.repository.deactivate.assert_not_called()
        self.service.repository.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()