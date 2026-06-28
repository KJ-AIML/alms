"""Template-system validation tests."""

import os
from pathlib import Path
import py_compile
import shutil
import subprocess
import sys
import tempfile

import pytest

from alms_cli.templates import TemplateGenerator, resolve_capabilities

PROFILES = ["core-api", "llm-agent", "workflow-agent", "db-agent", "observable", "full"]
OPTIONAL_IMPORTS = {
    "db-agent": ["sqlalchemy"],
    "observable": ["prometheus_client"],
    "full": ["prometheus_client", "sqlalchemy"],
}
UNRESOLVED_MARKERS = ("{{", "<TODO_TEMPLATE_VAR>")


def _renderer():
    renderer_module = __import__(
        "alms_cli.templates.template_renderer",
        fromlist=["TemplateRenderer"],
    )
    return renderer_module.TemplateRenderer()


@pytest.fixture
def renderer():
    return _renderer()


@pytest.fixture
def render_context() -> dict[str, object]:
    tmp = Path(tempfile.mkdtemp(prefix="alms_template_context_"))
    try:
        generator = TemplateGenerator("smoketest", tmp)
        generator.capabilities = resolve_capabilities(profile="full")
        return generator.template_context()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _missing_optional_imports(profile: str) -> list[str]:
    missing = []
    for module_name in OPTIONAL_IMPORTS.get(profile, []):
        try:
            __import__(module_name)
        except ImportError:
            missing.append(module_name)
    return missing


def _generate_profile(profile: str) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix=f"alms_template_{profile}_"))
    generator = TemplateGenerator("smoketest", tmp)
    generator.generate(resolve_capabilities(profile=profile))
    return tmp


def test_all_template_files_load(renderer):
    names = renderer.template_names()
    assert names, "expected packaged template files"
    for template_name in names:
        renderer.environment.get_template(template_name)


def test_all_template_files_render(renderer, render_context: dict[str, object]):
    for template_name in renderer.template_names():
        rendered = renderer.render(template_name, render_context)
        assert isinstance(rendered, str)


