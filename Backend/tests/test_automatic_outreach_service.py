import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.database.models.outreach_campaign import CampaignStatus
from app.database.models.outreach_event import DeliveryStatus, OutreachEventStatus
from app.database.models.outreach_workflow import OutreachChannel
from app.services.navigator.automatic_outreach_scheduler import AutomaticOutreachScheduler
from app.services.navigator.automatic_outreach_service import AutomaticOutreachService


class AutomaticOutreachServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AutomaticOutreachService(MagicMock())
        self.service.repository = MagicMock()
        self.service.campaign_service = MagicMock()
        self.campaign = SimpleNamespace(
            campaign_id=12,
            organization_id=7,
            status=CampaignStatus.ACTIVE,
            start_at=None,
            end_at=None,
        )
        self.workflow = SimpleNamespace(
            workflow_id=20,
            trigger_offset_hours=24,
            channel=OutreachChannel.SMS,
        )
        self.row = self.eligible_patient_row()
        self.service.repository.list_auto_outreach_campaigns.return_value = [self.campaign]
        self.service.repository.list_all_eligible_patients.return_value = [self.row]
        self.service.repository.list_eligible_outreach_events.return_value = []
        self.service.repository.stage_outreach_events.return_value = []
        self.service.campaign_service._metadata.return_value = {"criteria": {"cohort": "value"}}
        self.service.campaign_service._validate_cohort.return_value = {"cohort": "value"}
        self.service.campaign_service._manual_outreach_workflows.return_value = [self.workflow]
        self.service.campaign_service._outreach_idempotency_key.return_value = "occurrence-key"

    def test_creates_occurrence_at_exact_due_time(self):
        self.service.repository.stage_outreach_events.return_value = [(501, "occurrence-key")]

        result = self.service.run_due_outreach(datetime(2026, 10, 26, 9, 30))

        values = self.service.repository.stage_outreach_events.call_args.args[0]
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0]["scheduled_at"], datetime(2026, 10, 26, 9, 30))
        self.assertEqual(values[0]["event_status"], OutreachEventStatus.PENDING)
        self.assertEqual(values[0]["delivery_status"], DeliveryStatus.PENDING)
        self.assertEqual(result["created_occurrences"], 1)
        self.service.repository.commit_with_audit.assert_called_once()

    def test_does_not_create_future_occurrence(self):
        result = self.service.run_due_outreach(datetime(2026, 10, 26, 9, 29))

        self.service.repository.stage_outreach_events.assert_called_once_with([])
        self.service.repository.commit_with_audit.assert_not_called()
        self.assertEqual(result["created_occurrences"], 0)

    def test_does_not_recreate_existing_occurrence(self):
        self.service.repository.list_eligible_outreach_events.return_value = [SimpleNamespace(
            patient_id=42,
            episode_id=99,
            workflow_id=20,
        )]

        self.service.run_due_outreach(datetime(2026, 10, 27, 9, 30))

        self.service.repository.stage_outreach_events.assert_called_once_with([])
        self.service.repository.commit_with_audit.assert_not_called()

    @staticmethod
    def eligible_patient_row():
        discharge_at = datetime(2026, 10, 25, 9, 30)
        return (
            SimpleNamespace(patient_id=42),
            SimpleNamespace(first_name="Alex", last_name="Morgan"),
            99,
            SimpleNamespace(value="TCM"),
            SimpleNamespace(value="ACTIVE"),
            discharge_at,
            SimpleNamespace(value="POST_DISCHARGE_30_DAY"),
            SimpleNamespace(value="OPEN"),
            SimpleNamespace(value="DISCHARGE"),
            discharge_at,
            discharge_at,
        )


class AutomaticOutreachSchedulerTests(unittest.TestCase):
    @patch("app.services.navigator.automatic_outreach_scheduler.SessionLocal")
    @patch("app.services.navigator.automatic_outreach_scheduler.engine")
    def test_lock_loser_skips_processing(self, engine, session_local):
        connection = MagicMock()
        connection.execute.return_value.scalar.return_value = False
        engine.connect.return_value.__enter__.return_value = connection

        AutomaticOutreachScheduler.run_once()

        session_local.assert_not_called()


if __name__ == "__main__":
    unittest.main()