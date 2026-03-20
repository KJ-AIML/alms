# FastAPI-Agentic-Starter

> **The AI-First Backend for Scalable, Intelligent Applications.**

<p align="center">
  <img src="assets/images/asset_image_01.png" width="800" alt="FastAPI Agentic Starter Hero">
</p>

## Introduction

**FastAPI-Agentic-Starter** is a production-ready boilerplate designed for building robust, AI-powered backends. Built with an "AI-First" philosophy, it combines the performance of FastAPI with **ALMS** (Agentic Layer for Microservices) - a pragmatic layered architecture that treats LLM interactions as first-class citizens.

Whether you're building autonomous agents, RAG pipelines, or intelligent APIs, this starter kit provides the scalability and clean code structure you need to move fast without over-engineering.

## Key Features

- 🤖 **AI-Native Architecture**: Dedicated `src/agents` layer for managing LLM logic, tools, and complex agentic workflows
- 🏗️ **ALMS Architecture**: **A**gentic **L**ayer for **M**icro**S**ervices - A pragmatic layered architecture optimized for AI applications
- 🔌 **Provider Pattern**: Clean separation of external services (OpenAI, Redis, VectorDBs) via `src/providers`
- 🧠 **Business Logic Separation**: Clear distinction between `usecases` (orchestration) and `actions` (execution)
- 💾 **Database Abstraction**: Repository pattern with Alembic migrations and async PostgreSQL support
- 🔒 **Security-First**: Built-in middleware for security headers, CORS, and request validation
- 📊 **Standardized Responses**: Consistent API response format with error handling
- ⚡ **Async-Ready**: Full async/await support with FastAPI and asyncpg
- 🧪 **Testing Ready**: pytest setup with fixtures and organized test structure
- 📚 **Modern Documentation**: Scalar API docs for beautiful interactive documentation

## ALMS Architecture

**A**gentic **L**ayer for **M**icro**S**ervices is a layered architecture designed specifically for AI applications. Unlike complex Hexagonal architecture, ALMS prioritizes simplicity and rapid development while maintaining clean separation of concerns.

### Why ALMS?

| Feature | ALMS | Hexagonal | Traditional MVC |
|---------|------|-----------|-----------------|
| **Complexity** | Low | High | Medium |
| **AI-First** | ✅ Native | ❌ Add-on | ❌ Add-on |
| **Learning Curve** | Gentle | Steep | Moderate |
| **Microservice Ready** | ✅ Yes | ⚠️ Overhead | ❌ No |
| **Production Speed** | Fast | Slow | Medium |

### Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (src/api/)                     │
│         HTTP handling, routing, middleware, validation      │
├─────────────────────────────────────────────────────────────┤
│  • endpoints/v1/         - Versioned API endpoints          │
│  • middlewares/          - Security, logging, error handling │
│  • router/               - Router aggregation                │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                 Execution Layer (src/execution/)            │
│       Business logic, use cases, action orchestration       │
├─────────────────────────────────────────────────────────────┤
│  • usecases/             - Orchestrate business flow        │
│  • actions/              - Execute discrete operations      │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                   Agent Layer (src/agents/)                 │
│      AI logic, prompts, tools, workflows (when needed)      │
├─────────────────────────────────────────────────────────────┤
│  • agent_manager/        - Agent definitions                │
│  • prompts/              - LLM prompt templates             │
│  • tools/                - Agent tools                      │
│  • workflows/            - LangGraph workflows              │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              Infrastructure Layers (src/*)                  │
│    Providers, Database, Core utilities, Configurations      │
├─────────────────────────────────────────────────────────────┤
│  • providers/            - External service integrations    │
│  • database/             - Repositories, migrations         │
│  • core/                 - Exceptions, base classes         │
│  • config/               - Settings, logging                │
└─────────────────────────────────────────────────────────────┘
```

### Layer Communication Rules

```python
# ✅ Correct: Flow through layers
API Endpoint → Usecase → Action → Provider

# ❌ Wrong: Never skip layers
API Endpoint → Provider  # Don't bypass execution layer
Usecase → Database       # Use repository pattern
```

## Project Structure

```
fastapi-agentic-starter/
├── src/
│   ├── api/                      # API Layer
│   │   ├── endpoints/v1/         # Versioned endpoints
│   │   │   ├── dependencies.py   # DI for v1
│   │   │   ├── health.py         # Health check endpoint
│   │   │   ├── sample_agent.py   # Agent endpoint example
│   │   │   ├── sample_di.py      # DI example
│   │   │   └── schemas/          # Pydantic schemas
│   │   │       ├── base.py       # AppResponse wrapper
│   │   │       └── sample.py     # Request/response schemas
│   │   ├── middlewares/          # Global middlewares
│   │   │   ├── error_handler.py  # Exception handling
│   │   │   ├── logging.py        # Request logging
│   │   │   └── security.py       # Security headers
│   │   ├── router/               # Router aggregation
│   │   │   └── routers.py        # Main API router
│   │   └── main.py               # FastAPI app factory
│   ├── execution/                # Execution Layer
│   │   ├── actions/              # Discrete operations
│   │   │   └── sample_action.py
│   │   └── usecases/             # Business flow orchestration
│   │       └── sample_usecase.py
│   ├── agents/                   # Agent Layer
│   │   ├── agent_manager/
│   │   │   └── agent.py          # Agent definitions
│   │   ├── prompts/
│   │   │   └── sample_agent_prompt.py
│   │   ├── tools/                # Agent tools (empty)
│   │   └── workflows/            # LangGraph workflows (empty)
│   ├── providers/                # Infrastructure Providers
│   │   └── ai/
│   │       └── langchain_model_loader.py
│   ├── database/                 # Database Layer
│   │   ├── connection.py         # DB connection setup
│   │   ├── migrations/           # Alembic migrations
│   │   └── repositories/
│   │       └── base.py           # BaseRepository pattern
│   ├── core/                     # Shared Core
│   │   └── exceptions.py         # Custom exceptions
│   ├── config/                   # Configuration
│   │   ├── settings.py           # Pydantic Settings
│   │   └── logs_config.py        # Logging setup
│   ├── models/                   # Domain models (empty)
│   ├── utils/                    # Utilities
│   └── tests/                    # Tests
│       ├── conftest.py           # pytest fixtures
│       └── v1/                   # Versioned tests
│           ├── test_health.py
│           └── test_agent.py
├── alembic/                      # Database migrations
│   ├── env.py
│   └── README
├── rules/
│   └── project_rules.md          # ALMS guidelines
├── .env.example                  # Environment template
├── pyproject.toml               # Dependencies (uv)
└── README.md                    # This file
```

## Tech Stack

| Category | Technology | Purpose |
|----------|-----------|---------|
| **Framework** | [FastAPI](https://fastapi.tiangolo.com/) | High-performance API framework |
| **AI/LLM** | [LangChain](https://www.langchain.com/) + [LangGraph](https://langchain-ai.github.io/langgraph/) | Agent orchestration |
| **Database** | PostgreSQL + [SQLAlchemy](https://www.sqlalchemy.org/) | Data persistence |
| **Async DB** | [asyncpg](https://magicstack.github.io/asyncpg/current/) | Async PostgreSQL driver |
| **Migrations** | [Alembic](https://alembic.sqlalchemy.org/) | Database schema migrations |
| **Caching** | [Redis](https://redis.io/) | Caching & message broker |
| **Validation** | [Pydantic v2](https://docs.pydantic.dev/) | Data validation & settings |
| **Documentation** | [Scalar](https://scalar.com/) | Modern API documentation |
| **Testing** | [pytest](https://docs.pytest.org/) | Testing framework |
| **Linting** | [Ruff](https://docs.astral.sh/ruff/) | Fast Python linter |
| **Package Manager** | [uv](https://docs.astral.sh/uv/) | Modern Python package manager |

## Quick Start

### Prerequisites

- Python 3.13+
- PostgreSQL (optional, for database features)
- Redis (optional, for caching)
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

### 1. Clone & Setup

```bash
git clone https://github.com/KJ-AIML/fastapi-agentic-starter.git
cd fastapi-agentic-starter

# Copy environment file
cp .env.example .env

# Edit .env with your credentials
# Required: OPENAI_API_KEY
# Optional: DATABASE_URL, REDIS_URL
```

### 2. Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

### 3. Run Database Migrations (if using PostgreSQL)

```bash
# Create initial migration
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

### 4. Start the Application

```bash
# Development mode with hot-reload
uv run -m src.api.main

# The API will be available at:
# - API: http://localhost:3000
# - Docs: http://localhost:3000/docs (Scalar)
```

## Development Commands

### Application

```bash
# Run development server
uv run -m src.api.main

# Run with specific host/port
uv run -m src.api.main --host 0.0.0.0 --port 8080
```

### Testing

```bash
# Run all tests
uv run pytest src/tests

# Run with verbose output
uv run pytest src/tests -v

# Run specific test file
uv run pytest src/tests/v1/test_agent.py -v

# Run with coverage
uv run pytest src/tests --cov=src
```

### Database

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply all migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# View migration history
alembic history --verbose
```

### Dependencies

```bash
# Add production dependency
uv add <package>

# Add development dependency
uv add --dev <package>

# Sync with lock file
uv sync

# Update lock file
uv lock

# Show dependency tree
uv tree
```

### Code Quality

```bash
# Run linter
ruff check src/

# Fix auto-fixable issues
ruff check --fix src/

# Format code
ruff format src/
```

## API Standards

### Response Format

All API responses use the standardized `AppResponse` wrapper:

**Success Response:**
```json
{
  "success": true,
  "data": {
    "message": "Operation completed",
    "result": {...}
  },
  "error": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Error Response:**
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Exception Handling

Use custom exceptions from `src/core/exceptions.py`:

```python
from src.core.exceptions import NotFoundException, ValidationException

# Resource not found
raise NotFoundException(
    message="User not found",
    error_code="USER_NOT_FOUND",
    details={"user_id": user_id}
)

# Validation error
raise ValidationException(
    message="Invalid email format",
    error_code="INVALID_EMAIL",
    details={"field": "email", "value": email}
)
```

## Repository Pattern

Database access is abstracted through the Repository pattern:

```python
from src.database.repositories.base import BaseRepository
from src.models.user import User
from typing import Optional

class UserRepository(BaseRepository[User]):
    def __init__(self):
        super().__init__(User)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        # Implementation using SQLAlchemy
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_active_users(self, skip: int = 0, limit: int = 100):
        result = await self.session.execute(
            select(User)
            .where(User.is_active == True)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
```

## Configuration

Configuration is managed via Pydantic Settings with environment variables:

```python
# .env file
OPENAI_API_KEY=sk-...
OPENAI_MODEL_BASIC=gpt-4o-mini
OPENAI_MODEL_REASONING=gpt-4o

DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=mydb
DATABASE_USER=postgres
DATABASE_PASSWORD=secret

REDIS_HOST=localhost
REDIS_PORT=6379

DEBUG=true
LOG_LEVEL=info
SERVER_PORT=3000
```

Access settings anywhere:

```python
from src.config.settings import settings

# Use settings
api_key = settings.OPENAI_API_KEY
db_url = settings.DATABASE_URL
```

## Creating a New Agent

1. **Define the agent** in `src/agents/agent_manager/`:

```python
# src/agents/agent_manager/my_agent.py
from langchain_openai import ChatOpenAI
from src.config.settings import settings

llm = ChatOpenAI(
    model=settings.OPENAI_MODEL_BASIC,
    api_key=settings.OPENAI_API_KEY
)

class MyAgent:
    def __init__(self):
        self.llm = llm
    
    async def process(self, query: str) -> str:
        response = await self.llm.ainvoke(query)
        return response.content
```

2. **Create use case** in `src/execution/usecases/`:

```python
# src/execution/usecases/my_usecase.py
from src.agents.agent_manager.my_agent import MyAgent

class MyUsecase:
    def __init__(self):
        self.agent = MyAgent()
    
    async def execute(self, query: str):
        result = await self.agent.process(query)
        return {"response": result}
```

3. **Create endpoint** in `src/api/endpoints/v1/`:

```python
# src/api/endpoints/v1/my_endpoint.py
from fastapi import APIRouter
from src.execution.usecases.my_usecase import MyUsecase
from src.api.endpoints.v1.schemas.base import AppResponse

router = APIRouter()

@router.post("/my-agent")
async def my_agent_endpoint(query: str):
    usecase = MyUsecase()
    result = await usecase.execute(query)
    return AppResponse(success=True, data=result)
```

4. **Register router** in `src/api/endpoints/v1/routers.py`:

```python
from src.api.endpoints.v1 import my_endpoint
v1_router.include_router(my_endpoint.router, prefix="/my-agent")
```

## Scaling to Microservices

ALMS makes it easy to extract layers into microservices:

```
Monolith                    Microservices
┌──────────┐                ┌──────────────┐
│ API      │ ────────────→  │ API Gateway  │
├──────────┤                ├──────────────┤
│ Execution│ ────────────→  │ Logic Service│
├──────────┤                ├──────────────┤
│ Agent    │ ────────────→  │ Agent Service│
├──────────┤                ├──────────────┤
│ DB       │ ────────────→  │ Data Service │
└──────────┘                └──────────────┘
```

Each layer is already isolated - just add HTTP/gRPC clients between them!

## Contributing

1. Follow ALMS layer rules - never skip layers
2. Add tests for all use cases and actions
3. Use custom exceptions, not raw HTTPException
4. Add type hints to all functions
5. Update documentation for new features
6. Run `ruff check` before committing
7. Ensure all tests pass: `uv run pytest src/tests`

## License

[MIT License](LICENSE)

---

<p align="center">
  <strong>Built for the next generation of AI applications</strong><br>
  <sub>ALMS Architecture - Pragmatic, Scalable, AI-First</sub>
</p>
