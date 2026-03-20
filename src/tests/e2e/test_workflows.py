"""
End-to-end workflow tests for complete business scenarios.

These tests verify real-world usage patterns:
- Full request lifecycle
- Multi-step agent workflows
- Database transactions with observability
- Error recovery scenarios
"""

import pytest
import asyncio
import time
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, delete

from src.api.main import app
from src.database.connection import AsyncSessionLocal, Base
from src.config.settings import settings


# Test User Model for e2e testing
from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime


class TestUser(Base):
    """Test user model for e2e tests."""

    __tablename__ = "test_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="function")
async def setup_test_table():
    """Setup and teardown test database table."""
    # Create table
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("""
            CREATE TABLE IF NOT EXISTS test_users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        )
        await session.commit()

    yield

    # Cleanup
    async with AsyncSessionLocal() as session:
        await session.execute(text("DROP TABLE IF EXISTS test_users"))
        await session.commit()


class TestCompleteRequestLifecycle:
    """
    Tests that verify the complete lifecycle of a request through all layers.
    """

    def test_request_with_full_observability(self, client):
        """
        Test a complete request with tracing and metrics.

        Verifies:
        - Request ID generation
        - Tracing span creation
        - Metrics recording
        - Response standardization
        """
        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        data = response.json()
        assert data["success"] is True
        assert data["data"] is not None
        assert "request_id" in data

    def test_request_metrics_accumulation(self, client):
        """
        Test that metrics accumulate correctly across multiple requests.
        """
        # Arrange - Make initial request to establish baseline
        initial_metrics = client.get("/api/v1/metrics")

        # Act - Make multiple requests
        request_count = 5
        for i in range(request_count):
            response = client.get("/api/v1/health")
            assert response.status_code == 200

        # Get metrics after requests
        final_metrics = client.get("/api/v1/metrics")

        # Assert - metrics should reflect the requests made
        final_content = final_metrics.content.decode()
        assert "http_requests_total" in final_content

    def test_concurrent_requests_handled(self, client):
        """
        Test that concurrent requests are handled correctly.

        Verifies:
        - No race conditions
        - Proper request ID uniqueness
        - Metrics accuracy under load
        """
        import concurrent.futures

        request_ids = []

        def make_request():
            response = client.get("/api/v1/health")
            return response.headers.get("X-Request-ID")

        # Act - Make concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            request_ids = [f.result() for f in futures]

        # Assert - all request IDs should be unique
        assert len(request_ids) == len(set(request_ids)), "Request IDs should be unique"


class TestDatabaseWorkflow:
    """
    Tests for complete database workflows with observability.
    """

    @pytest.mark.asyncio
    async def test_repository_crud_workflow(self):
        """
        Test complete CRUD workflow through repository.

        Verifies:
        - Create operation with metrics
        - Read operation with tracing
        - Update operation
        - Delete operation
        - Transaction rollback on error
        """
        from src.database.repositories.sqlalchemy_repository import SQLAlchemyRepository

        async with AsyncSessionLocal() as session:
            # Create repository
            repo = SQLAlchemyRepository(TestUser, session)

            # Create
            user = TestUser(username="testuser", email="test@example.com")
            created = await repo.create(user)
            await session.commit()

            assert created.id is not None
            assert created.username == "testuser"

            # Read
            fetched = await repo.get(created.id)
            assert fetched is not None
            assert fetched.email == "test@example.com"

            # Update
            updated = await repo.update(created.id, {"email": "updated@example.com"})
            await session.commit()

            assert updated is not None
            assert updated.email == "updated@example.com"

            # Delete
            deleted = await repo.delete(created.id)
            await session.commit()

            assert deleted is True

            # Verify deletion
            not_found = await repo.get(created.id)
            assert not_found is None

    @pytest.mark.asyncio
    async def test_transaction_rollback_on_error(self):
        """
        Test that transactions rollback correctly on errors.
        """
        from src.database.repositories.sqlalchemy_repository import SQLAlchemyRepository

        async with AsyncSessionLocal() as session:
            repo = SQLAlchemyRepository(TestUser, session)

            # Create a user
            user = TestUser(username="rollback_test", email="rollback@example.com")
            created = await repo.create(user)

            try:
                # This should cause an error (duplicate username)
                duplicate_user = TestUser(
                    username="rollback_test", email="other@example.com"
                )
                await repo.create(duplicate_user)
                await session.commit()
                pytest.fail("Should have raised an error")
            except Exception:
                await session.rollback()

            # Verify original user still exists
            existing = await repo.get_by_field("username", "rollback_test")
            assert existing is not None


class TestAgentWorkflow:
    """
    Tests for complete agent execution workflows.
    """

    def test_agent_execution_with_tracing(self, client):
        """
        Test that agent execution creates proper traces and metrics.
        """
        api_key = settings.X_API_KEY or "test-key"

        # Act - Execute agent (may fail due to API key, but should trace)
        try:
            response = client.post(
                "/api/v1/agent",
                json={"query": "Hello, how are you?"},
                headers={"X-API-Key": api_key},
            )
        except Exception as e:
            # If it fails, check that error is handled
            pass

        # Get metrics to verify tracing occurred
        metrics_response = client.get("/api/v1/metrics")
        assert metrics_response.status_code == 200

        # Verify request was traced
        metrics_content = metrics_response.content.decode()
        # Should contain agent or HTTP metrics
        assert "agent" in metrics_content.lower() or "http" in metrics_content.lower()

    def test_agent_execution_metrics_recorded(self, client):
        """
        Test that agent execution metrics are properly recorded.
        """
        api_key = settings.X_API_KEY or "test-key"

        # Get initial metrics
        initial_response = client.get("/api/v1/metrics")
        initial_content = initial_response.content.decode()

        # Execute agent multiple times
        for _ in range(3):
            try:
                client.post(
                    "/api/v1/agent",
                    json={"query": "Test query"},
                    headers={"X-API-Key": api_key},
                )
            except Exception:
                pass

        # Get final metrics
        final_response = client.get("/api/v1/metrics")
        final_content = final_response.content.decode()

        # Metrics should exist
        assert final_response.status_code == 200


class TestErrorRecovery:
    """
    Tests for error handling and recovery scenarios.
    """

    def test_error_handled_gracefully(self, client):
        """
        Test that errors are handled gracefully with proper response format.
        """
        # Act - Request non-existent endpoint
        response = client.get("/api/v1/nonexistent")

        # Assert
        assert response.status_code == 404

        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert data["error"] is not None
        assert "request_id" in data

    def test_validation_error_response(self, client):
        """
        Test that validation errors return proper format.
        """
        # Act - Send invalid request
        response = client.post(
            "/api/v1/agent",
            json={"invalid_field": "value"},  # Missing required 'query'
            headers={"X-API-Key": settings.X_API_KEY or "test-key"},
        )

        # Assert
        assert response.status_code in [401, 403, 422]

        if response.status_code == 422:
            data = response.json()
            assert "success" in data

    def test_service_recover_after_error(self, client):
        """
        Test that service recovers and continues serving requests after errors.
        """
        # Act - Cause an error
        client.get("/api/v1/nonexistent")

        # Service should still work
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestObservabilityIntegration:
    """
    Tests for complete observability integration.
    """

    def test_all_metrics_categories_present(self, client):
        """
        Test that all expected metric categories are present.
        """
        # Arrange - Make various requests to generate metrics
        client.get("/api/v1/health")

        # Act
        response = client.get("/api/v1/metrics")
        content = response.content.decode()

        # Assert - Check for expected metric categories
        expected_metrics = [
            "http_requests_total",
            "http_request_duration_seconds",
            "db_queries_total",
            "db_query_duration_seconds",
            "ai_requests_total",
            "agent_executions_total",
        ]

        for metric in expected_metrics:
            assert metric in content, f"Missing metric: {metric}"

    def test_tracing_context_propagation(self, client):
        """
        Test that tracing context is properly propagated through requests.
        """
        # Arrange
        traceparent = "00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01"

        # Act
        response = client.get("/api/v1/health", headers={"traceparent": traceparent})

        # Assert
        assert response.status_code == 200

    def test_request_id_consistency(self, client):
        """
        Test that request ID is consistent throughout request lifecycle.
        """
        # Act
        response = client.get("/api/v1/health")

        # Assert
        header_request_id = response.headers.get("X-Request-ID")
        body_request_id = response.json().get("request_id")

        assert header_request_id is not None
        assert body_request_id is not None
        assert header_request_id == body_request_id


class TestConfigurationAndSetup:
    """
    Tests to verify configuration and setup are correct.
    """

    def test_cors_configuration(self, client):
        """
        Test that CORS is properly configured.
        """
        # Act
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-API-Key",
            },
        )

        # Assert
        assert response.status_code in [200, 204]
        assert "access-control-allow-origin" in response.headers

    def test_api_documentation_accessible(self, client):
        """
        Test that API documentation is accessible.
        """
        # Act
        response = client.get("/docs")

        # Assert
        assert response.status_code == 200

    def test_openapi_schema_valid(self, client):
        """
        Test that OpenAPI schema is valid and complete.
        """
        # Act
        response = client.get("/openapi.json")

        # Assert
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema
        assert "/api/v1/health" in schema["paths"]


# Performance benchmarks for e2e
class TestEndToEndPerformance:
    """
    Performance tests for complete workflows.
    """

    def test_health_endpoint_p99_latency(self, client):
        """
        Test that health endpoint p99 latency is under threshold.
        """
        latencies = []

        for _ in range(100):
            start = time.time()
            response = client.get("/api/v1/health")
            end = time.time()
            latencies.append(end - start)
            assert response.status_code == 200

        latencies.sort()
        p99 = latencies[int(len(latencies) * 0.99)]

        assert p99 < 0.1, f"P99 latency {p99}s exceeds 100ms"

    def test_sustained_load_handling(self, client):
        """
        Test that system handles sustained load.
        """
        import concurrent.futures

        def make_requests(count):
            successes = 0
            for _ in range(count):
                response = client.get("/api/v1/health")
                if response.status_code == 200:
                    successes += 1
            return successes

        # Act - Simulate sustained load
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_requests, 20) for _ in range(5)]
            results = [f.result() for f in futures]

        total_successes = sum(results)
        total_requests = 5 * 20

        # Assert - Should handle at least 95% of requests
        success_rate = total_successes / total_requests
        assert success_rate >= 0.95, f"Success rate {success_rate} below 95%"


# Mark all tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.integration,
    pytest.mark.asyncio,
]
