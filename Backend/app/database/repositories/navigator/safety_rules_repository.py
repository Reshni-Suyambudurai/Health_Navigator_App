import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SafetyRulesRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_active_role(self, user_id: int) -> str | None:
        return self.db.execute(text("""
            SELECT r.role_name::text FROM users u JOIN roles r ON r.role_id=u.role_id
            WHERE u.user_id=:user_id AND u.status='ACTIVE'
        """), {"user_id": user_id}).scalar_one_or_none()

    def list_rules(self) -> list[dict[str, Any]]:
        rules = self.db.execute(text("""
            SELECT r.rule_id, r.guardrail_id, g.guardrail_name, g.guardrail_markdown,
                   r.rule_name, r.rule_category::text AS category, r.urgency_level::text AS urgency,
                   r.action_type::text AS action_type, r.status::text AS status,
                   r.patient_response_template, r.target_queue_type::text AS target_queue_type,
                   r.escalation_type::text AS escalation_type, r.escalation_priority::text AS escalation_priority,
                   r.created_at, r.updated_at,
                   COUNT(DISTINCT h.guardrail_hit_id) AS hit_count,
                   MAX(h.created_at) AS last_hit_at,
                   COUNT(DISTINCT ee.emergency_event_id) AS emergency_event_count
            FROM clinical_guardrail_rules r
            JOIN clinical_guardrail g ON g.guardrail_id=r.guardrail_id
            LEFT JOIN conversation_guardrail_hits h ON h.rule_id=r.rule_id
            LEFT JOIN emergency_events ee ON ee.guardrail_hit_id=h.guardrail_hit_id
            GROUP BY r.rule_id, g.guardrail_id, g.guardrail_name, g.guardrail_markdown
            ORDER BY CASE r.status::text WHEN 'DRAFT' THEN 0 WHEN 'ACTIVE' THEN 1 ELSE 2 END,
                     r.updated_at DESC, r.rule_id
        """)).mappings().all()
        matchers = self.db.execute(text("""
            SELECT matcher_id, rule_id, pattern, match_type::text AS match_type,
                   priority, is_active, created_at, updated_at
            FROM clinical_guardrail_matchers ORDER BY rule_id, priority, matcher_id
        """)).mappings().all()
        history = self.db.execute(text("""
            SELECT a.audit_id, a.resource_id AS rule_id, a.action, a.details,
                   a.created_at, CONCAT(u.first_name,' ',u.last_name) AS actor_name
            FROM audit_logs a LEFT JOIN users u ON u.user_id=a.user_id
                        WHERE a.resource_type='CARE_PLAN' AND a.action='UPDATE_CARE_PLAN'
                            AND a.details LIKE '%guardrail_rule_approval%'
            ORDER BY a.created_at DESC
        """)).mappings().all()
        matcher_map: dict[int, list[dict[str, Any]]] = {}
        for matcher in matchers:
            matcher_map.setdefault(matcher["rule_id"], []).append(self._serialize(matcher))
        history_map: dict[int, list[dict[str, Any]]] = {}
        for event in history:
            item = self._serialize(event)
            try: item["details"] = json.loads(item["details"]) if item.get("details") else None
            except (TypeError, json.JSONDecodeError): pass
            history_map.setdefault(event["rule_id"], []).append(item)
        result = []
        for row in rules:
            item = self._serialize(row)
            item["matchers"] = matcher_map.get(row["rule_id"], [])
            item["approval_history"] = history_map.get(row["rule_id"], [])
            item["version"] = f"v1.{len(item['approval_history']) + 1}"
            item["last_reviewed_at"] = item["approval_history"][0]["created_at"] if item["approval_history"] else item["updated_at"]
            result.append(item)
        return result

    def approve_rule(self, rule_id: int, user_id: int, note: str) -> bool:
        row = self.db.execute(text("SELECT rule_name, status::text FROM clinical_guardrail_rules WHERE rule_id=:rule_id FOR UPDATE"), {"rule_id": rule_id}).mappings().one_or_none()
        if not row: return False
        self.db.execute(text("UPDATE clinical_guardrail_rules SET status='ACTIVE', updated_at=CURRENT_TIMESTAMP WHERE rule_id=:rule_id"), {"rule_id": rule_id})
        self.db.execute(text("""
            INSERT INTO audit_logs (audit_id,user_id,action,resource_type,resource_id,details,created_at)
            SELECT COALESCE(MAX(audit_id),0)+1,:user_id,'UPDATE_CARE_PLAN','CARE_PLAN',:rule_id,:details,CURRENT_TIMESTAMP FROM audit_logs
        """), {"user_id": user_id, "rule_id": rule_id, "details": json.dumps({"event_type": "guardrail_rule_approval", "note": note, "previous_status": row["status"], "rule_name": row["rule_name"]})})
        self.db.commit()
        return True

    @staticmethod
    def _serialize(row: Any) -> dict[str, Any]:
        return {key: value.isoformat() if hasattr(value, "isoformat") else value for key, value in row.items()}
