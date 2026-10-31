import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException
from app.database.models.care_navigation_episode import EpisodeStatus, TriggerType
from app.database.models.checkin_escalation import CheckinEscalationStatus, CheckinEscalationType
from app.database.models.checkin_session import CheckinSessionStatus
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.services.navigator.tcm_tracker_service import TcmTrackerService


class TcmTrackerServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = TcmTrackerService(MagicMock())
        self.service.repository = MagicMock()
        self.user = SimpleNamespace(user_id=7, organization_id=4, status=UserStatus.ACTIVE)
        self.staff = SimpleNamespace(staff_id=22)
        self.role = SimpleNamespace(role_name=RoleName.CARE_MANAGER)
        self.service.repository.find_context.return_value = (self.user, self.staff, self.role)
        self.service.repository.list_campaigns.return_value = []
        self.service.repository.list_workflows.return_value = []
        self.service.repository.list_events.return_value = []
        self.service.repository.list_sessions.return_value = []
        self.service.repository.list_appointments.return_value = []
        self.service.repository.list_escalations.return_value = []

    def test_care_manager_uses_organization_scope_without_owner_filter(self):
        result = self.service.get_summary(7)

        self.assertEqual(result["scope"], "ORGANIZATION")
        self.service.repository.list_campaigns.assert_called_once_with(4)

    def test_nurse_uses_assigned_patient_scope(self):
        self.role.role_name = RoleName.TRANSITIONAL_CARE_NURSE
        campaign = SimpleNamespace(campaign_id=9, campaign_name="TCM", organization_id=4)
        self.service.repository.list_campaigns.return_value = [campaign]
        self.service.repository.list_eligible_episodes.return_value = []

        result = self.service.get_summary(7)

        self.assertEqual(result["scope"], "ASSIGNED_PATIENTS")
        owner_filter = self.service.repository.list_eligible_episodes.call_args.args[1]
        self.assertEqual(owner_filter, 22)

    def test_care_manager_does_not_apply_owner_filter(self):
        campaign = SimpleNamespace(campaign_id=9, campaign_name="TCM", organization_id=4)
        self.service.repository.list_campaigns.return_value = [campaign]
        self.service.repository.list_eligible_episodes.return_value = []

        self.service.get_summary(7)

        owner_filter = self.service.repository.list_eligible_episodes.call_args.args[1]
        self.assertIsNone(owner_filter)

    def test_rejects_unsupported_role(self):
        self.role.role_name = RoleName.PHARMACIST

        with self.assertRaises(AuthorizationException):
            self.service.get_summary(7)

    def test_required_appointment_blocks_next_workflow_eligibility(self):
        self._configure_episode(appointment_required=True)

        result = self.service.get_workflow_progress(7)

        first, second = result["workflows"]
        self.assertEqual(first["eligible_count"], 1)
        self.assertEqual(first["checkin"]["completed"], 1)
        self.assertEqual(first["appointment"]["eligible"], 1)
        self.assertEqual(first["appointment"]["pending_booking"], 1)
        self.assertEqual(second["eligible_count"], 0)

    def test_emergency_priority_over_pending_appointment(self):
        session = self._configure_episode(appointment_required=True)
        escalation = SimpleNamespace(
            checkin_escalation_id=81,
            checkin_session_id=session.checkin_session_id,
            escalation_type=CheckinEscalationType.EMERGENCY,
            escalation_status=CheckinEscalationStatus.ASSIGNED,
            escalation_reason="Urgent symptom",
            action_taken=None,
            resolution_notes=None,
        )
        assignment = SimpleNamespace(assigned_at=datetime.now() - timedelta(hours=1))
        self.service.repository.list_escalations.return_value = [
            (escalation, assignment, None, None),
        ]

        result = self.service.list_patients(7, "NEEDS_ATTENTION")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["patients"][0]["category"], "NEEDS_ATTENTION")

    def _configure_episode(self, appointment_required: bool):
        now = datetime.now()
        campaign = SimpleNamespace(
            campaign_id=9,
            campaign_name="Post-Discharge TCM",
            organization_id=4,
        )
        workflows = [
            SimpleNamespace(
                workflow_id=31,
                campaign_id=9,
                step_name="Initial check-in",
                step_order=1,
                trigger_offset_hours=0,
            ),
            SimpleNamespace(
                workflow_id=32,
                campaign_id=9,
                step_name="Day-7 follow-up",
                step_order=2,
                trigger_offset_hours=0,
            ),
        ]
        templates = [
            SimpleNamespace(appointment_required=appointment_required),
            SimpleNamespace(appointment_required=False),
        ]
        episode = SimpleNamespace(
            episode_id=15,
            patient_id=5,
            episode_status=EpisodeStatus.IN_PROGRESS,
            trigger_type=TriggerType.DISCHARGE,
            opened_at=now - timedelta(days=2),
            closed_at=None,
            owner_staff_id=22,
            external_fhir_patient_id=None,
            first_name="Alex",
            last_name="Morgan",
        )
        event = SimpleNamespace(
            outreach_event_id=41,
            campaign_id=9,
            workflow_id=31,
            episode_id=15,
            created_at=now - timedelta(days=1),
        )
        session = SimpleNamespace(
            checkin_session_id=51,
            outreach_event_id=41,
            appointment_id=None,
            session_status=CheckinSessionStatus.COMPLETED,
            created_at=now - timedelta(days=1),
            updated_at=now,
            completed_at=now,
        )
        self.service.repository.list_campaigns.return_value = [campaign]
        self.service.repository.list_workflows.return_value = list(zip(workflows, templates))
        self.service.repository.list_eligible_episodes.return_value = [episode]
        self.service.repository.list_events.return_value = [event]
        self.service.repository.list_sessions.return_value = [session]
        self.service.repository.list_appointments.return_value = []
        self.service.repository.list_escalations.return_value = []
        return session


if __name__ == "__main__":
    unittest.main()