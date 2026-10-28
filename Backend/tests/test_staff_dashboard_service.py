import unittest
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.exceptions import AuthorizationException, ValidationException
from app.database.models.role import RoleName
from app.database.models.user import UserStatus
from app.services.navigator.staff_dashboard_service import StaffDashboardService


class StaffDashboardServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = StaffDashboardService(MagicMock())
        self.service.repository = MagicMock()
        self.user = SimpleNamespace(user_id=20, organization_id=4, status=UserStatus.ACTIVE)
        self.staff = SimpleNamespace(staff_id=70)
        self.role = SimpleNamespace(role_name=RoleName.PHARMACIST)
        self.service.repository.find_context.return_value = (self.user, self.staff, self.role)
        self.service.repository.list_assigned_escalations.return_value = []
        self.service.repository.list_checkin_escalations.return_value = []
        self.service.repository.list_appointments.return_value = []

    def test_today_bounds_use_midnight_and_exclusive_tomorrow(self):
        start, end = self.service._period_bounds(
            "TODAY",
            now=datetime(2026, 10, 28, 21, 15),
        )

        self.assertEqual(start, datetime(2026, 10, 28))
        self.assertEqual(end, datetime(2026, 10, 29))

    def test_this_month_bounds_handle_year_transition(self):
        start, end = self.service._period_bounds(
            "THIS_MONTH",
            now=datetime(2026, 12, 28, 21, 15),
        )

        self.assertEqual(start, datetime(2026, 12, 1))
        self.assertEqual(end, datetime(2027, 1, 1))

    def test_selected_dates_control_inclusive_range_bounds(self):
        result = self.service.get_analytics(
            20,
            "THIS_MONTH",
            date(2025, 2, 14),
            date(2025, 2, 20),
        )

        query_args = self.service.repository.list_assigned_escalations.call_args.args
        self.assertEqual(query_args[2], datetime(2025, 2, 14))
        self.assertEqual(query_args[3], datetime(2025, 2, 21))
        self.assertEqual(result["from_date"], "2025-02-14")
        self.assertEqual(result["to_date"], "2025-02-20")

    def test_rejects_reversed_date_range(self):
        with self.assertRaises(ValidationException):
            self.service.get_analytics(
                20,
                "THIS_MONTH",
                date(2025, 2, 20),
                date(2025, 2, 14),
            )

    def test_rejects_invalid_period(self):
        with self.assertRaises(ValidationException):
            self.service.get_analytics(20, "THIS_WEEK")

    def test_rejects_role_outside_pharmacist_and_social_worker(self):
        self.role.role_name = RoleName.CARE_MANAGER

        with self.assertRaises(AuthorizationException):
            self.service.get_analytics(20, "TODAY")

    def test_scopes_queries_to_resolved_staff_and_organization(self):
        result = self.service.get_analytics(20, "TODAY")

        escalation_args = self.service.repository.list_assigned_escalations.call_args.args
        checkin_args = self.service.repository.list_checkin_escalations.call_args.args
        appointment_args = self.service.repository.list_appointments.call_args.args
        self.assertEqual(escalation_args[:2], (70, 4))
        self.assertEqual(checkin_args[:2], (70, 4))
        self.assertEqual(appointment_args[:2], (70, 4))
        self.assertEqual(result["period"], "TODAY")

    def test_calculates_staff_metrics_and_detail_rows(self):
        assigned_at = datetime(2026, 10, 28, 9)
        self.service.repository.list_assigned_escalations.return_value = [
            SimpleNamespace(
                patient_id=1,
                escalation_type="EMERGENCY",
                priority="CRITICAL",
                status="ASSIGNED",
                reason="Urgent concern",
                assigned_at=assigned_at,
                first_name="Avery",
                last_name="Ng",
            ),
            SimpleNamespace(
                patient_id=1,
                escalation_type="MEDICATION",
                priority="MEDIUM",
                status="IN_PROGRESS",
                reason=None,
                assigned_at=assigned_at,
                first_name="Avery",
                last_name="Ng",
            ),
        ]
        self.service.repository.list_checkin_escalations.return_value = [
            SimpleNamespace(
                patient_id=2,
                escalation_type="ROUTINE",
                status="ASSIGNED",
                reason="Follow-up response",
                trigger_source="ANSWER_RISK",
                assigned_at=assigned_at,
                first_name="Morgan",
                last_name="Lee",
                response_text="I need assistance",
            )
        ]
        self.service.repository.list_appointments.return_value = [
            SimpleNamespace(
                appointment_type="CHECK-IN",
                status="SCHEDULED",
                appointment_datetime=assigned_at,
                location_or_channel="Phone",
                first_name="Morgan",
                last_name="Lee",
            )
        ]

        result = self.service.get_analytics(20, "THIS_MONTH")

        self.assertEqual(result["patients_escalated"], 1)
        self.assertEqual(result["emergency_escalations"], 1)
        self.assertEqual(result["routine_escalations"], 1)
        self.assertEqual(result["checkin_emergency_escalations"], 0)
        self.assertEqual(result["checkin_routine_escalations"], 1)
        self.assertEqual(result["appointments_count"], 1)
        self.assertEqual(result["details"]["appointments"][0]["patient"], "Morgan Lee")

    def test_recent_emergency_panels_return_newest_five(self):
        base_time = datetime(2026, 10, 28, 8)
        emergency_escalations = [
            SimpleNamespace(
                patient_id=index,
                escalation_type="EMERGENCY",
                priority="CRITICAL",
                status="ASSIGNED",
                reason=f"Emergency {index}",
                assigned_at=base_time.replace(hour=8 + index),
                first_name="Patient",
                last_name=str(index),
            )
            for index in range(7, 0, -1)
        ]
        emergency_checkins = [
            SimpleNamespace(
                patient_id=index,
                escalation_type="EMERGENCY",
                status="ASSIGNED",
                reason=f"Check-in {index}",
                response_text=f"Response {index}",
                trigger_source="ANSWER_RISK",
                assigned_at=base_time.replace(hour=8 + index),
                first_name="Checkin",
                last_name=str(index),
            )
            for index in range(7, 0, -1)
        ]
        self.service.repository.list_assigned_escalations.return_value = emergency_escalations
        self.service.repository.list_checkin_escalations.return_value = emergency_checkins

        details = self.service.get_analytics(20, "TODAY")["details"]

        self.assertEqual(len(details["recent_emergency_escalations"]), 5)
        self.assertEqual(len(details["recent_emergency_checkins"]), 5)
        self.assertEqual(details["recent_emergency_escalations"][0]["patient_id"], 7)
        self.assertEqual(details["recent_emergency_checkins"][0]["response"], "Response 7")


if __name__ == "__main__":
    unittest.main()
