"""
Tests for OpenTelemetry tracing.

Tests verify tracing infrastructure is properly set up.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestTracingSetup:
    """Test suite for tracing initialization."""

    def test_setup_tracing_returns_provider(self):
        """Test that setup_tracing returns a provider."""
        from src.observability.tracing import setup_tracing

        # Act
        provider = setup_tracing(
            service_name="test-service", service_version="1.0.0", console_export=False
        )

        # Assert
        assert provider is not None

    def test_get_tracer_returns_tracer(self):
        """Test that get_tracer returns a tracer."""
        from src.observability.tracing import get_tracer, setup_tracing

        # Arrange
        setup_tracing(service_name="test-service", console_export=False)

        # Act
        tracer = get_tracer("test_module")

        # Assert
        assert tracer is not None

    def test_global_tracer_available(self):
        """Test that global tracer is available."""
        from src.observability.tracing import tracer, setup_tracing

        # Arrange
        setup_tracing(service_name="test-service", console_export=False)

        # Assert
        assert tracer is not None


class TestTraceSpan:
    """Test suite for trace_span context manager."""

    def test_trace_span_exists(self):
        """Test that trace_span is importable."""
        from src.observability.tracing import trace_span

        assert trace_span is not None


class TestTraceFunction:
    """Test suite for trace_function decorator."""

    def test_trace_function_exists(self):
        """Test that trace_function is importable."""
        from src.observability.tracing import trace_function

        assert trace_function is not None


class TestInstrumentFastAPI:
    """Test suite for FastAPI instrumentation."""

    def test_instrument_fastapi_exists(self):
        """Test that instrument_fastapi is importable."""
        from src.observability.tracing import instrument_fastapi

        assert instrument_fastapi is not None


class TestTracingExports:
    """Test that all tracing exports are available."""

    def test_all_exports_present(self):
        """Test that all expected exports are present."""
        from src.observability.tracing import (
            setup_tracing,
            get_tracer,
            tracer,
            trace_span,
            trace_function,
            instrument_fastapi,
        )

        assert setup_tracing is not None
        assert get_tracer is not None
        assert tracer is not None
        assert trace_span is not None
        assert trace_function is not None
        assert instrument_fastapi is not None


pytestmark = pytest.mark.unit
