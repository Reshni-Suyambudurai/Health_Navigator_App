"""Database operations for clinical guardrail management."""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database.models.notification import Notification


class ClinicalGuardrailRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_actor(self, user_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT u.user_id, u.organization_id, r.role_name::text AS role_name,
                       CONCAT(u.first_name, ' ', u.last_name) AS display_name
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE u.user_id = :user_id AND u.status = 'ACTIVE'
                """
            ),
            {"user_id": user_id},
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_governance_users(self, organization_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT u.user_id, u.organization_id
                FROM users u
                JOIN roles r ON r.role_id = u.role_id
                WHERE u.organization_id = :organization_id
                  AND u.status = 'ACTIVE'
                  AND r.role_name = 'CLINICAL_GOVERNANCE'
                ORDER BY u.user_id
                """
            ),
            {"organization_id": organization_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_handler_roles(self) -> list[dict[str, Any]]:
        rows = self.db.execute(
            text(
                """
                SELECT role_id, role_name::text AS role_name
                FROM roles
                ORDER BY role_name
                """
            )
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_rules(self, *, include_matchers: bool = False) -> list[dict[str, Any]]:
        rules = self.db.execute(
            text(
                """
                SELECT r.rule_id, r.guardrail_id, g.guardrail_name,
                       g.guardrail_markdown AS description,
                       r.rule_name, r.rule_category::text AS category,
                       r.urgency_level::text AS urgency,
                       r.handler_role_id, hr.role_name::text AS handler_role,
                       r.action_type::text AS action_type,
                       r.status::text AS status,
                       r.approval_status::text AS approval_status,
                       r.patient_response_template,
                       r.target_queue_type::text AS target_queue_type,
                       r.escalation_type::text AS escalation_type,
                       r.escalation_priority::text AS escalation_priority,
                       r.created_by_user_id,
                       CONCAT(cu.first_name, ' ', cu.last_name) AS created_by_name,
                       cu.organization_id AS creator_organization_id,
                       r.approved_by_user_id,
                       CONCAT(au.first_name, ' ', au.last_name) AS approved_by_name,
                       r.approved_at, r.effective_from, r.rejection_reason,
                       r.created_at, r.updated_at,
                       COUNT(DISTINCT h.guardrail_hit_id) AS hit_count,
                       MAX(h.created_at) AS last_hit_at,
                       COUNT(DISTINCT ee.emergency_event_id) AS emergency_event_count
                FROM clinical_guardrail_rules r
                JOIN clinical_guardrail g ON g.guardrail_id = r.guardrail_id
                LEFT JOIN roles hr ON hr.role_id = r.handler_role_id
                LEFT JOIN users cu ON cu.user_id = r.created_by_user_id
                LEFT JOIN users au ON au.user_id = r.approved_by_user_id
                LEFT JOIN conversation_guardrail_hits h ON h.rule_id = r.rule_id
                LEFT JOIN emergency_events ee ON ee.guardrail_hit_id = h.guardrail_hit_id
                GROUP BY r.rule_id, g.guardrail_id, g.guardrail_name,
                         g.guardrail_markdown, hr.role_name, cu.user_id, au.user_id
                ORDER BY g.guardrail_name, r.updated_at DESC, r.rule_id
                """
            )
        ).mappings().all()
        matcher_rows = []
        if include_matchers:
            matcher_rows = self.db.execute(
                text(
                    """
                    SELECT matcher_id, rule_id, pattern, match_type::text AS match_type,
                           priority, is_active, created_at, updated_at
                    FROM clinical_guardrail_matchers
                    ORDER BY rule_id, priority, matcher_id
                    """
                )
            ).mappings().all()
        history_rows = self.db.execute(
            text(
                """
                SELECT a.audit_id, a.resource_id AS rule_id, a.action, a.details,
                       a.created_at,
                       CONCAT(u.first_name, ' ', u.last_name) AS actor_name
                FROM audit_logs a
                LEFT JOIN users u ON u.user_id = a.user_id
                                WHERE a.resource_type = 'CARE_PLAN'
                                    AND a.details LIKE '%guardrail_%'
                ORDER BY a.created_at DESC, a.audit_id DESC
                """
            )
        ).mappings().all()

        matcher_map: dict[int, list[dict[str, Any]]] = {}
        for row in matcher_rows:
            matcher_map.setdefault(row["rule_id"], []).append(self._serialize(row))
        history_map: dict[int, list[dict[str, Any]]] = {}
        for row in history_rows:
            item = self._serialize(row)
            try:
                item["details"] = json.loads(item["details"]) if item.get("details") else None
            except (TypeError, json.JSONDecodeError):
                pass
            history_map.setdefault(row["rule_id"], []).append(item)

        result: list[dict[str, Any]] = []
        for row in rules:
            item = self._serialize(row)
            if include_matchers:
                item["matchers"] = matcher_map.get(row["rule_id"], [])
            item["activity_history"] = history_map.get(row["rule_id"], [])
            result.append(item)
        return result

    def find_guardrail(self, guardrail_id: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT guardrail_id, guardrail_name, guardrail_markdown AS description,
                       created_at, updated_at
                FROM clinical_guardrail
                WHERE guardrail_id = :guardrail_id
                """
            ),
            {"guardrail_id": guardrail_id},
        ).mappings().one_or_none()
        return self._serialize(row) if row else None

    def find_rule(self, rule_id: int, *, for_update: bool = False) -> dict[str, Any] | None:
        lock = " FOR UPDATE" if for_update else ""
        row = self.db.execute(
            text(
                """
                SELECT r.rule_id, r.guardrail_id, g.guardrail_name,
                       g.guardrail_markdown AS description,
                       r.rule_name, r.rule_category::text AS category,
                       r.urgency_level::text AS urgency, r.handler_role_id,
                       r.action_type::text AS action_type,
                       r.status::text AS status,
                       r.approval_status::text AS approval_status,
                       r.patient_response_template,
                       r.target_queue_type::text AS target_queue_type,
                       r.escalation_type::text AS escalation_type,
                       r.escalation_priority::text AS escalation_priority,
                       r.created_by_user_id, r.approved_by_user_id,
                       r.approved_at, r.effective_from, r.rejection_reason,
                       r.created_at, r.updated_at
                FROM clinical_guardrail_rules r
                JOIN clinical_guardrail g ON g.guardrail_id = r.guardrail_id
                WHERE r.rule_id = :rule_id
                """ + lock
            ),
            {"rule_id": rule_id},
        ).mappings().one_or_none()
        return self._serialize(row) if row else None

    def create_guardrail(self, name: str, description: str) -> int:
        self.db.execute(text("LOCK TABLE clinical_guardrail IN SHARE ROW EXCLUSIVE MODE"))
        guardrail_id = self.db.execute(
            text("SELECT COALESCE(MAX(guardrail_id), 0) + 1 FROM clinical_guardrail")
        ).scalar_one()
        self.db.execute(
            text(
                """
                INSERT INTO clinical_guardrail (
                    guardrail_id, guardrail_name, guardrail_markdown,
                    created_at, updated_at
                ) VALUES (
                    :guardrail_id, :name, :description,
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            {"guardrail_id": guardrail_id, "name": name, "description": description},
        )
        return guardrail_id

    def create_rule(self, guardrail_id: int, creator_user_id: int, values: dict[str, Any]) -> int:
        self.db.execute(text("LOCK TABLE clinical_guardrail_rules IN SHARE ROW EXCLUSIVE MODE"))
        rule_id = self.db.execute(
            text("SELECT COALESCE(MAX(rule_id), 0) + 1 FROM clinical_guardrail_rules")
        ).scalar_one()
        self.db.execute(
            text(
                """
                INSERT INTO clinical_guardrail_rules (
                    rule_id, guardrail_id, rule_name, rule_category,
                    urgency_level, handler_role_id, action_type, status,
                    patient_response_template, target_queue_type,
                    escalation_type, escalation_priority, created_by_user_id,
                    approval_status, created_at, updated_at
                ) VALUES (
                    :rule_id, :guardrail_id, :rule_name,
                        :category, :urgency, :handler_role_id,
                        :action_type, 'DRAFT',
                    :patient_response_template,
                        :target_queue_type,
                        :escalation_type,
                        :escalation_priority,
                    :creator_user_id, 'DRAFT', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                )
                """
            ),
            values
            | {
                "rule_id": rule_id,
                "guardrail_id": guardrail_id,
                "creator_user_id": creator_user_id,
            },
        )
        return rule_id

    def update_rule(self, rule_id: int, values: dict[str, Any]) -> None:
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail
                SET guardrail_name = :guardrail_name,
                    guardrail_markdown = :description,
                    updated_at = CURRENT_TIMESTAMP
                WHERE guardrail_id = (
                    SELECT guardrail_id FROM clinical_guardrail_rules
                    WHERE rule_id = :rule_id
                )
                """
            ),
            values | {"rule_id": rule_id},
        )
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail_rules
                SET rule_name = :rule_name,
                        rule_category = :category,
                        urgency_level = :urgency,
                    handler_role_id = :handler_role_id,
                        action_type = :action_type,
                    patient_response_template = :patient_response_template,
                        target_queue_type = :target_queue_type,
                        escalation_type = :escalation_type,
                        escalation_priority = :escalation_priority,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_id = :rule_id
                """
            ),
            values | {"rule_id": rule_id},
        )
    def set_pending(self, rule_id: int) -> None:
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail_rules
                SET approval_status = 'PENDING', status = 'DRAFT',
                    rejection_reason = NULL, approved_by_user_id = NULL,
                    approved_at = NULL, effective_from = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_id = :rule_id
                """
            ),
            {"rule_id": rule_id},
        )

    def approve(self, rule_id: int, reviewer_user_id: int, effective_from: Any) -> None:
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail_rules
                SET approval_status = 'APPROVED', status = 'ACTIVE',
                    approved_by_user_id = :reviewer_user_id,
                    approved_at = CURRENT_TIMESTAMP,
                    effective_from = :effective_from,
                    rejection_reason = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_id = :rule_id
                """
            ),
            {
                "rule_id": rule_id,
                "reviewer_user_id": reviewer_user_id,
                "effective_from": effective_from,
            },
        )

    def reject(self, rule_id: int, reason: str) -> None:
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail_rules
                SET approval_status = 'REJECTED', status = 'DRAFT',
                    rejection_reason = :reason, approved_by_user_id = NULL,
                    approved_at = NULL, effective_from = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE rule_id = :rule_id
                """
            ),
            {"rule_id": rule_id, "reason": reason},
        )

    def deactivate(self, rule_id: int) -> None:
        self.db.execute(
            text(
                """
                UPDATE clinical_guardrail_rules
                SET status = 'INACTIVE', updated_at = CURRENT_TIMESTAMP
                WHERE rule_id = :rule_id
                """
            ),
            {"rule_id": rule_id},
        )

    def stage_audit(
        self,
        *,
        user_id: int,
        event_type: str,
        resource_id: int,
        details: dict[str, Any],
    ) -> None:
        self.db.execute(text("LOCK TABLE audit_logs IN SHARE ROW EXCLUSIVE MODE"))
        audit_id = self.db.execute(
            text("SELECT COALESCE(MAX(audit_id), 0) + 1 FROM audit_logs")
        ).scalar_one()
        self.db.execute(
            text(
                """
                INSERT INTO audit_logs (
                    audit_id, user_id, action, resource_type,
                    resource_id, details, created_at
                ) VALUES (
                    :audit_id, :user_id, 'UPDATE_CARE_PLAN', 'CARE_PLAN',
                    :resource_id, :details, CURRENT_TIMESTAMP
                )
                """
            ),
            {
                "audit_id": audit_id,
                "user_id": user_id,
                "resource_id": resource_id,
                "details": json.dumps({"event_type": event_type} | details, default=str),
            },
        )

    def stage_notifications(self, notifications: list[Notification]) -> None:
        self.db.add_all(notifications)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    @staticmethod
    def _serialize(row: Any) -> dict[str, Any]:
        return {
            key: value.isoformat() if hasattr(value, "isoformat") else value
            for key, value in row.items()
        }