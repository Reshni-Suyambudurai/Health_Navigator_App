"""Database access for system-admin organization management."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models.audit_log import AuditLog
from app.database.models.organization import Organization
from app.database.models.role import Role, RoleName
from app.database.models.user import User, UserStatus


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def find_admin_user(self, user_id: int) -> User | None:
        return (
            self.db.query(User)
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.user_id == user_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.SYSTEM_ADMIN,
            )
            .one_or_none()
        )

    def find_by_id(self, organization_id: int) -> Organization | None:
        return (
            self.db.query(Organization)
            .filter(Organization.organization_id == organization_id)
            .one_or_none()
        )

    def count_users(self, organization_id: int) -> int:
        return (
            self.db.query(func.count(User.user_id))
            .filter(User.organization_id == organization_id)
            .scalar()
            or 0
        )

    def organization_name_exists(self, organization_name: str, excluded_id: int) -> bool:
        return (
            self.db.query(Organization.organization_id)
            .filter(
                func.lower(Organization.organization_name) == organization_name.lower(),
                Organization.organization_id != excluded_id,
            )
            .first()
            is not None
        )

    def email_exists(self, email: str, excluded_user_id: int) -> bool:
        return (
            self.db.query(User.user_id)
            .filter(func.lower(User.email) == email.lower(), User.user_id != excluded_user_id)
            .first()
            is not None
        )

    def save_with_audit(self, organization: Organization, contact: User, audit_log: AuditLog) -> None:
        try:
            self.db.add_all([organization, contact, audit_log])
            self.db.commit()
            self.db.refresh(organization)
            self.db.refresh(contact)
        except Exception:
            self.db.rollback()
            raise