import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.database.models.checkin_escalation import CheckinEscalation, CheckinEscalationStatus, CheckinEscalationType
from app.database.models.checkin_escalation_response import CheckinEscalationResponse
from app.core.exceptions import ConflictException
from app.database.models.checkin_question import CheckinAnswerType, CheckinQuestion, CheckinRiskLevel
from app.database.models.checkin_response import CheckinResponse
from app.database.models.checkin_session import CheckinSession, CheckinSessionStatus
from app.database.models.escalation_assignment import EscalationAssignmentStatus
from app.database.models.notification import Notification, NotificationStatus, NotificationType
from app.database.models.role import RoleName
from app.services.navigator.outreach_service import OutreachService


class OutreachCheckinRiskTests(unittest.TestCase):
    def test_record_response_locks_session_before_processing(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        service.profile_repository = MagicMock()
        session = SimpleNamespace(
            checkin_session_id=11,
            patient_id=17,
            checkin_template_id=7,
            session_status=CheckinSessionStatus.PENDING,
            expires_at=None,
            started_at=None,
            completed_at=None,
        )
        question = SimpleNamespace(
            question_id=22,
            checkin_template_id=7,
            question_key="follow_up_needed",
            answer_type=CheckinAnswerType.YES_NO,
            critical_response=None,
            risk_level=CheckinRiskLevel.NORMAL,
            is_active=True,
            is_required=False,
        )
        service.repository.lock_session.return_value = session
        service.profile_repository.find_by_user_id.return_value = SimpleNamespace(patient_id=17)
        service.repository.get_question.return_value = question
        service.repository.user_exists.return_value = True
        service.repository.get_response.return_value = None
        service.repository.get_checkin_escalation.return_value = None
        service.repository.list_questions.return_value = [question]
        service.repository.add.side_effect = lambda entity: entity

        service.record_response(
            11,
            {
                "question_id": 22,
                "answer_text": None,
                "answer_value": "Yes",
                "response_source": "PATIENT_REPORTED",
                "answered_at": datetime(2026, 10, 28, 9, 0),
            },
            user_id=5,
        )

        service.repository.lock_session.assert_called_once_with(11)
        service.repository.get_session.assert_not_called()
        service.repository.get_checkin_escalation.assert_not_called()
        self.assertEqual(session.session_status, CheckinSessionStatus.IN_PROGRESS)
        saved_response = service.repository.add.call_args.args[0]
        self.assertEqual(saved_response.evaluated_risk_level, CheckinRiskLevel.NORMAL)
        self.assertIsNone(saved_response.risk_evaluation)

    def test_numeric_critical_response_uses_inclusive_range(self):
        question = SimpleNamespace(
            answer_type=CheckinAnswerType.NUMBER,
            critical_response={"min": 5, "max": 10},
        )

        self.assertTrue(OutreachService._is_critical_response(question, {"answer_value": 5}))
        self.assertTrue(OutreachService._is_critical_response(question, {"answer_value": 10}))
        self.assertFalse(OutreachService._is_critical_response(question, {"answer_value": 11}))

    def test_numeric_critical_response_respects_exclusive_boundaries(self):
        question = SimpleNamespace(
            answer_type=CheckinAnswerType.NUMBER,
            critical_response={
                "min": 5,
                "max": 10,
                "min_inclusive": False,
                "max_inclusive": False,
            },
        )

        self.assertFalse(OutreachService._is_critical_response(question, {"answer_value": 5}))
        self.assertTrue(OutreachService._is_critical_response(question, {"answer_value": 6}))
        self.assertFalse(OutreachService._is_critical_response(question, {"answer_value": 10}))

    def test_submit_session_completes_all_normal_answers_atomically(self):
        db = MagicMock()
        service = OutreachService(db)
        service.repository = MagicMock()
        service.profile_repository = MagicMock()
        session = CheckinSession(
            checkin_session_id=11,
            patient_id=17,
            outreach_event_id=3,
            checkin_template_id=7,
            scheduled_at=datetime(2026, 10, 28, 8, 0),
            session_status=CheckinSessionStatus.IN_PROGRESS,
        )
        question = CheckinQuestion(
            question_id=22,
            checkin_template_id=7,
            question_key="symptoms",
            question_text="How are you feeling?",
            answer_type=CheckinAnswerType.TEXT,
            risk_level=CheckinRiskLevel.NORMAL,
            display_order=1,
            is_required=True,
            is_active=True,
        )
        saved_responses = {}

        def add(entity):
            if isinstance(entity, CheckinResponse):
                entity.response_id = 31
                saved_responses[entity.question_id] = entity
            return entity

        service.repository.lock_session.return_value = session
        service.profile_repository.find_by_user_id.return_value = SimpleNamespace(patient_id=17)
        service.repository.list_questions.return_value = [question]
        service.repository.list_responses.side_effect = lambda _session_id: list(saved_responses.values())
        service.repository.get_response.side_effect = lambda _session_id, question_id: saved_responses.get(question_id)
        service.repository.get_checkin_escalation.return_value = None
        service.repository.add.side_effect = add

        result = service.submit_session(
            11,
            {"responses": [{"question_id": 22, "answer_text": "Much better", "answer_value": None}]},
            user_id=5,
        )

        self.assertEqual(session.session_status, CheckinSessionStatus.COMPLETED)
        self.assertEqual(result["session_status"], CheckinSessionStatus.COMPLETED.value)
        self.assertEqual(saved_responses[22].evaluated_risk_level, CheckinRiskLevel.NORMAL)
        self.assertIsNone(saved_responses[22].risk_evaluation)
        db.commit.assert_called_once()

    def test_changed_retry_after_finalization_returns_conflict(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        service.profile_repository = MagicMock()
        session = SimpleNamespace(
            checkin_session_id=11,
            patient_id=17,
            checkin_template_id=7,
            session_status=CheckinSessionStatus.COMPLETED,
        )
        question = SimpleNamespace(question_id=22, is_active=True)
        response = SimpleNamespace(question_id=22, answer_text="Original", answer_value=None)
        service.repository.lock_session.return_value = session
        service.profile_repository.find_by_user_id.return_value = SimpleNamespace(patient_id=17)
        service.repository.list_questions.return_value = [question]
        service.repository.list_responses.return_value = [response]

        with self.assertRaises(ConflictException):
            service.submit_session(
                11,
                {"responses": [{"question_id": 22, "answer_text": "Changed", "answer_value": None}]},
                user_id=5,
            )

    def test_nurse_assignment_uses_episode_owner(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        session = SimpleNamespace(episode_id=8)
        template = SimpleNamespace(organization_id=2, escalation_role_id=3)
        escalation = SimpleNamespace(
            checkin_escalation_id=44,
            target_role_id=None,
            queue_id=None,
            assigned_to_staff_id=None,
            assigned_at=None,
            escalation_status=CheckinEscalationStatus.OPEN,
        )
        service.repository.get_role.return_value = SimpleNamespace(role_name=RoleName.TRANSITIONAL_CARE_NURSE)
        service.repository.get_episode.return_value = SimpleNamespace(owner_staff_id=12)
        service.repository.get_eligible_staff.return_value = SimpleNamespace(staff_id=12)
        service.repository.get_checkin_assignment.return_value = None
        service.repository.add.side_effect = lambda entity: entity

        assignment = service._assign_checkin_escalation(
            session,
            template,
            escalation,
            datetime(2026, 10, 28, 9, 0),
        )

        self.assertEqual(assignment.assigned_to_staff_id, 12)
        self.assertIsNone(escalation.queue_id)
        self.assertEqual(escalation.escalation_status, CheckinEscalationStatus.ASSIGNED)
        service.repository.get_care_team_queue.assert_not_called()
        service.repository.find_least_loaded_staff.assert_not_called()

    def test_pharmacist_and_social_worker_use_least_loaded_role_staff(self):
        for role_name in (RoleName.PHARMACIST, RoleName.SOCIAL_WORKER):
            with self.subTest(role_name=role_name):
                service = OutreachService(MagicMock())
                service.repository = MagicMock()
                session = SimpleNamespace(episode_id=8)
                template = SimpleNamespace(organization_id=2, escalation_role_id=3)
                escalation = SimpleNamespace(
                    checkin_escalation_id=44,
                    target_role_id=None,
                    queue_id=None,
                    assigned_to_staff_id=None,
                    assigned_at=None,
                    escalation_status=CheckinEscalationStatus.OPEN,
                )
                service.repository.get_role.return_value = SimpleNamespace(role_name=role_name)
                service.repository.find_least_loaded_staff.return_value = SimpleNamespace(staff_id=15)
                service.repository.get_checkin_assignment.return_value = None
                service.repository.add.side_effect = lambda entity: entity

                assignment = service._assign_checkin_escalation(
                    session,
                    template,
                    escalation,
                    datetime(2026, 10, 28, 9, 0),
                )

                self.assertEqual(assignment.assigned_to_staff_id, 15)
                self.assertEqual(escalation.escalation_status, CheckinEscalationStatus.ASSIGNED)
                service.repository.find_least_loaded_staff.assert_called_once_with(2, 3)
                service.repository.get_episode.assert_not_called()
                service.repository.get_care_team_queue.assert_not_called()

    def test_resolve_notifies_patient_once_and_completes_session(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        assignment = SimpleNamespace(
            assignment_status=EscalationAssignmentStatus.IN_PROGRESS,
            action_taken=None,
            resolution_notes=None,
            completed_at=None,
            is_active=True,
        )
        escalation = SimpleNamespace(
            checkin_session_id=11,
            escalation_status=CheckinEscalationStatus.IN_PROGRESS,
            action_taken=None,
            resolution_notes=None,
            resolved_at=None,
        )
        session = SimpleNamespace(
            patient_id=17,
            checkin_template_id=7,
            session_status=CheckinSessionStatus.ESCALATED,
            completed_at=datetime(2026, 10, 28, 9, 0),
        )
        sender_user = SimpleNamespace(user_id=3, organization_id=2)
        patient_user = SimpleNamespace(user_id=5, organization_id=2)
        role = SimpleNamespace(role_name=RoleName.TRANSITIONAL_CARE_NURSE)
        service._require_owned_assignment = MagicMock(return_value=(assignment, escalation))
        service._require_checkin_staff = MagicMock(return_value=(SimpleNamespace(), sender_user, role))
        service._staff_checkin_result = MagicMock(return_value={})
        service.repository.get_session.return_value = session
        service.repository.get_patient_identity.return_value = (SimpleNamespace(), patient_user)
        service.repository.get_template.return_value = SimpleNamespace(template_name="Day 2 Follow-up")
        service.repository.add.side_effect = lambda entity: entity

        service.resolve_checkin_assignment(
            13,
            {"action_taken": "Social worker assigned", "resolution_notes": "A social worker will contact you."},
            user_id=3,
        )

        self.assertEqual(session.session_status, CheckinSessionStatus.COMPLETED)
        notification = service.repository.add.call_args.args[0]
        self.assertIsInstance(notification, Notification)
        self.assertEqual(notification.recipient_user_id, 5)
        self.assertEqual(notification.sender_user_id, 3)
        self.assertEqual(notification.notification_type, NotificationType.FOLLOW_UP)
        self.assertEqual(notification.status, NotificationStatus.UNREAD)

        service.repository.add.reset_mock()
        service.resolve_checkin_assignment(
            13,
            {"action_taken": "Social worker assigned", "resolution_notes": "A social worker will contact you."},
            user_id=3,
        )
        service.repository.add.assert_not_called()

    def test_multiple_choice_critical_response_matches_any_selected_option(self):
        question = SimpleNamespace(
            answer_type=CheckinAnswerType.MULTIPLE_CHOICE,
            critical_response={"values": ["transport", "food"]},
        )

        self.assertTrue(OutreachService._is_critical_response(question, {"answer_value": ["Medication", "FOOD"]}))
        self.assertFalse(OutreachService._is_critical_response(question, {"answer_value": ["Housing"]}))

    def test_multiple_critical_responses_share_one_session_escalation(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        session = SimpleNamespace(
            checkin_session_id=11,
            session_status=CheckinSessionStatus.IN_PROGRESS,
        )
        routine_question = SimpleNamespace(
            question_key="follow_up_needed",
            risk_level=CheckinRiskLevel.ROUTINE,
        )
        emergency_question = SimpleNamespace(
            question_key="severe_symptoms",
            risk_level=CheckinRiskLevel.EMERGENCY,
        )
        routine_response = SimpleNamespace(response_id=22)
        emergency_response = SimpleNamespace(response_id=23)
        saved_escalation = None

        def add(entity):
            nonlocal saved_escalation
            if isinstance(entity, CheckinEscalation):
                entity.checkin_escalation_id = 44
                saved_escalation = entity
            return entity

        service.repository.add.side_effect = add
        service.repository.get_checkin_escalation.side_effect = lambda _session_id: saved_escalation
        service.repository.get_checkin_escalation_response.return_value = None

        first = service._apply_checkin_risk(session, routine_question, routine_response)
        second = service._apply_checkin_risk(session, emergency_question, emergency_response)

        self.assertEqual(session.session_status, CheckinSessionStatus.ESCALATED)
        self.assertIs(first, second)
        self.assertEqual(first.checkin_session_id, 11)
        self.assertEqual(first.escalation_type, CheckinEscalationType.EMERGENCY)
        self.assertEqual(first.escalation_status, CheckinEscalationStatus.OPEN)
        added_entities = [call.args[0] for call in service.repository.add.call_args_list]
        self.assertEqual(sum(isinstance(item, CheckinEscalation) for item in added_entities), 1)
        links = [item for item in added_entities if isinstance(item, CheckinEscalationResponse)]
        self.assertEqual({link.response_id for link in links}, {22, 23})

    def test_retry_does_not_duplicate_escalation_response_link(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        session = SimpleNamespace(
            checkin_session_id=11,
            session_status=CheckinSessionStatus.ESCALATED,
        )
        question = SimpleNamespace(
            question_key="severe_symptoms",
            risk_level=CheckinRiskLevel.EMERGENCY,
        )
        response = SimpleNamespace(response_id=22)
        escalation = SimpleNamespace(
            checkin_escalation_id=44,
            escalation_type=CheckinEscalationType.EMERGENCY,
        )
        service.repository.get_checkin_escalation.return_value = escalation
        service.repository.get_checkin_escalation_response.return_value = SimpleNamespace(
            checkin_escalation_id=44,
            response_id=22,
        )

        result = service._apply_checkin_risk(session, question, response)

        self.assertIs(result, escalation)
        service.repository.add.assert_not_called()

    def test_noncritical_edit_removes_empty_escalation(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        session = SimpleNamespace(checkin_session_id=11)
        response = SimpleNamespace(response_id=22)
        escalation = SimpleNamespace(checkin_escalation_id=44)
        link = SimpleNamespace(checkin_escalation_id=44, response_id=22)
        service.repository.get_checkin_escalation.return_value = escalation
        service.repository.get_checkin_escalation_response.return_value = link
        service.repository.list_checkin_escalation_responses.return_value = []

        result = service._remove_checkin_risk(session, response)

        self.assertIsNone(result)
        self.assertEqual(
            [call.args[0] for call in service.repository.delete.call_args_list],
            [link, escalation],
        )

    def test_noncritical_edit_recalculates_remaining_severity(self):
        service = OutreachService(MagicMock())
        service.repository = MagicMock()
        session = SimpleNamespace(checkin_session_id=11)
        response = SimpleNamespace(response_id=22)
        escalation = SimpleNamespace(
            checkin_escalation_id=44,
            escalation_type=CheckinEscalationType.EMERGENCY,
        )
        link = SimpleNamespace(checkin_escalation_id=44, response_id=22)
        remaining_response = SimpleNamespace(evaluated_risk_level=CheckinRiskLevel.ROUTINE)
        service.repository.get_checkin_escalation.return_value = escalation
        service.repository.get_checkin_escalation_response.return_value = link
        service.repository.list_checkin_escalation_responses.return_value = [remaining_response]

        result = service._remove_checkin_risk(session, response)

        self.assertIs(result, escalation)
        self.assertEqual(escalation.escalation_type, CheckinEscalationType.ROUTINE)
        service.repository.delete.assert_called_once_with(link)


if __name__ == "__main__":
    unittest.main()
