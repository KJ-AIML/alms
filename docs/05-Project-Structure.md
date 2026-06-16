# 05 - Project Structure

> **Last Updated:** June 16, 2026  
> **Version:** 0.3.0  
> **Status:** ✅ Active

```
alms/
├── README.md                           # Project overview and quick start
├── .env.example                        # Environment variable template
├── .env                                # Local environment (gitignored)
├── .gitignore                          # Git ignore patterns
├── .python-version                     # Python version specification
├── pyproject.toml                      # Project dependencies (UV)
├── uv.lock                             # Locked dependency versions
├── alembic.ini                         # Alembic migration configuration
├── docker-compose.yml                  # Docker services configuration
├── Dockerfile                          # Container build instructions
├── rules/
│   └── project_rules.md                # ALMS architecture guidelines
├── docs/                               # Documentation
│   ├── 01-System-Design.md             # System architecture overview
│   ├── 02-Design-Patterns.md           # Design patterns used
│   ├── 03-Database-Design.md           # Database schema and queries
│   ├── 04-Tech-Stack.md                # Technology inventory
│   ├── 05-Project-Structure.md         # This file
│   ├── 06-API-Documentation.md         # API endpoints reference
│   ├── 07-Setup-Installation.md        # Setup guide
│   ├── 08-Contribution-Guide.md        # Contribution guidelines
│   ├── UPDATE-SUMMARY.md               # Documentation changes log
│   ├── changelogs/                     # Version changelogs
│   │   └── version-0.1.0.md
│   └── milestone/                      # Feature milestones
│       └── (empty)
├── alembic/                            # Database migrations
│   ├── README                          # Migration instructions
│   ├── env.py                          # Alembic environment
│   ├── script.py.mako                  # Migration template
│   └── versions/                       # Migration files
│       └── (auto-generated)
├── assets/
│   └── images/
│       └── asset_image_01.png          # README hero image
└── src/                                # Source code
    ├── api/                            # API Layer
    │   ├── main.py                     # FastAPI app factory
    │   ├── middlewares/                # Global middlewares
    │   │   ├── error_handler.py        # Exception handling middleware
    │   │   ├── logging.py              # Request logging middleware
    │   │   └── security.py             # Security headers middleware
    │   ├── router/                     # Router aggregation
    │   │   └── routers.py              # Main API router
    │   └── endpoints/                  # API endpoints
    │       └── v1/                     # Version 1 endpoints
    │           ├── dependencies.py     # Version-specific DI
    │           ├── health.py           # Health check endpoint
    │           ├── sample_agent.py     # Sample agent endpoint
    │           ├── sample_di.py        # Dependency injection example
    │           ├── routers.py          # v1 router aggregation
    │           └── schemas/            # Pydantic schemas
    │               ├── base.py         # AppResponse wrapper
    │               └── sample.py       # Sample schemas
    ├── execution/                      # Execution Layer
    │   ├── actions/                    # Discrete operations
    │   │   └── sample_action.py        # Sample action
    │   └── usecases/                   # Business flow orchestration
    │       └── sample_usecase.py       # Sample use case
    ├── agents/                         # Agent Layer
    │   ├── agent_manager/              # Agent definitions
    │   │   └── agent.py                # Sample agent
    │   ├── prompts/                    # Agent prompts
    │   │   ├── prompt_manager.py       # Markdown prompt loader
    │   │   └── agents/
    │   │       └── agent_sample.md
    │   ├── schemas/                    # Structured agent output schemas
    │   ├── tools/                      # Agent tools
    │   └── workflows/                  # LangGraph workflows
    │       └── sample/
    │           ├── state.py
    │           ├── nodes.py
    │           └── build.py
    ├── providers/                      # Infrastructure Providers
    │   ├── ai/                         # AI model providers
    │   │   ├── base.py                 # AIModelProvider abstract base
    │   │   ├── factory.py              # get_ai_provider() factory
    │   │   └── langchain_model_loader.py
    │   ├── cache/                      # Cache providers (Redis)
    │   └── vectordb/                   # Vector database providers
    ├── database/                       # Database Layer
    │   ├── connection.py               # Database connection setup
    │   ├── repositories/               # Repository implementations
    │   │   └── base.py                 # BaseRepository
    │   └── migrations/                 # Alembic migrations (empty)
    ├── core/                           # Shared Core
    │   └── exceptions.py               # Custom exceptions
    ├── config/                         # Configuration
    │   ├── settings.py                 # Pydantic Settings
    │   └── logs_config.py              # Logging configuration
    ├── models/                         # Domain models (empty)
    ├── data/                           # Data files (empty)
    ├── utils/                          # Utility functions (empty)
    ├── docs/                           # Project docs (empty)
    ├── evaluation/                     # AI evaluation scripts (empty)
    ├── scripts/                        # Utility scripts (empty)
    └── tests/                          # Automated tests
        ├── conftest.py                 # pytest configuration
        ├── v1/                         # Versioned tests
        │   ├── test_health.py          # Health endpoint tests
        │   ├── test_agent.py           # Agent endpoint tests
        │   ├── test_metrics.py         # Metrics tests
        │   ├── test_metrics_endpoint.py
        │   ├── test_observability_middleware.py
        │   ├── test_sqlalchemy_repository.py
        │   ├── test_settings.py        # Settings validation tests
        │   └── test_tracing.py
        ├── integration/
        │   └── test_full_stack.py
        └── e2e/
            └── test_workflows.py
```

