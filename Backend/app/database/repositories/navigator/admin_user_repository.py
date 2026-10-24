"""Database operations for system-admin user management."""

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, aliased

from app.database.models.audit_log import AuditLog
from app.database.models.role import Role, RoleName
from app.database.models.user import User, UserStatus


class AdminUserRepository:
    ADMIN_AUDIT_ACTIONS = ("CREATE_USER", "UPDATE_USER", "DISABLE_USER", "ENABLE_USER")

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

    def find_organization_user(self, user_id: int, organization_id: int) -> User | None:
        return (
            self.db.query(User)
            .filter(User.user_id == user_id, User.organization_id == organization_id)
            .one_or_none()
        )

    def list_users(
        self,
        organization_id: int,
        skip: int,
        limit: int,
        search: str | None = None,
        role_name: RoleName | None = None,
        user_status: UserStatus | None = None,
    ) -> tuple[list[User], int]:
        query = self.db.query(User).join(Role, User.role_id == Role.role_id).filter(
            User.organization_id == organization_id
        )
        if search:
            pattern = f"%{search.lower()}%"
            query = query.filter(or_(
                func.lower(User.first_name).like(pattern),
                func.lower(User.last_name).like(pattern),
                func.lower(User.email).like(pattern),
            ))
        if role_name:
            query = query.filter(Role.role_name == role_name)
        if user_status:
            query = query.filter(User.status == user_status)

        total = query.count()
        users = query.order_by(User.first_name.asc(), User.last_name.asc()).offset(skip).limit(limit).all()
        return users, total

    def list_roles(self, role_names: tuple[RoleName, ...]) -> list[Role]:
        return (
            self.db.query(Role)
            .filter(Role.role_name.in_(role_names))
            .order_by(Role.role_name.asc())
            .all()
        )

    def find_role(self, role_name: RoleName) -> Role | None:
        return self.db.query(Role).filter(Role.role_name == role_name).one_or_none()

    def email_exists(self, email: str, excluded_user_id: int | None = None) -> bool:
        query = self.db.query(User.user_id).filter(func.lower(User.email) == email.lower())
        if excluded_user_id is not None:
            query = query.filter(User.user_id != excluded_user_id)
        return query.first() is not None

    def count_active_system_admins(self, organization_id: int) -> int:
        return (
            self.db.query(func.count(User.user_id))
            .join(Role, User.role_id == Role.role_id)
            .filter(
                User.organization_id == organization_id,
                User.status == UserStatus.ACTIVE,
                Role.role_name == RoleName.SYSTEM_ADMIN,
            )
            .scalar()
            or 0
        )

    def save_with_audit(self, user: User, audit_log: AuditLog) -> User:
        try:
            self.db.add(user)
            self.db.flush()
            if audit_log.resource_id is None:
                audit_log.resource_id = user.user_id
            self.db.add(audit_log)
            self.db.commit()
            self.db.refresh(user)
            return user
        except Exception:
            self.db.rollback()
            raise

    def list_audit_trail(
        self,
        organization_id: int,
        skip: int,
        limit: int,
        action: str | None = None,
    ) -> tuple[list[tuple[AuditLog, User | None, User]], int]:
        actor = aliased(User)
        target = aliased(User)
        query = (
            self.db.query(AuditLog, actor, target)
            .outerjoin(actor, AuditLog.user_id == actor.user_id)
            .join(target, AuditLog.resource_id == target.user_id)
            .filter(
                AuditLog.resource_type == "USER",
                AuditLog.action.in_(self.ADMIN_AUDIT_ACTIONS),
                target.organization_id == organization_id,
            )
        )
        if action:
            query = query.filter(AuditLog.action == action)

        total = query.count()
        rows = query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()
        return rows, total