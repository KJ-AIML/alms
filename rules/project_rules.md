# Repository Guidelines

## Project Structure & Module Organization

- The project should follow the **ALMS (Agentic Layer for Microservices)** architecture
- **ALMS** is a pragmatic layered architecture designed for AI applications
- It prioritizes simplicity over complex abstractions while maintaining clean separation of concerns
- The project should have a `src` directory at the root level
- The `src` directory should have the following subdirectories:
  - `api`: Contains the FastAPI application code
    - `endpoints`: Contains the API endpoint definitions (grouped by version)
      - Each version (v1, v2, etc.) has its own `dependencies.py` for version-specific DI
    - `router`: Contains router aggregation and version prefix management
    - `middlewares`: Contains global middlewares (error handling, logging)
  - `execution`: Contains the business logic and execution code (equivalent to services layer)
    - `usecases`: Contains the usecases code for executing actions
    - `actions`: Contains the actions code implementations
  - `core`: Contains shared core logic (custom exceptions, base schemas)
  - `agents`: Contains AI agent management
    - `agent_manager`: Contains agent definitions
    - `prompts`: Contains agent prompts
    - `tools`: Contains agent tools
    - `workflows`: Contains agent workflows
  - `providers`: Contains infrastructure providers
    - `ai`: Contains AI model providers
    - `cache`: Contains cache providers
    - `vectordb`: Contains vector database providers
  - `database`: Contains database layer
    - `connection.py`: Database connection setup
    - `migrations/`: Contains Alembic database migrations
    - `repositories/`: Contains data repositories (BaseRepository pattern)
  - `config`: Contains configuration files
    - `settings.py`: Pydantic Settings for environment variables
    - `logs_config.py`: Logging configuration
  - `models`: Contains domain models (Pydantic models for business entities)
  - `data`: Contains data files (datasets, seed data, etc.)
  - `docs`: Contains project documentation
  - `evaluation`: Contains evaluation scripts for AI agents
  - `scripts`: Contains utility scripts
  - `tests`: Contains automated tests
    - `conftest.py`: pytest configuration and fixtures
    - `v1/`: Tests organized by API version
  - `utils`: Contains utility functions and helpers

## ALMS Architecture Flow

**A**gentic **L**ayer for **M**icro**S**ervices - A pragmatic layered architecture optimized for AI applications.

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (src/api/)                     │
│         HTTP handling, routing, middleware, validation      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Execution Layer (src/execution/)            │
│       Business logic, use cases, action orchestration       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Agent Layer (src/agents/)                 │
│      AI logic, prompts, tools, workflows (when needed)      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layers (src/*)                  │
│    Providers, Database, Core utilities, Configurations      │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

1. **API Layer** (`src/api/`): HTTP request handling, routing, middleware
2. **Execution Layer** (`src/execution/`): Business logic, use case orchestration
3. **Agent Layer** (`src/agents/`): AI agent management, prompts, tools, workflows
4. **Core Layer** (`src/core/`): Shared exceptions, base classes
5. **Provider Layer** (`src/providers/`): External service integrations
6. **Database Layer** (`src/database/`): Data persistence with Repository pattern

### Key Principles

- **Layered Dependencies**: Each layer only depends on layers below it
- **No Complex Abstractions**: No ports/adapters - just clean layers
- **AI-First**: Agent layer is a first-class citizen, not bolted on
- **Microservice-Ready**: Any layer can be extracted into its own service

## Build, Test, and Development Commands

- `uv run -m src.api.main` - Run the FastAPI application
- `uv run pytest src/tests` - Run all tests
- `uv run pytest src/tests/v1/ -v` - Run tests with verbose output
- `uv run -m src.utils.helpers` - Run utility functions

### Database Commands (Alembic)
- `alembic revision --autogenerate -m "description"` - Create new migration
- `alembic upgrade head` - Run all migrations
- `alembic downgrade -1` - Rollback one migration
- `alembic current` - Show current migration version

### Package Management
- `uv add <package>` - Add production dependency
- `uv add --dev <package>` - Add development dependency
- `uv sync` - Sync project with uv.lock
- `uv lock` - Update lock file

## Coding Style & Naming Conventions

- Language: Python
- Code Style: [PEP 8]
- Linter: Ruff (configured in pyproject.toml)
- Naming Conventions:
  - Variables: `snake_case`
  - Functions: `snake_case`
  - Classes: `PascalCase`
  - Constants: `UPPER_CASE`
  - Files: `snake_case.py`
  - Directories: `snake_case`

## API Response Standards

All API responses should use the standardized `AppResponse` wrapper:

```python
{
  "success": true,
  "data": { ... },
  "error": null,
  "request_id": "uuid-string"
}
```

Error responses:
```python
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  },
  "request_id": "uuid-string"
}
```

## Exception Handling

Use custom exceptions from `src/core/exceptions.py`:

- `AppException` - Base exception (status_code: 500)
- `DomainException` - Business logic errors (status_code: 400)
- `NotFoundException` - Resource not found (status_code: 404)
- `ValidationException` - Input validation errors (status_code: 422)

Example:
```python
from src.core.exceptions import NotFoundException

raise NotFoundException(
    message="User not found",
    error_code="USER_NOT_FOUND",
    details={"user_id": user_id}
)
```

## Repository Pattern

Database access is abstracted through the Repository pattern:

- Base repository: `src/database/repositories/base.py`
- Extend `BaseRepository[T]` for specific entities
- Implement CRUD methods: `get`, `get_all`, `create`, `update`, `delete`

Example:
```python
from src.database.repositories.base import BaseRepository
from src.models.user import User

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        # Implementation
        pass
```

## ALMS Best Practices

1. **Layer Isolation**: Never skip layers. API → Execution → Agent (not API → Agent directly)
2. **Dependency Injection**: Use FastAPI's DI in `endpoints/v1/dependencies.py`
3. **Versioning**: All endpoints versioned (v1, v2, etc.)
4. **Async/Await**: Use async/await for all I/O operations
5. **Type Hints**: Add type hints to all function signatures
6. **Error Handling**: Use custom exceptions, not raw HTTPException
7. **Testing**: Write tests for all use cases and actions
8. **Documentation**: Use docstrings for all public functions

### Layer Communication Rules

```python
# ✅ Correct: Flow through layers
api_endpoint → usecase → action → provider

# ❌ Wrong: Skipping layers
api_endpoint → provider  # Don't do this
usecase → database       # Use repository instead
```

### When to Extract to Microservice

- **API Layer** becomes too complex → Extract Gateway service
- **Agent Layer** needs scaling → Extract Agent service
- **Execution Layer** becomes heavy → Extract Business Logic service
