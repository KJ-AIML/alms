"""Project template generator -- capability-aware edition."""

from pathlib import Path

from .profiles import (
    ALL_CAPABILITIES,
    CAPABILITY_TO_EXTRA,
    EXTRA_DEPS,
    FEATURE_LABEL_TO_CAPABILITY,
    NO_EXTRA_CAPABILITIES,
    PROFILE_CAPABILITIES,
    resolve_capabilities,
    resolve_extras,
    resolve_profile,
)

BASE_DIRS = [
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

CAPABILITY_DIRS = {
    "llm": [
        "src/agents/agent_manager",
        "src/agents/prompts",
        "src/agents/tools",
        "src/providers/ai",
    ],
    "langgraph": ["src/agents/workflows"],
    "database": ["src/database/migrations", "src/database/repositories", "alembic"],
    "redis": ["src/providers/cache"],
    "ci": [".github/workflows", ".github/ISSUE_TEMPLATE"],
}

BASE_CONFIG_TEMPLATES = [
    "pyproject.toml",
    "README.md",
    ".env.example",
    ".gitignore",
    "rules/project_rules.md",
    "docs/01-System-Design.md",
    "docs/02-Design-Patterns.md",
    "docs/03-Database-Design.md",
    "docs/04-Tech-Stack.md",
    "docs/05-Project-Structure.md",
    "docs/06-API-Documentation.md",
    "docs/07-Setup-Installation.md",
    "docs/08-Contribution-Guide.md",
]

DATABASE_CONFIG_TEMPLATES = [
    "alembic.ini",
    "alembic/README",
    "alembic/env.py",
    "alembic/script.py.mako",
]

DOCKER_TEMPLATES = ["docker-compose.yml", "Dockerfile"]

CI_TEMPLATES = [
    ".github/workflows/ci.yml",
    ".github/dependabot.yml",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/pull_request_template.md",
]

BASE_SOURCE_TEMPLATES = [
    "src/api/main.py",
    "src/api/endpoints/v1/dependencies.py",
    "src/api/endpoints/v1/health.py",
    "src/api/endpoints/v1/routers.py",
    "src/api/endpoints/v1/schemas/base.py",
    "src/api/middlewares/error_handler.py",
    "src/api/middlewares/logging.py",
    "src/api/middlewares/security.py",
    "src/api/router/routers.py",
    "src/core/exceptions.py",
    "src/config/settings.py",
    "src/config/logs_config.py",
    "src/tests/conftest.py",
    "src/tests/README.md",
    "src/tests/v1/test_health.py",
    "src/tests/integration/test_full_stack.py",
    "src/tests/e2e/test_workflows.py",
]

LLM_TEMPLATES = [
    "src/agents/agent_manager/agent.py",
    "src/agents/prompts/sample_agent_prompt.py",
    "src/providers/ai/base.py",
    "src/providers/ai/factory.py",
    "src/providers/ai/langchain_model_loader.py",
    "src/execution/actions/sample_action.py",
    "src/execution/usecases/sample_usecase.py",
    "src/api/endpoints/v1/schemas/sample.py",
    "src/api/endpoints/v1/sample_agent.py",
    "src/api/endpoints/v1/sample_di.py",
    "src/tests/v1/test_agent.py",
]

DATABASE_SOURCE_TEMPLATES = [
    "src/database/connection.py",
    "src/database/repositories/base.py",
    "src/database/repositories/sqlalchemy_repository.py",
    "src/tests/v1/test_sqlalchemy_repository.py",
]

OBSERVABILITY_TEMPLATES = [
    "src/observability/__init__.py",
    "src/observability/metrics.py",
    "src/observability/tracing.py",
    "src/api/middlewares/observability.py",
    "src/api/endpoints/v1/metrics.py",
    "src/tests/v1/test_metrics.py",
    "src/tests/v1/test_metrics_endpoint.py",
    "src/tests/v1/test_observability_middleware.py",
    "src/tests/v1/test_tracing.py",
]

EMPTY_FILES = [
    "src/__init__.py",
    "src/api/__init__.py",
    "src/api/endpoints/__init__.py",
    "src/api/endpoints/v1/__init__.py",
    "src/api/endpoints/v1/schemas/__init__.py",
    "src/api/middlewares/__init__.py",
    "src/api/router/__init__.py",
    "src/execution/__init__.py",
    "src/execution/actions/__init__.py",
    "src/execution/usecases/__init__.py",
    "src/core/__init__.py",
    "src/config/__init__.py",
    "src/models/.gitkeep",
    "src/utils/.gitkeep",
    "src/scripts/.gitkeep",
    "src/docs/.gitkeep",
    "src/evaluation/.gitkeep",
    "src/data/.gitkeep",
    "src/tests/__init__.py",
    "src/tests/v1/__init__.py",
    "src/tests/integration/__init__.py",
    "src/tests/e2e/__init__.py",
]

LLM_EMPTY_FILES = [
    "src/agents/__init__.py",
    "src/agents/agent_manager/__init__.py",
    "src/agents/prompts/__init__.py",
    "src/providers/__init__.py",
    "src/providers/ai/__init__.py",
]
LANGGRAPH_EMPTY_FILES = ["src/agents/tools/.gitkeep", "src/agents/workflows/.gitkeep"]
DATABASE_EMPTY_FILES = [
    "src/database/__init__.py",
    "src/database/migrations/.gitkeep",
    "src/database/repositories/__init__.py",
]
REDIS_EMPTY_FILES = ["src/providers/cache/.gitkeep"]


class TemplateGenerator:
    """Generate ALMS project structure from profiles and capabilities."""

    def __init__(
        self,
        project_name: str,
        project_path: Path,
        renderer=None,
    ):
        self.project_name = project_name
        self.project_path = project_path
        self.capabilities: set[str] = set()
        self.renderer = renderer or _default_renderer()

    def generate(self, capabilities: set[str] | None = None) -> int:
        """Generate project structure and return file count."""
        self.capabilities = capabilities or {"runtime_auth", "tests"}
        self._create_base_structure()
        self._write_empty_files(self._empty_files())
        self._write_templates(self._template_files())
        return self._count_files()

    def _has(self, capability: str) -> bool:
        return capability in self.capabilities

    def _count_files(self) -> int:
        return sum(
            1
            for path in self.project_path.rglob("*")
            if path.is_file() and not path.name.startswith(".")
        )

    def _create_base_structure(self) -> None:
        dirs = list(BASE_DIRS)
        for capability, capability_dirs in CAPABILITY_DIRS.items():
            if self._has(capability):
                dirs.extend(capability_dirs)
        for dir_path in dirs:
            (self.project_path / dir_path).mkdir(parents=True, exist_ok=True)

    def _template_files(self) -> list[str]:
        templates = list(BASE_CONFIG_TEMPLATES) + list(BASE_SOURCE_TEMPLATES)
        if self._has("database"):
            templates.extend(DATABASE_CONFIG_TEMPLATES)
            templates.extend(DATABASE_SOURCE_TEMPLATES)
        if self._has("docker"):
            templates.extend(DOCKER_TEMPLATES)
        if self._has("ci"):
            templates.extend(CI_TEMPLATES)
        if self._has("llm"):
            templates.extend(LLM_TEMPLATES)
        if self._has("observability"):
            templates.extend(OBSERVABILITY_TEMPLATES)
        return templates

    def _empty_files(self) -> list[str]:
        files = list(EMPTY_FILES)
        if self._has("llm"):
            files.extend(LLM_EMPTY_FILES)
        if self._has("langgraph"):
            files.extend(LANGGRAPH_EMPTY_FILES)
        if self._has("database"):
            files.extend(DATABASE_EMPTY_FILES)
        if self._has("redis"):
            files.extend(REDIS_EMPTY_FILES)
        return files

    def _write_templates(self, template_paths: list[str]) -> None:
        context = self.template_context()
        for output_path in template_paths:
            self.renderer.render_to_path(
                f"{output_path}.j2",
                self.project_path / output_path,
                context,
            )

    def _write_empty_files(self, file_paths: list[str]) -> None:
        for output_path in file_paths:
            destination = self.project_path / output_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text("", encoding="utf-8")

    def template_context(self) -> dict[str, object]:
        """Return the Jinja context for the active capability set."""
        extras = resolve_extras(self.capabilities)
        all_specs: list[str] = []
        for extra in extras:
            all_specs.extend(EXTRA_DEPS.get(extra, []))
        extra_flag = ""
        if extras:
            extra_flag = " " + " ".join(f"--extra {extra}" for extra in extras)
        # ponytail: profile-required deps go in base so `uv sync` / `pip install -e .` works
        core_deps = [
            "fastapi[standard]>=0.122.0",
            "pydantic>=2.12.5",
            "pydantic-settings>=2.12.0",
            "uvicorn>=0.38.0",
        ]
        all_deps = core_deps + sorted(set(all_specs))
        return {
            "project_name": self.project_name,
            "capabilities": sorted(self.capabilities),
            "capabilities_repr": repr(sorted(self.capabilities)),
            "profile": resolve_profile(self.capabilities),
            "extras": extras,
            "extra_blocks": "".join(_extra_block(extra) for extra in extras),
            "full_extra_specs": sorted(set(all_specs)),
            "extra_flag": extra_flag,
            "all_deps": all_deps,
            "has_ai": self._has("llm") or self._has("langgraph"),
            "has_llm": self._has("llm"),
            "has_langgraph": self._has("langgraph"),
            "has_db": self._has("database"),
            "has_redis": self._has("redis"),
            "has_obs": self._has("observability"),
            "has_scalar": self._has("scalar_docs"),
            "has_docker": self._has("docker"),
            "has_ci": self._has("ci"),
        }


def _default_renderer():
    renderer_module = __import__(
        "alms_cli.templates.template_renderer",
        fromlist=["TemplateRenderer"],
    )
    return renderer_module.TemplateRenderer()


def _extra_block(extra_name: str) -> str:
    specs = EXTRA_DEPS.get(extra_name, [])
    if not specs:
        return ""
    block = f"{extra_name} = [\n"
    for spec in specs:
        block += f'    "{spec}",\n'
    block += "]\n"
    return block


__all__ = [
    "ALL_CAPABILITIES",
    "CAPABILITY_TO_EXTRA",
    "FEATURE_LABEL_TO_CAPABILITY",
    "NO_EXTRA_CAPABILITIES",
    "PROFILE_CAPABILITIES",
    "TemplateGenerator",
    "resolve_capabilities",
    "resolve_extras",
]
