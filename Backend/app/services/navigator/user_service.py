"""
User Service - Business logic layer
Similar to Spring Boot's @Service
"""

from sqlalchemy.orm import Session
from typing import Optional, List
from app.database.repositories.navigator.user_repository import UserRepository
from app.database.models.user import User, UserStatus
from app.database.models.role import RoleName
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
    NotFoundException,
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
        Returns: dict with role and basic identity details for UI routing
        Raises: AuthenticationException, AuthorizationException
        """
        logger.info(f"Login attempt for email: {email}")
        
        # Get user by email
        user = self.repository.find_by_email(email)
        
        if not user:
            logger.warning(f"Login failed: User not found for email {email}")
            raise AuthenticationException("Invalid email or password")
        
        # Check if user is active and return tailored account-status message.
        if user.status != UserStatus.ACTIVE:
            status_value = user.status.value
            logger.warning(f"Login failed: User {email} is not active (status: {status_value})")

            if user.status == UserStatus.INACTIVE:
                raise AuthorizationException(
                    "Your account is inactive. Please contact support or your administrator."
                )

            if user.status == UserStatus.SUSPENDED:
                raise AuthorizationException(
                    "Your account is suspended. Please contact support or your administrator."
                )

            raise AuthorizationException(f"Your account is not active (status: {status_value}).")
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            logger.warning(f"Login failed: Invalid password for email {email}")
            raise AuthenticationException("Invalid email or password")
        
        logger.info(f"Login successful for user: {email}")

        role_name = None
        if user.role and user.role.role_name:
            role_name = user.role.role_name.value
        
        return {
            "user_id": user.user_id,
            "email": user.email,
            "role_id": user.role_id,
            "role_name": role_name,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": f"{user.first_name} {user.last_name}",
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
            raise NotFoundException("User not found", "USER_NOT_FOUND")
        
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
            raise ConflictException("User with this email already exists", "USER_EMAIL_EXISTS")

        # Hash password before persisting
        user.password_hash = bcrypt.hashpw(
            user.password_hash.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")
        
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

    def get_active_users_by_role(self, role_name: str) -> List[User]:
        """Return active users for a validated role name."""
        try:
            role = RoleName(role_name.upper())
        except ValueError as exc:
            raise NotFoundException("Role not found", "ROLE_NOT_FOUND") from exc

        return self.repository.find_active_by_role(role)
