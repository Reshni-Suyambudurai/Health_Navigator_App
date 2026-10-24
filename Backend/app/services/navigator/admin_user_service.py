"""Business logic for organization-scoped system-admin user management."""

import json
import re
from typing import Any

import bcrypt
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import AuthorizationException, ConflictException, NotFoundException, ValidationException
from app.database.models.role import RoleName
from app.database.models.user import User, UserStatus
from app.database.repositories.navigator.admin_user_repository import AdminUserRepository
from app.utils.audit_logger import AuditAction, AuditLogger


class AdminUserService:
    ALLOWED_ROLES = (
        RoleName.PATIENT,
        RoleName.CARE_MANAGER,
        RoleName.TRANSITIONAL_CARE_NURSE,
        RoleName.PHARMACIST,
        RoleName.CLINICAL_GOVERNANCE,
        RoleName.SYSTEM_ADMIN,
    )
    EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def __init__(self, db: Session):
        self.repository = AdminUserRepository(db)

    def list_users(
        self,
        actor_user_id: int,
        skip: int = 0,
        limit: int = 25,
        search: str | None = None,
        role_name: str | None = None,
        user_status: str | None = None,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        role = self._parse_role(role_name) if role_name else None
        status = self._parse_status(user_status) if user_status else None
        users, total = self.repository.list_users(
            admin.organization_id,
            skip,
            limit,
            search.strip() if search else None,
            role,
            status,
        )
        return {"users": [self._serialize_user(user) for user in users], "count": total}

    def list_roles(self, actor_user_id: int) -> list[dict[str, Any]]:
        self._require_admin(actor_user_id)
        return [
            {
                "role_id": role.role_id,
                "role_name": role.role_name.value,
                "description": role.description,
            }
            for role in self.repository.list_roles(self.ALLOWED_ROLES)
        ]

    def create_user(
        self,
        actor_user_id: int,
        data: dict[str, Any],
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        first_name = self._required_text(data.get("first_name"), "First name")
        last_name = self._required_text(data.get("last_name"), "Last name")
        email = self._email(data.get("email"))
        role = self._required_role(data.get("role_name"))
        password = data.get("password", "")
        if len(password) < 8:
            raise ValidationException("Temporary password must contain at least 8 characters", "PASSWORD_TOO_SHORT")
        if self.repository.email_exists(email):
            raise ConflictException("User with this email already exists", "USER_EMAIL_EXISTS")

        user = User(
            organization_id=admin.organization_id,
            role_id=role.role_id,
            role=role,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=self._optional_text(data.get("phone")),
            password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
            status=UserStatus.ACTIVE,
            is_verified=True,
        )
        audit_log = AuditLogger.create_entry(
            user_id=admin.user_id,
            action=AuditAction.CREATE_USER,
            resource_type="USER",
            details={
                "changed_fields": ["first_name", "last_name", "email", "phone", "role_name", "status"],
                "before": None,
                "after": self._audit_snapshot(user),
            },
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        self._save(user, audit_log)
        return self._serialize_user(user)

    def update_user(
        self,
        actor_user_id: int,
        target_user_id: int,
        data: dict[str, Any],
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        admin, target = self._admin_and_target(actor_user_id, target_user_id)
        before = self._audit_snapshot(target)

        if "first_name" in data:
            target.first_name = self._required_text(data["first_name"], "First name")
        if "last_name" in data:
            target.last_name = self._required_text(data["last_name"], "Last name")
        if "email" in data:
            email = self._email(data["email"])
            if self.repository.email_exists(email, target.user_id):
                raise ConflictException("User with this email already exists", "USER_EMAIL_EXISTS")
            target.email = email
        if "phone" in data:
            target.phone = self._optional_text(data["phone"])
        if data.get("role_name") is not None:
            role = self._required_role(data["role_name"])
            current_role = target.role.role_name
            if current_role == RoleName.SYSTEM_ADMIN and role.role_name != RoleName.SYSTEM_ADMIN:
                self._protect_admin_change(admin, target)
            target.role_id = role.role_id
            target.role = role

        after = self._audit_snapshot(target)
        changed_fields = [field for field in before if before[field] != after[field]]
        if not changed_fields:
            raise ValidationException("No user changes were provided", "NO_USER_CHANGES")

        audit_log = AuditLogger.create_entry(
            user_id=admin.user_id,
            action=AuditAction.UPDATE_USER,
            resource_type="USER",
            resource_id=target.user_id,
            details={"changed_fields": changed_fields, "before": before, "after": after},
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        self._save(target, audit_log)
        return self._serialize_user(target)

    def update_status(
        self,
        actor_user_id: int,
        target_user_id: int,
        status_value: str,
        ip_address: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        admin, target = self._admin_and_target(actor_user_id, target_user_id)
        new_status = self._parse_status(status_value)
        if target.status == new_status:
            raise ValidationException("User already has this status", "USER_STATUS_UNCHANGED")
        if new_status != UserStatus.ACTIVE and target.role.role_name == RoleName.SYSTEM_ADMIN:
            self._protect_admin_change(admin, target)

        before = self._audit_snapshot(target)
        target.status = new_status
        after = self._audit_snapshot(target)
        action = AuditAction.ENABLE_USER if new_status == UserStatus.ACTIVE else AuditAction.DISABLE_USER
        audit_log = AuditLogger.create_entry(
            user_id=admin.user_id,
            action=action,
            resource_type="USER",
            resource_id=target.user_id,
            details={"changed_fields": ["status"], "before": before, "after": after},
            ip_address=ip_address,
            correlation_id=correlation_id,
        )
        self._save(target, audit_log)
        return self._serialize_user(target)

    def list_audit_trail(
        self,
        actor_user_id: int,
        skip: int = 0,
        limit: int = 25,
        action: str | None = None,
    ) -> dict[str, Any]:
        admin = self._require_admin(actor_user_id)
        normalized_action = action.upper() if action else None
        if normalized_action and normalized_action not in self.repository.ADMIN_AUDIT_ACTIONS:
            raise ValidationException("Invalid audit action", "INVALID_AUDIT_ACTION")
        rows, total = self.repository.list_audit_trail(
            admin.organization_id, skip, limit, normalized_action
        )
        entries = []
        for audit_log, actor, target in rows:
            try:
                details = json.loads(audit_log.details) if audit_log.details else None
            except json.JSONDecodeError:
                details = {"summary": audit_log.details}
            entries.append({
                "audit_id": audit_log.audit_id,
                "action": audit_log.action,
                "resource_id": audit_log.resource_id,
                "actor_name": f"{actor.first_name} {actor.last_name}" if actor else "System",
                "target_name": f"{target.first_name} {target.last_name}",
                "target_email": target.email,
                "details": details,
                "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
            })
        return {"entries": entries, "count": total}

    def _require_admin(self, user_id: int) -> User:
        admin = self.repository.find_admin_user(user_id)
        if not admin:
            raise AuthorizationException(
                "Active system administrator access is required",
                "SYSTEM_ADMIN_ACCESS_REQUIRED",
            )
        return admin

    def _admin_and_target(self, actor_user_id: int, target_user_id: int) -> tuple[User, User]:
        admin = self._require_admin(actor_user_id)
        target = self.repository.find_organization_user(target_user_id, admin.organization_id)
        if not target:
            raise NotFoundException("User not found", "USER_NOT_FOUND")
        return admin, target

    def _required_role(self, value: str | None):
        role_name = self._parse_role(value)
        role = self.repository.find_role(role_name)
        if not role:
            raise NotFoundException("Role not found", "ROLE_NOT_FOUND")
        return role

    def _parse_role(self, value: str | None) -> RoleName:
        try:
            role_name = RoleName((value or "").upper())
        except ValueError as exc:
            raise ValidationException("Invalid role assignment", "INVALID_ROLE") from exc
        if role_name not in self.ALLOWED_ROLES:
            raise AuthorizationException("This role cannot be assigned", "ROLE_ASSIGNMENT_FORBIDDEN")
        return role_name

    @staticmethod
    def _parse_status(value: str | None) -> UserStatus:
        try:
            return UserStatus((value or "").upper())
        except ValueError as exc:
            raise ValidationException("Invalid user status", "INVALID_USER_STATUS") from exc

    def _protect_admin_change(self, admin: User, target: User) -> None:
        if target.user_id == admin.user_id:
            raise ValidationException(
                "You cannot deactivate, suspend, or remove your own System Administrator role",
                "SELF_ADMIN_CHANGE_FORBIDDEN",
            )
        if self.repository.count_active_system_admins(admin.organization_id) <= 1:
            raise ValidationException(
                "The last active System Administrator cannot be disabled or demoted",
                "LAST_SYSTEM_ADMIN_REQUIRED",
            )

    @classmethod
    def _email(cls, value: str | None) -> str:
        email = (value or "").strip().lower()
        if not cls.EMAIL_PATTERN.match(email):
            raise ValidationException("Enter a valid email address", "INVALID_EMAIL")
        return email

    @staticmethod
    def _required_text(value: str | None, label: str) -> str:
        cleaned = (value or "").strip()
        if not cleaned:
            raise ValidationException(f"{label} is required", "REQUIRED_FIELD")
        return cleaned

    @staticmethod
    def _optional_text(value: str | None) -> str | None:
        cleaned = value.strip() if value else ""
        return cleaned or None

    def _save(self, user: User, audit_log) -> None:
        try:
            self.repository.save_with_audit(user, audit_log)
        except SQLAlchemyError as exc:
            raise ConflictException("User change conflicts with existing data", "USER_CHANGE_CONFLICT") from exc

    @staticmethod
    def _serialize_user(user: User) -> dict[str, Any]:
        return {
            "user_id": user.user_id,
            "organization_id": user.organization_id,
            "organization_name": user.organization.organization_name if user.organization else None,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role_id": user.role_id,
            "role_name": user.role.role_name.value,
            "status": user.status.value,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }

    @staticmethod
    def _audit_snapshot(user: User) -> dict[str, Any]:
        return {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "phone": user.phone,
            "role_name": user.role.role_name.value,
            "status": user.status.value,
        }