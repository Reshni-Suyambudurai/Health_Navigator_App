import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import ValidationException
from app.database.models.outreach_campaign import CampaignStatus, CampaignType
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


if __name__ == "__main__":
    unittest.main()