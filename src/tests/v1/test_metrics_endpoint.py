"""
Tests for the metrics endpoint.

These tests verify the /api/v1/metrics endpoint is accessible and returns data.
"""

import pytest


class TestMetricsEndpoint:
    """Test suite for /api/v1/metrics endpoint."""

    def test_metrics_endpoint_returns_200(self, client):
        """Test that metrics endpoint returns 200 status."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200

    def test_metrics_endpoint_returns_content(self, client):
        """Test that metrics endpoint returns content."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()
        assert len(content) > 0

    def test_metrics_endpoint_returns_prometheus_format(self, client):
        """Test that metrics endpoint returns Prometheus format."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "prometheus" in content_type.lower()

    def test_metrics_contains_expected_metrics(self, client):
        """Test that metrics contains expected metric names."""
        # Act
        response = client.get("/api/v1/metrics")

        # Assert
        assert response.status_code == 200
        content = response.content.decode()

        # Should contain some metrics
        assert len(content) > 0
        # Look for common metric patterns
        assert (
            "# HELP" in content
            or "# TYPE" in content
            or "_total" in content
            or "_seconds" in content
        )


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
        assert duration < 1.0, f"Response time {duration}s exceeds 1 second"


pytestmark = pytest.mark.unit
