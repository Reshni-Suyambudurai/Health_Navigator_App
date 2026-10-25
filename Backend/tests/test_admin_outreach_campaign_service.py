import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import ConflictException, ValidationException
from app.database.models.outreach_campaign import CampaignStatus, CampaignType
from app.database.models.outreach_event import DeliveryStatus, OutreachEventStatus
from app.database.models.outreach_workflow import OutreachChannel, TriggerAnchor, TriggerType
from app.services.navigator.admin_outreach_campaign_service import AdminOutreachCampaignService


class AdminOutreachCampaignServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AdminOutreachCampaignService(MagicMock())
        self.service.repository = MagicMock()
        self.admin = SimpleNamespace(
            user_id=4,
            organization_id=7,
            first_name="System",
            last_name="Administrator",
        )
        self.service.repository.find_admin_user.return_value = self.admin
        self.service.repository.campaign_name_exists.return_value = False
        self.service.repository.find_user.return_value = self.admin
        self.service.repository.list_workflows.return_value = []
        self.service.repository.list_eligible_outreach_events.return_value = []
        self.service.repository.count_eligible_patients.return_value = 3

    @staticmethod
    def cohort():
        return {
            "enrollment_statuses": ["ACTIVE"],
            "enrollment_programs": ["TCM"],
            "episode_types": ["POST_DISCHARGE_30_DAY"],
            "episode_statuses": ["OPEN", "IN_PROGRESS"],
            "discharged_within_days": 30,
        }

    @staticmethod
    def campaign(status=CampaignStatus.DRAFT):
        return SimpleNamespace(
            campaign_id=12,
            organization_id=7,
            campaign_name="Post-Discharge Follow-up",
            campaign_type=CampaignType.POST_DISCHARGE,
            target_cohort_definition={"description": "Follow recently discharged patients", "criteria": AdminOutreachCampaignServiceTests.cohort()},
            timezone="UTC",
            start_at=None,
            end_at=None,
            status=status,
            created_by_user_id=4,
            updated_by_user_id=4,
            created_at=None,
            updated_at=None,
        )

    def test_create_campaign_uses_admin_organization_and_draft_status(self):
        def save(entity):
            entity.campaign_id = 12

        self.service.repository.save.side_effect = save

        result = self.service.create_campaign(4, {
            "campaign_name": "Post-Discharge Follow-up",
            "description": "Follow recently discharged patients",
            "campaign_type": "POST_DISCHARGE",
            "timezone": "UTC",
            "start_at": None,
            "end_at": None,
            "cohort": self.cohort(),
        })

        campaign = self.service.repository.save.call_args.args[0]
        self.assertEqual(campaign.organization_id, 7)
        self.assertEqual(campaign.status, CampaignStatus.DRAFT)
        self.assertEqual(result["status"], "DRAFT")

    def test_activation_requires_active_workflow(self):
        campaign = self.campaign()
        self.service.repository.find_campaign.return_value = campaign

        with self.assertRaises(ValidationException):
            self.service.transition_status(4, campaign.campaign_id, "ACTIVE")

        self.service.repository.save.assert_not_called()

    def test_list_cohort_members_uses_campaign_criteria_and_admin_organization(self):
        campaign = self.campaign()
        profile = SimpleNamespace(patient_id=42, external_fhir_patient_id="FHIR-42")
        user = SimpleNamespace(first_name="Alex", last_name="Morgan")
        now = datetime(2026, 10, 25, 9, 30)
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_eligible_patients.return_value = ([
            (
                profile,
                user,
                99,
                SimpleNamespace(value="TCM"),
                SimpleNamespace(value="ACTIVE"),
                now,
                SimpleNamespace(value="POST_DISCHARGE_30_DAY"),
                SimpleNamespace(value="OPEN"),
                SimpleNamespace(value="DISCHARGE"),
                now,
                now,
            )
        ], 1)

        result = self.service.list_cohort_members(4, 12, skip=0, limit=20)

        self.service.repository.list_eligible_patients.assert_called_once_with(7, self.cohort(), 0, 20)
        self.assertEqual(result["campaign_name"], "Post-Discharge Follow-up")
        self.assertEqual(result["patients"][0]["patient_name"], "Alex Morgan")
        self.assertEqual(result["patients"][0]["episode_id"], 99)
        self.assertEqual(result["patients"][0]["outreach_status"], "NEWLY_ELIGIBLE")
        self.assertEqual(result["patients"][0]["external_fhir_patient_id"], "FHIR-42")
        self.assertFalse(result["has_more"])

    def test_activation_succeeds_with_valid_workflow_and_template(self):
        campaign = self.campaign()
        workflow = SimpleNamespace(
            workflow_id=20,
            campaign_id=12,
            step_order=1,
            step_name="Initial check-in",
            trigger_type=TriggerType.AFTER_DISCHARGE,
            trigger_anchor=TriggerAnchor.DISCHARGE_DATETIME,
            trigger_offset_hours=24,
            channel=OutreachChannel.SMS,
            template_text=None,
            checkin_template_id=9,
            escalation_on_no_response=True,
            max_attempts=3,
            retry_interval_minutes=30,
            is_active=True,
        )
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [workflow]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")

        result = self.service.transition_status(4, campaign.campaign_id, "ACTIVE")

        self.assertEqual(campaign.status, CampaignStatus.ACTIVE)
        self.service.repository.save.assert_called_once_with(campaign)
        self.assertTrue(result["readiness"]["ready"])

    def test_completed_campaign_is_terminal(self):
        campaign = self.campaign(CampaignStatus.COMPLETED)
        self.service.repository.find_campaign.return_value = campaign

        with self.assertRaises(ValidationException):
            self.service.transition_status(4, campaign.campaign_id, "ACTIVE")

    def test_create_outreach_events_creates_missing_ready_workflow_occurrence(self):
        campaign = self.campaign(CampaignStatus.ACTIVE)
        workflow = self.workflow()
        row = self.eligible_patient_row()
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [workflow]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")
        self.service.repository.find_selected_eligible_patients.return_value = [row]
        self.service.repository.list_eligible_outreach_events.return_value = []
        self.service.repository.stage_outreach_events.return_value = [(501, "campaign:12:workflow:20:patient:42:episode:99")]

        result = self.service.create_outreach_events(
            4,
            12,
            [{"patient_id": 42, "episode_id": 99}],
            "127.0.0.1",
            "test-correlation",
        )

        staged = self.service.repository.stage_outreach_events.call_args.args[0]
        self.assertEqual(len(staged), 1)
        self.assertEqual(staged[0]["patient_id"], 42)
        self.assertEqual(staged[0]["episode_id"], 99)
        self.assertEqual(staged[0]["scheduled_at"], datetime(2026, 10, 26, 9, 30))
        self.service.repository.commit_with_audit.assert_called_once()
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["created_occurrences"], 1)

    def test_create_outreach_events_requires_active_campaign(self):
        self.service.repository.find_campaign.return_value = self.campaign(CampaignStatus.DRAFT)

        with self.assertRaises(ValidationException):
            self.service.create_outreach_events(4, 12, [{"patient_id": 42, "episode_id": 99}])

        self.service.repository.stage_outreach_events.assert_not_called()

    def test_create_outreach_events_reports_existing_and_no_longer_eligible_patients(self):
        campaign = self.campaign(CampaignStatus.ACTIVE)
        workflow = self.workflow()
        row = self.eligible_patient_row()
        existing_event = SimpleNamespace(patient_id=42, episode_id=99, workflow_id=20)
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [workflow]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")
        self.service.repository.find_selected_eligible_patients.return_value = [row]
        self.service.repository.list_eligible_outreach_events.return_value = [existing_event]
        self.service.repository.stage_outreach_events.return_value = []

        result = self.service.create_outreach_events(4, 12, [
            {"patient_id": 42, "episode_id": 99},
            {"patient_id": 77, "episode_id": 100},
        ])

        self.service.repository.stage_outreach_events.assert_called_once_with([])
        self.service.repository.commit_with_audit.assert_called_once()
        self.assertEqual(result["created"], 0)
        self.assertEqual(result["already_existing"], 1)
        self.assertEqual(result["no_longer_eligible"], 1)

    def test_existing_outreach_disables_patient_when_another_workflow_is_new(self):
        campaign = self.campaign(CampaignStatus.ACTIVE)
        second_workflow = self.workflow()
        second_workflow.workflow_id = 21
        second_workflow.step_name = "Second check-in"
        existing_event = SimpleNamespace(
            outreach_event_id=501,
            patient_id=42,
            episode_id=99,
            workflow_id=20,
            event_status=OutreachEventStatus.PENDING,
            delivery_status=DeliveryStatus.PENDING,
        )
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [self.workflow(), second_workflow]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")
        self.service.repository.list_eligible_patients.return_value = ([self.eligible_patient_row()], 1)
        self.service.repository.list_eligible_outreach_events.return_value = [existing_event]

        result = self.service.list_cohort_members(4, 12)

        patient = result["patients"][0]
        self.assertEqual(patient["outreach_status"], "PENDING")
        self.assertFalse(patient["can_create_outreach"])

    def test_create_outreach_conflict_includes_database_reason(self):
        campaign = self.campaign(CampaignStatus.ACTIVE)
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [self.workflow()]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")
        self.service.repository.find_selected_eligible_patients.return_value = [self.eligible_patient_row()]
        self.service.repository.list_eligible_outreach_events.return_value = []
        self.service.repository.stage_outreach_events.side_effect = SQLAlchemyError(
            "audit action CREATE_OUTREACH_EVENTS is not available"
        )

        with self.assertRaises(ConflictException) as context:
            self.service.create_outreach_events(4, 12, [{"patient_id": 42, "episode_id": 99}])

        self.assertIn("audit action CREATE_OUTREACH_EVENTS is not available", context.exception.message)
        self.service.repository.rollback.assert_called_once()

    def test_enable_auto_outreach_requires_active_ready_campaign(self):
        campaign = self.campaign(CampaignStatus.ACTIVE)
        campaign.auto_outreach_enabled = False
        self.service.repository.find_campaign.return_value = campaign
        self.service.repository.list_workflows.return_value = [self.workflow()]
        self.service.repository.find_active_template.return_value = SimpleNamespace(template_name="Discharge v1")

        result = self.service.set_auto_outreach(4, 12, True)

        self.assertTrue(campaign.auto_outreach_enabled)
        self.assertTrue(result["auto_outreach_enabled"])
        self.service.repository.commit_with_audit.assert_called_once()

    def test_enable_auto_outreach_rejects_inactive_campaign(self):
        campaign = self.campaign(CampaignStatus.PAUSED)
        campaign.auto_outreach_enabled = False
        self.service.repository.find_campaign.return_value = campaign

        with self.assertRaises(ValidationException):
            self.service.set_auto_outreach(4, 12, True)

        self.service.repository.commit_with_audit.assert_not_called()

    @staticmethod
    def workflow():
        return SimpleNamespace(
            workflow_id=20,
            campaign_id=12,
            step_order=1,
            step_name="Initial check-in",
            trigger_type=TriggerType.AFTER_DISCHARGE,
            trigger_anchor=TriggerAnchor.DISCHARGE_DATETIME,
            trigger_offset_hours=24,
            channel=OutreachChannel.SMS,
            template_text=None,
            checkin_template_id=9,
            escalation_on_no_response=False,
            max_attempts=3,
            retry_interval_minutes=30,
            is_active=True,
        )

    @staticmethod
    def eligible_patient_row():
        now = datetime(2026, 10, 25, 9, 30)
        return (
            SimpleNamespace(patient_id=42, external_fhir_patient_id="FHIR-42"),
            SimpleNamespace(first_name="Alex", last_name="Morgan"),
            99,
            SimpleNamespace(value="TCM"),
            SimpleNamespace(value="ACTIVE"),
            now,
            SimpleNamespace(value="POST_DISCHARGE_30_DAY"),
            SimpleNamespace(value="OPEN"),
            SimpleNamespace(value="DISCHARGE"),
            now,
            now,
        )


if __name__ == "__main__":
    unittest.main()