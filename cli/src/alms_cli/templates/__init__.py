"""Project template generator -- capability-aware edition."""

from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Profile / capability model
# ---------------------------------------------------------------------------

ALL_CAPABILITIES = {
    "runtime_auth",
    "scalar_docs",
    "llm",
    "langgraph",
    "database",
    "redis",
    "observability",
    "tests",
    "docker",
    "ci",
}

PROFILE_CAPABILITIES: dict[str, set[str]] = {
    "core-api":       {"runtime_auth", "tests"},
    "llm-agent":      {"runtime_auth", "tests", "llm", "scalar_docs"},
    "workflow-agent": {"runtime_auth", "tests", "llm", "langgraph", "scalar_docs"},
    "db-agent":       {"runtime_auth", "tests", "database"},
    "observable":     {"runtime_auth", "tests", "observability"},
    "full": {
        "runtime_auth", "tests", "llm", "langgraph", "database",
        "redis", "observability", "scalar_docs", "docker", "ci",
    },
}

FEATURE_LABEL_TO_CAPABILITY: dict[str, str] = {
    "database":     "database",
    "redis cache":  "redis",
    "ai agents":    "llm",
    "observability": "observability",
    "docker support": "docker",
    "ci/cd":        "ci",
}

CAPABILITY_TO_EXTRA: dict[str, str | None] = {
    "llm":            "ai",
    "langgraph":      "workflow",
    "database":       "db",
    "redis":          "cache",
    "observability":  "observability",
    "scalar_docs":    "docs",
}

NO_EXTRA_CAPABILITIES = frozenset({"runtime_auth", "tests", "docker", "ci"})


def resolve_capabilities(
    profile: str | None = None,
    features: list[str] | None = None,
) -> set[str]:
    """Return the resolved capability set from a profile name and/or feature list."""
    caps: set[str] = set()

    if profile and profile in PROFILE_CAPABILITIES:
        caps = PROFILE_CAPABILITIES[profile].copy()

    if features:
        for f in features:
            key = f.strip().lower()
            for lbl, cap in FEATURE_LABEL_TO_CAPABILITY.items():
                if lbl in key:
                    caps.add(cap)
                    break

    caps.add("runtime_auth")
    caps.add("tests")
    return caps


def resolve_extras(capabilities: set[str]) -> list[str]:
    """Return the ordered list of pip extras needed for a capability set."""
    extras: list[str] = []
    for cap in sorted(capabilities):
        extra = CAPABILITY_TO_EXTRA.get(cap)
        if extra and extra not in extras:
            extras.append(extra)
    return extras

# ---------------------------------------------------------------------------
# Extra dependency specs (used by pyproject.toml generator)
# ---------------------------------------------------------------------------

_EXTRA_DEPS: dict[str, list[str]] = {
    "ai": [
        "langchain>=1.2.15",
        "langchain-community>=0.4.1",
        "langchain-mcp-adapters>=0.1.14",
        "langchain-openai>=1.1.0",
        "openai>=2.33.0",
    ],
    "workflow": [
        "langgraph>=1.1.9",
    ],
    "db": [
        "sqlalchemy>=2.0.49",
        "asyncpg>=0.31.0",
        "alembic>=1.17.2",
    ],
    "cache": [
        "redis>=7.4.0",
    ],
    "observability": [
        "opentelemetry-api>=1.25.0",
        "opentelemetry-sdk>=1.25.0",
        "opentelemetry-instrumentation-fastapi>=0.46b0",
        "opentelemetry-instrumentation-sqlalchemy>=0.46b0",
        "opentelemetry-instrumentation-redis>=0.46b0",
        "opentelemetry-exporter-otlp>=1.25.0",
        "prometheus-client>=0.20.0",
    ],
    "docs": [
        "scalar-fastapi>=1.6.0",
    ],
}


# ---------------------------------------------------------------------------
# TemplateGenerator
# ---------------------------------------------------------------------------

