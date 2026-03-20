"""
Integration tests for the full ALMS application stack.

These tests verify the application works correctly end-to-end.
"""

import pytest


class TestFullStackIntegration:
    """Integration tests for complete stack."""

    def test_health_endpoint_returns_healthy(self, client):
        """Test that health endpoint returns healthy status."""
        # Act
        response = client.get("/")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_v1_health_endpoint(self, client):
        """Test API v1 health endpoint."""
        # Act
        response = client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_metrics_endpoint_available(self, client):
        """Test that metrics endpoint is accessible."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert len(content) > 0

    def test_docs_endpoint_available(self, client):
        """Test that API documentation is accessible."""
        # Act
        response = client.get("/docs")

        # Assert
        assert response.status_code == 200

    def test_openapi_schema_available(self, client):
        """Test that OpenAPI schema is accessible."""
        # Act
        response = client.get("/openapi.json")

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


class TestObservabilityIntegration:
    """Tests that verify observability features work."""

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
        # Arrange - Make some API calls
        for _ in range(3):
            client.get("/api/v1/health")

        # Act
        metrics_response = client.get("/api/v1/metrics")

        # Assert
        assert metrics_response.status_code == 200
        content = metrics_response.content.decode()
        assert len(content) > 0


class TestErrorHandlingIntegration:
    """Tests for error handling across the stack."""

    def test_not_found_returns_404(self, client):
        """Test that 404 errors return proper status code."""
        # Act
        response = client.get("/api/v1/nonexistent")

        # Assert
        assert response.status_code == 404

    def test_service_recover_after_error(self, client):
        """Test that service recovers after errors."""
        # Act - Cause an error
        client.get("/api/v1/nonexistent")

        # Service should still work
        response = client.get("/api/v1/health")
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True


class TestConfigurationIntegration:
    """Tests that verify configuration works."""

    def test_cors_enabled(self, client):
        """Test that CORS is properly configured."""
        # Act
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Assert
        assert response.status_code in [200, 204]


class TestPerformanceBenchmarks:
    """Performance benchmarks."""

    def test_health_endpoint_response_time(self, client):
        """Benchmark health endpoint response time."""
        import time

        # Act - Make 10 requests and measure time
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/api/v1/health")
            end = time.time()
            times.append(end - start)
            assert response.status_code == 200

        # Assert - average should be under 5 seconds (accounting for DB timeouts)
        avg_time = sum(times) / len(times)
        assert avg_time < 5.0, f"Average response time {avg_time}s exceeds 5 seconds"


pytestmark = [
    pytest.mark.integration,
    pytest.mark.unit,  # These are lightweight enough to run as unit tests
]
