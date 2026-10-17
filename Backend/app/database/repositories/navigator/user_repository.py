"""
User Repository - Data access layer for User operations
Similar to Spring Boot's UserRepository interface
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional, List
from app.database.models.user import User, UserStatus


class UserRepository:
    """
    Repository for User database operations
    Similar to Spring Boot's JpaRepository<User, Long>
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def find_by_id(self, user_id: int) -> Optional[User]:
        """Find user by ID (like findById in Spring)"""
        return self.db.query(User).filter(User.user_id == user_id).first()
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email (like findByEmail in Spring)"""
        return self.db.query(User).filter(User.email == email).first()
    
    def find_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination (like findAll with Pageable)"""
        return self.db.query(User).offset(skip).limit(limit).all()
    
    def find_by_organization_id(self, organization_id: int) -> List[User]:
        """Find users by organization"""
        return self.db.query(User).filter(User.organization_id == organization_id).all()
    
    def find_by_status(self, status: UserStatus) -> List[User]:
        """Find users by status"""
        return self.db.query(User).filter(User.status == status).all()
    
    def save(self, user: User) -> User:
        """Save or update user (like save in Spring)"""
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def delete(self, user_id: int) -> bool:
        """Delete user by ID (like deleteById in Spring)"""
        user = self.find_by_id(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
    
    def exists_by_email(self, email: str) -> bool:
        """Check if user exists by email (like existsByEmail in Spring)"""
        return self.db.query(User).filter(User.email == email).count() > 0
    
    def count(self) -> int:
        """Count all users (like count in Spring)"""
        return self.db.query(User).count()
