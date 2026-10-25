"""Authorization and read-only access for staff outreach events."""

from datetime import datetime
from typing import Any

from app.core.exceptions import AuthorizationException, NotFoundException, ValidationException
from app.database.models.role import RoleName
from app.database.repositories.navigator.outreach_event_access_repository import OutreachEventAccessRepository
from app.utils.audit_logger import AuditAction, AuditLogger


class OutreachEventAccessService:
    def __init__(self, db):
        self.db = db
        self.repository = OutreachEventAccessRepository(db)

    def list_events(self, actor_user_id: int, role: RoleName, organization_id: int, **filters: Any) -> dict[str, Any]:
        actor, staff_id = self._scope(actor_user_id, role)
        self._validate_organization(actor.organization_id, organization_id)
        self._validate_date_range(filters.get("scheduled_from"), filters.get("scheduled_to"))
        events, count = self.repository.list_events(actor.organization_id, staff_id, **filters)
        return {
            "events": events,
            "count": count,
            "has_more": filters["skip"] + len(events) < count,
        }

    def list_filter_options(
        self,
        actor_user_id: int,
        role: RoleName,
        organization_id: int,
        campaign_id: int | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        actor, staff_id = self._scope(actor_user_id, role)
        self._validate_organization(actor.organization_id, organization_id)
        return self.repository.list_filter_options(actor.organization_id, staff_id, campaign_id)

    def get_event(
        self,
        actor_user_id: int,
        role: RoleName,
        event_id: int,
        *,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        actor, staff_id = self._scope(actor_user_id, role)
        event = self.repository.get_event(event_id, actor.organization_id, staff_id)
        if event is None:
            raise NotFoundException("Outreach event not found", "OUTREACH_EVENT_NOT_FOUND")
        AuditLogger.add_entry(
            self.db,
            action=AuditAction.VIEW_OUTREACH_EVENT,
            resource_type="OUTREACH_EVENT",
            resource_id=event_id,
            user_id=actor_user_id,
            patient_id=event["patient_id"],
            ip_address=ip_address,
            correlation_id=correlation_id,
            details={"view": "detail"},
        )
        self.db.commit()
        return event

    def _scope(self, actor_user_id: int, role: RoleName):
        actor = self.repository.find_actor(actor_user_id)
        if actor is None or actor.role.role_name != role:
            raise AuthorizationException("The requested outreach event access is not available", "OUTREACH_EVENT_ACCESS_REQUIRED")
        staff_id = None
        if role == RoleName.CARE_MANAGER:
            staff = self.repository.find_staff_profile(actor_user_id)
            if staff is None:
                raise AuthorizationException("Care Manager staff profile is required", "STAFF_PROFILE_REQUIRED")
            staff_id = staff.staff_id
        return actor, staff_id

    @staticmethod
    def _validate_organization(actor_organization_id: int, requested_organization_id: int) -> None:
        if actor_organization_id != requested_organization_id:
            raise AuthorizationException("Organization access is not available", "ORGANIZATION_ACCESS_REQUIRED")

    @staticmethod
    def _validate_date_range(scheduled_from: datetime | None, scheduled_to: datetime | None) -> None:
        if scheduled_from and scheduled_to and scheduled_to <= scheduled_from:
            raise ValidationException("Scheduled end must be after scheduled start", "INVALID_DATE_RANGE")