class TemplateGenerator:
    """Generate ALMS project structure from profiles and capabilities."""

    def __init__(self, project_name: str, project_path: Path):
        self.project_name = project_name
        self.project_path = project_path
        self.capabilities: set[str] = set()

    def generate(
        self,
        capabilities: Optional[set[str]] = None,
    ) -> int:
        """Generate project structure and return file count."""
        self.capabilities = capabilities or {"runtime_auth", "tests"}
        self._create_base_structure()
        self._create_config_files()
        self._create_source_files()
        return self._count_files()

    def _has(self, capability: str) -> bool:
        return capability in self.capabilities

    def _count_files(self) -> int:
        count = 0
        for path in self.project_path.rglob("*"):
            if path.is_file() and not path.name.startswith("."):
                count += 1
        return count

    # -- directory scaffolding -----------------------------------------------

    def _create_base_structure(self):
        dirs = [
            "src/api/endpoints/v1/schemas",
            "src/api/middlewares",
            "src/api/router",
            "src/execution/actions",
            "src/execution/usecases",
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
        if self._has("llm"):
            dirs.extend([
                "src/agents/agent_manager",
                "src/agents/prompts",
                "src/agents/tools",
                "src/providers/ai",
            ])
        if self._has("langgraph"):
            dirs.append("src/agents/workflows")
        if self._has("database"):
            dirs.extend([
                "src/database/migrations",
                "src/database/repositories",
                "alembic",
            ])
        if self._has("redis"):
            dirs.append("src/providers/cache")
        if self._has("ci"):
            dirs.extend([
                ".github/workflows",
                ".github/ISSUE_TEMPLATE",
            ])
        for dir_path in dirs:
            (self.project_path / dir_path).mkdir(parents=True, exist_ok=True)

    # -- config files --------------------------------------------------------

    def _create_config_files(self):
        templates: dict[str, str] = {
            "pyproject.toml": self._pyproject_toml(),
            "README.md": self._readme(),
            ".env.example": self._env_example(),
            ".gitignore": self._gitignore(),
            "pytest.ini": self._pytest_ini(),
            "rules/project_rules.md": self._project_rules(),
        }
        if self._has("database"):
            templates.update({
                "alembic.ini": self._alembic_ini(),
                "alembic/README": "Alembic migrations\n",
                "alembic/env.py": self._alembic_env(),
                "alembic/script.py.mako": self._alembic_mako(),
            })
        if self._has("docker"):
            templates.update({
                "docker-compose.yml": self._docker_compose(),
                "Dockerfile": self._dockerfile(),
            })
        if self._has("ci"):
            templates.update({
                ".github/workflows/ci.yml": self._ci_workflow(),
                ".github/dependabot.yml": self._dependabot(),
                ".github/ISSUE_TEMPLATE/bug_report.yml": self._bug_template(),
                ".github/ISSUE_TEMPLATE/feature_request.yml": self._feature_template(),
                ".github/pull_request_template.md": self._pr_template(),
            })
        doc_placeholders = {
            "docs/01-System-Design.md": "# System Design\n",
            "docs/02-Design-Patterns.md": "# Design Patterns\n",
            "docs/03-Database-Design.md": "# Database Design\n",
            "docs/04-Tech-Stack.md": "# Tech Stack\n",
            "docs/05-Project-Structure.md": "# Project Structure\n",
            "docs/06-API-Documentation.md": "# API Documentation\n",
            "docs/07-Setup-Installation.md": "# Setup & Installation\n",
            "docs/08-Contribution-Guide.md": "# Contribution Guide\n",
        }
        templates.update(doc_placeholders)
        for file_path, content in templates.items():
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

    # ========================================================================
    # pyproject.toml with [tool.alms] metadata
    # ========================================================================

    def _tool_alms_section(self) -> str:
        caps = sorted(self.capabilities)
        profile = "custom"
        for name, pcaps in PROFILE_CAPABILITIES.items():
            if pcaps == self.capabilities:
                profile = name
                break
        return (
            "\n[tool.alms]\n"
            f'profile = "{profile}"\n'
            f"capabilities = {caps!r}\n"
        )

    def _pyproject_toml(self) -> str:
        extras = resolve_extras(self.capabilities)
        dep_lines = [
            '    "fastapi[standard]>=0.122.0",',
            '    "pydantic>=2.12.5",',
            '    "pydantic-settings>=2.12.0",',
            '    "uvicorn>=0.38.0",',
        ]
        toml = (
            f"[project]\n"
            f'name = "{self.project_name}"\n'
            f'version = "0.1.0"\n'
            f'description = "ALMS AI-first backend starter"\n'
            f'readme = "README.md"\n'
            f'requires-python = ">=3.13"\n'
            f"dependencies = [\n"
        )
        toml += "\n".join(dep_lines)
        toml += "\n]\n"

        if extras:
            toml += "\n[project.optional-dependencies]\n"
            for extra in extras:
                toml += _extra_block(extra)
            all_specs: list[str] = []
            for extra in extras:
                all_specs.extend(_EXTRA_DEPS.get(extra, []))
            if all_specs:
                toml += "full = [\n"
                for spec in sorted(set(all_specs)):
                    toml += f'    "{spec}",\n'
                toml += "]\n"

        toml += (
            "\n[dependency-groups]\n"
            'dev = [\n'
            '    "httpx>=0.28.1",\n'
            '    "pytest>=9.0.2",\n'
            '    "pytest-asyncio>=1.3.0",\n'
            '    "ruff>=0.14.11",\n'
            "]\n"
        )
        toml += self._tool_alms_section()
        toml += "\n"
        return toml

    # -- source files --------------------------------------------------------

    def _create_source_files(self):
        templates: dict[str, str] = {
            "src/__init__.py": "",
            "src/api/__init__.py": "",
            "src/api/main.py": self._main_py(),
            "src/api/endpoints/__init__.py": "",
            "src/api/endpoints/v1/__init__.py": "",
            "src/api/endpoints/v1/dependencies.py": self._dependencies_py(),
            "src/api/endpoints/v1/health.py": self._health_py(),
            "src/api/endpoints/v1/routers.py": self._routers_py(),
            "src/api/endpoints/v1/schemas/__init__.py": "",
            "src/api/endpoints/v1/schemas/base.py": self._schema_base_py(),
            "src/api/middlewares/__init__.py": "",
            "src/api/middlewares/error_handler.py": self._error_handler_py(),
            "src/api/middlewares/logging.py": self._logging_middleware_py(),
            "src/api/middlewares/security.py": self._security_middleware_py(),
            "src/api/router/__init__.py": "",
            "src/api/router/routers.py": self._router_py(),
            "src/execution/__init__.py": "",
            "src/execution/actions/__init__.py": "",
            "src/execution/usecases/__init__.py": "",
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
            "src/tests/integration/__init__.py": "",
            "src/tests/integration/test_full_stack.py": self._test_full_stack_py(),
            "src/tests/e2e/__init__.py": "",
            "src/tests/e2e/test_workflows.py": self._test_workflows_py(),
        }

        if self._has("llm"):
            templates.update({
                "src/agents/__init__.py": "",
                "src/agents/agent_manager/__init__.py": "",
                "src/agents/agent_manager/agent.py": self._agent_py(),
                "src/agents/prompts/__init__.py": "",
                "src/agents/prompts/sample_agent_prompt.py": self._sample_prompt_py(),
                "src/providers/__init__.py": "",
                "src/providers/ai/__init__.py": "",
                "src/providers/ai/langchain_model_loader.py": self._model_loader_py(),
                "src/execution/actions/sample_action.py": self._sample_action_py(),
                "src/execution/usecases/sample_usecase.py": self._sample_usecase_py(),
                "src/api/endpoints/v1/schemas/sample.py": self._schema_sample_py(),
                "src/api/endpoints/v1/sample_agent.py": self._sample_agent_py(),
                "src/api/endpoints/v1/sample_di.py": self._sample_di_py(),
                "src/tests/v1/test_agent.py": self._test_agent_py(),
            })

        if self._has("langgraph"):
            templates.update({
                "src/agents/tools/.gitkeep": "",
                "src/agents/workflows/.gitkeep": "",
            })

        if self._has("database"):
            templates.update({
                "src/database/__init__.py": "",
                "src/database/connection.py": self._db_connection_py(),
                "src/database/migrations/.gitkeep": "",
                "src/database/repositories/__init__.py": "",
                "src/database/repositories/base.py": self._repository_base_py(),
                "src/database/repositories/sqlalchemy_repository.py": self._sqlalchemy_repo_py(),
                "src/tests/v1/test_sqlalchemy_repository.py": self._test_sqlalchemy_repository_py(),
            })

        if self._has("redis"):
            templates["src/providers/cache/.gitkeep"] = ""

        if self._has("observability"):
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

        for file_path, content in templates.items():
            full_path = self.project_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

    # ========================================================================
    # Profile-aware template generators
    # ========================================================================

    def _main_py(self) -> str:
        has_scalar = self._has("scalar_docs")
        has_obs = self._has("observability")
        imports = [
            "from contextlib import asynccontextmanager",
            "import uvicorn",
            "from fastapi import FastAPI",
            "from fastapi.middleware.cors import CORSMiddleware",
            "from src.config.settings import settings",
            "from src.api.router.routers import include_routers",
            "from src.api.middlewares.error_handler import setup_error_handler",
            "from src.api.middlewares.security import setup_security_middleware",
            "from src.api.middlewares.logging import setup_logging_middleware",
        ]
        obs_block = ""
        obs_mw = ""
        if has_obs:
            imports.append("from src.api.middlewares.observability import setup_observability_middleware")
            obs_mw = "    setup_observability_middleware(app)\n"
            obs_block = (
                "    try:\n"
                "        from src.observability import setup_metrics, setup_tracing, instrument_fastapi\n"
                "        if settings.METRICS_ENABLED:\n"
                "            setup_metrics(service_name=settings.SERVICE_NAME, service_version=settings.APP_VERSION)\n"
                "        if settings.TRACING_ENABLED:\n"
                "            setup_tracing(service_name=settings.SERVICE_NAME, service_version=settings.APP_VERSION)\n"
                "            instrument_fastapi(app)\n"
                "    except ImportError:\n"
                "        pass\n"
            )
        scalar_block = ""
        if has_scalar:
            scalar_block = (
                "\n    try:\n"
                "        from scalar_fastapi import get_scalar_api_reference\n"
                "        @app.get(\"/docs\", include_in_schema=False)\n"
                "        async def scalar_html():\n"
                "            return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)\n"
                "    except ImportError:\n"
                "        pass\n"
            )
        lifespan = (
            "@asynccontextmanager\n"
            "async def lifespan(app: FastAPI):\n"
            "    settings.validate_production_settings()\n"
            + obs_block +
            "    yield\n"
        )
        src = '"""FastAPI application entry point."""\n\n'
        src += "\n".join(imports) + "\n\n\n"
        src += lifespan + "\n\n"
        src += (
            "def create_app() -> FastAPI:\n"
            "    \"\"\"Create and configure FastAPI application.\"\"\"\n"
            "    app = FastAPI(\n"
            "        title=settings.PROJECT_NAME,\n"
            "        version=\"0.1.0\",\n"
            "        lifespan=lifespan,\n"
            "        docs_url=None,\n"
            "        redoc_url=None,\n"
            "    )\n\n"
            + obs_mw +
            "    setup_error_handler(app)\n"
            "    setup_security_middleware(app)\n"
            "    setup_logging_middleware(app)\n\n"
            "    app.add_middleware(\n"
            "        CORSMiddleware,\n"
            "        allow_origins=[\"*\"],\n"
            "        allow_credentials=True,\n"
            "        allow_methods=[\"*\"],\n"
            "        allow_headers=[\"*\"],\n"
            "    )\n\n"
            "    include_routers(app)\n"
            "    return app\n\n\n"
            "app = create_app()\n\n\n"
            'if __name__ == "__main__":\n'
            "    uvicorn.run(\n"
            '        "src.api.main:app",\n'
            "        host=settings.SERVER_HOST,\n"
            "        port=settings.SERVER_PORT,\n"
            "        reload=settings.DEBUG,\n"
            "    )\n"
        )
        src += scalar_block
        return src

    def _routers_py(self) -> str:
        has_llm = self._has("llm")
        has_obs = self._has("observability")
        src = '"""Main v1 router aggregation."""\n\n'
        src += "from fastapi import APIRouter\n"
        src += "from src.api.endpoints.v1 import health\n"
        if has_obs:
            src += "from src.api.endpoints.v1 import metrics\n"
        if has_llm:
            src += "from src.api.endpoints.v1 import sample_agent, sample_di\n"
        src += '\nv1_router = APIRouter(prefix="/api/v1")\n\n'
        src += 'v1_router.include_router(health.router, tags=["Health"])\n'
        if has_obs:
            src += 'v1_router.include_router(metrics.router, tags=["Monitoring"])\n'
        if has_llm:
            src += 'v1_router.include_router(sample_agent.router, tags=["Agent"])\n'
            src += 'v1_router.include_router(sample_di.router, tags=["DI Example"])\n'
        return src

    def _health_py(self) -> str:
        has_db = self._has("database")
        src = (
            '"""Health check endpoint."""\n\n'
            "from fastapi import APIRouter, status\n"
            "from src.api.endpoints.v1.schemas.base import AppResponse\n\n"
            "router = APIRouter()\n\n\n"
            '@router.get("/live", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)\n'
            "async def live_check():\n"
            '    return AppResponse(success=True, data={"status": "alive", "ready": True})\n\n\n'
        )
        if not has_db:
            src += (
                '@router.get("/ready", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)\n'
                "async def ready_check():\n"
                '    return AppResponse(success=True, data={"status": "ready", "ready": True})\n\n\n'
                '@router.get("/health")\n'
                "async def health_check():\n"
                "    return await ready_check()\n"
            )
        else:
            src += (
                "from src.config.settings import settings\n\n\n"
                '@router.get("/ready", response_model=AppResponse[dict], status_code=status.HTTP_200_OK)\n'
                "async def ready_check():\n"
                "    if not settings.DATABASE_ENABLED:\n"
                '        return AppResponse(success=True, data={"status": "ready", "ready": True})\n'
                "    try:\n"
                "        from src.database.connection import check_database_connection\n"
                "    except ImportError:\n"
                '        return AppResponse(success=False, data={"status": "degraded", "ready": False})\n'
                "    db_ready = await check_database_connection()\n"
                "    if db_ready:\n"
                '        return AppResponse(success=True, data={"status": "ready", "ready": True, "dependencies": {"database": "healthy"}})\n'
                "    from fastapi.responses import JSONResponse\n"
                "    return JSONResponse(\n"
                "        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,\n"
                '        content=AppResponse(success=False, data={"status": "degraded", "ready": False, "dependencies": {"database": "unhealthy"}}).model_dump(),\n'
                "    )\n\n\n"
                '@router.get("/health")\n'
                "async def health_check():\n"
                "    return await ready_check()\n"
            )
        return src

    def _settings_py(self) -> str:
        has_ai = self._has("llm") or self._has("langgraph")
        has_db = self._has("database")
        has_redis = self._has("redis")
        has_obs = self._has("observability")
        src = (
            '"""Application settings."""\n\n'
            "from pydantic_settings import BaseSettings\n"
            "from functools import lru_cache\n\n\n"
            "class Settings(BaseSettings):\n"
            '    PROJECT_NAME: str = "ALMS Backend"\n'
            '    SERVICE_NAME: str = "alms"\n'
            '    APP_VERSION: str = "0.1.0"\n'
            "    DEBUG: bool = True\n"
            '    SERVER_HOST: str = "0.0.0.0"\n'
            "    SERVER_PORT: int = 3000\n"
        )
        if has_ai:
            src += "    AI_ENABLED: bool = False\n"
        if has_db:
            src += "    DATABASE_ENABLED: bool = True\n"
        if has_redis:
            src += "    REDIS_ENABLED: bool = False\n"
        if has_ai:
            src += (
                '    OPENAI_API_KEY: str = ""\n'
                '    OPENAI_MODEL_BASIC: str = "gpt-4o-mini"\n'
                '    OPENAI_MODEL_REASONING: str = "gpt-4o"\n'
            )
        if has_db:
            src += (
                "    DATABASE_URL: str | None = None\n"
                '    DATABASE_HOST: str = "localhost"\n'
                "    DATABASE_PORT: int = 5432\n"
                '    DATABASE_NAME: str = "db"\n'
                '    DATABASE_USER: str = "postgres"\n'
                '    DATABASE_PASSWORD: str = "postgres"\n'
            )
        if has_redis:
            src += (
                '    REDIS_HOST: str = "localhost"\n'
                "    REDIS_PORT: int = 6379\n"
            )
        if has_obs:
            src += (
                "    METRICS_ENABLED: bool = True\n"
                "    TRACING_ENABLED: bool = True\n"
                "    OTLP_ENDPOINT: str | None = None\n"
            )
        src += (
            '    LOG_LEVEL: str = "info"\n'
            '    SECRET_KEY: str = "your-default-secret-key"\n'
            '    ALLOWED_HOSTS: list[str] = ["*"]\n'
            "    X_API_KEY: str | None = None\n"
            '    API_PREFIX: str = "/api"\n\n'
            "    class Config:\n"
            '        env_file = ".env"\n'
            "        case_sensitive = True\n\n\n"
            "@lru_cache()\n"
            "def get_settings() -> Settings:\n"
            "    return Settings()\n\n\n"
            "settings = get_settings()\n"
        )
        return src

    def _env_example(self) -> str:
        has_ai = self._has("llm") or self._has("langgraph")
        has_db = self._has("database")
        has_redis = self._has("redis")
        has_obs = self._has("observability")
        env = (
            "# Application\n"
            "DEBUG=true\n"
            "LOG_LEVEL=info\n"
            "SERVER_PORT=3000\n"
        )
        if has_ai:
            env += (
                "\n# OpenAI Configuration\n"
                "OPENAI_API_KEY=sk-...\n"
                "OPENAI_MODEL_BASIC=gpt-4o-mini\n"
                "OPENAI_MODEL_REASONING=gpt-4o\n"
            )
        if has_db:
            env += (
                "\n# Database Configuration (PostgreSQL)\n"
                "DATABASE_URL=\n"
                "DATABASE_HOST=localhost\n"
                "DATABASE_PORT=5432\n"
                "DATABASE_NAME=db\n"
                "DATABASE_USER=postgres\n"
                "DATABASE_PASSWORD=postgres\n"
            )
        if has_redis:
            env += (
                "\n# Redis Configuration\n"
                "REDIS_HOST=localhost\n"
                "REDIS_PORT=6379\n"
                "REDIS_PASSWORD=\n"
                "REDIS_DB=0\n"
            )
        if has_obs:
            env += (
                "\n# Observability\n"
                "METRICS_ENABLED=true\n"
                "TRACING_ENABLED=true\n"
                "OTLP_ENDPOINT=http://localhost:4317\n"
            )
        return env.rstrip() + "\n"

    def _dependencies_py(self) -> str:
        has_db = self._has("database")
        has_llm = self._has("llm") or self._has("langgraph")
        src = '"""Dependencies for v1 endpoints."""\n\nfrom fastapi import Depends\n'
        if has_db or has_llm:
            src += "from src.core.exceptions import AppException\n"
        src += "\n"
        if has_db:
            src += (
                'try:\n    from src.database.connection import get_db\n'
                '    _db_available = True\nexcept ImportError:\n    _db_available = False\n    get_db = None  # type: ignore\n\n\n'
                'def get_db_session():\n    if not _db_available:\n'
                '        raise AppException(message="Database deps not installed.", status_code=503, error_code="DB_UNAVAILABLE")\n'
                '    return get_db()\n'
            )
        else:
            src += 'def get_db_session():\n    """Get database session."""\n    pass\n'
        if has_llm:
            src += (
                '\n\n'
                'try:\n'
                '    from src.agents.agent_manager.agent import create_sample_agent\n'
                '    _ai_available = True\nexcept ImportError:\n'
                '    _ai_available = False\n\n\n'
                'def get_sample_agent():\n'
                '    if not _ai_available:\n'
                '        raise AppException(message="AI deps not installed.", status_code=503, error_code="AGENT_UNAVAILABLE")\n'
                '    return create_sample_agent()\n\n\n'
                'def get_sample_action(agent=Depends(get_sample_agent)):\n'
                '    from src.execution.actions.sample_action import SampleAction\n'
                '    return SampleAction(agent=agent)\n\n\n'
                'def get_sample_usecase(action=Depends(get_sample_action)):\n'
                '    from src.execution.usecases.sample_usecase import SampleUseCase\n'
                '    return SampleUseCase(action=action)\n'
            )
        return src

    def _conftest_py(self) -> str:
        has_db = self._has("database")
        src = (
            '"""Pytest configuration and fixtures."""\n\n'
            "import pytest\n"
            "from httpx import AsyncClient\n"
            "from src.api.main import app\n"
        )
        if has_db:
            src += (
                "try:\n"
                "    from src.database.connection import get_db\n"
                "except ImportError:\n"
                "    get_db = None  # type: ignore\n"
            )
        src += (
            "\n\n"
            "@pytest.fixture\n"
            "async def client():\n"
            '    """Create test client."""\n'
            '    async with AsyncClient(app=app, base_url="http://test") as client:\n'
            "        yield client\n"
        )
        if has_db:
            src += (
                "\n\n"
                "@pytest.fixture\n"
                "def mock_session():\n"
                "    from unittest.mock import AsyncMock\n"
                "    session = AsyncMock()\n"
                "    session.execute = AsyncMock()\n"
                "    session.commit = AsyncMock()\n"
                "    session.rollback = AsyncMock()\n"
                "    return session\n"
            )
        return src

    # ========================================================================
    # Static template generators (config files)
    # ========================================================================

    def _readme(self) -> str:
        return f"""# {self.project_name}

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
"""

    def _gitignore(self) -> str:
        return """# Byte-compiled / optimized / DLL files
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
"""

    def _pytest_ini(self) -> str:
        return """[pytest]
testpaths = src/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
"""

    def _project_rules(self) -> str:
        return """# Project Rules

## ALMS Architecture Guidelines

1. Never skip layers: API -> Execution -> Agent -> Infrastructure
2. Use repository pattern for database access
3. Use custom exceptions, not raw HTTPException
4. Add type hints to all functions
5. Write tests for all use cases and actions
"""

    def _alembic_ini(self) -> str:
        return """[alembic]
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
"""

    def _docker_compose(self) -> str:
        has_db = self._has("database")
        has_redis = self._has("redis")
        services = ""
        if has_db:
            services += """
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
"""
        if has_redis:
            services += """
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
"""
        volumes = ""
        if has_db:
            volumes += "\n  postgres_data:"
        if has_redis:
            volumes += "\n  redis_data:"
        return f"version: '3.8'\n\nservices:{services}\nvolumes:{volumes}\n"

    def _dockerfile(self) -> str:
        extras = resolve_extras(self.capabilities)
        extra_flag = ""
        if extras:
            extra_flag = " " + " ".join(f"--extra {e}" for e in extras)
        return f"""FROM python:3.13-slim

WORKDIR /app

RUN pip install uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev{extra_flag}

COPY . .

EXPOSE 3000

CMD ["uv", "run", "-m", "src.api.main", "--host", "0.0.0.0"]
"""

    def _ci_workflow(self) -> str:
        extras = resolve_extras(self.capabilities)
        extra_flag = ""
        if extras:
            extra_flag = " " + " ".join(f"--extra {e}" for e in extras)
        return f"""name: CI

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
      - run: uv sync{extra_flag}
      - run: uv run pytest src/tests
      - run: uv run ruff check src/
"""

    def _dependabot(self) -> str:
        return """version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
"""

    def _bug_template(self) -> str:
        return """name: Bug Report
description: Create a report to help us improve
body:
  - type: textarea
    attributes:
      label: Describe the bug
    validations:
      required: true
"""

    def _feature_template(self) -> str:
        return """name: Feature Request
description: Suggest an idea for this project
body:
  - type: textarea
    attributes:
      label: Describe the feature
    validations:
      required: true
"""

    def _pr_template(self) -> str:
        return """## Description

Please include a summary of the changes.

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
"""

    def _alembic_env(self) -> str:
        return """from logging.config import fileConfig
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
"""

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

    # ========================================================================
    # Static template generators (source files)
    # ========================================================================

    def _schema_base_py(self) -> str:
        return """\"\"\"Base response schemas.\"\"\"

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
"""

    def _schema_sample_py(self) -> str:
        return """\"\"\"Sample request/response schemas.\"\"\"

from pydantic import BaseModel


class SampleRequest(BaseModel):
    query: str


class SampleResponse(BaseModel):
    message: str
    result: str
"""

    def _error_handler_py(self) -> str:
        return """\"\"\"Error handler middleware.\"\"\"

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.core.exceptions import AppException
from src.api.endpoints.v1.schemas.base import AppResponse, ErrorDetail


def setup_error_handler(app: FastAPI):
    \"\"\"Setup global error handlers.\"\"\"

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
"""

    def _logging_middleware_py(self) -> str:
        return """\"\"\"Request logging middleware.\"\"\"

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
    \"\"\"Setup logging middleware.\"\"\"
    app.add_middleware(LoggingMiddleware)
"""

    def _security_middleware_py(self) -> str:
        return """\"\"\"Security headers middleware.\"\"\"

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
    \"\"\"Setup security middleware.\"\"\"
    app.add_middleware(SecurityMiddleware)
"""

    def _observability_middleware_py(self) -> str:
        return """\"\"\"Observability middleware for metrics and tracing.\"\"\"

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
    \"\"\"Setup observability middleware.\"\"\"
    app.add_middleware(ObservabilityMiddleware)
"""

    def _router_py(self) -> str:
        return """\"\"\"Router aggregation.\"\"\"

from fastapi import FastAPI
from src.api.endpoints.v1.routers import v1_router


def include_routers(app: FastAPI):
    \"\"\"Include all routers in the application.\"\"\"
    app.include_router(v1_router)
"""

    def _sample_action_py(self) -> str:
        return """\"\"\"Sample action.\"\"\"

from typing import Any


class SampleAction:
    \"\"\"Sample action that performs a discrete operation.\"\"\"

    async def execute(self, query: str) -> dict[str, Any]:
        \"\"\"Execute the action.\"\"\"
        return {"message": f"Processed: {query}", "status": "success"}
"""

    def _sample_usecase_py(self) -> str:
        return """\"\"\"Sample usecase.\"\"\"

from typing import Any
from src.execution.actions.sample_action import SampleAction


class SampleUsecase:
    \"\"\"Sample usecase that orchestrates business flow.\"\"\"

    def __init__(self):
        self.action = SampleAction()

    async def execute(self, query: str) -> dict[str, Any]:
        \"\"\"Execute the usecase.\"\"\"
        result = await self.action.execute(query)
        return {"usecase_result": result}
"""

    def _sample_agent_py(self) -> str:
        return """\"\"\"Sample agent endpoint.\"\"\"

from fastapi import APIRouter
from src.api.endpoints.v1.schemas.base import AppResponse
from src.execution.usecases.sample_usecase import SampleUsecase

router = APIRouter()


@router.post("/agent/sample")
async def sample_agent(query: str):
    \"\"\"Sample agent endpoint.\"\"\"
    usecase = SampleUsecase()
    result = await usecase.execute(query)
    return AppResponse(success=True, data=result)
"""

    def _sample_di_py(self) -> str:
        return """\"\"\"Sample dependency injection endpoint.\"\"\"

from fastapi import APIRouter, Depends
from src.api.endpoints.v1.schemas.base import AppResponse
from src.api.endpoints.v1.dependencies import get_db_session

router = APIRouter()


@router.get("/di/sample")
async def sample_di(session=Depends(get_db_session)):
    \"\"\"Sample DI endpoint.\"\"\"
    return AppResponse(success=True, data={"message": "DI working"})
"""

    def _agent_py(self) -> str:
        return """\"\"\"Agent definitions.\"\"\"

from langchain_openai import ChatOpenAI
from src.config.settings import settings


class SampleAgent:
    \"\"\"Sample AI agent.\"\"\"

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.OPENAI_MODEL_BASIC,
            api_key=settings.OPENAI_API_KEY,
        )

    async def process(self, query: str) -> str:
        \"\"\"Process a query using the agent.\"\"\"
        response = await self.llm.ainvoke(query)
        return response.content
"""

    def _sample_prompt_py(self) -> str:
        return """\"\"\"Sample agent prompt template.\"\"\"

SAMPLE_AGENT_PROMPT = \"\"\"You are a helpful AI assistant.

Query: {query}

Please provide a helpful response.\"\"\"
"""

    def _model_loader_py(self) -> str:
        return """\"\"\"AI model loader provider.\"\"\"

from langchain_openai import ChatOpenAI
from src.config.settings import settings


def get_llm(model: str = "basic") -> ChatOpenAI:
    \"\"\"Get LLM instance.\"\"\"
    model_name = (
        settings.OPENAI_MODEL_REASONING
        if model == "reasoning"
        else settings.OPENAI_MODEL_BASIC
    )

    return ChatOpenAI(
        model=model_name,
        api_key=settings.OPENAI_API_KEY,
    )
"""

    def _observability_init_py(self) -> str:
        return """\"\"\"Observability module.\"\"\"

from src.observability.metrics import metrics
from src.observability.tracing import tracer

__all__ = ["metrics", "tracer"]
"""

    def _metrics_module_py(self) -> str:
        return """\"\"\"Prometheus metrics.\"\"\"

from prometheus_client import Counter, Histogram, generate_latest


metrics_counter = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])


class MetricsCollector:
    \"\"\"Collect and expose metrics.\"\"\"

    def counter(self, name: str, labels: dict[str, str]):
        \"\"\"Increment a counter metric.\"\"\"
        pass

    def generate(self) -> bytes:
        \"\"\"Generate metrics data.\"\"\"
        return generate_latest()


metrics = MetricsCollector()


def generate_metrics() -> bytes:
    \"\"\"Generate Prometheus metrics.\"\"\"
    return generate_latest()
"""

    def _tracing_py(self) -> str:
        return """\"\"\"OpenTelemetry tracing.\"\"\"

from contextlib import contextmanager


class Tracer:
    \"\"\"Simple tracer for distributed tracing.\"\"\"

    @contextmanager
    def start_as_current_span(self, name: str):
        \"\"\"Start a new span.\"\"\"
        yield


tracer = Tracer()
"""

    def _db_connection_py(self) -> str:
        return """\"\"\"Database connection setup.\"\"\"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings


engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)

async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncSession:
    \"\"\"Get database session.\"\"\"
    async with async_session() as session:
        yield session
"""

    def _metrics_py(self) -> str:
        return """\"\"\"Prometheus metrics endpoint.\"\"\"

from fastapi import APIRouter, Response
from src.observability.metrics import generate_metrics

router = APIRouter()


@router.get("/metrics")
async def metrics():
    \"\"\"Expose Prometheus metrics.\"\"\"
    metrics_data = generate_metrics()
    return Response(content=metrics_data, media_type="text/plain")
"""

    def _repository_base_py(self) -> str:
        return """\"\"\"Base repository pattern.\"\"\"

from typing import Generic, TypeVar, Type, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    \"\"\"Base repository with common CRUD operations.\"\"\"

    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, session: AsyncSession, id: int) -> Optional[ModelType]:
        \"\"\"Get by ID.\"\"\"
        result = await session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_multi(
        self, session: AsyncSession, skip: int = 0, limit: int = 100
    ) -> Sequence[ModelType]:
        \"\"\"Get multiple records.\"\"\"
        result = await session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        return result.scalars().all()
"""

    def _sqlalchemy_repo_py(self) -> str:
        return """\"\"\"SQLAlchemy repository implementation.\"\"\"

from src.database.repositories.base import BaseRepository


class SQLAlchemyRepository(BaseRepository):
    \"\"\"SQLAlchemy specific repository implementation.\"\"\"
    pass
"""

    def _exceptions_py(self) -> str:
        return """\"\"\"Custom exceptions.\"\"\"

from typing import Optional


class AppException(Exception):
    \"\"\"Base application exception.\"\"\"

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
    \"\"\"Resource not found.\"\"\"

    def __init__(self, message: str, error_code: str = "NOT_FOUND", details: Optional[dict] = None):
        super().__init__(message, error_code, 404, details)


class ValidationException(AppException):
    \"\"\"Validation error.\"\"\"

    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", details: Optional[dict] = None):
        super().__init__(message, error_code, 422, details)
"""

    def _logs_config_py(self) -> str:
        return """\"\"\"Logging configuration.\"\"\"

import logging
import sys
from src.config.settings import settings


def setup_logging():
    \"\"\"Configure application logging.\"\"\"
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
"""

    def _test_health_py(self) -> str:
        return """\"\"\"Health endpoint tests.\"\"\"

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    \"\"\"Test health check endpoint.\"\"\"
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
"""

    def _test_agent_py(self) -> str:
        return """\"\"\"Agent endpoint tests.\"\"\"

import pytest


@pytest.mark.asyncio
async def test_sample_agent(client):
    \"\"\"Test sample agent endpoint.\"\"\"
    response = await client.post("/api/v1/agent/sample", json={"query": "test"})
    assert response.status_code == 200
"""

    def _test_metrics_py(self) -> str:
        return '"""Metrics tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_metrics_collection():\n    """Test metrics collection."""\n    pass\n'

    def _test_metrics_endpoint_py(self) -> str:
        return '"""Metrics endpoint tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_metrics_endpoint(client):\n    """Test metrics endpoint."""\n    response = await client.get("/api/v1/metrics")\n    assert response.status_code == 200\n'

    def _test_observability_middleware_py(self) -> str:
        return '"""Observability middleware tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_observability_middleware(client):\n    """Test observability middleware."""\n    response = await client.get("/api/v1/health")\n    assert response.status_code == 200\n'

    def _test_sqlalchemy_repository_py(self) -> str:
        return '"""SQLAlchemy repository tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_repository_base():\n    """Test base repository."""\n    pass\n'

    def _test_tracing_py(self) -> str:
        return '"""Tracing tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_tracing():\n    """Test tracing setup."""\n    pass\n'

    def _test_full_stack_py(self) -> str:
        return '"""Full stack integration tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_full_stack(client):\n    """Test full stack integration."""\n    response = await client.get("/api/v1/health")\n    assert response.status_code == 200\n'

    def _test_workflows_py(self) -> str:
        return '"""End-to-end workflow tests."""\n\nimport pytest\n\n\n@pytest.mark.asyncio\nasync def test_workflow(client):\n    """Test complete workflow."""\n    pass\n'


# ---------------------------------------------------------------------------
# Module-level helper
# ---------------------------------------------------------------------------

def _extra_block(extra_name: str) -> str:
    specs = _EXTRA_DEPS.get(extra_name, [])
    if not specs:
        return ""
    block = f"{extra_name} = [\n"
    for spec in specs:
        block += f'    "{spec}",\n'
    block += "]\n"
    return block