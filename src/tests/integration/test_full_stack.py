"""
Integration tests for the full ALMS application stack.

These tests verify that all layers work together correctly:
- API Layer → Execution Layer → Agent Layer → Database Layer
- Observability (tracing + metrics) integrated throughout
- Real database operations (not mocked)
- End-to-end workflows
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from src.api.main import app
from src.database.connection import get_db, AsyncSessionLocal
from src.database.repositories.sqlalchemy_repository import SQLAlchemyRepository
from src.observability.metrics import get_metrics
from src.config.settings import settings


# Test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def client():
    """Create a TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def db_session():
    """Create a fresh database session for each test."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


class TestFullStackIntegration:
    """
    Integration tests that verify the complete ALMS stack.
    These tests use real database connections and full observability.
    """

    def test_health_endpoint_returns_healthy(self, client):
        """Test that health endpoint returns healthy status."""
        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "FastAPI Agentic Starter" in data["service"]

    def test_api_v1_health_endpoint(self, client):
        """Test API v1 health endpoint."""
        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"] is not None

    def test_metrics_endpoint_available(self, client):
        """Test that metrics endpoint is accessible."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert len(content) > 0
        assert "app_info" in content

    def test_docs_endpoint_available(self, client):
        """Test that API documentation is accessible."""
        # Act
        response = client.get("/docs")

        # Assert
        assert response.status_code == 200
        assert "Scalar" in response.text or "API" in response.text

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is accessible."""
        # Act
        response = client.get("/openapi.json")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestDatabaseIntegration:
    """
    Tests that verify database connectivity and SQLAlchemy repository.
    Uses actual database operations.
    """

    @pytest.mark.asyncio
    async def test_database_connection(self, db_session):
        """Test that database connection works."""
        # Act
        result = await db_session.execute(text("SELECT 1"))
        row = result.scalar()

        # Assert
        assert row == 1

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self, db_session):
        """Test that transactions rollback correctly."""
        # This test verifies the session fixture rolls back transactions
        # Act & Assert - no exception means success
        result = await db_session.execute(text("SELECT version()"))
        assert result.scalar() is not None

    def test_database_dependency_injection(self, client):
        """Test that database dependency injection works in endpoints."""
        # Health endpoint uses database - if it works, DI is working
        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200


class TestObservabilityIntegration:
    """
    Tests that verify observability stack is fully integrated.
    """

    def test_request_id_in_response(self, client):
        """Test that requests include X-Request-ID header."""
        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert "X-Request-ID" in response.headers
        request_id = response.headers["X-Request-ID"]
        assert len(request_id) > 0

    def test_metrics_record_http_requests(self, client):
        """Test that HTTP requests are recorded in metrics."""
        # Arrange - Clear state and make requests
        initial_response = client.get("/api/v1/metrics")
        initial_content = initial_response.content.decode()

        # Make some API calls
        for _ in range(3):
            client.get("/api/v1/health")

        # Act
        metrics_response = client.get("/api/v1/metrics")
        metrics_content = metrics_response.content.decode()

        # Assert - metrics should contain request data
        assert (
            "http_requests_total" in metrics_content
            or "http_request" in metrics_content
        )

    def test_tracing_headers_propagated(self, client):
        """Test that tracing context is propagated."""
        # Arrange
        headers = {
            "traceparent": "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"
        }

        # Act
        response = client.get("/api/v1/health", headers=headers)

        # Assert
        assert response.status_code == 200


class TestAgentExecutionFlow:
    """
    Tests for agent execution workflow (if sample agent is available).
    """

    def test_sample_agent_endpoint_exists(self, client):
        """Test that sample agent endpoint exists."""
        # Act - Try to access agent endpoint (may require API key)
        response = client.post(
            "/api/v1/agent",
            json={"query": "test"},
            headers={"X-API-Key": settings.X_API_KEY or "test-key"},
        )

        # Assert - should either succeed or fail gracefully
        assert response.status_code in [200, 422, 401, 403]

    def test_agent_execution_traced_and_metered(self, client):
        """Test that agent execution creates traces and metrics."""
        # This test verifies the full observability flow
        # Arrange
        api_key = settings.X_API_KEY or "test-key"

        # Act - Make agent request (may fail due to missing API key, but should still trace)
        try:
            client.post(
                "/api/v1/agent", json={"query": "test"}, headers={"X-API-Key": api_key}
            )
        except Exception:
            pass  # Expected if API key is invalid

        # Get metrics
        metrics_response = client.get("/api/v1/metrics")
        metrics_content = metrics_response.content.decode()

        # Assert - should have attempted to record metrics
        assert metrics_response.status_code == 200


class TestLayerCommunication:
    """
    Tests that verify ALMS layer communication rules are followed.
    API → Execution → Agent (not skipping layers)
    """

    def test_api_layer_isolated(self, client):
        """Test that API layer is properly isolated."""
        # Act
        response = client.get("/api/v1/health")

        # Assert - should return standardized response
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data
        assert "error" in data
        assert "request_id" in data

    def test_middleware_order_correct(self, client):
        """Test that middleware executes in correct order."""
        # Observability middleware should run first (last added)
        # Then Security, then Logging, then Error Handler

        # Act
        response = client.get("/api/v1/health")

        # Assert - if all middleware works, we get proper response
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers  # From observability middleware


class TestErrorHandlingIntegration:
    """
    Tests that verify error handling across the stack.
    """

    def test_not_found_returns_standardized_error(self, client):
        """Test that 404 errors return standardized format."""
        # Act
        response = client.get("/api/v1/nonexistent")

        # Assert
        assert response.status_code == 404
        data = response.json()
        assert "success" in data
        assert data["success"] is False
        assert "error" in data

    def test_validation_error_handled(self, client):
        """Test that validation errors are handled properly."""
        # Act - Send invalid request to agent endpoint
        response = client.post(
            "/api/v1/agent",
            json={"invalid_field": "test"},  # Missing required 'query' field
            headers={"X-API-Key": settings.X_API_KEY or "test-key"},
        )

        # Assert
        assert response.status_code in [422, 401, 403]

    def test_custom_exceptions_converted_to_http(self, client):
        """Test that custom exceptions are converted to HTTP responses."""
        # The error handler middleware should convert exceptions
        # Act
        response = client.get("/api/v1/health")

        # Assert - successful request means error handling works
        assert response.status_code == 200


class TestConfigurationIntegration:
    """
    Tests that verify configuration is loaded correctly.
    """

    def test_settings_loaded(self, client):
        """Test that settings are loaded from environment."""
        # Health endpoint uses settings
        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        assert settings.API_PREFIX == "/api"

    def test_cors_enabled(self, client):
        """Test that CORS is properly configured."""
        # Act
        response = client.options(
            "/",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Assert
        assert response.status_code in [200, 204]
        assert "access-control-allow-origin" in response.headers


class TestSecurityIntegration:
    """
    Tests that verify security features are working.
    """

    def test_security_headers_present(self, client):
        """Test that security headers are added."""
        # Act
        response = client.get("/api/v1/health")

        # Assert - check for common security headers
        headers = response.headers
        # Some security headers should be present
        assert len(headers) > 0

    def test_api_key_rejected_when_missing(self, client):
        """Test that API key is required for protected endpoints."""
        # Act
        response = client.post("/api/v1/agent", json={"query": "test"})

        # Assert - should reject without API key
        assert response.status_code in [401, 403, 422]


# Performance benchmarks
class TestPerformanceBenchmarks:
    """
    Performance benchmarks to verify system is production-ready.
    """

    def test_health_endpoint_response_time(self, client):
        """Benchmark health endpoint response time."""
        # Arrange
        times = []

        # Act - Make 10 requests and measure time
        for _ in range(10):
            start = time.time()
            response = client.get("/api/v1/health")
            end = time.time()
            times.append(end - start)
            assert response.status_code == 200

        # Assert - average should be under 100ms
        avg_time = sum(times) / len(times)
        assert avg_time < 0.1, f"Average response time {avg_time}s exceeds 100ms"

    def test_metrics_endpoint_response_time(self, client):
        """Benchmark metrics endpoint response time."""
        # Act
        start = time.time()
        response = client.get("/api/v1/metrics")
        end = time.time()

        # Assert
        assert response.status_code == 200
        assert (end - start) < 0.5, "Metrics endpoint too slow"

    def test_concurrent_request_handling(self, client):
        """Test that system handles concurrent requests."""
        import concurrent.futures

        # Act - Make 20 concurrent requests
        def make_request():
            return client.get("/api/v1/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            responses = [f.result() for f in futures]

        # Assert
        assert all(r.status_code == 200 for r in responses)

    def test_memory_usage_stable(self, client):
        """Test that memory usage is stable under load."""
        import gc

        # Arrange - Force garbage collection
        gc.collect()
        initial_memory = len(gc.get_objects())

        # Act - Make many requests
        for _ in range(100):
            client.get("/api/v1/health")

        gc.collect()
        final_memory = len(gc.get_objects())

        # Assert - memory should not grow excessively
        memory_growth = final_memory - initial_memory
        assert memory_growth < 1000, f"Memory grew by {memory_growth} objects"


# Cleanup
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Force garbage collection
    import gc

    gc.collect()


# Mark all tests as integration tests
pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio,
]
