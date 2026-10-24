import json
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException
from app.database.models.organization import OrganizationStatus, OrganizationType
from app.services.navigator.organization_service import OrganizationService


class OrganizationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = OrganizationService(MagicMock())
        self.service.repository = MagicMock()

    def test_non_admin_cannot_view_organization(self):
        self.service.repository.find_admin_user.return_value = None

        with self.assertRaises(AuthorizationException):
            self.service.get_current_organization(42)

        self.service.repository.find_by_id.assert_not_called()

    def test_admin_update_saves_contact_and_audit_record(self):
        admin = SimpleNamespace(
            user_id=9,
            organization_id=3,
            first_name="Avery",
            last_name="Morgan",
            email="avery@hospital.test",
            phone="555-0100",
        )
        organization = SimpleNamespace(
            organization_id=3,
            organization_name="City Hospital",
            organization_type=OrganizationType.HOSPITAL,
            npi_number="1234567890",
            address="100 Main Street",
            phone="555-1000",
            status=OrganizationStatus.ACTIVE,
            created_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 2),
        )
        self.service.repository.find_admin_user.return_value = admin
        self.service.repository.find_by_id.return_value = organization
        self.service.repository.organization_name_exists.return_value = False
        self.service.repository.email_exists.return_value = False
        self.service.repository.count_users.return_value = 18

        result = self.service.update_current_organization(
            user_id=9,
            data={
                "organization_name": "City Medical Center",
                "organization_type": "HEALTHCARE_GROUP",
                "status": "ACTIVE",
                "contact_first_name": "Alex",
                "contact_email": "alex@hospital.test",
            },
            ip_address="127.0.0.1",
            correlation_id="organization-test",
        )

        self.assertEqual(organization.organization_name, "City Medical Center")
        self.assertEqual(organization.organization_type, OrganizationType.HEALTHCARE_GROUP)
        self.assertEqual(admin.first_name, "Alex")
        self.assertEqual(admin.email, "alex@hospital.test")
        self.assertEqual(result["user_count"], 18)

        _, _, audit_log = self.service.repository.save_with_audit.call_args.args
        self.assertEqual(audit_log.user_id, 9)
        self.assertEqual(audit_log.resource_type, "ORGANIZATION")
        self.assertEqual(audit_log.resource_id, 3)
        details = json.loads(audit_log.details)
        self.assertIn("organization_name", details["changed_fields"])
        self.assertIn("contact_email", details["changed_fields"])


if __name__ == "__main__":
    unittest.main()