# Backend Architecture Rules

These rules apply to backend work under `backend/`.

## Request Flow

```text
Client -> Routes -> Services -> Repositories -> Models -> PostgreSQL
```

## File Placement

- Routes: `backend/app/api/routes/{entity}_routes.py`
- Services: `backend/app/services/{entity}_service.py`
- Repositories: `backend/app/database/repositories/{entity}_repository.py`
- Models: `backend/app/database/models/{entity}.py`
- Exceptions: `backend/app/core/exceptions.py`
- Response models: `backend/app/core/response_models.py`

## Rules by Layer

**Routes** - HTTP only

- Return `SuccessResponse(status, message, data)`.
- Call service methods.
- Do not add business logic or database queries.

**Services** - Business logic

- Raise custom exceptions such as `AuthenticationException` and `NotFoundException`.
- Use bcrypt for passwords.
- Do not raise `HTTPException` or query the database directly.

**Repositories** - Database only

- Implement database operations such as `find_by_id()`, `find_all()`, `save()`, and `delete()`.
- Do not add business logic.

**Models** - Table definitions

- Define SQLAlchemy columns and relationships.
- Do not add methods or business logic.

## Exception Types

- `AuthenticationException`: Invalid credentials (401)
- `AuthorizationException`: Access denied (403)
- `NotFoundException`: Resource not found (404)
- `ValidationException`: Invalid input (400)
- `ConflictException`: Duplicate resource (409)

## Response Format

Success responses use:

```python
SuccessResponse(status="success", message="...", data={...})
```

Errors should be raised as custom exceptions and converted by the existing exception handlers.

## Adding a Feature

Follow this order:

1. Model
2. Repository
3. Service
4. Routes
5. Register the router in `main.py`
