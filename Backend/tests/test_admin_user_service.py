import json
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

import bcrypt

from app.core.exceptions import NotFoundException, ValidationException
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.services.navigator.admin_user_service import AdminUserService


class AdminUserServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = AdminUserService(MagicMock())
        self.service.repository = MagicMock()
        self.admin_role = SimpleNamespace(role_id=9, role_name=RoleName.SYSTEM_ADMIN)
        self.admin = SimpleNamespace(
            user_id=4,
            organization_id=1,
            role=self.admin_role,
            status=UserStatus.ACTIVE,
        )
        self.service.repository.find_admin_user.return_value = self.admin

    def test_create_user_hashes_password_and_excludes_it_from_audit(self):
        role = SimpleNamespace(role_id=2, role_name=RoleName.CARE_MANAGER)
        self.service.repository.find_role.return_value = role
        self.service.repository.email_exists.return_value = False

        def save_user(user, _audit_log):
            user.user_id = 20

        self.service.repository.save_with_audit.side_effect = save_user

        result = self.service.create_user(
            4,
            {
                "first_name": "Avery",
                "last_name": "Morgan",
                "email": " AVERY@EXAMPLE.COM ",
                "phone": "555-0100",
                "password": "TempPass123",
                "role_name": "CARE_MANAGER",
            },
            correlation_id="create-user-test",
        )

        user, audit_log = self.service.repository.save_with_audit.call_args.args
        self.assertTrue(bcrypt.checkpw(b"TempPass123", user.password_hash.encode("utf-8")))
        self.assertEqual(user.organization_id, 1)
        self.assertTrue(user.is_verified)
        self.assertEqual(result["email"], "avery@example.com")
        self.assertEqual(audit_log.action, "CREATE_USER")
        details = json.loads(audit_log.details)
        self.assertNotIn("password", json.dumps(details).lower())

    def test_update_rejects_user_outside_admin_organization(self):
        self.service.repository.find_organization_user.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.update_user(4, 99, {"first_name": "No Access"})

    def test_status_change_creates_disable_audit(self):
        role = SimpleNamespace(role_id=2, role_name=RoleName.CARE_MANAGER)
        target = SimpleNamespace(
            user_id=10,
            organization_id=1,
            organization=None,
            role_id=2,
            role=role,
            first_name="Casey",
            last_name="Lee",
            email="casey@example.com",
            phone=None,
            status=UserStatus.ACTIVE,
            created_at=None,
            updated_at=None,
        )
        self.service.repository.find_organization_user.return_value = target

        result = self.service.update_status(4, 10, "SUSPENDED")

        _, audit_log = self.service.repository.save_with_audit.call_args.args
        self.assertEqual(result["status"], "SUSPENDED")
        self.assertEqual(audit_log.action, "DISABLE_USER")
        self.assertEqual(audit_log.resource_id, 10)

    def test_admin_cannot_disable_self(self):
        target = SimpleNamespace(
            user_id=4,
            organization_id=1,
            role=self.admin_role,
            status=UserStatus.ACTIVE,
        )
        self.service.repository.find_organization_user.return_value = target

        with self.assertRaises(ValidationException):
            self.service.update_status(4, 4, "INACTIVE")

        self.service.repository.save_with_audit.assert_not_called()

    def test_last_active_admin_cannot_be_disabled(self):
        target = SimpleNamespace(
            user_id=8,
            organization_id=1,
            role=self.admin_role,
            status=UserStatus.ACTIVE,
        )
        self.service.repository.find_organization_user.return_value = target
        self.service.repository.count_active_system_admins.return_value = 1

        with self.assertRaises(ValidationException):
            self.service.update_status(4, 8, "SUSPENDED")

        self.service.repository.save_with_audit.assert_not_called()


if __name__ == "__main__":
    unittest.main()