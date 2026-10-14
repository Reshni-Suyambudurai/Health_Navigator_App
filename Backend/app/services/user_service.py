"""
User Service - Business logic layer
Similar to Spring Boot's @Service
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from app.database.repositories.user_repository import UserRepository
from app.database.models.user import User
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
    ValidationException,
    ConflictException
)
import bcrypt
import logging

logger = logging.getLogger(__name__)


class UserService:
    """
    Business logic for User operations
    Similar to Spring Boot's UserService with @Service annotation
    """
    
    def __init__(self, db: Session):
        self.repository = UserRepository(db)
    
    def login(self, email: str, password: str) -> dict:
        """
        Login user - verify email, password, and active status
        Returns: dict with role_id and username
        Raises: AuthenticationException, AuthorizationException
        """
        logger.info(f"Login attempt for email: {email}")
        
        # Get user by email
        user = self.repository.find_by_email(email)
        
        if not user:
            logger.warning(f"Login failed: User not found for email {email}")
            raise AuthenticationException("Invalid email or password")
        
        # Check if user is active
        if user.status.value != "ACTIVE":
            logger.warning(f"Login failed: User {email} is not active (status: {user.status.value})")
            raise AuthorizationException("User account is not active")
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Login failed: Invalid password for email {email}")
            raise AuthenticationException("Invalid email or password")
        
        logger.info(f"Login successful for user: {email}")
        
        return {
            "role_id": user.role_id,
            "username": f"{user.first_name} {user.last_name}"
        }
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """
        Get user by ID with business logic
        Similar to: public User getUserById(Long id)
        """
        logger.info(f"Fetching user with ID: {user_id}")
        user = self.repository.find_by_id(user_id)
        
        if not user:
            logger.warning(f"User not found: {user_id}")
            return None
        
        return user
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        Similar to: public User getUserByEmail(String email)
        """
        logger.info(f"Fetching user with email: {email}")
        return self.repository.find_by_email(email)
    
    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """
        Get all users with pagination
        Similar to: public Page<User> getAllUsers(Pageable pageable)
        """
        logger.info(f"Fetching all users (skip={skip}, limit={limit})")
        return self.repository.find_all(skip, limit)
    
    def create_user(self, user: User) -> User:
        """
        Create new user with validation
        Similar to: public User createUser(User user)
        """
        logger.info(f"Creating new user: {user.email}")
        
        # Business logic: Check if email already exists
        if self.repository.exists_by_email(user.email):
            logger.error(f"Email already exists: {user.email}")
            raise ValueError(f"User with email {user.email} already exists")
        
        # Save user
        created_user = self.repository.save(user)
        logger.info(f"User created successfully: {created_user.user_id}")
        
        return created_user
    
    def update_user(self, user_id: int, user_data: dict) -> Optional[User]:
        """
        Update existing user
        Similar to: public User updateUser(Long id, User userData)
        """
        logger.info(f"Updating user: {user_id}")
        
        user = self.repository.find_by_id(user_id)
        if not user:
            logger.warning(f"User not found for update: {user_id}")
            return None
        
        # Update fields
        for key, value in user_data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        
        updated_user = self.repository.save(user)
        logger.info(f"User updated successfully: {user_id}")
        
        return updated_user
    
    def delete_user(self, user_id: int) -> bool:
        """
        Delete user
        Similar to: public void deleteUser(Long id)
        """
        logger.info(f"Deleting user: {user_id}")
        
        success = self.repository.delete(user_id)
        if success:
            logger.info(f"User deleted successfully: {user_id}")
        else:
            logger.warning(f"User not found for deletion: {user_id}")
        
        return success
    
    def get_active_users(self) -> List[User]:
        """
        Get all active users
        Similar to: public List<User> getActiveUsers()
        """
        logger.info("Fetching all active users")
        return self.repository.find_by_status(UserStatus.ACTIVE)
