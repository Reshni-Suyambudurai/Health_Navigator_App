import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException, NotFoundException
from app.database.models.notification import NotificationPriority, NotificationStatus, NotificationType
from app.database.models.role import RoleName
from app.services.notification_service import NotificationService


class NotificationServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = NotificationService(MagicMock())
        self.service.repository = MagicMock()
        self.sender = SimpleNamespace(user_id=4, organization_id=7, first_name="System", last_name="Admin")
        self.recipient = SimpleNamespace(user_id=8, organization_id=7, first_name="Clinical", last_name="Reviewer")
        self.service.repository.find_active_user.side_effect = self.find_user

    def find_user(self, user_id):
        return {4: self.sender, 8: self.recipient}.get(user_id)

    @staticmethod
    def notification(status=NotificationStatus.UNREAD):
        return SimpleNamespace(
            notification_id=20,
            organization_id=7,
            sender_user_id=4,
            recipient_user_id=8,
            title="Review available",
            message="A check-in template is ready for review.",
            notification_type=NotificationType.GENERAL,
            priority=NotificationPriority.NORMAL,
            status=status,
            created_at=None,
            read_at=None,
        )

    def test_create_notification_scopes_to_sender_organization_and_unread(self):
        def save(notification):
            notification.notification_id = 20
            notification.created_at = None
            notification.read_at = None

        self.service.repository.save.side_effect = save

        result = self.service.create_notification(
            sender_user_id=4,
            recipient_user_id=8,
            title="Review available",
            message="A check-in template is ready for review.",
        )

        notification = self.service.repository.save.call_args.args[0]
        self.assertEqual(notification.organization_id, 7)
        self.assertEqual(notification.status, NotificationStatus.UNREAD)
        self.assertEqual(result["status"], "UNREAD")

    def test_create_notification_rejects_cross_organization_recipient(self):
        other = SimpleNamespace(user_id=9, organization_id=10)
        self.service.repository.find_active_user.side_effect = lambda user_id: self.sender if user_id == 4 else other

        with self.assertRaises(AuthorizationException):
            self.service.create_notification(4, 9, "Not allowed")

        self.service.repository.save.assert_not_called()

    def test_list_returns_repository_unread_count(self):
        notification = self.notification()
        self.service.repository.list_for_recipient.return_value = ([(notification, self.sender)], 1)
        self.service.repository.count_unread.return_value = 1

        result = self.service.list_notifications(8)

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["unread_count"], 1)
        self.assertEqual(result["notifications"][0]["notification_id"], 20)

    def test_prepare_for_role_targets_every_active_recipient(self):
        second_recipient = SimpleNamespace(user_id=9, organization_id=7)
        self.service.repository.list_active_users_by_role.return_value = [self.recipient, second_recipient]

        notifications = self.service.prepare_for_role(
            sender_user_id=4,
            organization_id=7,
            role_name=RoleName.CLINICAL_GOVERNANCE,
            title="Review requested",
            message="A template needs review.",
            notification_type=NotificationType.FOLLOW_UP,
            priority=NotificationPriority.HIGH,
        )

        self.assertEqual([item.recipient_user_id for item in notifications], [8, 9])
        self.assertTrue(all(item.status == NotificationStatus.UNREAD for item in notifications))

    def test_marking_final_unread_notification_removes_unread_count(self):
        notification = self.notification()
        self.service.repository.find_for_recipient.return_value = (notification, self.sender)
        self.service.repository.count_unread.return_value = 0

        result = self.service.mark_read(8, 20)
        count = self.service.unread_count(8)

        self.assertEqual(result["status"], "READ")
        self.assertIsNotNone(notification.read_at)
        self.service.repository.save.assert_called_once_with(notification)
        self.assertEqual(count["unread_count"], 0)

    def test_recipient_cannot_open_another_users_notification(self):
        self.service.repository.find_for_recipient.return_value = None

        with self.assertRaises(NotFoundException):
            self.service.get_notification(8, 99)


if __name__ == "__main__":
    unittest.main()
