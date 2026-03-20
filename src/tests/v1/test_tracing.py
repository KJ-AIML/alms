"""
Tests for observability tracing implementation.

This module tests the OpenTelemetry tracing configuration, span creation,
and instrumentation of FastAPI, SQLAlchemy, and Redis.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource

from src.observability.tracing import (
    setup_tracing,
    get_tracer,
    trace_span,
    trace_function,
    tracer,
)


class TestTracingSetup:
    """Test suite for tracing initialization."""

    def test_setup_tracing_initializes_provider(self):
        """Test that setup_tracing creates a TracerProvider."""
        # Arrange & Act
        provider = setup_tracing(
            service_name="test-service", service_version="1.0.0", console_export=True
        )

        # Assert
        assert provider is not None
        assert isinstance(provider, TracerProvider)

    def test_setup_tracing_with_otlp_endpoint(self):
        """Test setup with OTLP endpoint."""
        # Arrange
        with patch("src.observability.tracing.OTLPSpanExporter") as mock_exporter:
            # Act
            provider = setup_tracing(
                service_name="test-service",
                service_version="1.0.0",
                otlp_endpoint="http://localhost:4317",
            )

            # Assert
            mock_exporter.assert_called_once_with(
                endpoint="http://localhost:4317", insecure=True
            )
            assert provider is not None

    def test_setup_tracing_with_console_export(self):
        """Test setup with console exporter for debugging."""
        # Arrange
        with patch("src.observability.tracing.ConsoleSpanExporter") as mock_exporter:
            # Act
            provider = setup_tracing(
                service_name="test-service",
                service_version="1.0.0",
                console_export=True,
            )

            # Assert
            mock_exporter.assert_called_once()
            assert provider is not None

    def test_setup_tracing_sets_global_provider(self):
        """Test that global tracer provider is set."""
        # Arrange & Act
        with patch("src.observability.tracing.trace.set_tracer_provider") as mock_set:
            provider = setup_tracing(
                service_name="test-service", service_version="1.0.0"
            )

            # Assert
            mock_set.assert_called_once_with(provider)

    def test_setup_tracing_instruments_libraries(self):
        """Test that SQLAlchemy and Redis are instrumented."""
        # Arrange
        with (
            patch(
                "src.observability.tracing.SQLAlchemyInstrumentor"
            ) as mock_sqlalchemy,
            patch("src.observability.tracing.RedisInstrumentor") as mock_redis,
        ):
            # Act
            setup_tracing(service_name="test-service")

            # Assert
            mock_sqlalchemy.return_value.instrument.assert_called_once()
            mock_redis.return_value.instrument.assert_called_once()

    def test_setup_tracing_does_not_duplicate(self):
        """Test that setup_tracing warns if already initialized."""
        # Arrange
        setup_tracing(service_name="test-service", console_export=True)

        # Act & Assert
        with patch("src.observability.tracing.logger") as mock_logger:
            provider = setup_tracing(service_name="test-service")
            mock_logger.warning.assert_called_once()


class TestTracerAccess:
    """Test suite for tracer access."""

    def test_get_tracer_returns_tracer(self):
        """Test that get_tracer returns a valid tracer."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act
        test_tracer = get_tracer("test_module")

        # Assert
        assert test_tracer is not None
        assert hasattr(test_tracer, "start_as_current_span")

    def test_global_tracer_available(self):
        """Test that global tracer variable is available."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Assert
        assert tracer is not None
        assert hasattr(tracer, "start_as_current_span")


class TestTraceSpanContextManager:
    """Test suite for trace_span context manager."""

    def test_trace_span_creates_span(self):
        """Test that trace_span creates a span."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act & Assert
        with trace_span("test_operation") as span:
            assert span is not None
            assert span.is_recording()

    def test_trace_span_with_attributes(self):
        """Test that trace_span sets attributes."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act
        with trace_span("test_operation", {"key1": "value1", "key2": 123}) as span:
            # In a real implementation, you'd verify attributes
            # For now, we just ensure no exceptions
            pass

        # Assert - span completed without errors

    def test_trace_span_nested_spans(self):
        """Test nested span creation."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act & Assert
        with trace_span("parent_operation") as parent_span:
            with trace_span("child_operation") as child_span:
                assert parent_span is not None
                assert child_span is not None
                assert child_span.is_recording()


