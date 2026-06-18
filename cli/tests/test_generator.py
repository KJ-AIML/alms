"""Tests for the ALMS CLI template generator."""

import tempfile
import shutil
from pathlib import Path

import pytest

from alms_cli.templates import (
    TemplateGenerator,
    PROFILE_CAPABILITIES,
    resolve_capabilities,
    resolve_extras,
)


@pytest.fixture
def tmp_project():
    """Create a temporary directory for a generated project."""
    tmp = Path(tempfile.mkdtemp(prefix="alms_test_"))
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


class TestResolveCapabilities:
    def test_core_api_defaults(self):
        caps = resolve_capabilities(profile="core-api")
        assert "runtime_auth" in caps
        assert "tests" in caps
        assert "llm" not in caps
        assert "langgraph" not in caps
        assert "database" not in caps
        assert "redis" not in caps
        assert "observability" not in caps
        assert "scalar_docs" not in caps

    def test_full_includes_everything(self):
        caps = resolve_capabilities(profile="full")
        assert "llm" in caps
        assert "langgraph" in caps
        assert "database" in caps
        assert "redis" in caps
        assert "observability" in caps
        assert "scalar_docs" in caps
        assert "docker" in caps
        assert "ci" in caps

    def test_llm_agent_has_ai_but_no_db(self):
        caps = resolve_capabilities(profile="llm-agent")
        assert "llm" in caps
        assert "langgraph" not in caps
        assert "database" not in caps

    def test_workflow_agent_has_langgraph(self):
        caps = resolve_capabilities(profile="workflow-agent")
        assert "llm" in caps
        assert "langgraph" in caps

    def test_db_agent_has_database_no_ai(self):
        caps = resolve_capabilities(profile="db-agent")
        assert "database" in caps
        assert "llm" not in caps

    def test_unknown_profile_falls_back_to_empty(self):
        caps = resolve_capabilities(profile="nonexistent")
        # runtime_auth and tests are always added
        assert "runtime_auth" in caps
        assert "tests" in caps

    def test_features_merge_with_profile(self):
        caps = resolve_capabilities(profile="core-api", features=["Database (PostgreSQL)"])
        assert "database" in caps
        assert "runtime_auth" in caps


class TestResolveExtras:
    def test_core_api_no_extras(self):
        caps = resolve_capabilities(profile="core-api")
        extras = resolve_extras(caps)
        assert extras == []

    def test_full_has_all_extras(self):
        caps = resolve_capabilities(profile="full")
        extras = resolve_extras(caps)
        assert "ai" in extras
        assert "workflow" in extras
        assert "db" in extras
        assert "cache" in extras
        assert "observability" in extras
        assert "docs" in extras

    def test_llm_agent_has_ai_and_docs(self):
        caps = resolve_capabilities(profile="llm-agent")
        extras = resolve_extras(caps)
        assert "ai" in extras
        assert "docs" in extras
        assert "db" not in extras


class TestProfileMapping:
    def test_all_profiles_have_valid_capabilities(self):
        for profile, caps in PROFILE_CAPABILITIES.items():
            for cap in caps:
                from alms_cli.templates import ALL_CAPABILITIES
                assert cap in ALL_CAPABILITIES, f"Profile {profile} has unknown capability: {cap}"

    def test_all_profiles_include_runtime_auth_and_tests(self):
        for profile, caps in PROFILE_CAPABILITIES.items():
            assert "runtime_auth" in caps, f"{profile} missing runtime_auth"
            assert "tests" in caps, f"{profile} missing tests"


class TestGenerateCoreApi:
    def test_pyproject_has_no_optional_deps(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "pyproject.toml").read_text()
        assert "langchain" not in content
        assert "langgraph" not in content
        assert "sqlalchemy" not in content
        assert "redis" not in content
        assert "opentelemetry" not in content
        assert "prometheus" not in content
        assert "scalar-fastapi" not in content
        # ruff should be in dev deps
        assert "ruff" in content

    def test_tool_alms_metadata_exists(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "pyproject.toml").read_text()
        assert "[tool.alms]" in content
        assert 'profile = "core-api"' in content
        assert "capabilities" in content

    def test_routers_no_sample_agent_or_metrics(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/api/endpoints/v1/routers.py").read_text()
        assert "sample_agent" not in content
        assert "metrics" not in content
        assert "health" in content

    def test_health_no_database_import(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/api/endpoints/v1/health.py").read_text()
        assert "database" not in content

    def test_no_agents_folder(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert not (tmp_project / "src/agents").exists()
        assert not (tmp_project / "src/providers/ai").exists()

    def test_no_observability_folder(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert not (tmp_project / "src/observability").exists()

    def test_no_database_folder(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert not (tmp_project / "src/database").exists()

    def test_settings_no_ai_or_db_fields(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/config/settings.py").read_text()
        assert "OPENAI_API_KEY" not in content
        assert "DATABASE_URL" not in content
        assert "REDIS_HOST" not in content
        assert "OTLP_ENDPOINT" not in content

    def test_env_example_minimal(self, tmp_project):
        caps = resolve_capabilities(profile="core-api")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / ".env.example").read_text()
        assert "DEBUG=true" in content
        assert "OPENAI" not in content
        assert "DATABASE" not in content


class TestGenerateFull:
    def test_pyproject_has_all_optional_deps(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "pyproject.toml").read_text()
        assert "langchain" in content
        assert "langgraph" in content
        assert "sqlalchemy" in content
        assert "redis" in content
        assert "opentelemetry" in content
        assert "prometheus" in content
        assert "scalar-fastapi" in content
        # optional-dependencies section exists
        assert "[project.optional-dependencies]" in content
        # full extra exists
        assert "full = [" in content

    def test_routers_has_everything(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/api/endpoints/v1/routers.py").read_text()
        assert "sample_agent" in content
        assert "sample_di" in content
        assert "metrics" in content
        assert "health" in content

    def test_health_has_db_import(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/api/endpoints/v1/health.py").read_text()
        assert "database" in content

    def test_agents_folder_exists(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert (tmp_project / "src/agents").exists()
        assert (tmp_project / "src/providers/ai").exists()

    def test_observability_folder_exists(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert (tmp_project / "src/observability").exists()

    def test_database_folder_exists(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert (tmp_project / "src/database").exists()

    def test_tool_alms_full_metadata(self, tmp_project):
        caps = resolve_capabilities(profile="full")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "pyproject.toml").read_text()
        assert 'profile = "full"' in content


class TestGenerateDbAgent:
    def test_has_database_no_ai(self, tmp_project):
        caps = resolve_capabilities(profile="db-agent")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert (tmp_project / "src/database").exists()
        assert not (tmp_project / "src/agents").exists()

        pyproject = (tmp_project / "pyproject.toml").read_text()
        assert "sqlalchemy" in pyproject
        assert "langchain" not in pyproject

    def test_health_imports_database(self, tmp_project):
        caps = resolve_capabilities(profile="db-agent")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        content = (tmp_project / "src/api/endpoints/v1/health.py").read_text()
        assert "database" in content


class TestGenerateObservable:
    def test_has_observability_no_ai(self, tmp_project):
        caps = resolve_capabilities(profile="observable")
        gen = TemplateGenerator("testproj", tmp_project)
        gen.generate(caps)

        assert (tmp_project / "src/observability").exists()
        assert not (tmp_project / "src/agents").exists()

        pyproject = (tmp_project / "pyproject.toml").read_text()
        assert "opentelemetry" in pyproject
        assert "langchain" not in pyproject