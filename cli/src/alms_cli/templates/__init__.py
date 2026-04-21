"""Project template generator."""

from pathlib import Path
from typing import Optional

class TemplateGenerator:
    """Generate ALMS project structure from templates."""
    
    def __init__(self, project_name: str, project_path: Path):
        self.project_name = project_name
        self.project_path = project_path
        self.features = []
    
    def generate(self, features: Optional[list[str]] = None) -> int:
        """Generate project structure and return file count."""
        self.features = features or []
        
        self._create_base_structure()
        self._create_config_files()
        self._create_source_files()
        
        return self._count_files()
    
    def _has_feature(self, keyword: str) -> bool:
        """Check if a feature is selected."""
        return any(keyword.lower() in f.lower() for f in self.features)
    
    def _create_base_structure(self):
        """Create base directory structure."""
        dirs = [
            "src/api/endpoints/v1/schemas",
            "src/api/middlewares",
            "src/api/router",
            "src/execution/actions",
            "src/execution/usecases",
            "src/agents/agent_manager",
            "src/agents/prompts",
            "src/agents/tools",
            "src/agents/workflows",
            "src/providers/ai",
            "src/providers/cache",
            "src/providers/vectordb",
            "src/core",
            "src/config",
            "src/models",
            "src/utils",
            "src/scripts",
            "src/docs",
            "src/evaluation",
            "src/data",
            "src/tests/v1",
            "src/tests/integration",
            "src/tests/e2e",
            "rules",
            "docs/changelogs",
            "assets/images",
        ]
        
        if self._has_feature("database"):
            dirs.extend([
                "src/database/migrations",
                "src/database/repositories",
                "alembic",
            ])
        
        if self._has_feature("ci/cd") or self._has_feature("github"):
            dirs.extend([
                ".github/workflows",
                ".github/ISSUE_TEMPLATE",
            ])
        
        for dir_path in dirs:
            (self.project_path / dir_path).mkdir(parents=True, exist_ok=True)
    
    def _create_config_files(self):
        """Create configuration files."""
        templates = {
            "pyproject.toml": self._pyproject_toml(),
            "README.md": self._readme(),
            ".env.example": self._env_example(),
            ".gitignore": self._gitignore(),
            "pytest.ini": self._pytest_ini(),
            "rules/project_rules.md": self._project_rules(),
            "docs/01-System-Design.md": "# System Design\n",
            "docs/02-Design-Patterns.md": "# Design Patterns\n",
            "docs/03-Database-Design.md": "# Database Design\n",
            "docs/04-Tech-Stack.md": "# Tech Stack\n",
            "docs/05-Project-Structure.md": "# Project Structure\n",
            "docs/06-API-Documentation.md": "# API Documentation\n",
            "docs/07-Setup-Installation.md": "# Setup & Installation\n",
            "docs/08-Contribution-Guide.md": "# Contribution Guide\n",
        }
        
        if self._has_feature("database"):
            templates.update({
                "alembic.ini": self._alembic_ini(),
                "alembic/README": "Alembic migrations\n",
                "alembic/env.py": self._alembic_env(),
                "alembic/script.py.mako": self._alembic_mako(),
            })
        
        if self._has_feature("docker"):
            templates.update({
                "docker-compose.yml": self._docker_compose(),
                "Dockerfile": self._dockerfile(),
            })
        
        if self._has_feature("ci/cd") or self._has_feature("github"):
            templates.update({
                ".github/workflows/ci.yml": self._ci_workflow(),
                ".github/dependabot.yml": self._dependabot(),
                ".github/ISSUE_TEMPLATE/bug_report.yml": self._bug_template(),
                ".github/ISSUE_TEMPLATE/feature_request.yml": self._feature_template(),
                ".github/pull_request_template.md": self._pr_template(),
            })
        
        for file_path, content in templates.items():
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
    
    def _create_source_files(self):
        """Create source code files."""
        templates = {
            "src/__init__.py": "",
            "src/api/__init__.py": "",
            "src/api/main.py": self._main_py(),
            "src/api/endpoints/__init__.py": "",
            "src/api/endpoints/v1/__init__.py": "",
            "src/api/endpoints/v1/dependencies.py": self._dependencies_py(),
            "src/api/endpoints/v1/health.py": self._health_py(),
            "src/api/endpoints/v1/routers.py": self._routers_py(),
            "src/api/endpoints/v1/sample_agent.py": self._sample_agent_py(),
            "src/api/endpoints/v1/sample_di.py": self._sample_di_py(),
            "src/api/endpoints/v1/schemas/__init__.py": "",
            "src/api/endpoints/v1/schemas/base.py": self._schema_base_py(),
            "src/api/endpoints/v1/schemas/sample.py": self._schema_sample_py(),
            "src/api/middlewares/__init__.py": "",
            "src/api/middlewares/error_handler.py": self._error_handler_py(),
            "src/api/middlewares/logging.py": self._logging_middleware_py(),
            "src/api/middlewares/security.py": self._security_middleware_py(),
            "src/api/router/__init__.py": "",
            "src/api/router/routers.py": self._router_py(),
            "src/execution/__init__.py": "",
            "src/execution/actions/__init__.py": "",
            "src/execution/actions/sample_action.py": self._sample_action_py(),
            "src/execution/usecases/__init__.py": "",
            "src/execution/usecases/sample_usecase.py": self._sample_usecase_py(),
            "src/agents/__init__.py": "",
            "src/agents/agent_manager/__init__.py": "",
            "src/agents/agent_manager/agent.py": self._agent_py(),
            "src/agents/prompts/__init__.py": "",
            "src/agents/prompts/sample_agent_prompt.py": self._sample_prompt_py(),
            "src/agents/tools/.gitkeep": "",
            "src/agents/workflows/.gitkeep": "",
            "src/providers/__init__.py": "",
            "src/providers/ai/__init__.py": "",
            "src/providers/ai/langchain_model_loader.py": self._model_loader_py(),
            "src/providers/cache/.gitkeep": "",
            "src/providers/vectordb/.gitkeep": "",
            "src/core/__init__.py": "",
            "src/core/exceptions.py": self._exceptions_py(),
            "src/config/__init__.py": "",
            "src/config/settings.py": self._settings_py(),
            "src/config/logs_config.py": self._logs_config_py(),
            "src/models/.gitkeep": "",
            "src/utils/.gitkeep": "",
            "src/scripts/.gitkeep": "",
            "src/docs/.gitkeep": "",
            "src/evaluation/.gitkeep": "",
            "src/data/.gitkeep": "",
            "src/tests/__init__.py": "",
            "src/tests/conftest.py": self._conftest_py(),
            "src/tests/README.md": "# Tests\n",
            "src/tests/v1/__init__.py": "",
            "src/tests/v1/test_health.py": self._test_health_py(),
            "src/tests/v1/test_agent.py": self._test_agent_py(),
            "src/tests/integration/__init__.py": "",
            "src/tests/integration/test_full_stack.py": self._test_full_stack_py(),
            "src/tests/e2e/__init__.py": "",
            "src/tests/e2e/test_workflows.py": self._test_workflows_py(),
        }
        
        if self._has_feature("observability"):
            templates.update({
                "src/observability/__init__.py": self._observability_init_py(),
                "src/observability/metrics.py": self._metrics_module_py(),
                "src/observability/tracing.py": self._tracing_py(),
                "src/api/middlewares/observability.py": self._observability_middleware_py(),
                "src/api/endpoints/v1/metrics.py": self._metrics_py(),
                "src/tests/v1/test_metrics.py": self._test_metrics_py(),
                "src/tests/v1/test_metrics_endpoint.py": self._test_metrics_endpoint_py(),
                "src/tests/v1/test_observability_middleware.py": self._test_observability_middleware_py(),
                "src/tests/v1/test_tracing.py": self._test_tracing_py(),
            })
        
        if self._has_feature("database"):
            templates.update({
                "src/database/__init__.py": "",
                "src/database/connection.py": self._db_connection_py(),
                "src/database/migrations/.gitkeep": "",
                "src/database/repositories/__init__.py": "",
                "src/database/repositories/base.py": self._repository_base_py(),
                "src/database/repositories/sqlalchemy_repository.py": self._sqlalchemy_repo_py(),
                "src/tests/v1/test_sqlalchemy_repository.py": self._test_sqlalchemy_repository_py(),
            })
        
        for file_path, content in templates.items():
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
    
    def _count_files(self) -> int:
        """Count created files."""
        count = 0
        for path in self.project_path.rglob("*"):
            if path.is_file() and not path.name.startswith('.'):
                count += 1
        return count
    
    def _pyproject_toml(self) -> str:
        return f'''[project]
name = "{self.project_name}"
version = "0.1.0"
description = "ALMS AI-first backend starter"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "fastapi[standard]>=0.122.0",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.12.0",
    "uvicorn>=0.38.0",
    "ruff>=0.14.11",
]

[dependency-groups]
dev = [
    "httpx>=0.28.1",
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
]
'''
    
    def _readme(self) -> str:
        return f'''# {self.project_name}

> **The AI-First Backend for Scalable, Intelligent Applications.**

## Quick Start

### Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed

### 1. Setup

```bash
cp .env.example .env
```

### 2. Install Dependencies

```bash
uv sync
```

### 3. Start the Application

```bash
uv run -m src.api.main
```

The API will be available at:
- API: http://localhost:3000
- Docs: http://localhost:3000/docs
'''
    
    def _env_example(self) -> str:
        return '''# OpenAI Configuration
OPENAI_API_KEY=sk-...
OPENAI_MODEL_BASIC=gpt-4o-mini
OPENAI_MODEL_REASONING=gpt-4o

# Application
DEBUG=true
LOG_LEVEL=info
SERVER_PORT=3000
'''
    
    def _gitignore(self) -> str:
        return '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Virtual environments
