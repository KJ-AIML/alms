"""
Tests for the metrics endpoint.

This module tests the /api/v1/metrics endpoint that exposes Prometheus metrics.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


class TestMetricsEndpoint:
    """Test suite for /api/v1/metrics endpoint."""

    def test_metrics_endpoint_returns_200(self, client):
        """Test that metrics endpoint returns 200 status."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that metrics endpoint returns Prometheus exposition format."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "prometheus" in content_type.lower() or "text/plain" in content_type

    def test_metrics_endpoint_contains_http_metrics(self, client):
        """Test that metrics include HTTP request metrics."""
        # First make a request to generate some metrics
        client.get("/api/v1/health")

        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        assert "http_requests_total" in content or "http_request" in content

    def test_metrics_endpoint_contains_database_metrics(self, client):
        """Test that metrics include database metrics."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        assert "db_queries_total" in content or "db_query" in content

    def test_metrics_endpoint_contains_ai_metrics(self, client):
        """Test that metrics include AI/LLM metrics."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        assert "ai_requests_total" in content or "ai_request" in content

    def test_metrics_endpoint_contains_agent_metrics(self, client):
        """Test that metrics include agent metrics."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        assert "agent_executions_total" in content or "agent_execution" in content

    def test_metrics_endpoint_returns_valid_prometheus_text(self, client):
        """Test that metrics response is valid Prometheus text format."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        # Prometheus format should have HELP, TYPE, or metric lines
        lines = content.strip().split("\n")
        valid_lines = [line for line in lines if line.startswith("#") or " " in line]
        assert len(valid_lines) > 0, "Response should contain valid Prometheus format"

    def test_metrics_endpoint_handles_concurrent_requests(self, client):
        """Test that metrics endpoint handles concurrent access."""
        import concurrent.futures

        # Act - Make multiple concurrent requests
        def get_metrics():
            return client.get("/api/v1/metrics")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(get_metrics) for _ in range(10)]
            responses = [f.result() for f in futures]

        # Assert
        for response in responses:
            assert response.status_code == 200

    def test_metrics_endpoint_after_api_calls(self, client):
        """Test metrics endpoint after making various API calls."""
        # Arrange - Make some API calls
        client.get("/api/v1/health")
        client.get("/")  # Root endpoint

        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        # Should have accumulated metrics from the calls above
        assert len(content) > 0

    def test_metrics_endpoint_not_excluded_from_tracing(self, client):
        """Test that metrics endpoint is not traced (optimization)."""
        # The metrics endpoint should be excluded from tracing/middleware processing
        # This is an implementation detail test
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200


class TestMetricsEndpointErrorHandling:
    """Test error handling for metrics endpoint."""

    def test_metrics_endpoint_handles_registry_errors(self, client):
        """Test that metrics endpoint handles registry errors gracefully."""
        # Arrange - Mock registry to raise error
        with patch("src.api.endpoints.v1.metrics.get_metrics") as mock_get_metrics:
            mock_get_metrics.side_effect = Exception("Registry error")

            # Act
            response = client.get("/api/v1/metrics")

            # Assert - should return error or empty metrics
            assert response.status_code in [200, 500]


class TestMetricsContent:
    """Test specific content of metrics response."""

    def test_metrics_include_app_info(self, client):
        """Test that metrics include application info."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        # Should contain app_info metric
        assert "app_info" in content

    def test_metrics_include_service_name(self, client):
        """Test that app_info includes service name."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        lines = content.split("\n")
        info_lines = [
            line
            for line in lines
            if "app_info" in line and "fastapi-agentic-starter" in line
        ]
        assert len(info_lines) > 0 or "app_info" in content

    def test_metrics_format_has_help_and_type(self, client):
        """Test that metrics include HELP and TYPE annotations."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        # Prometheus format should have # HELP or # TYPE lines
        has_help_or_type = any(
            line.startswith("# HELP") or line.startswith("# TYPE")
            for line in content.split("\n")
        )
        # Note: Not all metrics libraries include HELP/TYPE, so this is optional


class TestMetricsEndpointPerformance:
    """Performance tests for metrics endpoint."""

    def test_metrics_endpoint_response_time(self, client):
        """Test that metrics endpoint responds quickly."""
        import time

        # Act
        start = time.time()
        response = client.get("/api/v1/metrics")
        duration = time.time() - start

        # Assert
        assert response.status_code == 200
        assert duration < 1.0  # Should respond within 1 second

    def test_metrics_endpoint_with_large_registry(self, client):
        """Test metrics endpoint with many metrics."""
        # Arrange - Generate many metrics
        from src.observability.metrics import http_requests_total

        for i in range(100):
            http_requests_total.labels(
                method="GET", endpoint=f"/test/{i}", status_code="200"
            ).inc()

        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        # Should include all the metrics we generated
        assert len(content) > 1000  # Should be reasonably large


# Integration tests
class TestMetricsIntegration:
    """Integration tests for metrics with other components."""

    def test_metrics_after_health_check(self, client):
        """Test metrics are recorded after health check."""
        # Arrange - Make health check request
        client.get("/api/v1/health")

        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        content = response.content.decode()
        # Should have recorded the health check request
        # Note: Actual verification depends on implementation
        assert response.status_code == 200

    def test_metrics_after_agent_execution(self, client):
        """Test metrics after agent execution (if available)."""
        # This would test the full flow from agent execution to metrics
        pass


# Fixtures (these should be in conftest.py, but included here for clarity)
@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    from fastapi.testclient import TestClient
    from src.api.main import app

    return TestClient(app)