## Directory Responsibilities

### `/.agents/skills` - Repo-Packaged Agent Skills

**Purpose:** Local skills that help LLM coding agents work inside this repository with the intended ALMS conventions.

**Key Files:**
- `.agents/skills/alms-dev/SKILL.md` - General ALMS development guidance
- `.agents/skills/alms-dev/references/alms-dev-patterns.md` - Layer recipes, templates, naming, tests, and documentation rules

**Rules:**
- Keep repo-packaged skills focused on helping agents modify this project correctly
- Use `alms-dev` for normal ALMS backend development
- Use the separate public `alms-langgraph-agent` skill for LangGraph-specific workflow implementation
- Update the skill when ALMS architecture or file placement rules change

### `/src/api` - API Layer

**Purpose:** HTTP request handling, routing, middleware, and validation

**Key Files:**
- `main.py` - FastAPI application factory with CORS, middleware, router setup
- `middlewares/error_handler.py` - Global exception handling
- `middlewares/logging.py` - Request/response logging
- `middlewares/security.py` - Security headers and CORS
- `router/routers.py` - Centralized router aggregation
- `endpoints/v1/` - Versioned API endpoints

**Rules:**
- Only handles HTTP concerns
- Delegates business logic to Execution Layer
- Uses Pydantic for request/response validation
- Never accesses database directly

### `/src/execution` - Execution Layer

**Purpose:** Business logic, use case orchestration, action execution

**Key Files:**
- `usecases/sample_usecase.py` - Orchestrates business flow
- `actions/sample_action.py` - Executes discrete operations

**Rules:**
- Usecases orchestrate actions
- Actions perform single operations
- May interact with Agent Layer for AI features
- Uses Repository pattern for database access
- Pure business logic, no HTTP or DB concerns

### `/src/agents` - Agent Layer

**Purpose:** AI agent management, prompts, tools, and workflows

**Key Files:**
- `agent_manager/agent.py` - LangChain agent definitions
- `prompts/` - LLM prompt templates
- `tools/` - Agent tools (to be implemented)
- `workflows/` - LangGraph workflows (to be implemented)

**Rules:**
- Encapsulates all AI/LLM logic
- Agent definitions in `agent_manager/`
- Prompt templates in `prompts/`
- Tools and workflows for complex agent behavior

### `/src/providers` - Provider Layer

**Purpose:** External service integrations

**Key Files:**
- `ai/langchain_model_loader.py` - LLM model initialization

**Subdirectories:**
- `ai/` - AI model providers (OpenAI, Google)
- `cache/` - Cache providers (Redis)
- `vectordb/` - Vector database providers

**Rules:**
- Abstract external service details
- Easy to swap implementations
- Handle connection pooling and retries

### `/src/database` - Database Layer

**Purpose:** Data persistence and access

**Key Files:**
- `connection.py` - SQLAlchemy async engine and session
- `repositories/base.py` - BaseRepository pattern

**Rules:**
- Repository pattern for all DB access
- Async operations only (asyncpg)
- Models defined in `/src/models`
- Migrations in `/alembic`

### `/src/core` - Shared Core

**Purpose:** Common utilities and base classes

**Key Files:**
- `exceptions.py` - Custom exceptions (AppException, NotFoundException, etc.)

**Rules:**
- Shared across all layers
- No business logic
- Base classes and utilities only

### `/src/config` - Configuration

**Purpose:** Application configuration

**Key Files:**
- `settings.py` - Pydantic Settings for environment variables
- `logs_config.py` - Logging configuration

**Rules:**
- Environment-based configuration
- Pydantic validation
- Sensitive values from environment

### `/src/models` - Domain Models

**Purpose:** Business entity definitions

**Rules:**
- Pydantic models for business entities
- Used across layers
- Separate from database models (if using SQLAlchemy)

### `/src/tests` - Automated Tests

**Purpose:** Test suite

**Key Files:**
- `conftest.py` - pytest fixtures and configuration
- `v1/test_health.py` - Health endpoint tests
- `v1/test_agent.py` - Agent endpoint tests