.venv/
venv/

# Distribution / packaging
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Environment
.env
.env.local

# Logs
*.log
logs/

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
'''
    
    def _pytest_ini(self) -> str:
        return '''[pytest]
testpaths = src/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
'''
    
    def _project_rules(self) -> str:
        return '''# Project Rules

## ALMS Architecture Guidelines

1. Never skip layers: API -> Execution -> Agent -> Infrastructure
2. Use repository pattern for database access
3. Use custom exceptions, not raw HTTPException
4. Add type hints to all functions
5. Write tests for all use cases and actions
'''
    
    def _alembic_ini(self) -> str:
        return '''[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://postgres:secret@localhost:5432/mydb

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
    
    def _docker_compose(self) -> str:
        return '''version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: mydb
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: secret
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
'''
    
    def _dockerfile(self) -> str:
        return '''FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

EXPOSE 3000

CMD ["uv", "run", "-m", "src.api.main", "--host", "0.0.0.0"]
'''
    
    def _ci_workflow(self) -> str:
        return '''name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync
      - run: uv run pytest src/tests
      - run: uv run ruff check src/
'''
    
    def _dependabot(self) -> str:
        return '''version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
'''
    
    def _bug_template(self) -> str:
        return '''name: Bug Report
description: Create a report to help us improve
body:
  - type: textarea
    attributes:
      label: Describe the bug
    validations:
      required: true
'''
    
    def _feature_template(self) -> str:
        return '''name: Feature Request
description: Suggest an idea for this project
body:
  - type: textarea
    attributes:
      label: Describe the feature
    validations:
      required: true
'''
    
    def _pr_template(self) -> str:
        return '''## Description

Please include a summary of the changes.

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
'''
    
    def _alembic_env(self) -> str:
        return '''from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    def _alembic_mako(self) -> str:
        return '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''
    
    def _main_py(self) -> str:
        return '''"""FastAPI application entry point."""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.config.settings import settings
from src.api.router.routers import include_routers
from src.api.middlewares.security import setup_security_middleware
from src.api.middlewares.logging import setup_logging_middleware
from src.api.middlewares.error_handler import setup_error_handler


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
    )
    
    setup_security_middleware(app)
    setup_logging_middleware(app)
    setup_error_handler(app)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    include_routers(app)
    
    try:
        from scalar_fastapi import get_scalar_api_reference
        
        @app.get("/docs", include_in_schema=False)
        async def scalar_html():
            return get_scalar_api_reference(
                openapi_url=app.openapi_url,
                title=app.title,
            )
    except ImportError:
        pass
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG,
    )
