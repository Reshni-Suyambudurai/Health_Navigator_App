import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import ConflictException, ValidationException
from app.database.models.checkin_question import CheckinAnswerType
from app.database.models.checkin_template import CheckinTemplateStatus, CheckinTemplateType
from app.database.models.checkin_template_review import CheckinTemplateReviewStatus
from app.database.models.notification import NotificationPriority, NotificationType
from app.database.models.role import RoleName
from app.services.navigator.admin_checkin_template_service import AdminCheckinTemplateService


class AdminCheckinTemplateServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AdminCheckinTemplateService(MagicMock())
        self.service.repository = MagicMock()
        self.service.notifications = MagicMock()
        self.admin = SimpleNamespace(user_id=4, organization_id=7)
        self.reviewer = SimpleNamespace(user_id=8, organization_id=7)
        self.service.repository.find_active_user_with_role.side_effect = (
            lambda _user_id, role: self.admin if role == RoleName.SYSTEM_ADMIN else self.reviewer
        )
        self.service.repository.latest_review.return_value = None
        self.service.repository.find_pending_review.return_value = None
        self.service.repository.list_questions.return_value = []
        self.service.notifications.prepare_for_role.return_value = [SimpleNamespace(notification_id=41)]

    @staticmethod
    def template(status=CheckinTemplateStatus.DRAFT):
        return SimpleNamespace(
            checkin_template_id=11,
            organization_id=7,
            template_name="Initial Post-Discharge Check-in",
            template_type=CheckinTemplateType.POST_DISCHARGE,
            description="Initial outreach check-in",
            version=1,
            status=status,
            created_by_user_id=4,
            created_at=None,
            updated_at=None,
        )

    @staticmethod
    def question(answer_type=CheckinAnswerType.YES_NO, options=None):
        return SimpleNamespace(
            question_id=21,
            checkin_template_id=11,
            question_key="medication_pickup",
            question_text="Were you able to pick up your medications?",
            answer_type=answer_type,
            options=options,
            display_order=1,
            is_required=True,
            is_active=True,
        )

    def test_create_template_is_scoped_to_admin_and_saved_as_draft(self):
        self.service.repository.template_version_exists.return_value = False

        def save(entity):
            entity.checkin_template_id = 11

        self.service.repository.save.side_effect = save
        result = self.service.create_template(4, {
            "template_name": "Initial Post-Discharge Check-in",
            "template_type": "POST_DISCHARGE",
            "description": "Initial outreach check-in",
        })

        template = self.service.repository.save.call_args.args[0]
        self.assertEqual(template.organization_id, 7)
        self.assertEqual(template.status, CheckinTemplateStatus.DRAFT)
        self.assertEqual(result["status"], "DRAFT")

    def test_choice_question_requires_two_unique_options(self):
        template = self.template()
        self.service.repository.find_template.return_value = template
        self.service.repository.question_key_exists.return_value = False
        self.service.repository.question_order_exists.return_value = False

        with self.assertRaises(ValidationException):
            self.service.create_question(4, 11, {
                "question_key": "barriers",
                "question_text": "Which barriers apply?",
                "answer_type": "MULTIPLE_CHOICE",
                "options": ["Transport", "transport"],
                "display_order": 1,
            })

    def test_pending_review_blocks_template_changes(self):
        self.service.repository.find_template.return_value = self.template()
        self.service.repository.find_pending_review.return_value = SimpleNamespace(review_id=31)

        with self.assertRaises(ConflictException):
            self.service.update_template(4, 11, {"description": "Changed"})

        self.service.repository.save.assert_not_called()

    def test_template_detail_includes_latest_review_notes(self):
        template = self.template()
        self.service.repository.find_template.return_value = template
        self.service.repository.latest_review.return_value = SimpleNamespace(
            review_id=31,
            status=CheckinTemplateReviewStatus.REJECTED,
            review_notes="Clarify the medication escalation question.",
        )

        result = self.service.get_template(4, 11)

        self.assertEqual(result["review_status"], "REJECTED")
        self.assertEqual(result["review_notes"], "Clarify the medication escalation question.")

    def test_submit_review_requires_active_valid_question(self):
        template = self.template()
        self.service.repository.find_template.return_value = template
        self.service.repository.list_questions.return_value = [self.question()]

        def save_all(entities):
            entities[0].review_id = 31
            entities[0].submitted_at = None
            entities[0].reviewed_at = None

        self.service.repository.save_all.side_effect = save_all
        self.service.repository.latest_review.side_effect = lambda _template_id: self.service.repository.save_all.call_args.args[0][0]

        result = self.service.submit_review(4, 11, "Ready for review")

        saved_entities = self.service.repository.save_all.call_args.args[0]
        review = saved_entities[0]
        self.assertEqual(review.status, CheckinTemplateReviewStatus.PENDING)
        self.assertEqual(len(saved_entities), 2)
        self.service.notifications.prepare_for_role.assert_called_once_with(
            sender_user_id=4,
            organization_id=7,
            role_name=RoleName.CLINICAL_GOVERNANCE,
            title="Check-in template review requested",
            message="Initial Post-Discharge Check-in v1 was submitted for clinical review.",
            notification_type=NotificationType.FOLLOW_UP,
            priority=NotificationPriority.HIGH,
        )
        self.assertEqual(result["status"], "PENDING")

    def test_approval_marks_review_and_delegates_single_active_transaction(self):
        template = self.template()
        review = SimpleNamespace(
            review_id=31,
            checkin_template_id=11,
            status=CheckinTemplateReviewStatus.PENDING,
            submission_note=None,
            review_notes=None,
            submitted_by_user_id=4,
            reviewed_by_user_id=None,
            submitted_at=None,
            reviewed_at=None,
        )
        self.service.repository.find_review.return_value = (review, template)
        self.service.repository.list_questions.return_value = [self.question()]
        self.service.repository.latest_review.return_value = review

        result = self.service.decide_review(8, 31, "APPROVED", "Clinically appropriate")

        self.assertEqual(review.status, CheckinTemplateReviewStatus.APPROVED)
        self.assertEqual(review.reviewed_by_user_id, 8)
        self.service.repository.decide_review.assert_called_once_with(review, template, True)
        self.assertEqual(result["status"], "APPROVED")

    def test_submit_review_requires_active_clinical_governance_recipient(self):
        template = self.template()
        self.service.repository.find_template.return_value = template
        self.service.repository.list_questions.return_value = [self.question()]
        self.service.notifications.prepare_for_role.return_value = []

        with self.assertRaises(ValidationException):
            self.service.submit_review(4, 11, None)

        self.service.repository.save_all.assert_not_called()


if __name__ == "__main__":
    unittest.main()
