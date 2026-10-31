import json
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class SafetyEvaluationRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_active_role(self, user_id: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT u.user_id,u.organization_id,r.role_name::text AS role_name
            FROM users u JOIN roles r ON r.role_id=u.role_id
            WHERE u.user_id=:user_id AND u.status='ACTIVE'
        """), {"user_id": user_id}).mappings().one_or_none()
        return dict(row) if row else None

    def list_organizations(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self.db.execute(text("""
            SELECT organization_id,organization_name FROM organizations
            WHERE status='ACTIVE' ORDER BY organization_name
        """)).mappings().all()]

    def organization_exists(self, organization_id: int) -> bool:
        return self.db.execute(text("SELECT 1 FROM organizations WHERE organization_id=:id"), {"id": organization_id}).first() is not None

    def evidence_counts(self, organization_id: int) -> dict[str, Any]:
        row = self.db.execute(text("""
            SELECT
              COUNT(DISTINCT h.guardrail_hit_id) AS total_hits,
              COUNT(DISTINCT h.guardrail_hit_id) FILTER (WHERE h.hit_urgency_level::text IN ('EMERGENCY','HIGH')) AS emergency_hits,
              COUNT(DISTINCT ee.emergency_event_id) AS emergency_events,
              COUNT(DISTINCT ee.emergency_event_id) FILTER (WHERE ee.emergency_instruction_sent) AS instructions_sent,
              COUNT(DISTINCT ee.emergency_event_id) FILTER (WHERE ee.notified_care_team) AS teams_notified,
              COUNT(DISTINCT ee.emergency_event_id) FILTER (WHERE ee.event_status::text IN ('RESOLVED','CLOSED')) AS events_resolved,
              COUNT(DISTINCT e.escalation_id) FILTER (WHERE h.hit_urgency_level::text IN ('EMERGENCY','HIGH')) AS emergency_escalations
            FROM conversation_guardrail_hits h
            JOIN patient_profiles pp ON pp.patient_id=h.patient_id
            JOIN users u ON u.user_id=pp.user_id
            LEFT JOIN emergency_events ee ON ee.guardrail_hit_id=h.guardrail_hit_id
            LEFT JOIN escalations e ON e.guardrail_hit_id=h.guardrail_hit_id
            WHERE u.organization_id=:organization_id
        """), {"organization_id": organization_id}).mappings().one()
        coverage = self.db.execute(text("""
            SELECT COUNT(*) AS active_rules,
              COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM clinical_guardrail_matchers m WHERE m.rule_id=r.rule_id AND m.is_active)) AS covered_rules
            FROM clinical_guardrail_rules r WHERE r.status='ACTIVE'
        """)).mappings().one()
        evidence = self.db.execute(text("""
            SELECT h.guardrail_hit_id, h.rule_id, h.hit_urgency_level::text AS urgency,
                   h.action_taken::text AS action_taken, h.hit_reason, h.created_at,
                   ee.emergency_event_id, ee.event_status::text AS event_status,
                   ee.emergency_instruction_sent, ee.notified_care_team,
                   e.escalation_id
            FROM conversation_guardrail_hits h
            JOIN patient_profiles pp ON pp.patient_id=h.patient_id
            JOIN users u ON u.user_id=pp.user_id
            LEFT JOIN emergency_events ee ON ee.guardrail_hit_id=h.guardrail_hit_id
            LEFT JOIN escalations e ON e.guardrail_hit_id=h.guardrail_hit_id
            WHERE u.organization_id=:organization_id
            ORDER BY h.created_at DESC LIMIT 50
        """), {"organization_id": organization_id}).mappings().all()
        return {**dict(row), **dict(coverage), "evidence": [self._serialize(item) for item in evidence]}

    def list_decisions(self, organization_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT a.audit_id,a.user_id,a.details,a.created_at,CONCAT(u.first_name,' ',u.last_name) AS reviewer_name
            FROM audit_logs a LEFT JOIN users u ON u.user_id=a.user_id
            WHERE a.resource_type='CARE_PLAN' AND a.action='UPDATE_CARE_PLAN'
              AND a.details LIKE '%safety_evaluation_decision%'
            ORDER BY a.created_at DESC
        """)).mappings().all()
        decisions=[]
        for row in rows:
            try: details=json.loads(row["details"] or "{}")
            except json.JSONDecodeError: continue
            if int(details.get("organization_id",0)) != organization_id: continue
            item=self._serialize(row); item["details"]=details; decisions.append(item)
        return decisions

    def record_decision(self, user_id: int, organization_id: int, result_key: str, decision: str, notes: str, evidence: dict[str, Any]) -> None:
        details=json.dumps({"event_type":"safety_evaluation_decision","organization_id":organization_id,"result_key":result_key,"decision":decision,"notes":notes,"evidence":evidence})
        self.db.execute(text("""
            INSERT INTO audit_logs (audit_id,user_id,action,resource_type,resource_id,details,created_at)
            SELECT COALESCE(MAX(audit_id),0)+1,:user_id,'UPDATE_CARE_PLAN','CARE_PLAN',NULL,:details,CURRENT_TIMESTAMP FROM audit_logs
        """), {"user_id":user_id,"details":details})
        self.db.commit()

    @staticmethod
    def _serialize(row: Any) -> dict[str, Any]:
        return {key:value.isoformat() if isinstance(value,datetime) else value for key,value in row.items()}