'''
    
    def _dependencies_py(self) -> str:
        return '''"""Dependencies for v1 endpoints."""

from fastapi import Depends


def get_db_session():
    """Get database session."""
    pass
'''
    
    def _health_py(self) -> str:
        return '''"""Health check endpoint."""

from fastapi import APIRouter
from src.api.endpoints.v1.schemas.base import AppResponse

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return AppResponse(success=True, data={"status": "healthy"})
'''
    
    def _metrics_py(self) -> str:
        return '''"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response
from src.observability.metrics import generate_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """Expose Prometheus metrics."""
    metrics_data = generate_metrics()
    return Response(content=metrics_data, media_type="text/plain")
'''
    
    def _routers_py(self) -> str:
        return '''"""Main v1 router aggregation."""

from fastapi import APIRouter
from src.api.endpoints.v1 import health, sample_agent, sample_di

v1_router = APIRouter(prefix="/api/v1")

v1_router.include_router(health.router, tags=["Health"])
v1_router.include_router(sample_agent.router, tags=["Agent"])
v1_router.include_router(sample_di.router, tags=["DI Example"])
'''
    
    def _sample_agent_py(self) -> str:
        return '''"""Sample agent endpoint."""

from fastapi import APIRouter
from src.api.endpoints.v1.schemas.base import AppResponse
from src.execution.usecases.sample_usecase import SampleUsecase

