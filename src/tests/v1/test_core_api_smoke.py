"""Smoke tests for core-api profile -- verifies the app starts without optional deps.

These tests do NOT require langchain, langgraph, sqlalchemy, redis,
opentelemetry, prometheus, or scalar-fastapi to be installed.
"""

import pytest

from src.config.settings import settings


class TestCoreApiImport:
    """App module must be importable without optional dependencies."""

    def test_main_imports_without_crashing(self):
        """src.api.main should import cleanly."""
        import src.api.main  # noqa: F401

    def test_create_app_returns_fastapi_instance(self):
        """create_app() must succeed with all optional flags disabled."""
        from fastapi import FastAPI
        from src.api.main import create_app

        orig_ai = settings.AI_ENABLED
        orig_db = settings.DATABASE_ENABLED
        orig_metrics = settings.METRICS_ENABLED
        orig_tracing = settings.TRACING_ENABLED

        try:
            settings.AI_ENABLED = False
            settings.DATABASE_ENABLED = False
            settings.METRICS_ENABLED = False
            settings.TRACING_ENABLED = False

            app = create_app()
            assert isinstance(app, FastAPI)
        finally:
            settings.AI_ENABLED = orig_ai
            settings.DATABASE_ENABLED = orig_db
            settings.METRICS_ENABLED = orig_metrics
            settings.TRACING_ENABLED = orig_tracing

    def test_app_instance_exists(self):
        """The module-level app instance must be a FastAPI app."""
        from fastapi import FastAPI
        from src.api.main import app
        assert isinstance(app, FastAPI)


class TestHealthEndpoints:
    """Health endpoints must work with all optional flags disabled."""

    @pytest.fixture(autouse=True)
    def _disable_optional(self, monkeypatch):
        monkeypatch.setattr(settings, "AI_ENABLED", False)
        monkeypatch.setattr(settings, "DATABASE_ENABLED", False)
        monkeypatch.setattr(settings, "METRICS_ENABLED", False)
        monkeypatch.setattr(settings, "TRACING_ENABLED", False)

    def test_live_endpoint(self, client_no_auth):
        """GET /api/v1/health/live returns 200 with alive status."""
        response = client_no_auth.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "alive"
        assert data["data"]["ready"] is True

    def test_ready_skips_db_when_disabled(self, client_no_auth):
        """GET /api/v1/health/ready returns 200 when DATABASE_ENABLED=False."""
        response = client_no_auth.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["ready"] is True
        assert data["data"]["dependencies"] == {}

    def test_health_check_legacy(self, client_no_auth):
        """GET /api/v1/health (legacy) also works."""
        response = client_no_auth.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_root_alive(self, client):
        """GET / returns alive status."""
        response = client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"


class TestOptionalDepsFlags:
    """Verify the guard flags correctly detect installed packages."""

    def test_scalar_flag_is_bool(self):
        """_scalar_available must be a bool."""
        from src.api.main import _scalar_available
        assert isinstance(_scalar_available, bool)

    def test_observability_flag_is_bool(self):
        """_observability_available must be a bool."""
        from src.api.main import _observability_available
        assert isinstance(_observability_available, bool)

    def test_db_module_imports(self):
        """database.connection should be importable."""
        from src.database import connection
        # In full mode, SQLAlchemy should be available
        # SQLAlchemy is optional; just verify the function exists
        assert hasattr(connection, "_ensure_sqlalchemy")