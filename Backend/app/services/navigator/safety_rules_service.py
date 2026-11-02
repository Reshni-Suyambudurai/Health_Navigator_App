from datetime import date
from typing import Any

from app.core.exceptions import AuthorizationException, ValidationException
from app.database.repositories.clinical_guardrail_repository import ClinicalGuardrailRepository
from app.services.clinical_guardrail_service import ClinicalGuardrailService


class SafetyRulesService:
    URGENCY_RANK = {"EMERGENCY": 0, "HIGH": 1, "SAME_DAY": 1, "ROUTINE": 2}
    VALID_VALUES = {
        "category": {"EMERGENCY", "MEDICATION", "SYMPTOM", "PRIVACY", "CLINICAL_SCOPE", "SYMPTOM_SAFETY"},
        "urgency": {"ROUTINE", "SAME_DAY", "EMERGENCY", "HIGH"},
        "action_type": {"SAFE_RESPOND", "BLOCK_RESPONSE", "ESCALATE", "EMERGENCY_PROTOCOL", "CREATE_ESCALATION"},
        "status": {"DRAFT", "ACTIVE", "INACTIVE", "RETIRED"},
        "target_queue_type": {"MEDICATION", "APPOINTMENT", "SOCIAL_SUPPORT", "CLINICAL", "CLINICAL_REVIEW", "EMERGENCY"},
        "escalation_type": {"MEDICATION", "APPOINTMENT", "SOCIAL_SUPPORT", "CLINICAL_REVIEW", "EMERGENCY"},
        "escalation_priority": {"LOW", "MEDIUM", "HIGH", "CRITICAL"},
    }

    def __init__(self, db):
        self.repository = ClinicalGuardrailRepository(db)
        self.guardrails = ClinicalGuardrailService(db)

    def get_overview(self, user_id: int) -> dict[str, Any]:
        self._authorize(user_id)
        return self.guardrails.get_overview(user_id)

    def approve_rule(self, rule_id: int, user_id: int, note: str) -> None:
        self._authorize(user_id)
        self.guardrails.approve_rule(rule_id, user_id, note, date.today())

    def update_rule(self, rule_id: int, user_id: int, values: dict[str, Any]) -> None:
        self._authorize(user_id)
        raise ValidationException(
            "Use the inactive-rule activation workflow to update approved rules.",
            "GUARDRAIL_WORKFLOW_REQUIRED",
        )

    def test_scenario(self, user_id: int, text: str, rule_id: int | None = None) -> dict[str, Any]:
        self._authorize(user_id)
        normalized = " ".join(text.lower().split())
        if not normalized: raise ValidationException("A patient scenario is required.", "SCENARIO_REQUIRED")
        rules = self.repository.list_rules(include_matchers=True)
        candidates = []
        for rule in rules:
            if rule_id is not None and rule["rule_id"] != rule_id: continue
            for matcher in rule["matchers"]:
                if not matcher["is_active"]: continue
                pattern = " ".join(matcher["pattern"].lower().split())
                if matcher["match_type"] == "ALL_TERMS":
                    terms = [term.strip() for term in pattern.split("|") if term.strip()]
                    matched = bool(terms) and all(term in normalized for term in terms)
                else:
                    matched = pattern in normalized
                if matched:
                    candidates.append((self.URGENCY_RANK.get(rule["urgency"], 3), matcher["priority"], rule, matcher))
        if not candidates: return {"matched": False, "rule": None, "matcher": None, "side_effects_created": False}
        _, _, rule, matcher = min(candidates, key=lambda candidate: (candidate[0], candidate[1], candidate[2]["rule_id"]))
        return {"matched": True, "rule": rule, "matcher": matcher, "side_effects_created": False}

    def _authorize(self, user_id: int) -> None:
        actor = self.repository.find_actor(user_id)
        if actor is None or actor["role_name"] not in {"CLINICAL_GOVERNANCE", "SYSTEM_ADMIN"}:
            raise AuthorizationException("Only clinical governance users can manage safety rules.", "SAFETY_RULES_ACCESS_DENIED")