router = APIRouter()


@router.post("/agent/sample")
async def sample_agent(query: str):
    """Sample agent endpoint."""
    usecase = SampleUsecase()
    result = await usecase.execute(query)
    return AppResponse(success=True, data=result)
'''
    
    def _sample_di_py(self) -> str:
        return '''"""Sample dependency injection endpoint."""

from fastapi import APIRouter, Depends
from src.api.endpoints.v1.schemas.base import AppResponse
from src.api.endpoints.v1.dependencies import get_db_session

router = APIRouter()


@router.get("/di/sample")
async def sample_di(session=Depends(get_db_session)):
    """Sample DI endpoint."""
    return AppResponse(success=True, data={"message": "DI working"})
'''
    
    def _schema_base_py(self) -> str:
        return '''"""Base response schemas."""

from pydantic import BaseModel
from typing import Any, Optional
from uuid import UUID, uuid4


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[dict[str, Any]] = None


class AppResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None
    request_id: UUID = uuid4()
'''
    
    def _schema_sample_py(self) -> str:
        return '''"""Sample request/response schemas."""

from pydantic import BaseModel


class SampleRequest(BaseModel):
    query: str


class SampleResponse(BaseModel):
    message: str
    result: str
'''
    
    def _error_handler_py(self) -> str:
        return '''"""Error handler middleware."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.core.exceptions import AppException
from src.api.endpoints.v1.schemas.base import AppResponse, ErrorDetail


def setup_error_handler(app: FastAPI):
    """Setup global error handlers."""
    
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content=AppResponse(
                success=False,
                error=ErrorDetail(
                    code=exc.error_code,
                    message=exc.message,
                    details=exc.details,
                ),
            ).model_dump(),
        )
'''
    
    def _logging_middleware_py(self) -> str:
        return '''"""Request logging middleware."""

import logging
import time
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s"
        )
        
        return response


def setup_logging_middleware(app: FastAPI):
    """Setup logging middleware."""
    app.add_middleware(LoggingMiddleware)
'''
    
    def _observability_middleware_py(self) -> str:
        return '''"""Observability middleware for metrics and tracing."""

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
from src.observability.metrics import metrics


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        metrics.counter(
            "http_requests_total",
            {"method": request.method, "endpoint": request.url.path, "status": str(response.status_code)},
        )
        
        return response


def setup_observability_middleware(app: FastAPI):
    """Setup observability middleware."""
    app.add_middleware(ObservabilityMiddleware)
'''
    
    def _security_middleware_py(self) -> str:
        return '''"""Security headers middleware."""

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware


class SecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_security_middleware(app: FastAPI):
    """Setup security middleware."""
    app.add_middleware(SecurityMiddleware)
'''
    
    def _router_py(self) -> str:
        return '''"""Router aggregation."""

from fastapi import FastAPI
from src.api.endpoints.v1.routers import v1_router


def include_routers(app: FastAPI):
    """Include all routers in the application."""
    app.include_router(v1_router)
'''
    
    def _sample_action_py(self) -> str:
        return '''"""Sample action."""

from typing import Any


class SampleAction:
    """Sample action that performs a discrete operation."""
    
    async def execute(self, query: str) -> dict[str, Any]:
        """Execute the action."""
        return {"message": f"Processed: {query}", "status": "success"}
'''
    
    def _sample_usecase_py(self) -> str:
        return '''"""Sample usecase."""

from typing import Any
from src.execution.actions.sample_action import SampleAction


class SampleUsecase:
    """Sample usecase that orchestrates business flow."""
    
    def __init__(self):
        self.action = SampleAction()
    
    async def execute(self, query: str) -> dict[str, Any]:
        """Execute the usecase."""
        result = await self.action.execute(query)
        return {"usecase_result": result}
'''
    
    def _agent_py(self) -> str:
        return '''"""Agent definitions."""

from langchain_openai import ChatOpenAI
from src.config.settings import settings


class SampleAgent:
    """Sample AI agent."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_BASIC,
            api_key=settings.OPENAI_API_KEY,
        )
    
    async def process(self, query: str) -> str:
        """Process a query using the agent."""
        response = await self.llm.ainvoke(query)
        return response.content
