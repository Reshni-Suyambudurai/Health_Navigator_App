import unittest

from main import app


class ClinicalGuardrailRouteTests(unittest.TestCase):
    def test_workflow_routes_are_registered_once_with_expected_methods(self):
        expected = {
            ("/api/v1/clinical-guardrails", "GET"),
            ("/api/v1/clinical-guardrails", "POST"),
            ("/api/v1/clinical-guardrails/{guardrail_id}/rules", "POST"),
            ("/api/v1/clinical-guardrails/rules/submit", "POST"),
            ("/api/v1/clinical-guardrails/rules/{rule_id}", "PUT"),
            ("/api/v1/clinical-guardrails/rules/{rule_id}/approve", "POST"),
            ("/api/v1/clinical-guardrails/rules/{rule_id}/reject", "POST"),
            ("/api/v1/clinical-guardrails/rules/{rule_id}/deactivate", "POST"),
            ("/api/v1/clinical-guardrails/rules/{rule_id}/activate", "PUT"),
        }
        registered = [
            (route.path, method)
            for route in app.routes
            if route.path.startswith("/api/v1/clinical-guardrails")
            for method in route.methods
            if method not in {"HEAD", "OPTIONS"}
        ]

        self.assertEqual(set(registered), expected)
        self.assertEqual(len(registered), len(expected))


if __name__ == "__main__":
    unittest.main()