**Rules:**
- Mirror source structure
- Test each layer independently
- Integration tests for API endpoints

### `/docs` - Documentation

**Purpose:** Comprehensive project documentation

**Files:**
- `01-System-Design.md` - Architecture overview
- `02-Design-Patterns.md` - Design patterns
- `03-Database-Design.md` - Database documentation
- `04-Tech-Stack.md` - Technology inventory
- `05-Project-Structure.md` - This file
- `06-API-Documentation.md` - API reference
- `07-Setup-Installation.md` - Setup guide
- `08-Contribution-Guide.md` - Contributing
- `UPDATE-SUMMARY.md` - Recent changes
- `changelogs/` - Version history
- `milestone/` - Feature tracking

### `/alembic` - Database Migrations

**Purpose:** Database schema migrations

**Key Files:**
- `env.py` - Alembic environment configuration
- `script.py.mako` - Migration template
- `versions/` - Migration files

### Configuration Files

**`.env.example`**
Template for environment variables. Copy to `.env` and customize.

**`pyproject.toml`**
- Project metadata
- Dependencies (production and dev)
- Tool configurations (Ruff, etc.)

**`alembic.ini`**
Alembic migration configuration

**`docker-compose.yml`**
Docker services (PostgreSQL, Redis, app)

**`Dockerfile`**
Container build instructions

## Layer Communication

### Allowed Dependencies

```
API Layer
  ↓ (depends on)
Execution Layer
  ↓ (depends on)
Agent Layer (optional)
  ↓ (depends on)
Infrastructure (Providers, Database, Core)
```

### Dependency Rules

1. **No Circular Dependencies**
   ```python
   # ❌ WRONG: Circular dependency
   # api.py imports from execution.py
   # execution.py imports from api.py
   ```

2. **No Skipping Layers**
   ```python
   # ❌ WRONG: API talking directly to database
   @router.get("/users")
   async def get_users(db: AsyncSession = Depends(get_db)):
       result = await db.execute(select(User))
       return result.scalars().all()
   
   # ✅ CORRECT: API → Usecase → Repository
   @router.get("/users")
   async def get_users():
       usecase = GetUsersUsecase()
       return await usecase.execute()
   ```

3. **Infrastructure at Bottom**
   - Providers don't know about Agents
   - Database doesn't know about Execution
   - Core is independent

## File Naming Conventions

### Python Files

| Type | Pattern | Example |
|------|---------|---------|
| Modules | `snake_case.py` | `user_repository.py` |
| Classes | `PascalCase` | `UserRepository` |
| Functions | `snake_case` | `get_user_by_id` |
| Constants | `UPPER_CASE` | `MAX_RETRY_COUNT` |

### Directories

| Type | Pattern | Example |
|------|---------|---------|
| Directories | `snake_case` | `user_management` |
| Packages | `lowercase` | `api`, `core` |

## Adding New Features

### 1. New API Endpoint

1. Create endpoint in `src/api/endpoints/v1/`
2. Define schemas in `src/api/endpoints/v1/schemas/`
3. Add to `src/api/endpoints/v1/routers.py`
4. Create tests in `src/tests/v1/`

### 2. New Business Logic

1. Create usecase in `src/execution/usecases/`
2. Create actions in `src/execution/actions/`
3. Use Repository pattern for DB access
4. Add unit tests

### 3. New AI Agent

1. Define prompts as markdown in `src/agents/prompts/agents/`
2. Register prompts in `src/agents/prompts/prompt_manager.py`
3. Define agent or structured-output agent access in `src/agents/agent_manager/`
4. Add tools in `src/agents/tools/` when deterministic helpers are needed
5. For LangGraph workflows, create `src/agents/workflows/<feature>/state.py`, `nodes.py`, and `build.py`
6. Create an action that invokes the agent or compiled workflow
7. Create a usecase that orchestrates the action

### 4. New Database Entity

1. Create model in `src/models/`
2. Create repository in `src/database/repositories/`
3. Generate migration: `alembic revision --autogenerate -m "Add X table"`
4. Apply migration: `alembic upgrade head`

## Key Principles

1. **Separation of Concerns**
   - Each layer has a single responsibility
   - No mixing of HTTP, business, and data logic

2. **Dependency Inversion**
   - High-level modules don't depend on low-level details
   - Use abstractions (Repository pattern)

3. **Testability**
   - Each layer can be tested independently
   - Mock dependencies for unit tests

4. **Scalability**
   - Layers can be extracted to microservices
   - Clear interfaces between layers

5. **Maintainability**
   - Consistent structure
   - Clear naming
   - Comprehensive documentation

**Updated:** v0.3.0 - Added feature flags, provider abstraction (base.py, factory.py), production validation, updated test listing