'''
    
    def _sample_prompt_py(self) -> str:
        return '''"""Sample agent prompt template."""

SAMPLE_AGENT_PROMPT = """You are a helpful AI assistant.

Query: {query}

Please provide a helpful response."""
'''
    
    def _model_loader_py(self) -> str:
        return '''"""AI model loader provider."""

from langchain_openai import ChatOpenAI
from src.config.settings import settings


def get_llm(model: str = "basic") -> ChatOpenAI:
    """Get LLM instance."""
    model_name = (
        settings.OPENAI_MODEL_REASONING
        if model == "reasoning"
        else settings.OPENAI_MODEL_BASIC
    )
    
    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
    )
'''
    
    def _observability_init_py(self) -> str:
        return '''"""Observability module."""

from src.observability.metrics import metrics
from src.observability.tracing import tracer

__all__ = ["metrics", "tracer"]
'''
    
    def _metrics_module_py(self) -> str:
        return '''"""Prometheus metrics."""

from prometheus_client import Counter, Histogram, generate_latest


metrics_counter = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])


class MetricsCollector:
    """Collect and expose metrics."""
    
    def counter(self, name: str, labels: dict[str, str]):
        """Increment a counter metric."""
        pass
    
    def generate(self) -> bytes:
        """Generate metrics data."""
        return generate_latest()


metrics = MetricsCollector()


def generate_metrics() -> bytes:
    """Generate Prometheus metrics."""
    return generate_latest()
'''
    
    def _tracing_py(self) -> str:
        return '''"""OpenTelemetry tracing."""

from contextlib import contextmanager


class Tracer:
    """Simple tracer for distributed tracing."""
    
    @contextmanager
    def start_as_current_span(self, name: str):
        """Start a new span."""
        yield


