"""Shared audit-log entry construction."""

import json
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLog


class AuditAction(str, Enum):
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    FAILED_LOGIN = "FAILED_LOGIN"
    VIEW_PATIENT = "VIEW_PATIENT"
    UPDATE_PATIENT = "UPDATE_PATIENT"
    VIEW_MEDICATION = "VIEW_MEDICATION"
    VIEW_CONVERSATION = "VIEW_CONVERSATION"
    CREATE_ESCALATION = "CREATE_ESCALATION"
    UPDATE_ESCALATION = "UPDATE_ESCALATION"
    CLOSE_ESCALATION = "CLOSE_ESCALATION"
    VIEW_CARE_PLAN = "VIEW_CARE_PLAN"
    UPDATE_CARE_PLAN = "UPDATE_CARE_PLAN"
    VIEW_APPOINTMENT = "VIEW_APPOINTMENT"
    UPDATE_APPOINTMENT = "UPDATE_APPOINTMENT"
    CREATE_USER = "CREATE_USER"
    UPDATE_USER = "UPDATE_USER"
    DISABLE_USER = "DISABLE_USER"
    ENABLE_USER = "ENABLE_USER"


class AuditLogger:
    """Build audit records for persistence in a repository transaction."""

    @classmethod
    def create_entry(
        cls,
        *,
        action: AuditAction | str,
        resource_type: str,
        user_id: int | None = None,
        patient_id: int | None = None,
        resource_id: int | None = None,
        details: Mapping[str, Any] | str | None = None,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> AuditLog:
        return AuditLog(
            user_id=user_id,
            patient_id=patient_id,
            action=AuditAction(action).value,
            resource_type=resource_type,
            resource_id=resource_id,
            details=cls._serialize_details(details),
            ip_address=ip_address,
            correlation_id=correlation_id,
        )

    @classmethod
    def add_entry(cls, db: Session, **entry_data: Any) -> AuditLog:
        """Stage an audit entry without committing the repository transaction."""
        entry = cls.create_entry(**entry_data)
        db.add(entry)
        return entry

    @classmethod
    def _serialize_details(cls, details: Mapping[str, Any] | str | None) -> str | None:
        if details is None or isinstance(details, str):
            return details
        return json.dumps(details, default=cls._json_default)

    @staticmethod
    def _json_default(value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")