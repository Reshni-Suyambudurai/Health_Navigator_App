import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.database.models.outreach_event import (
    DeliveryStatus,
    OutreachEventChannel,
    OutreachEventStatus,
)
from app.database.models.checkin_session import CheckinSessionStatus
from app.services.navigator.outreach_delivery_service import OutreachDeliveryService


class OutreachDeliveryServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = MagicMock()
        self.service = OutreachDeliveryService(self.db)
        self.service.repository = MagicMock()
        self.event = SimpleNamespace(
            outreach_event_id=501,
            patient_id=42,
            episode_id=99,
            campaign_id=12,
            workflow_id=20,
            channel=OutreachEventChannel.PORTAL,
            scheduled_at=datetime(2026, 10, 28, 9, 0),
            event_status=OutreachEventStatus.PENDING,
            delivery_status=DeliveryStatus.PENDING,
            attempt_count=0,
            sent_at=None,
            completed_at=None,
            last_error=None,
        )
        self.service.repository.list_due_events.return_value = [self.event]
        self.service.repository.get_workflow.return_value = SimpleNamespace(
            checkin_template_id=77,
            max_attempts=3,
            retry_interval_minutes=30,
        )
        self.service.repository.get_template.return_value = SimpleNamespace(
            expiry_after_hours=24,
            template_name="Day 2 Follow-up Appointment",
        )
        self.service.repository.get_campaign.return_value = SimpleNamespace(
            campaign_id=12,
            organization_id=7,
            created_by_user_id=8,
        )
        self.service.repository.get_patient.return_value = (
            SimpleNamespace(preferred_language="en"),
            SimpleNamespace(user_id=42),
        )
        self.service.repository.get_active_sender.return_value = SimpleNamespace(user_id=8)
        self.service.repository.get_session.return_value = None
        self.service.repository.get_thread.return_value = None

        def add(entity):
            if entity.__class__.__name__ == "ConversationThread":
                entity.thread_id = 901
            elif entity.__class__.__name__ == "CheckinSession":
                entity.checkin_session_id = 902
            return entity

        self.service.repository.add.side_effect = add

    def test_delivers_due_portal_checkin(self):
        result = self.service.process_due_events(datetime(2026, 10, 28, 9, 1))

        self.assertEqual(result, {"scanned": 1, "delivered": 1, "failed": 0})
        self.assertEqual(self.event.event_status, OutreachEventStatus.PENDING)
        self.assertEqual(self.event.delivery_status, DeliveryStatus.SENT)
        self.assertEqual(self.event.attempt_count, 1)
        self.assertEqual(self.event.scheduled_at, datetime(2026, 10, 28, 9, 31))
        self.assertIsNotNone(self.event.sent_at)
        self.db.commit.assert_called_once()
        self.assertEqual(self.service.repository.add.call_count, 4)
        session = next(
            entity for entity in self.service.repository.add.call_args_list[1:]
            if entity.args[0].__class__.__name__ == "CheckinSession"
        )
        self.assertEqual(session.args[0].expires_at, datetime(2026, 10, 29, 9, 0))

    def test_retries_incomplete_session_at_workflow_interval(self):
        session = SimpleNamespace(session_status=CheckinSessionStatus.IN_PROGRESS)
        self.service.repository.get_session.return_value = session

        self.service._deliver_event(self.event, datetime(2026, 10, 28, 9, 31))

        self.assertEqual(self.event.event_status, OutreachEventStatus.PENDING)
        self.assertEqual(self.event.attempt_count, 1)
        self.assertEqual(self.event.scheduled_at, datetime(2026, 10, 28, 10, 1))
        self.assertEqual(self.event.delivery_status, DeliveryStatus.SENT)
        self.service.repository.add.assert_called_once()

    def test_rejects_non_portal_delivery(self):
        self.event.channel = OutreachEventChannel.SMS
        failed_event = SimpleNamespace(
            outreach_event_id=501,
            event_status=OutreachEventStatus.PENDING,
            delivery_status=DeliveryStatus.PENDING,
            attempt_count=0,
            completed_at=None,
            last_error=None,
        )
        self.db.query.return_value.filter_by.return_value.one_or_none.return_value = failed_event

        result = self.service.process_due_events(datetime(2026, 10, 28, 9, 1))

        self.assertEqual(result, {"scanned": 1, "delivered": 0, "failed": 1})
        self.assertEqual(failed_event.event_status, OutreachEventStatus.PENDING)
        self.assertEqual(failed_event.delivery_status, DeliveryStatus.FAILED)
        self.assertEqual(failed_event.attempt_count, 1)
        self.assertEqual(failed_event.scheduled_at, datetime(2026, 10, 28, 9, 31))
        self.db.rollback.assert_called_once()

    def test_expires_due_pending_sessions(self):
        session = SimpleNamespace(session_status=CheckinSessionStatus.PENDING)
        self.service.repository.list_expired_sessions.return_value = [session]

        result = self.service.expire_sessions(datetime(2026, 10, 30, 9, 0))

        self.assertEqual(result, {"scanned": 1, "expired": 1})
        self.assertEqual(session.session_status, CheckinSessionStatus.EXPIRED)
        self.db.commit.assert_called_once()


if __name__ == "__main__":
    unittest.main()