tracer = Tracer()
'''
    
    def _db_connection_py(self) -> str:
        return '''"""Database connection setup."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    """Get database session."""
    async with async_session() as session:
        yield session
'''
    
    def _repository_base_py(self) -> str:
        return '''"""Base repository pattern."""

from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""
    
    def __init__(self, model: Type[ModelType]):
        self.model = model
    
    async def get(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        """Get by ID."""
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    
    async def get_multi(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        """Get multiple records."""
        result = await session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
'''
    
    def _sqlalchemy_repo_py(self) -> str:
        return '''"""SQLAlchemy repository implementation."""

from src.database.repositories.base import BaseRepository


class SQLAlchemyRepository(BaseRepository):
    """SQLAlchemy specific repository implementation."""
    pass
'''
    
    def _exceptions_py(self) -> str:
        return '''"""Custom exceptions."""

from typing import Optional


class AppException(Exception):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundException(AppException):
    """Resource not found."""
    
    def __init__(self, message: str, error_code: str = "NOT_FOUND", details: Optional[dict] = None):
        super().__init__(message, error_code, 404, details)


class ValidationException(AppException):
    """Validation error."""
    
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", details: Optional[dict] = None):
        super().__init__(message, error_code, 422, details)
'''
    
    def _settings_py(self) -> str:
        return '''"""Application settings."""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    PROJECT_NAME: str = "ALMS Backend"
    DEBUG: bool = True
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 3000
    
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_BASIC: str = "gpt-4o-mini"
    OPENAI_MODEL_REASONING: str = "gpt-4o"
    
    LOG_LEVEL: str = "info"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
'''
    
    def _logs_config_py(self) -> str:
        return '''"""Logging configuration."""

import logging
import sys
from src.config.settings import settings


def setup_logging():
    """Configure application logging."""
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
'''
    
    def _conftest_py(self) -> str:
        return '''"""Pytest configuration and fixtures."""

import pytest
from httpx import AsyncClient
from src.api.main import app


@pytest.fixture
async def client():
    """Create test client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
'''
    
    def _test_health_py(self) -> str:
        return '''"""Health endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test health check endpoint."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
'''
    
    def _test_agent_py(self) -> str:
        return '''"""Agent endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_sample_agent(client):
    """Test sample agent endpoint."""
    response = await client.post("/api/v1/agent/sample", json={"query": "test"})
    assert response.status_code == 200
'''
    
    def _test_metrics_py(self) -> str:
        return '''"""Metrics tests."""

import pytest


@pytest.mark.asyncio
async def test_metrics_collection():
    """Test metrics collection."""
    pass
'''
    
    def _test_metrics_endpoint_py(self) -> str:
        return '''"""Metrics endpoint tests."""

import pytest


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    """Test metrics endpoint."""
    response = await client.get("/api/v1/metrics")
    assert response.status_code == 200
'''
    
    def _test_observability_middleware_py(self) -> str:
        return '''"""Observability middleware tests."""

import pytest


@pytest.mark.asyncio
async def test_observability_middleware(client):
    """Test observability middleware."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
'''
    
    def _test_sqlalchemy_repository_py(self) -> str:
        return '''"""SQLAlchemy repository tests."""

import pytest


@pytest.mark.asyncio
async def test_repository_base():
    """Test base repository."""
    pass
'''
    
    def _test_tracing_py(self) -> str:
        return '''"""Tracing tests."""

import pytest


@pytest.mark.asyncio
async def test_tracing():
    """Test tracing setup."""
    pass
'''
    
    def _test_full_stack_py(self) -> str:
        return '''"""Full stack integration tests."""

import pytest


@pytest.mark.asyncio
async def test_full_stack(client):
    """Test full stack integration."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
'''
    
    def _test_workflows_py(self) -> str:
        return '''"""End-to-end workflow tests."""

import pytest


@pytest.mark.asyncio
async def test_workflow(client):
    """Test complete workflow."""
    pass
'''
