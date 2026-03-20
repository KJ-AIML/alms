# Design Patterns

> **Last Updated:** March 20, 2026  
> **Version:** 0.1.0  
> **Status:** ✅ Active

## Table of Contents

1. [ALMS Architecture](#alms-architecture)
2. [Repository Pattern](#repository-pattern)
3. [Provider Pattern](#provider-pattern)
4. [Usecase/Action Pattern](#usecaseaction-pattern)
5. [Dependency Injection](#dependency-injection)
6. [Standardized Responses](#standardized-responses)

---

## ALMS Architecture

**A**gentic **L**ayer for **M**icro**S**ervices is a layered architecture designed specifically for AI applications.

### Why ALMS?

| Feature | ALMS | Hexagonal | Traditional MVC |
|---------|------|-----------|-----------------|
| **Complexity** | Low | High | Medium |
| **AI-First** | ✅ Native | ❌ Add-on | ❌ Add-on |
| **Learning Curve** | Gentle | Steep | Moderate |
| **Microservice Ready** | ✅ Yes | ⚠️ Overhead | ❌ No |
| **Production Speed** | Fast | Slow | Medium |

### Layer Responsibilities

```
┌─────────────────────────────────────────┐
│  API Layer (src/api/)                   │
│  Responsibilities:                      │
│  • HTTP request/response handling        │
│  • Input validation (Pydantic)          │
│  • Routing and middleware               │
│  • Authentication/authorization         │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Execution Layer (src/execution/)       │
│  Responsibilities:                      │
│  • Business logic orchestration         │
│  • Transaction management               │
│  • Use case coordination                │
│  • High-level business rules            │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Agent Layer (src/agents/)              │
│  Responsibilities:                      │
│  • LLM interactions                     │
│  • Prompt management                    │
│  • Tool orchestration                   │
│  • Workflow execution (LangGraph)       │
└─────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────┐
│  Infrastructure Layers                  │
│  Responsibilities:                      │
│  • External service integration         │
│  • Data persistence                     │
│  • Caching                              │
│  • Configuration                        │
└─────────────────────────────────────────┘
```

### Layer Communication Rules

```python
# ✅ CORRECT: Flow through layers
API Endpoint → Usecase → Action → Provider

# src/api/endpoints/v1/sample_agent.py
@router.post("/agent")
async def agent_endpoint(request: AgentRequest):
    usecase = AgentUsecase()         # Execution Layer
    result = await usecase.execute(request)
    return AppResponse(success=True, data=result)

# src/execution/usecases/agent_usecase.py
class AgentUsecase:
    async def execute(self, request: AgentRequest):
        action = AgentAction()       # Action Layer
        return await action.run(request.query)

# src/execution/actions/agent_action.py
class AgentAction:
    async def run(self, query: str):
        agent = AgentManager()       # Agent Layer
        return await agent.process(query)

# src/agents/agent_manager/agent.py
class AgentManager:
    async def process(self, query: str):
        llm = ChatOpenAI(...)        # Provider Layer
        return await llm.ainvoke(query)
```

---

## Repository Pattern

Database access is abstracted through the Repository pattern for testability and flexibility.

### Base Repository

```python
# src/database/repositories/base.py
from typing import Generic, TypeVar, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

T = TypeVar("T")

class BaseRepository(Generic[T]):
    """
    Base repository providing common CRUD operations.
    
    Usage:
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(User, session)
    """
    
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def get_by_id(self, id: int) -> T | None:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def create(self, obj_in: dict) -> T:
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def update(self, db_obj: T, obj_in: dict) -> T:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj
    
    async def delete(self, db_obj: T) -> None:
        await self.session.delete(db_obj)
        await self.session.commit()
```

### Custom Repository Example

```python
# src/database/repositories/user_repository.py
from typing import Optional
from sqlalchemy import select
from src.database.repositories.base import BaseRepository
from src.models.user import User

class UserRepository(BaseRepository[User]):
    """
    User-specific repository with custom queries.
    """
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Get all active users with pagination."""
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def search_by_name(self, name: str) -> list[User]:
        """Search users by name (case-insensitive)."""
        result = await self.session.execute(
            select(User).where(User.name.ilike(f"%{name}%"))
        )
        return result.scalars().all()
```

---

## Provider Pattern

External services are encapsulated in the Provider layer for loose coupling.

### AI Provider Example

```python
# src/providers/ai/langchain_model_loader.py
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from src.config.settings import settings

class AIModelProvider:
    """
    Provider for AI model interactions.
    Encapsulates LLM initialization and configuration.
    """
    
    @staticmethod
    def get_openai_model(model_type: str = "basic") -> ChatOpenAI:
        """Get configured OpenAI model."""
        model_name = (
            settings.OPENAI_MODEL_BASIC 
            if model_type == "basic" 
            else settings.OPENAI_MODEL_REASONING
        )
        return ChatOpenAI(
            model=model_name,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.7,
        )
    
    @staticmethod
    def get_google_model(model_type: str = "basic") -> ChatGoogleGenerativeAI:
        """Get configured Google Gemini model."""
        model_name = (
            settings.GOOGLE_MODEL_BASIC 
            if model_type == "basic" 
            else settings.GOOGLE_MODEL_REASONING
        )
        return ChatGoogleGenerativeAI(
            model=model_name,
            api_key=settings.GOOGLE_API_KEY,
            temperature=0.7,
        )
```

### Cache Provider Example

```python
# src/providers/cache/redis_provider.py
import redis.asyncio as redis
from src.config.settings import settings

class RedisProvider:
    """
    Provider for Redis cache operations.
    """
    
    def __init__(self):
        self.client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    
    async def get(self, key: str) -> str | None:
        """Get value from cache."""
        return await self.client.get(key)
    
    async def set(self, key: str, value: str, ttl: int = None) -> None:
        """Set value in cache with optional TTL."""
        await self.client.set(key, value, ex=ttl or settings.CACHE_TTL)
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        await self.client.delete(key)
```

---

## Usecase/Action Pattern

Separates high-level orchestration (usecases) from discrete operations (actions).

### Usecase (Orchestration)

```python
# src/execution/usecases/user_registration_usecase.py
from src.execution.actions.create_user_action import CreateUserAction
from src.execution.actions.send_email_action import SendEmailAction
from src.providers.cache.redis_provider import RedisProvider

class UserRegistrationUsecase:
    """
    Orchestrates the user registration flow.
    
    Responsibilities:
    - Coordinate multiple actions
    - Handle transactions
    - Business rule enforcement
    """
    
    def __init__(self):
        self.create_user_action = CreateUserAction()
        self.send_email_action = SendEmailAction()
        self.cache = RedisProvider()
    
    async def execute(self, user_data: dict) -> dict:
        """
        Execute registration usecase.
        
        Flow:
        1. Create user in database
        2. Send welcome email
        3. Cache user data
        4. Return result
        """
        # Step 1: Create user
        user = await self.create_user_action.run(user_data)
        
        # Step 2: Send welcome email
        await self.send_email_action.run(
            to=user.email,
            template="welcome",
            context={"name": user.name}
        )
        
        # Step 3: Cache user data
        await self.cache.set(
            f"user:{user.id}",
            user.json(),
            ttl=3600
        )
        
        return {"user_id": user.id, "status": "registered"}
```

### Action (Execution)

```python
# src/execution/actions/create_user_action.py
from src.database.repositories.user_repository import UserRepository
from src.database.connection import get_db_session
from src.core.exceptions import ValidationException

class CreateUserAction:
    """
    Executes the discrete operation of creating a user.
    
    Responsibilities:
    - Single, focused operation
    - No orchestration logic
    - Reusable across usecases
    """
    
    async def run(self, user_data: dict) -> User:
        """Create a new user."""
        # Validation
        if not user_data.get("email"):
            raise ValidationException(
                message="Email is required",
                error_code="EMAIL_REQUIRED"
            )
        
        # Database operation
        async with get_db_session() as session:
            repo = UserRepository(session)
            
            # Check if email exists
            existing = await repo.get_by_email(user_data["email"])
            if existing:
                raise ValidationException(
                    message="Email already registered",
                    error_code="EMAIL_EXISTS"
                )
            
            # Create user
            user = await repo.create(user_data)
            return user
```

---

## Dependency Injection

FastAPI's built-in DI system is used for clean dependency management.

### Dependency Definition

```python
# src/api/endpoints/v1/dependencies.py
from typing import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import async_session_maker
from src.database.repositories.user_repository import UserRepository

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database session dependency."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()

async def get_user_repo(
    session: AsyncSession = Depends(get_db)
) -> UserRepository:
    """User repository dependency."""
    return UserRepository(session)
```

### Using Dependencies

```python
# src/api/endpoints/v1/users.py
from fastapi import APIRouter, Depends
from src.api.endpoints.v1.dependencies import get_user_repo
from src.database.repositories.user_repository import UserRepository
from src.api.endpoints.v1.schemas.base import AppResponse

router = APIRouter()

@router.get("/users/{user_id}")
async def get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repo)
) -> AppResponse:
    """Get user by ID."""
    user = await repo.get_by_id(user_id)
    if not user:
        raise NotFoundException(
            message="User not found",
            error_code="USER_NOT_FOUND"
        )
    return AppResponse(success=True, data=user)
```

---

## Standardized Responses

All API responses use the standardized `AppResponse` wrapper for consistency.

### Response Schema

```python
# src/api/endpoints/v1/schemas/base.py
from typing import Any, Generic, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")

class ErrorDetail(BaseModel):
    """Standardized error details."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Any] = Field(None, description="Additional context")

class AppResponse(BaseModel, Generic[T]):
    """
    Standardized API response wrapper.
    
    Used for ALL API responses to ensure consistency.
    """
    success: bool = Field(..., description="Request success status")
    data: Optional[T] = Field(None, description="Response data")
    error: Optional[ErrorDetail] = Field(
        None, description="Error details if success is false"
    )
    request_id: Optional[str] = Field(
        None, description="Unique request identifier"
    )
```

### Success Response Example

```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "name": "John Doe",
    "email": "john@example.com"
  },
  "error": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Response Example

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid email format",
    "details": {
      "field": "email",
      "value": "invalid-email"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Best Practices

1. **Never skip layers** - Always flow through API → Usecase → Action → Provider
2. **Single Responsibility** - Each class/function does one thing well
3. **Dependency Injection** - Use FastAPI's DI system for testability
4. **Type Hints** - Always add type hints for clarity
5. **Async-First** - Use async/await for I/O operations
6. **Custom Exceptions** - Use domain exceptions, not raw HTTPException
7. **Repository Pattern** - Abstract database access
8. **Provider Pattern** - Encapsulate external services
