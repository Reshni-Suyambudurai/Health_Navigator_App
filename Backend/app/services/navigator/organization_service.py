"""Business logic for system-admin organization management."""

from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.organization import OrganizationStatus, OrganizationType
from app.database.repositories.navigator.organization_repository import OrganizationRepository
from app.utils.audit_logger import AuditAction, AuditLogger


class OrganizationService:
    ORGANIZATION_FIELDS = {
        "organization_name",
        "organization_type",
        "npi_number",
        "address",
        "phone",
        "status",
    }
    CONTACT_FIELDS = {
        "contact_first_name": "first_name",
        "contact_last_name": "last_name",
        "contact_email": "email",
        "contact_phone": "phone",
    }

    def __init__(self, db: Session):
        self.repository = OrganizationRepository(db)

    def get_current_organization(self, user_id: int) -> dict[str, Any]:
        admin = self._require_admin(user_id)
        organization = self.repository.find_by_id(admin.organization_id)
        if not organization:
            raise NotFoundException("Organization not found", "ORGANIZATION_NOT_FOUND")
        return self._serialize(organization, admin)

    def update_current_organization(
        self,
        user_id: int,
        data: dict[str, Any],
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        admin = self._require_admin(user_id)
        organization = self.repository.find_by_id(admin.organization_id)
        if not organization:
            raise NotFoundException("Organization not found", "ORGANIZATION_NOT_FOUND")

        organization_name = data.get("organization_name")
        if organization_name and self.repository.organization_name_exists(
            organization_name,
            organization.organization_id,
        ):
            raise ConflictException("Organization name already exists", "ORGANIZATION_NAME_EXISTS")

        contact_email = data.get("contact_email")
        if contact_email and self.repository.email_exists(contact_email, admin.user_id):
            raise ConflictException("Contact email already belongs to another user", "CONTACT_EMAIL_EXISTS")

        before = self._audit_snapshot(organization, admin)
        for field in self.ORGANIZATION_FIELDS:
            if field not in data:
                continue
            value = data[field]
            if field == "organization_type":
                value = self._enum(OrganizationType, value, "organization type")
            elif field == "status":
                value = self._enum(OrganizationStatus, value, "organization status")
            setattr(organization, field, value)

        for request_field, model_field in self.CONTACT_FIELDS.items():
            if request_field in data:
                setattr(admin, model_field, data[request_field])

        after = self._audit_snapshot(organization, admin)
        changed_fields = [key for key in before if before[key] != after[key]]
        if not changed_fields:
            raise ValidationException("No organization changes were provided", "NO_ORGANIZATION_CHANGES")

        audit_log = AuditLogger.create_entry(
            user_id=admin.user_id,
            action=AuditAction.UPDATE_USER,
            resource_type="ORGANIZATION",
            resource_id=organization.organization_id,
            details={
                "changed_fields": changed_fields,
                "before": before,
                "after": after,
            },
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        try:
            self.repository.save_with_audit(organization, admin, audit_log)
        except SQLAlchemyError as exc:
            raise ConflictException("Organization update conflicts with existing data", "ORGANIZATION_UPDATE_CONFLICT") from exc

        return self._serialize(organization, admin)

    def _require_admin(self, user_id: int):
        admin = self.repository.find_admin_user(user_id)
        if not admin:
            raise AuthorizationException(
                "Active system administrator access is required",
                "SYSTEM_ADMIN_ACCESS_REQUIRED",
            )
        return admin

    @staticmethod
    def _enum(enum_type, value: str, label: str):
        try:
            return enum_type(value)
        except ValueError as exc:
            allowed = ", ".join(item.value for item in enum_type)
            raise ValidationException(
                f"Invalid {label}. Expected one of: {allowed}",
                "INVALID_ENUM_VALUE",
            ) from exc

    def _serialize(self, organization, admin) -> dict[str, Any]:
        return {
            "organization_id": organization.organization_id,
            "organization_name": organization.organization_name,
            "organization_type": organization.organization_type.value,
            "npi_number": organization.npi_number,
            "address": organization.address,
            "phone": organization.phone,
            "status": organization.status.value,
            "created_at": organization.created_at.isoformat() if organization.created_at else None,
            "updated_at": organization.updated_at.isoformat() if organization.updated_at else None,
            "user_count": self.repository.count_users(organization.organization_id),
            "contact": {
                "user_id": admin.user_id,
                "first_name": admin.first_name,
                "last_name": admin.last_name,
                "email": admin.email,
                "phone": admin.phone,
            },
        }

    @staticmethod
    def _audit_snapshot(organization, admin) -> dict[str, Any]:
        return {
            "organization_name": organization.organization_name,
            "organization_type": organization.organization_type.value,
            "npi_number": organization.npi_number,
            "address": organization.address,
            "phone": organization.phone,
            "status": organization.status.value,
            "contact_first_name": admin.first_name,
            "contact_last_name": admin.last_name,
            "contact_email": admin.email,
            "contact_phone": admin.phone,
        }