"""Business rules for clinical guardrail management."""

from datetime import date
from typing import Any

from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.core.exceptions import (
    AuthorizationException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.database.models.notification import (
    Notification,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from app.database.repositories.clinical_guardrail_repository import (
    ClinicalGuardrailRepository,
)
class ClinicalGuardrailService:
    VIEW_ROLES = {"CARE_MANAGER", "CLINICAL_GOVERNANCE", "SYSTEM_ADMIN"}
    GOVERNANCE_ROLES = {"CLINICAL_GOVERNANCE", "SYSTEM_ADMIN"}

    def __init__(self, db):
        self.repository = ClinicalGuardrailRepository(db)

    def get_overview(self, user_id: int) -> dict[str, Any]:
        self._require_actor(user_id, self.VIEW_ROLES)
        rules = self.repository.list_rules()
        guardrails: dict[int, dict[str, Any]] = {}
        for rule in rules:
            guardrail = guardrails.setdefault(
                rule["guardrail_id"],
                {
                    "guardrail_id": rule["guardrail_id"],
                    "guardrail_name": rule["guardrail_name"],
                    "description": rule["description"],
                    "rules": [],
                },
            )
            guardrail["rules"].append(rule)
        return {
            "summary": {
                "total_guardrails": len(guardrails),
                "total_rules": len(rules),
                "active_rules": sum(rule["status"] == "ACTIVE" for rule in rules),
                "inactive_rules": sum(rule["status"] == "INACTIVE" for rule in rules),
                "pending_rules": sum(rule["approval_status"] == "PENDING" for rule in rules),
                "draft_rules": sum(rule["approval_status"] == "DRAFT" for rule in rules),
                "rejected_rules": sum(rule["approval_status"] == "REJECTED" for rule in rules),
                "emergency_rules": sum(rule["category"] == "EMERGENCY" for rule in rules),
                "hits_30_days": sum(int(rule["hit_count"] or 0) for rule in rules),
            },
            "guardrails": list(guardrails.values()),
            "rules": rules,
            "handler_roles": self.repository.list_handler_roles(),
        }

    def create_guardrail(self, user_id: int, values: dict[str, Any]) -> dict[str, Any]:
        actor = self._require_actor(user_id, {"CARE_MANAGER"})
        name = self._required_text(values.get("guardrail_name"), "Guardrail name")
        description = self._required_text(values.get("description"), "Description")
        rules = values.get("rules") or []
        if not rules:
            raise ValidationException("At least one rule is required.", "GUARDRAIL_RULE_REQUIRED")
        try:
            guardrail_id = self.repository.create_guardrail(name, description)
            rule_ids = []
            for rule_values in rules:
                payload = self._normalize_rule(rule_values)
                rule_id = self.repository.create_rule(guardrail_id, user_id, payload)
                rule_ids.append(rule_id)
                self.repository.stage_audit(
                    user_id=user_id,
                    event_type="guardrail_rule_created",
                    resource_id=rule_id,
                    details={
                        "guardrail_id": guardrail_id,
                        "guardrail_name": name,
                        "after": self._audit_payload(payload),
                    },
                )
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_created",
                resource_id=rule_ids[0],
                details={
                    "guardrail_id": guardrail_id,
                    "guardrail_name": name,
                    "rule_ids": rule_ids,
                },
            )
            self.repository.commit()
            return {"guardrail_id": guardrail_id, "rule_ids": rule_ids}
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictException(
                "A guardrail or matcher with the same name already exists.",
                "GUARDRAIL_DUPLICATE",
            ) from exc
        except Exception:
            self.repository.rollback()
            raise

    def add_rule(self, guardrail_id: int, user_id: int, values: dict[str, Any]) -> dict[str, int]:
        self._require_actor(user_id, {"CARE_MANAGER"})
        guardrail = self.repository.find_guardrail(guardrail_id)
        if guardrail is None:
            raise NotFoundException("Clinical guardrail not found.", "GUARDRAIL_NOT_FOUND")
        payload = self._normalize_rule(values)
        try:
            rule_id = self.repository.create_rule(guardrail_id, user_id, payload)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_created",
                resource_id=rule_id,
                details={
                    "guardrail_id": guardrail_id,
                    "guardrail_name": guardrail["guardrail_name"],
                    "after": self._audit_payload(payload),
                },
            )
            self.repository.commit()
            return {"rule_id": rule_id}
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictException("A matcher pattern is duplicated.", "GUARDRAIL_MATCHER_DUPLICATE") from exc
        except Exception:
            self.repository.rollback()
            raise

    def update_draft_rule(self, rule_id: int, user_id: int, values: dict[str, Any]) -> dict[str, int]:
        self._require_actor(user_id, {"CARE_MANAGER"})
        payload = self._normalize_rule(values)
        payload["guardrail_name"] = self._required_text(values.get("guardrail_name"), "Guardrail name")
        payload["description"] = self._required_text(values.get("description"), "Description")
        try:
            rule = self._require_rule(rule_id, for_update=True)
            if rule["created_by_user_id"] != user_id:
                raise AuthorizationException(
                    "Care Managers can edit only rules they created.",
                    "GUARDRAIL_RULE_OWNER_REQUIRED",
                )
            if rule["approval_status"] not in {"DRAFT", "REJECTED"}:
                raise ValidationException(
                    "Only draft or rejected rules can be edited.",
                    "GUARDRAIL_RULE_NOT_EDITABLE",
                )
            self.repository.update_rule(rule_id, payload)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_updated",
                resource_id=rule_id,
                details={"before": rule, "after": self._audit_payload(payload)},
            )
            self.repository.commit()
            return {"rule_id": rule_id}
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictException("A guardrail or matcher value is duplicated.", "GUARDRAIL_DUPLICATE") from exc
        except Exception:
            self.repository.rollback()
            raise

    def submit_rules(self, user_id: int, rule_ids: list[int]) -> dict[str, Any]:
        actor = self._require_actor(user_id, {"CARE_MANAGER"})
        unique_ids = list(dict.fromkeys(rule_ids))
        if not unique_ids:
            raise ValidationException("At least one rule is required.", "GUARDRAIL_RULE_REQUIRED")
        try:
            recipients = self.repository.list_governance_users(actor["organization_id"])
            if not recipients:
                raise ValidationException(
                    "No active Clinical Governance reviewer is available in your organization.",
                    "GUARDRAIL_REVIEWER_REQUIRED",
                )
            notifications: list[Notification] = []
            submitted = []
            for rule_id in unique_ids:
                rule = self._require_rule(rule_id, for_update=True)
                if rule["created_by_user_id"] != user_id:
                    raise AuthorizationException(
                        "Care Managers can submit only rules they created.",
                        "GUARDRAIL_RULE_OWNER_REQUIRED",
                    )
                if rule["approval_status"] not in {"DRAFT", "REJECTED"}:
                    raise ConflictException(
                        "The rule is not eligible for submission.",
                        "INVALID_GUARDRAIL_TRANSITION",
                    )
                self.repository.set_pending(rule_id)
                self.repository.stage_audit(
                    user_id=user_id,
                    event_type="guardrail_rule_submitted",
                    resource_id=rule_id,
                    details={
                        "guardrail_id": rule["guardrail_id"],
                        "guardrail_name": rule["guardrail_name"],
                        "rule_name": rule["rule_name"],
                        "previous_approval_status": rule["approval_status"],
                        "approval_status": "PENDING",
                    },
                )
                notifications.extend(
                    self._notifications_for_recipients(
                        actor,
                        recipients,
                        "Clinical guardrail review required",
                        self._notification_message(rule, "submitted for review"),
                    )
                )
                submitted.append(rule_id)
            self.repository.stage_notifications(notifications)
            self.repository.commit()
            return {"rule_ids": submitted, "notified_reviewers": len(notifications)}
        except Exception:
            self.repository.rollback()
            raise

    def approve_rule(
        self,
        rule_id: int,
        user_id: int,
        reason: str,
        effective_from: date,
    ) -> dict[str, int]:
        actor = self._require_actor(user_id, self.GOVERNANCE_ROLES)
        reason = self._required_text(reason, "Approval reason")
        try:
            rule = self._require_rule(rule_id, for_update=True)
            self._validate_decision(rule, user_id)
            self.repository.approve(rule_id, user_id, effective_from)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_approved",
                resource_id=rule_id,
                details={
                    "guardrail_id": rule["guardrail_id"],
                    "guardrail_name": rule["guardrail_name"],
                    "rule_name": rule["rule_name"],
                    "reason": reason,
                    "effective_from": effective_from.isoformat(),
                    "previous_approval_status": rule["approval_status"],
                    "approval_status": "APPROVED",
                    "status": "ACTIVE",
                },
            )
            self._stage_creator_notification(actor, rule, "approved", reason)
            self.repository.commit()
            return {"rule_id": rule_id}
        except Exception:
            self.repository.rollback()
            raise

    def reject_rule(self, rule_id: int, user_id: int, reason: str) -> dict[str, int]:
        actor = self._require_actor(user_id, self.GOVERNANCE_ROLES)
        reason = self._required_text(reason, "Rejection reason")
        try:
            rule = self._require_rule(rule_id, for_update=True)
            self._validate_decision(rule, user_id)
            self.repository.reject(rule_id, reason)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_rejected",
                resource_id=rule_id,
                details={
                    "guardrail_id": rule["guardrail_id"],
                    "guardrail_name": rule["guardrail_name"],
                    "rule_name": rule["rule_name"],
                    "reason": reason,
                    "previous_approval_status": rule["approval_status"],
                    "approval_status": "REJECTED",
                    "status": "DRAFT",
                },
            )
            self._stage_creator_notification(actor, rule, "rejected", reason)
            self.repository.commit()
            return {"rule_id": rule_id}
        except Exception:
            self.repository.rollback()
            raise

    def deactivate_rule(self, rule_id: int, user_id: int, reason: str) -> dict[str, int]:
        self._require_actor(user_id, self.GOVERNANCE_ROLES)
        reason = self._required_text(reason, "Deactivation reason")
        try:
            rule = self._require_rule(rule_id, for_update=True)
            if rule["approval_status"] != "APPROVED" or rule["status"] != "ACTIVE":
                raise ConflictException(
                    "Only approved active rules can be deactivated.",
                    "INVALID_GUARDRAIL_TRANSITION",
                )
            self.repository.deactivate(rule_id)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_deactivated",
                resource_id=rule_id,
                details={
                    "guardrail_id": rule["guardrail_id"],
                    "rule_name": rule["rule_name"],
                    "reason": reason,
                    "previous_status": "ACTIVE",
                    "status": "INACTIVE",
                },
            )
            self.repository.commit()
            return {"rule_id": rule_id}
        except Exception:
            self.repository.rollback()
            raise

    def activate_updated_rule(
        self,
        rule_id: int,
        user_id: int,
        values: dict[str, Any],
        change_reason: str,
        effective_from: date,
    ) -> dict[str, int]:
        actor = self._require_actor(user_id, self.GOVERNANCE_ROLES)
        reason = self._required_text(change_reason, "Change reason")
        payload = self._normalize_rule(values)
        payload["guardrail_name"] = self._required_text(values.get("guardrail_name"), "Guardrail name")
        payload["description"] = self._required_text(values.get("description"), "Description")
        try:
            rule = self._require_rule(rule_id, for_update=True)
            if rule["approval_status"] != "APPROVED" or rule["status"] != "INACTIVE":
                raise ConflictException(
                    "Only approved inactive rules can be updated and activated.",
                    "INVALID_GUARDRAIL_TRANSITION",
                )
            self.repository.update_rule(rule_id, payload)
            self.repository.approve(rule_id, user_id, effective_from)
            self.repository.stage_audit(
                user_id=user_id,
                event_type="guardrail_rule_activated",
                resource_id=rule_id,
                details={
                    "reason": reason,
                    "effective_from": effective_from.isoformat(),
                    "before": rule,
                    "after": self._audit_payload(payload) | {"status": "ACTIVE"},
                },
            )
            self._stage_creator_notification(actor, rule, "updated and activated", reason)
            self.repository.commit()
            return {"rule_id": rule_id}
        except IntegrityError as exc:
            self.repository.rollback()
            raise ConflictException("A guardrail or matcher value is duplicated.", "GUARDRAIL_DUPLICATE") from exc
        except Exception:
            self.repository.rollback()
            raise

    def _require_actor(self, user_id: int, allowed_roles: set[str]) -> dict[str, Any]:
        actor = self.repository.find_actor(user_id)
        if actor is None or actor["role_name"] not in allowed_roles:
            raise AuthorizationException(
                "You do not have access to clinical guardrail management.",
                "CLINICAL_GUARDRAIL_ACCESS_DENIED",
            )
        return actor

    def _require_rule(self, rule_id: int, *, for_update: bool) -> dict[str, Any]:
        rule = self.repository.find_rule(rule_id, for_update=for_update)
        if rule is None:
            raise NotFoundException("Clinical guardrail rule not found.", "GUARDRAIL_RULE_NOT_FOUND")
        return rule

    @staticmethod
    def _validate_decision(rule: dict[str, Any], reviewer_user_id: int) -> None:
        if rule["approval_status"] != "PENDING":
            raise ConflictException(
                "Only pending rules can be reviewed.",
                "INVALID_GUARDRAIL_TRANSITION",
            )
        if rule["created_by_user_id"] == reviewer_user_id:
            raise AuthorizationException(
                "You cannot review a rule you created.",
                "GUARDRAIL_SELF_APPROVAL_DENIED",
            )

    def _stage_creator_notification(
        self,
        actor: dict[str, Any],
        rule: dict[str, Any],
        action: str,
        reason: str,
    ) -> None:
        creator_id = rule.get("created_by_user_id")
        if creator_id is None:
            return
        creator = self.repository.find_actor(creator_id)
        if creator is None or creator["organization_id"] != actor["organization_id"]:
            return
        notification = self._build_notification(
            actor,
            creator,
            f"Clinical guardrail {action}",
            f"{self._notification_message(rule, action)} Reason: {reason}",
        )
        self.repository.stage_notifications([notification])

    def _notifications_for_recipients(
        self,
        actor: dict[str, Any],
        recipients: list[dict[str, Any]],
        title: str,
        message: str,
    ) -> list[Notification]:
        return [self._build_notification(actor, recipient, title, message) for recipient in recipients]

    @staticmethod
    def _build_notification(
        actor: dict[str, Any],
        recipient: dict[str, Any],
        title: str,
        message: str,
    ) -> Notification:
        return Notification(
            organization_id=actor["organization_id"],
            sender_user_id=actor["user_id"],
            recipient_user_id=recipient["user_id"],
            title=title,
            message=message,
            notification_type=NotificationType.SYSTEM_ALERT,
            priority=NotificationPriority.HIGH,
            status=NotificationStatus.UNREAD,
        )

    @staticmethod
    def _notification_message(rule: dict[str, Any], action: str) -> str:
        return (
            f"Guardrail '{rule['guardrail_name']}', rule '{rule['rule_name']}' was {action}. "
            f"Guardrail ID: {rule['guardrail_id']}; Rule ID: {rule['rule_id']}."
        )

    def _normalize_rule(self, values: dict[str, Any]) -> dict[str, Any]:
        payload = dict(values)
        payload["rule_name"] = self._required_text(payload.get("rule_name"), "Rule name")
        return payload

    @staticmethod
    def _required_text(value: Any, label: str) -> str:
        normalized = str(value).strip() if value is not None else ""
        if not normalized:
            raise ValidationException(f"{label} is required.", "GUARDRAIL_FIELD_REQUIRED")
        return normalized

    @staticmethod
    def _audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return dict(payload)