@pytest.mark.parametrize("profile", PROFILES)
def test_all_profiles_generate_and_compile(profile: str):
    tmp = _generate_profile(profile)
    try:
        python_files = sorted((tmp / "src").rglob("*.py"))
        assert python_files, f"{profile} generated no Python files"
        for python_file in python_files:
            py_compile.compile(str(python_file), doraise=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("profile", PROFILES)
def test_generated_projects_import_main_and_have_health_route(profile: str):
    missing = _missing_optional_imports(profile)
    if missing:
        pytest.skip(
            f"optional imports not installed for {profile}: {', '.join(missing)}"
        )

    tmp = _generate_profile(profile)
    script = tmp / "_inspect_routes.py"
    script.write_text(
        "from src.api.main import app\n"
        "schema = app.openapi()\n"
        "routes = sorted(schema.get('paths', {}).keys())\n"
        "print('\\n'.join(routes))\n"
        "assert any('health' in route for route in routes)\n",
        encoding="utf-8",
    )
    try:
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tmp),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "health" in result.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("profile", PROFILES)
def test_generated_projects_have_exact_health_routes(profile: str):
    """Verify exact health route contract for all profiles."""
    missing = _missing_optional_imports(profile)
    if missing:
        pytest.skip(
            f"optional imports not installed for {profile}: {', '.join(missing)}"
        )

    tmp = _generate_profile(profile)
    script = tmp / "_check_health_routes.py"
    script.write_text(
        "from src.api.main import app\n"
        "schema = app.openapi()\n"
        "routes = sorted(schema.get('paths', {}).keys())\n"
        "assert '/api/v1/health/live' in routes, f'Missing /api/v1/health/live, got {routes}'\n"
        "assert '/api/v1/health/ready' in routes, f'Missing /api/v1/health/ready, got {routes}'\n"
        "assert '/api/v1/health' in routes, f'Missing /api/v1/health, got {routes}'\n"
        "assert '/api/v1/health/health' not in routes, f'Unexpected /api/v1/health/health, got {routes}'\n"
        "print('HEALTH_ROUTES_OK')\n",
        encoding="utf-8",
    )
    try:
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tmp),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Health route check failed for {profile}: {result.stderr}"
        )
        assert "HEALTH_ROUTES_OK" in result.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize(
    "profile,expected_routes,forbidden_routes",
    [
        (
            "core-api",
            ["/api/v1/health/live", "/api/v1/health/ready", "/api/v1/health"],
            ["/api/v1/health/health", "/api/v1/metrics", "/api/v1/agent"],
        ),
        (
            "llm-agent",
            [
                "/api/v1/health/live",
                "/api/v1/health/ready",
                "/api/v1/health",
                "/api/v1/agent/sample",
                "/api/v1/di/sample",
            ],
            ["/api/v1/health/health", "/api/v1/agent/agent", "/api/v1/di/di"],
        ),
        (
            "workflow-agent",
            [
                "/api/v1/health/live",
                "/api/v1/health/ready",
                "/api/v1/health",
                "/api/v1/agent/sample",
                "/api/v1/di/sample",
            ],
            ["/api/v1/health/health", "/api/v1/agent/agent", "/api/v1/di/di"],
        ),
        (
            "db-agent",
            ["/api/v1/health/live", "/api/v1/health/ready", "/api/v1/health"],
            ["/api/v1/health/health", "/api/v1/metrics", "/api/v1/agent"],
        ),
        (
            "observable",
            [
                "/api/v1/health/live",
                "/api/v1/health/ready",
                "/api/v1/health",
                "/api/v1/metrics",
            ],
            ["/api/v1/health/health", "/api/v1/metrics/metrics"],
        ),
        (
            "full",
            [
                "/api/v1/health/live",
                "/api/v1/health/ready",
                "/api/v1/health",
                "/api/v1/agent/sample",
                "/api/v1/di/sample",
                "/api/v1/metrics",
            ],
            [
                "/api/v1/health/health",
                "/api/v1/metrics/metrics",
                "/api/v1/agent/agent",
                "/api/v1/di/di",
            ],
        ),
    ],
)
def test_generated_projects_have_exact_route_contract(
    profile: str, expected_routes: list[str], forbidden_routes: list[str]
):
    """Verify exact route contract for all profiles, including no doubled-prefix bugs."""
    missing = _missing_optional_imports(profile)
    if missing:
        pytest.skip(
            f"optional imports not installed for {profile}: {', '.join(missing)}"
        )

    tmp = _generate_profile(profile)
    script = tmp / "_check_route_contract.py"
    expected_str = repr(expected_routes)
    forbidden_str = repr(forbidden_routes)
    script.write_text(
        f"from src.api.main import app\n"
        f"schema = app.openapi()\n"
        f"routes = sorted(schema.get('paths', {{}}).keys())\n"
        f"expected = {expected_str}\n"
        f"forbidden = {forbidden_str}\n"
        f"for route in expected:\n"
        f"    assert route in routes, f'Missing {{route}}, got {{routes}}'\n"
        f"for route in forbidden:\n"
        f"    assert route not in routes, f'Unexpected {{route}} (doubled prefix?), got {{routes}}'\n"
        f"print('ROUTE_CONTRACT_OK')\n",
        encoding="utf-8",
    )
    try:
        env = {**os.environ, "PYTHONPATH": str(tmp)}
        result = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(tmp),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Route contract check failed for {profile}: {result.stderr}"
        )
        assert "ROUTE_CONTRACT_OK" in result.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.parametrize("profile", PROFILES)
def test_generated_output_has_no_unresolved_template_markers(profile: str):
    tmp = _generate_profile(profile)
    try:
        for output_file in tmp.rglob("*"):
            if not output_file.is_file():
                continue
            text = output_file.read_text(encoding="utf-8")
            for marker in UNRESOLVED_MARKERS:
                assert marker not in text, f"{marker} left in {output_file}"
            if output_file.suffix != ".mako":
                assert "${" not in text, f"${{ left in {output_file}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_core_api_stable_markers():
    tmp = _generate_profile("core-api")
    try:
        expected_markers = {
            "src/api/main.py": [
                "FastAPI",
                "APP_NAME",
                "APP_DESCRIPTION",
                "ErrorHandlerMiddleware",
                "LoggingMiddleware",
                "APIKeyMiddleware",
                "SecurityHeadersMiddleware",
                "add_middleware",
            ],
            "src/config/settings.py": [
                "Settings",
                "APP_NAME",
                "APP_DESCRIPTION",
                "validate_production_settings",
                "API_PREFIX",
            ],
            "src/api/endpoints/v1/schemas/base.py": [
                "AppResponse",
                "Generic[T]",
                "request_id: Optional[str]",
            ],
            "src/api/endpoints/v1/health.py": ["health"],
            "src/api/router/routers.py": ["api_router", "v1_router"],
        }
        for relative_path, markers in expected_markers.items():
            content = (tmp / relative_path).read_text(encoding="utf-8")
            for marker in markers:
                assert marker in content, f"missing {marker} in {relative_path}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------------------
