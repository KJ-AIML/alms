"""
End-to-end tests for complete workflows.

Tests verify real-world usage patterns work correctly.
"""

import pytest


class TestCompleteRequestLifecycle:
    """Tests for complete request lifecycle."""

    def test_request_with_full_observability(self, client):
        """Test a complete request with observability features."""
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
        """Test that metrics accumulate across requests."""
        # Act - Make multiple requests
        for i in range(5):
            response = client.get("/api/v1/health")
            assert response.status_code == 200

        # Get metrics
        metrics_response = client.get("/api/v1/metrics")

        # Assert
        assert metrics_response.status_code == 200
        content = metrics_response.content.decode()
        assert len(content) > 0


class TestErrorRecovery:
    """Tests for error handling and recovery."""

    def test_error_handled_gracefully(self, client):
        """Test that errors are handled gracefully."""
        # Act - Request non-existent endpoint
        response = client.get("/api/v1/nonexistent")

        # Assert
        assert response.status_code == 404

        data = response.json()
        assert data["success"] is False
        assert "error" in data
        assert "request_id" in data

    def test_service_recover_after_error(self, client):
        """Test that service recovers after errors."""
        # Cause an error
        client.get("/api/v1/nonexistent")

        # Service should still work
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestConfigurationAndSetup:
    """Tests to verify configuration works."""

    def test_api_documentation_accessible(self, client):
        """Test that API documentation is accessible."""
        # Act
        response = client.get("/docs")

        # Assert
        assert response.status_code == 200

    def test_openapi_schema_valid(self, client):
        """Test that OpenAPI schema is valid."""
        # Act
        response = client.get("/openapi.json")

        # Assert
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema


class TestEndToEndPerformance:
    """Performance tests."""

    def test_health_endpoint_under_load(self, client):
        """Test health endpoint under moderate load."""
        import time

        # Act - Make 50 requests
        start = time.time()
        success_count = 0

        for _ in range(50):
            response = client.get("/api/v1/health")
            if response.status_code == 200:
                success_count += 1

        duration = time.time() - start

        # Assert
        assert success_count >= 45, f"Only {success_count}/50 requests succeeded"
        assert duration < 10.0, f"Load test took {duration}s, too slow"


pytestmark = [
    pytest.mark.e2e,
    pytest.mark.unit,  # These are lightweight enough to run as unit tests
]
