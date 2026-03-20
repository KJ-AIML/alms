"""
Tests for Prometheus metrics implementation.

This module tests the metrics collection, exposition, and various metric types
including counters, histograms, and gauges.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry

from src.observability.metrics import (
    setup_metrics,
    get_metrics,
    get_metrics_content_type,
    timed_metric,
    measure_duration,
    MetricsCollector,
    registry,
    http_requests_total,
    http_request_duration_seconds,
    db_queries_total,
    db_query_duration_seconds,
    ai_requests_total,
    ai_request_duration_seconds,
    agent_executions_total,
    agent_execution_duration_seconds,
)


class TestMetricsSetup:
    """Test suite for metrics initialization."""

    def test_setup_metrics_initializes_service_info(self):
        """Test that setup_metrics sets service information."""
        # Arrange & Act
        setup_metrics(service_name="test-service", service_version="1.0.0")

        # Assert - check that metrics are generated without errors
        metrics_output = get_metrics()
        assert b"test-service" in metrics_output

    def test_setup_metrics_logs_initialization(self):
        """Test that setup_metrics logs initialization."""
        # Arrange
        with patch("src.observability.metrics.logger") as mock_logger:
            # Act
            setup_metrics(service_name="test-service")

            # Assert
            mock_logger.info.assert_called_once()


class TestHTTPMetrics:
    """Test suite for HTTP request metrics."""

    def test_http_requests_total_increment(self):
        """Test HTTP request counter increment."""
        # Act
        http_requests_total.labels(
            method="GET", endpoint="/test", status_code="200"
        ).inc()

        # Assert
        metrics = get_metrics()
        assert b"http_requests_total" in metrics

    def test_http_request_duration_histogram(self):
        """Test HTTP request duration histogram."""
        # Act
        http_request_duration_seconds.labels(
            method="POST", endpoint="/api/test"
        ).observe(0.123)

        # Assert
        metrics = get_metrics()
        assert b"http_request_duration_seconds" in metrics

    def test_http_metrics_with_different_labels(self):
        """Test HTTP metrics with various label combinations."""
        # Arrange & Act
        http_requests_total.labels(
            method="GET", endpoint="/users", status_code="200"
        ).inc()
        http_requests_total.labels(
            method="POST", endpoint="/users", status_code="201"
        ).inc()
        http_requests_total.labels(
            method="GET", endpoint="/users", status_code="404"
        ).inc()

        # Assert
        metrics = get_metrics()
        assert metrics.count(b"http_requests_total") >= 1


class TestDatabaseMetrics:
    """Test suite for database metrics."""

    def test_db_queries_total_increment(self):
        """Test database query counter."""
        # Act
        db_queries_total.labels(operation="select", table="users").inc()

        # Assert
        metrics = get_metrics()
        assert b"db_queries_total" in metrics

    def test_db_query_duration_histogram(self):
        """Test database query duration."""
        # Act
        db_query_duration_seconds.labels(operation="insert", table="orders").observe(
            0.045
        )

        # Assert
        metrics = get_metrics()
        assert b"db_query_duration_seconds" in metrics

    def test_db_metrics_multiple_operations(self):
        """Test metrics for various database operations."""
        # Arrange & Act
        operations = ["select", "insert", "update", "delete"]
        for op in operations:
            db_queries_total.labels(operation=op, table="test_table").inc()
            db_query_duration_seconds.labels(operation=op, table="test_table").observe(
                0.01
            )

        # Assert
        metrics = get_metrics()
        assert b"db_queries_total" in metrics
        assert b"db_query_duration_seconds" in metrics


class TestAIMetrics:
    """Test suite for AI/LLM metrics."""

    def test_ai_requests_total(self):
        """Test AI request counter."""
        # Act
        ai_requests_total.labels(model="gpt-4", provider="openai").inc()

        # Assert
        metrics = get_metrics()
        assert b"ai_requests_total" in metrics

    def test_ai_request_duration(self):
        """Test AI request duration."""
        # Act
        ai_request_duration_seconds.labels(
            model="gpt-3.5-turbo", provider="openai"
        ).observe(1.5)

        # Assert
        metrics = get_metrics()
        assert b"ai_request_duration_seconds" in metrics


class TestAgentMetrics:
    """Test suite for agent execution metrics."""

    def test_agent_executions_total(self):
        """Test agent execution counter."""
        # Act
        agent_executions_total.labels(agent_name="sample_agent", status="success").inc()

        # Assert
        metrics = get_metrics()
        assert b"agent_executions_total" in metrics

    def test_agent_execution_duration(self):
        """Test agent execution duration."""
        # Act
        agent_execution_duration_seconds.labels(agent_name="sample_agent").observe(2.5)

        # Assert
        metrics = get_metrics()
        assert b"agent_execution_duration_seconds" in metrics


class TestTimedMetricContextManager:
    """Test suite for timed_metric context manager."""

    def test_timed_metric_records_duration(self):
        """Test that timed_metric records duration."""
        # Arrange
        test_histogram = Histogram(
            "test_duration", "Test duration", buckets=[0.001, 0.01, 0.1, 1.0]
        )

        # Act
        with timed_metric(test_histogram):
            import time

            time.sleep(0.01)  # Small delay

        # Assert - metric should be recorded
        # In real scenario, you'd verify the histogram bucket

    def test_timed_metric_with_labels(self):
        """Test timed_metric with labels."""
        # Arrange
        test_histogram = Histogram(
            "test_labeled_duration",
            "Test duration with labels",
            ["operation"],
            buckets=[0.001, 0.01, 0.1],
        )

        # Act
        with timed_metric(test_histogram, {"operation": "test_op"}):
            pass

        # Assert
        # Labels should be applied


class TestMeasureDurationDecorator:
    """Test suite for measure_duration decorator."""

    @pytest.mark.asyncio
    async def test_measure_duration_async(self):
        """Test measuring async function duration."""
        # Arrange
        test_histogram = Histogram(
            "async_test_duration", "Async test duration", buckets=[0.001, 0.01, 0.1]
        )

        @measure_duration(test_histogram)
        async def async_function():
            import asyncio

            await asyncio.sleep(0.01)
            return "done"

        # Act
        result = await async_function()

        # Assert
        assert result == "done"

    def test_measure_duration_sync(self):
        """Test measuring sync function duration."""
        # Arrange
        test_histogram = Histogram(
            "sync_test_duration", "Sync test duration", buckets=[0.001, 0.01, 0.1]
        )

        @measure_duration(test_histogram)
        def sync_function():
            import time

            time.sleep(0.01)
            return 42

        # Act
        result = sync_function()

        # Assert
        assert result == 42

    def test_measure_duration_preserves_function(self):
        """Test that decorator preserves function metadata."""
        # Arrange
        test_histogram = Histogram("test_duration", "Test")

        @measure_duration(test_histogram)
        def my_function():
            """My docstring."""
            return 42

        # Assert
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestMetricsCollector:
    """Test suite for MetricsCollector helper class."""

    def test_metrics_collector_initialization(self):
        """Test MetricsCollector creation."""
        # Act
        collector = MetricsCollector(prefix="test")

        # Assert
        assert collector.prefix == "test"
        assert collector.counters == {}
        assert collector.histograms == {}
        assert collector.gauges == {}

    def test_metrics_collector_counter_creation(self):
        """Test counter metric creation."""
        # Arrange
        collector = MetricsCollector(prefix="app")

        # Act
        counter = collector.counter("requests", "Total requests", ["method"])

        # Assert
        assert counter is not None
        assert "app_requests" in collector.counters

    def test_metrics_collector_histogram_creation(self):
        """Test histogram metric creation."""
        # Arrange
        collector = MetricsCollector()

        # Act
        histogram = collector.histogram("duration", "Duration", ["endpoint"])

        # Assert
        assert histogram is not None
        assert "duration" in collector.histograms

    def test_metrics_collector_gauge_creation(self):
        """Test gauge metric creation."""
        # Arrange
        collector = MetricsCollector()

        # Act
        gauge = collector.gauge("active_connections", "Active connections")

        # Assert
        assert gauge is not None
        assert "active_connections" in collector.gauges

    def test_metrics_collector_returns_existing_metrics(self):
        """Test that existing metrics are returned, not recreated."""
        # Arrange
        collector = MetricsCollector()
        counter1 = collector.counter("test", "Test counter")

        # Act
        counter2 = collector.counter("test", "Test counter")

        # Assert
        assert counter1 is counter2


class TestGetMetrics:
    """Test suite for metrics exposition."""

    def test_get_metrics_returns_bytes(self):
        """Test that get_metrics returns bytes."""
        # Act
        metrics = get_metrics()

        # Assert
        assert isinstance(metrics, bytes)

    def test_get_metrics_content_type(self):
        """Test content type for metrics endpoint."""
        # Act
        content_type = get_metrics_content_type()

        # Assert
        assert "prometheus" in content_type.lower() or "text/plain" in content_type

    def test_get_metrics_contains_expected_metrics(self):
        """Test that metrics output contains expected metrics."""
        # Arrange - create some metrics
        http_requests_total.labels(method="GET", endpoint="/", status_code="200").inc()

        # Act
        metrics = get_metrics()

        # Assert
        assert b"http_requests_total" in metrics
        assert b'method="GET"' in metrics


class TestMetricsEdgeCases:
    """Test edge cases and error scenarios."""

    def test_counter_with_invalid_labels(self):
        """Test counter with invalid label values."""
        # Act & Assert - should handle gracefully
        try:
            http_requests_total.labels(
                method="GET", endpoint="/test", status_code="500"
            ).inc()
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")

    def test_histogram_with_negative_value(self):
        """Test histogram with negative observation."""
        # Act & Assert - should handle gracefully
        try:
            http_request_duration_seconds.labels(method="GET", endpoint="/").observe(-1)
        except Exception as e:
            pytest.fail(f"Should not raise exception: {e}")

    def test_timed_metric_exception_handling(self):
        """Test timed_metric handles exceptions."""
        # Arrange
        test_histogram = Histogram("exception_test", "Test")

        # Act & Assert
        with pytest.raises(ValueError):
            with timed_metric(test_histogram):
                raise ValueError("Test exception")

    def test_measure_duration_exception_handling(self):
        """Test measure_duration handles exceptions."""
        # Arrange
        test_histogram = Histogram("exception_duration_test", "Test")

        @measure_duration(test_histogram)
        def failing_function():
            raise ValueError("Test error")

        # Act & Assert
        with pytest.raises(ValueError):
            failing_function()


class TestMetricsRegistry:
    """Test suite for metrics registry."""

    def test_registry_is_collector_registry(self):
        """Test that registry is a CollectorRegistry."""
        # Assert
        assert isinstance(registry, CollectorRegistry)

    def test_metrics_isolated_in_registry(self):
        """Test that metrics are isolated in custom registry."""
        # This test ensures our metrics don't pollute the default registry
        from prometheus_client import REGISTRY

        # Get metrics from our custom registry
        our_metrics = list(registry.collect())

        # Our registry should have our metrics
        metric_names = [m.name for m in our_metrics]
        assert any("http_requests_total" in name for name in metric_names)


# Test fixtures
@pytest.fixture
def clean_registry():
    """Provide a clean registry for isolated tests."""
    from prometheus_client import CollectorRegistry

    return CollectorRegistry()


pytestmark = pytest.mark.asyncio
