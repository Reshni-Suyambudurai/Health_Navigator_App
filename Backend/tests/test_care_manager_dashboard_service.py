import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException
from app.database.models.appointment_action import AppointmentResolutionStatus
from app.database.models.care_navigation_episode import EpisodeStatus, EpisodeType
from app.database.models.escalation import EscalationPriority, EscalationStatus, EscalationType
from app.database.models.follow_up_task import FollowUpPriority, FollowUpTaskStatus, FollowUpTaskType
from app.database.models.patient_enrollment import EnrollmentStatus
from app.database.models.patient_profile import RiskTier
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.services.navigator.care_manager_dashboard_service import CareManagerDashboardService


class CareManagerDashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = CareManagerDashboardService(MagicMock())
        self.service.repository = MagicMock()
        self.user = SimpleNamespace(user_id=4, organization_id=9, status=UserStatus.ACTIVE)
        self.staff = SimpleNamespace(staff_id=12)
        self.role = SimpleNamespace(role_name=RoleName.CARE_MANAGER)
        self.service.repository.find_context.return_value = (self.user, self.staff, self.role)
        for method in (
            "list_assigned_episodes",
            "list_enrollments",
            "list_episodes",
            "list_appointments",
            "list_appointment_actions",
            "list_outreach",
            "list_checkins",
            "list_escalations",
            "list_assignments",
            "list_escalation_actions",
            "list_follow_ups",
        ):
            getattr(self.service.repository, method).return_value = []
        self.service.repository.count_checkin_responses.return_value = 0

    def test_rejects_user_without_care_manager_role(self):
        self.role.role_name = RoleName.TRANSITIONAL_CARE_NURSE

        with self.assertRaises(AuthorizationException):
            self.service.get_analytics(4)

    def test_returns_all_requested_analytics_sections(self):
        result = self.service.get_analytics(4)

        self.assertEqual(
            set(result),
            {
                "generated_at",
                "dashboard",
                "caseload",
                "appointments",
                "outreach",
                "escalations",
                "follow_up",
                "program_performance",
            },
        )
        self.assertEqual(result["dashboard"]["metrics"][0]["value"], 0)
        self.assertEqual(result["program_performance"]["metrics"][-1]["value"], "0%")

    def test_follow_up_metrics_use_tasks_and_appointment_actions(self):
        now = datetime.now(UTC).replace(tzinfo=None)
        patient_user = SimpleNamespace(first_name="Jordan", last_name="Lee")
        task = SimpleNamespace(
            patient_id=10,
            title="Call patient",
            task_type=FollowUpTaskType.PATIENT_CONTACT,
            priority=FollowUpPriority.HIGH,
            status=FollowUpTaskStatus.OPEN,
            due_at=now - timedelta(days=1),
            escalation_id=31,
            appointment_id=None,
        )
        self.service.repository.list_follow_ups.return_value = [
            (task, SimpleNamespace(patient_id=10), patient_user)
        ]
        self.service.repository.list_appointment_actions.return_value = [
            SimpleNamespace(
                appointment_id=8,
                follow_up_required=True,
                resolution_status=AppointmentResolutionStatus.FOLLOW_UP_REQUIRED,
                created_at=now,
            )
        ]

        result = self.service.get_analytics(4)
        metrics = {metric["label"]: metric["value"] for metric in result["follow_up"]["metrics"]}

        self.assertEqual(metrics["Overdue tasks"], 1)
        self.assertEqual(metrics["Follow-up-required cases"], 1)
        self.assertEqual(result["follow_up"]["rows"][0]["linked_case"], "Escalation 31")

    def test_dashboard_rows_show_patient_episode_and_work_counts(self):
        now = datetime.now(UTC).replace(tzinfo=None)
        patient = SimpleNamespace(patient_id=10, risk_tier=RiskTier.HIGH)
        patient_user = SimpleNamespace(first_name="Jordan", last_name="Lee")
        episode = SimpleNamespace(
            status=EpisodeStatus.IN_PROGRESS,
            episode_type=EpisodeType.GENERAL_NAVIGATION,
            opened_at=now - timedelta(days=4),
        )
        enrollment = SimpleNamespace(enrollment_status=EnrollmentStatus.ACTIVE)
        self.service.repository.list_assigned_episodes.return_value = [
            (episode, patient, enrollment, patient_user)
        ]
        self.service.repository.list_escalations.return_value = [
            (
                SimpleNamespace(
                    escalation_id=31,
                    patient_id=10,
                    status=EscalationStatus.OPEN,
                    priority=EscalationPriority.HIGH,
                    escalation_type=EscalationType.CLINICAL_REVIEW,
                    created_at=now,
                    resolved_at=None,
                ),
                patient,
                patient_user,
                None,
            )
        ]
        task = SimpleNamespace(
            patient_id=10,
            title="Call patient",
            task_type=FollowUpTaskType.PATIENT_CONTACT,
            priority=FollowUpPriority.HIGH,
            status=FollowUpTaskStatus.OPEN,
            due_at=now - timedelta(days=1),
            escalation_id=31,
            appointment_id=None,
        )
        self.service.repository.list_follow_ups.return_value = [(task, patient, patient_user)]

        details = self.service.get_analytics(4)["dashboard"]["detail_groups"]

        self.assertEqual(details["active_care_episodes"][0]["patient"], "Jordan Lee")
        self.assertEqual(details["active_care_episodes"][0]["duration"], "4 days")
        self.assertEqual(details["high_risk_patients"][0]["risk_tier"], "HIGH")
        self.assertEqual(details["open_escalations"][0]["priority"], "HIGH")
        self.assertEqual(details["overdue_follow_ups"][0]["title"], "Call patient")


if __name__ == "__main__":
    unittest.main()
