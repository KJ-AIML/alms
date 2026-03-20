"""
Tests for Prometheus metrics implementation.

Tests verify metrics infrastructure is properly set up.
"""

import pytest


class TestMetricsSetup:
    """Test suite for metrics initialization."""

    def test_setup_metrics_exists(self):
        """Test that setup_metrics function exists."""
        from src.observability.metrics import setup_metrics

        assert setup_metrics is not None

    def test_get_metrics_exists(self):
        """Test that get_metrics function exists."""
        from src.observability.metrics import get_metrics

        assert get_metrics is not None

    def test_get_metrics_content_type_exists(self):
        """Test that get_metrics_content_type function exists."""
        from src.observability.metrics import get_metrics_content_type

        assert get_metrics_content_type is not None


class TestMetricsExports:
    """Test that all metrics exports are available."""

    def test_all_metric_variables_exist(self):
        """Test that all expected metric variables are present."""
        from src.observability.metrics import (
            http_requests_total,
            http_request_duration_seconds,
            db_queries_total,
            db_query_duration_seconds,
            ai_requests_total,
            ai_request_duration_seconds,
            agent_executions_total,
            agent_execution_duration_seconds,
        )

        assert http_requests_total is not None
        assert http_request_duration_seconds is not None
        assert db_queries_total is not None
        assert db_query_duration_seconds is not None
        assert ai_requests_total is not None
        assert ai_request_duration_seconds is not None
        assert agent_executions_total is not None
        assert agent_execution_duration_seconds is not None


class TestMetricsCollector:
    """Test suite for MetricsCollector."""

    def test_metrics_collector_exists(self):
        """Test that MetricsCollector class exists."""
        from src.observability.metrics import MetricsCollector

        assert MetricsCollector is not None

    def test_metrics_collector_can_be_instantiated(self):
        """Test that MetricsCollector can be created."""
        from src.observability.metrics import MetricsCollector

        collector = MetricsCollector(prefix="test")
        assert collector is not None
        assert collector.prefix == "test"


class TestTimedMetric:
    """Test suite for timed_metric context manager."""

    def test_timed_metric_exists(self):
        """Test that timed_metric is importable."""
        from src.observability.metrics import timed_metric

        assert timed_metric is not None


class TestMeasureDuration:
    """Test suite for measure_duration decorator."""

    def test_measure_duration_exists(self):
        """Test that measure_duration is importable."""
        from src.observability.metrics import measure_duration

        assert measure_duration is not None


pytestmark = pytest.mark.unit
