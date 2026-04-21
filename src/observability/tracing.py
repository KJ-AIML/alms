"""
OpenTelemetry tracing configuration for distributed tracing.

This module provides automatic instrumentation for:
- HTTP requests
- Database queries
- External service calls
- Custom spans

Usage:
    from src.observability.tracing import tracer, trace_span

    @trace_span("my_operation")
    async def my_function():
        with tracer.start_as_current_span("child_operation"):
            pass
"""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

from src.config.settings import settings
from src.config.logs_config import get_logger

logger = get_logger(__name__)

# Global tracer provider
_tracer_provider: Optional[TracerProvider] = None


def setup_tracing(
    service_name: str = settings.SERVICE_NAME,
    service_version: str = settings.APP_VERSION,
    otlp_endpoint: Optional[str] = None,
    console_export: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        service_version: Version of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://localhost:4317")
        console_export: Also export traces to console (for debugging)

    Returns:
        TracerProvider instance
    """
    global _tracer_provider

    if _tracer_provider is not None:
        logger.warning("Tracing already initialized")
        return _tracer_provider

    # Create resource
    resource = Resource.create(
        {
            SERVICE_NAME: service_name,
            SERVICE_VERSION: service_version,
            "deployment.environment": "production"
            if settings.is_production
            else "development",
        }
    )

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint provided
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info(f"OTLP tracing exporter configured: {otlp_endpoint}")

    # Add console exporter for debugging
    if console_export or settings.DEBUG:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))
        logger.info("Console tracing exporter configured")

    # Set global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Instrument libraries
    SQLAlchemyInstrumentor().instrument()
    RedisInstrumentor().instrument()

    logger.info(f"Tracing initialized for service: {service_name}")
    return _tracer_provider


def instrument_fastapi(app):
    """Instrument FastAPI application for tracing."""
    FastAPIInstrumentor.instrument_app(app)
    logger.info("FastAPI instrumented for tracing")


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get a tracer instance."""
    return trace.get_tracer(name)


# Global tracer for convenience
tracer = get_tracer()


@contextmanager
def trace_span(name: str, attributes: Optional[dict] = None):
    """
    Context manager for creating a trace span.

    Usage:
        with trace_span("database_query", {"table": "users"}):
            result = await db.execute(query)
    """
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def trace_function(name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator to trace function execution.

    Usage:
        @trace_function("process_payment")
        async def process_payment(order_id: str):
            pass
    """

    def decorator(func: Callable) -> Callable:
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                # Add function arguments as attributes
                if args:
                    span.set_attribute("args.count", len(args))
                if kwargs:
                    span.set_attribute("kwargs.keys", list(kwargs.keys()))

                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)

                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.record_exception(e)
                    raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


import asyncio  # noqa: E402
