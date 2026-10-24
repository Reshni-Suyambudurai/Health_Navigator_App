import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from app.database.models.organization import OrganizationStatus
from app.utils.audit_logger import AuditAction, AuditLogger


class AuditLoggerTests(unittest.TestCase):
    def test_create_entry_serializes_structured_details(self):
        entry = AuditLogger.create_entry(
            user_id=7,
            action=AuditAction.UPDATE_USER,
            resource_type="ORGANIZATION",
            resource_id=3,
            details={
                "status": OrganizationStatus.ACTIVE,
                "changed_at": datetime(2026, 10, 24, 9, 30),
            },
            correlation_id="audit-test",
        )

        self.assertEqual(entry.action, "UPDATE_USER")
        self.assertEqual(entry.resource_type, "ORGANIZATION")
        self.assertEqual(entry.resource_id, 3)
        self.assertEqual(entry.correlation_id, "audit-test")
        self.assertEqual(
            json.loads(entry.details),
            {"status": "ACTIVE", "changed_at": "2026-10-24T09:30:00"},
        )

    def test_create_entry_rejects_unknown_database_action(self):
        with self.assertRaises(ValueError):
            AuditLogger.create_entry(action="UPDATE", resource_type="ORGANIZATION")

    def test_add_entry_stages_without_committing(self):
        db = MagicMock()

        entry = AuditLogger.add_entry(
            db,
            action=AuditAction.VIEW_PATIENT,
            resource_type="PATIENT",
            resource_id=11,
        )

        db.add.assert_called_once_with(entry)
        db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()