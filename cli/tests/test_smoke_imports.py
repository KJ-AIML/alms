"""Smoke tests: generate projects and verify they import successfully.

These tests generate a project into a temp directory, then run
`python -c "import src.api.main"` in a subprocess to verify the
generated code has no import errors or missing symbols.

Profiles that require optional dependencies (prometheus_client, sqlalchemy,
langchain) are skipped if those deps are not installed in the current
environment.
"""

import os
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

import pytest

from alms_cli.templates import TemplateGenerator, resolve_capabilities


def _generate_and_import(profile: str, extra_deps: list[str] | None = None) -> str:
    """Generate a project for the given profile and verify import succeeds.

    Returns the temp directory path (for cleanup).
    Raises pytest.skip if required deps are not installed.
    """
    # Check if required optional deps are available
    if extra_deps:
        for dep in extra_deps:
            try:
                __import__(dep)
            except ImportError:
                pytest.skip(
                    f"Optional dependency '{dep}' not installed, skipping {profile} profile"
                )

    tmp = Path(tempfile.mkdtemp(prefix=f"alms_smoke_{profile}_"))
    try:
        caps = resolve_capabilities(profile=profile)
        gen = TemplateGenerator("smoketest", tmp)
        gen.generate(caps)

        # Run import in a subprocess to get a clean module state
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import src.api.main; print('import ok')",
            ],
            capture_output=True,
            text=True,
            cwd=str(tmp),
            env={**os.environ, "PYTHONPATH": str(tmp)},
        )

        if result.returncode != 0:
            pytest.fail(
                f"Profile '{profile}' failed to import:\n"
                f"stdout: {result.stdout}\n"
                f"stderr: {result.stderr}"
            )

        assert "import ok" in result.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    return str(tmp)


class TestCoreApiImport:
    """core-api profile should import with only base dependencies."""

    def test_core_api_imports(self):
        _generate_and_import("core-api")


class TestLlmAgentImport:
    """llm-agent profile should import with base deps (langchain behind try/except)."""

    def test_llm_agent_imports(self):
        _generate_and_import("llm-agent")


class TestObservableImport:
    """observable profile requires prometheus_client."""

    def test_observable_imports(self):
        _generate_and_import("observable", extra_deps=["prometheus_client"])


class TestFullImport:
    """full profile requires prometheus_client and sqlalchemy."""

    def test_full_imports(self):
        _generate_and_import("full", extra_deps=["prometheus_client", "sqlalchemy"])


class TestDbAgentImport:
    """db-agent profile requires sqlalchemy."""

    def test_db_agent_imports(self):
        _generate_and_import("db-agent", extra_deps=["sqlalchemy"])


class TestGeneratedCodeConsistency:
    """Verify generated code has consistent cross-file references."""

    def test_sample_usecase_class_name_matches_import(self):
        """Generated SampleUseCase class name must match import in sample_agent."""
        tmp = Path(tempfile.mkdtemp(prefix="alms_consistency_"))
        try:
            caps = resolve_capabilities(profile="llm-agent")
            gen = TemplateGenerator("smoketest", tmp)
            gen.generate(caps)

            # Read the generated usecase file
            usecase_content = (
                tmp / "src" / "execution" / "usecases" / "sample_usecase.py"
            ).read_text()
            # Read the generated agent file
            agent_content = (
                tmp / "src" / "api" / "endpoints" / "v1" / "sample_agent.py"
            ).read_text()

            # The class defined in usecase must match what DI provides
            assert "class SampleUseCase:" in usecase_content, (
                "Generated usecase should define 'class SampleUseCase:'"
            )
            assert (
                "from src.api.endpoints.v1.dependencies import get_sample_usecase"
                in agent_content
            ), "Generated agent should use DI via 'get_sample_usecase'"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_appresponse_is_generic(self):
        """Generated AppResponse must be Generic to support AppResponse[dict] in health."""
        tmp = Path(tempfile.mkdtemp(prefix="alms_consistency_"))
        try:
            caps = resolve_capabilities(profile="core-api")
            gen = TemplateGenerator("smoketest", tmp)
            gen.generate(caps)

            schema_content = (
                tmp / "src" / "api" / "endpoints" / "v1" / "schemas" / "base.py"
            ).read_text()
            health_content = (
                tmp / "src" / "api" / "endpoints" / "v1" / "health.py"
            ).read_text()

            assert "Generic[T]" in schema_content, "AppResponse must be Generic[T]"
            assert "AppResponse[dict]" in health_content, (
                "Health endpoint uses AppResponse[dict]"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_settings_has_validate_method(self):
        """Generated Settings must have validate_production_settings method."""
        tmp = Path(tempfile.mkdtemp(prefix="alms_consistency_"))
        try:
            caps = resolve_capabilities(profile="core-api")
            gen = TemplateGenerator("smoketest", tmp)
            gen.generate(caps)

            settings_content = (tmp / "src" / "config" / "settings.py").read_text()
            assert "def validate_production_settings" in settings_content, (
                "Settings must have validate_production_settings method"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