# v0.3.2 scaffold correctness regression tests
# ---------------------------------------------------------------------------


def test_scalar_docs_route_inside_create_app():
    """F-01: Scalar docs route must be registered inside create_app(), not after if __name__."""
    for profile in ("llm-agent", "full"):
        tmp = _generate_profile(profile)
        try:
            content = (tmp / "src" / "api" / "main.py").read_text(encoding="utf-8")
            # The scalar_html function must appear BEFORE the if __name__ guard
            scalar_pos = content.find("scalar_html")
            name_guard_pos = content.find("if __name__")
            assert scalar_pos > 0, f"{profile}: scalar_html not found in main.py"
            assert name_guard_pos > 0, f"{profile}: if __name__ not found in main.py"
            assert scalar_pos < name_guard_pos, (
                f"{profile}: scalar_html (pos {scalar_pos}) must be before "
                f"if __name__ (pos {name_guard_pos})"
            )
            # Also verify it's inside create_app (before 'return app')
            create_app_pos = content.find("def create_app")
            return_app_pos = content.rfind("return app")
            assert create_app_pos < scalar_pos < return_app_pos, (
                f"{profile}: scalar_html must be inside create_app()"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_cors_uses_settings_allowed_hosts():
    """F-04: CORS must use settings.ALLOWED_HOSTS, not hardcoded ['*']."""
    for profile in PROFILES:
        tmp = _generate_profile(profile)
        try:
            content = (tmp / "src" / "api" / "main.py").read_text(encoding="utf-8")
            assert "allow_origins=settings.ALLOWED_HOSTS" in content, (
                f"{profile}: CORS must use settings.ALLOWED_HOSTS"
            )
            hardcoded_wildcard = "allow_origins=[" + '"*"' + "]"
            assert hardcoded_wildcard not in content, (
                f"{profile}: CORS must not hardcode allow_origins with wildcard"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_model_provider_in_ai_capable_settings():
    """F-02: MODEL_PROVIDER must exist in AI-capable generated settings."""
    for profile in ("llm-agent", "workflow-agent", "full"):
        tmp = _generate_profile(profile)
        try:
            content = (tmp / "src" / "config" / "settings.py").read_text(
                encoding="utf-8"
            )
            assert "MODEL_PROVIDER" in content, (
                f"{profile}: MODEL_PROVIDER missing from generated settings"
            )
            assert 'MODEL_PROVIDER: str = "openai"' in content, (
                f"{profile}: MODEL_PROVIDER should default to 'openai'"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_model_provider_absent_in_non_ai_profiles():
    """F-02: MODEL_PROVIDER should not appear in non-AI profiles."""
    for profile in ("core-api", "db-agent", "observable"):
        tmp = _generate_profile(profile)
        try:
            content = (tmp / "src" / "config" / "settings.py").read_text(
                encoding="utf-8"
            )
            assert "MODEL_PROVIDER" not in content, (
                f"{profile}: MODEL_PROVIDER should not appear in non-AI settings"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_provider_class_name_aligned_with_reference():
    """F-03: Generated provider class must be LangchainModelLoader (matching reference)."""
    for profile in ("llm-agent", "workflow-agent", "full"):
        tmp = _generate_profile(profile)
        try:
            loader_content = (
                tmp / "src" / "providers" / "ai" / "langchain_model_loader.py"
            ).read_text(encoding="utf-8")
            factory_content = (
                tmp / "src" / "providers" / "ai" / "factory.py"
            ).read_text(encoding="utf-8")
            assert "class LangchainModelLoader" in loader_content, (
                f"{profile}: class must be LangchainModelLoader"
            )
            assert "LangChainModelProvider" not in loader_content, (
                f"{profile}: old name LangChainModelProvider should not appear"
            )
            assert "LangChainModelProvider" not in factory_content, (
                f"{profile}: old name LangChainModelProvider should not appear in factory"
            )
            # Factory must return abstract AIModelProvider, not concrete class
            assert "-> AIModelProvider" in factory_content, (
                f"{profile}: factory must return AIModelProvider (abstract)"
            )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