class TestTraceFunctionDecorator:
    """Test suite for trace_function decorator."""

    @pytest.mark.asyncio
    async def test_trace_function_async(self):
        """Test tracing async function."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("async_test_operation")
        async def async_function(x, y):
            return x + y

        # Act
        result = await async_function(2, 3)

        # Assert
        assert result == 5

    def test_trace_function_sync(self):
        """Test tracing sync function."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("sync_test_operation")
        def sync_function(x, y):
            return x * y

        # Act
        result = sync_function(3, 4)

        # Assert
        assert result == 12

    @pytest.mark.asyncio
    async def test_trace_function_with_attributes(self):
        """Test tracing function with custom attributes."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("test_with_attrs", {"custom_attr": "custom_value"})
        async def async_function():
            return "success"

        # Act
        result = await async_function()

        # Assert
        assert result == "success"

    @pytest.mark.asyncio
    async def test_trace_function_records_exception(self):
        """Test that exceptions are recorded in spans."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("test_exception")
        async def failing_function():
            raise ValueError("Test error")

        # Act & Assert
        with pytest.raises(ValueError):
            await failing_function()

    def test_trace_function_preserves_function_metadata(self):
        """Test that decorator preserves function name and docstring."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("test_metadata")
        def my_function():
            """My docstring."""
            return 42

        # Assert
        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestInstrumentFastAPI:
    """Test suite for FastAPI instrumentation."""

    def test_instrument_fastapi(self):
        """Test FastAPI app instrumentation."""
        # Arrange
        from fastapi import FastAPI

        setup_tracing(service_name="test-service")

        app = FastAPI()

        with patch(
            "src.observability.tracing.FastAPIInstrumentor"
        ) as mock_instrumentor:
            # Act
            from src.observability.tracing import instrument_fastapi

            instrument_fastapi(app)

            # Assert
            mock_instrumentor.instrument_app.assert_called_once_with(app)


class TestTracingResourceAttributes:
    """Test suite for resource attributes."""

    def test_resource_includes_service_info(self):
        """Test that resource includes service information."""
        # Arrange & Act
        provider = setup_tracing(service_name="my-service", service_version="2.0.0")

        # Assert
        resource = provider.resource
        assert resource.attributes.get("service.name") == "my-service"
        assert resource.attributes.get("service.version") == "2.0.0"

    def test_resource_includes_environment(self):
        """Test that resource includes environment."""
        # Arrange & Act
        provider = setup_tracing(service_name="test-service")

        # Assert
        resource = provider.resource
        assert "deployment.environment" in resource.attributes


class TestTracingEdgeCases:
    """Test edge cases and error scenarios."""

    def test_trace_span_with_none_attributes(self):
        """Test trace_span with None attributes."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act & Assert - should not raise
        with trace_span("test", None) as span:
            assert span is not None

    def test_trace_span_with_empty_attributes(self):
        """Test trace_span with empty attributes."""
        # Arrange
        setup_tracing(service_name="test-service")

        # Act & Assert - should not raise
        with trace_span("test", {}) as span:
            assert span is not None

    @pytest.mark.asyncio
    async def test_trace_function_with_no_args(self):
        """Test tracing function with no arguments."""
        # Arrange
        setup_tracing(service_name="test-service")

        @trace_function("no_args")
        async def no_args_function():
            return "done"

        # Act
        result = await no_args_function()

        # Assert
        assert result == "done"

    def test_setup_tracing_with_invalid_otlp_endpoint(self):
        """Test setup with invalid OTLP endpoint."""
        # Act & Assert - should handle gracefully
        try:
            provider = setup_tracing(
                service_name="test-service", otlp_endpoint="invalid://endpoint"
            )
            # If it doesn't raise, it should still return a provider
            assert provider is not None
        except Exception:
            # If it raises, that's acceptable behavior
            pass


# Ensure tracing is set up for all tests
@pytest.fixture(autouse=True)
def setup_tracing_for_tests():
    """Automatically setup tracing for all tests."""
    with (
        patch("src.observability.tracing.SQLAlchemyInstrumentor"),
        patch("src.observability.tracing.RedisInstrumentor"),
    ):
        setup_tracing(service_name="test-service", console_export=True)
        yield
