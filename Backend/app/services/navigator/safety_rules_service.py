from typing import Any

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.repositories.navigator.safety_rules_repository import SafetyRulesRepository


class SafetyRulesService:
    URGENCY_RANK = {"EMERGENCY": 0, "HIGH": 1, "SAME_DAY": 1, "ROUTINE": 2}

    def __init__(self, db):
        self.repository = SafetyRulesRepository(db)

    def get_overview(self, user_id: int) -> dict[str, Any]:
        self._authorize(user_id)
        rules = self.repository.list_rules()
        return {
            "summary": {
                "total_rules": len(rules),
                "active_rules": sum(1 for rule in rules if rule["status"] == "ACTIVE"),
                "draft_rules": sum(1 for rule in rules if rule["status"] == "DRAFT"),
                "emergency_rules": sum(1 for rule in rules if rule["category"] == "EMERGENCY"),
                "hits_30_days": sum(int(rule["hit_count"] or 0) for rule in rules),
            },
            "rules": rules,
        }

    def approve_rule(self, rule_id: int, user_id: int, note: str) -> None:
        self._authorize(user_id)
        if not note.strip(): raise ValidationException("An approval note is required.", "APPROVAL_NOTE_REQUIRED")
        if not self.repository.approve_rule(rule_id, user_id, note.strip()):
            raise NotFoundException("Guardrail rule not found.", "GUARDRAIL_RULE_NOT_FOUND")

    def test_scenario(self, user_id: int, text: str, rule_id: int | None = None) -> dict[str, Any]:
        self._authorize(user_id)
        normalized = " ".join(text.lower().split())
        if not normalized: raise ValidationException("A patient scenario is required.", "SCENARIO_REQUIRED")
        rules = self.repository.list_rules()
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
        role = self.repository.find_active_role(user_id)
        if role not in {"CLINICAL_GOVERNANCE", "SYSTEM_ADMIN"}:
            raise AuthorizationException("Only clinical governance users can manage safety rules.", "SAFETY_RULES_ACCESS_DENIED")
