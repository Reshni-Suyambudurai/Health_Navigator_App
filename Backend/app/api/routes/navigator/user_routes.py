"""
User API Routes - REST endpoints
Similar to Spring Boot's @RestController
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.services.navigator.user_service import UserService
from app.database.models.user import User
from app.core.response_models import SuccessResponse
from pydantic import BaseModel, EmailStr
import logging

logger = logging.getLogger(__name__)

# Create router (similar to @RestController in Spring)
router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


# DTOs (Data Transfer Objects) - similar to Spring Boot DTOs
class UserResponse(BaseModel):
    """Response DTO for User"""
    user_id: int
    first_name: str
    last_name: str
    email: str
    status: str
    
    class Config:
        from_attributes = True


class UserCreateRequest(BaseModel):
    """Request DTO for creating User"""
    organization_id: int
    role_id: int
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone: str | None = None


class LoginRequest(BaseModel):
    """Request DTO for user login"""
    email: EmailStr
    password: str


# Similar to: @PostMapping("/users/login")
@router.post("/login", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def login_user(
    login_request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login user - verify email, password, and active status
    Spring equivalent:
    @PostMapping("/users/login")
    public ResponseEntity<LoginResponse> login(@RequestBody LoginRequest request)
    """
    service = UserService(db)
    
    # Business logic handled in service layer
    login_data = service.login(login_request.email, login_request.password)
    
    # Return standardized success response
    return SuccessResponse(
        status="success",
        message="Login successful",
        data=login_data
    )


# Similar to: @GetMapping("/users/{id}")
@router.get("/{user_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get user by ID
    Spring equivalent: 
    @GetMapping("/users/{id}")
    public ResponseEntity<User> getUser(@PathVariable Long id)
    """
    service = UserService(db)
    user = service.get_user_by_id(user_id)
    
    return SuccessResponse(
        status="success",
        message="User retrieved successfully",
        data={
            "user_id": user.user_id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "status": user.status.value
        }
    )


# Similar to: @GetMapping("/users")
@router.get("/", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Get all users with pagination
    Spring equivalent:
    @GetMapping("/users")
    public ResponseEntity<Page<User>> getAllUsers(Pageable pageable)
    """
    service = UserService(db)
    users = service.get_all_users(skip, limit)
    
    return SuccessResponse(
        status="success",
        message="Users retrieved successfully",
        data={"users": users, "count": len(users)}
    )


# Similar to: @PostMapping("/users")
@router.post("/", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_request: UserCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create new user
    Spring equivalent:
    @PostMapping("/users")
    public ResponseEntity<User> createUser(@RequestBody UserDTO userDTO)
    """
    service = UserService(db)
    
    # Convert DTO to Entity (similar to ModelMapper in Spring)
    user = User(
        organization_id=user_request.organization_id,
        role_id=user_request.role_id,
        first_name=user_request.first_name,
        last_name=user_request.last_name,
        email=user_request.email,
        password_hash=user_request.password,
        phone=user_request.phone
    )
    
    created_user = service.create_user(user)
    
    return SuccessResponse(
        status="success",
        message="User created successfully",
        data={"user_id": created_user.user_id}
    )


# Similar to: @DeleteMapping("/users/{id}")
@router.delete("/{user_id}", response_model=SuccessResponse, status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete user
    Spring equivalent:
    @DeleteMapping("/users/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id)
    """
    service = UserService(db)
    service.delete_user(user_id)
    
    return SuccessResponse(
        status="success",
        message="User deleted successfully",
        data=None
    )


# Similar to: @GetMapping("/users/active")
@router.get("/status/active", response_model=SuccessResponse)
async def get_active_users(db: Session = Depends(get_db)):
    """
    Get all active users
    Spring equivalent:
    @GetMapping("/users/active")
    public ResponseEntity<List<User>> getActiveUsers()
    """
    service = UserService(db)
    users = service.get_active_users()
    
    return SuccessResponse(
        status="success",
        message="Active users retrieved successfully",
        data={"users": users, "count": len(users)}
    )
