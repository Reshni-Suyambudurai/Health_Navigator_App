import unittest
from unittest.mock import MagicMock

from app.core.exceptions import ValidationException
from app.database.models.checkin_question import CheckinAnswerType, CheckinRiskLevel
from app.services.navigator.admin_checkin_template_service import AdminCheckinTemplateService


class AdminCheckinRiskConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.service = AdminCheckinTemplateService(MagicMock())

    def test_number_range_requires_complete_valid_boundaries(self):
        result = self.service._validate_critical_response(
            CheckinAnswerType.NUMBER,
            None,
            {"min": 1, "max": 5, "min_inclusive": True, "max_inclusive": False},
        )
        self.assertEqual(result["max"], 5)

        with self.assertRaises(ValidationException):
            self.service._validate_critical_response(
                CheckinAnswerType.NUMBER,
                None,
                {"min": 5, "max": 1, "min_inclusive": True, "max_inclusive": True},
            )

    def test_choice_critical_response_must_exist_in_options(self):
        with self.assertRaises(ValidationException):
            self.service._validate_critical_response(
                CheckinAnswerType.SINGLE_CHOICE,
                ["Yes", "No"],
                ["Maybe"],
            )

    def test_normal_risk_rejects_critical_response_and_destination(self):
        with self.assertRaises(ValidationException):
            self.service._validate_risk_configuration(
                CheckinRiskLevel.NORMAL,
                ["No"],
                None,
                12,
            )


if __name__ == "__main__":
    unittest.main()
