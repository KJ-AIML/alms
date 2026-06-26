"""
Prometheus metrics configuration for application monitoring.

This module provides:
- Request duration histograms
- Request/response counters
- Custom business metrics
- Database query metrics
- AI/LLM operation metrics

Usage:
    from src.observability.metrics import request_duration, ai_requests_total

    with request_duration.time():
        await process_request()

    ai_requests_total.labels(model="gpt-4").inc()
"""

from contextlib import contextmanager
from functools import wraps
from time import time
from typing import Callable, Optional

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.openmetrics.exposition import generate_latest

from src.config.logs_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# Create a custom registry
registry = CollectorRegistry()

# Service info
service_info = Info("app_info", "Application information", registry=registry)

# HTTP Request metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=registry,
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=registry,
)

# Database metrics
db_queries_total = Counter(
    "db_queries_total",
    "Total database queries",
    ["operation", "table"],
    registry=registry,
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["operation", "table"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

db_connections_active = Gauge(
    "db_connections_active", "Number of active database connections", registry=registry
)

# AI/LLM metrics
ai_requests_total = Counter(
    "ai_requests_total",
    "Total AI/LLM requests",
    ["model", "provider"],
    registry=registry,
)

ai_request_duration_seconds = Histogram(
    "ai_request_duration_seconds",
    "AI/LLM request duration in seconds",
    ["model", "provider"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)

ai_tokens_total = Counter(
    "ai_tokens_total",
    "Total tokens used",
    ["model", "type"],  # type: prompt, completion
    registry=registry,
)

ai_errors_total = Counter(
    "ai_errors_total", "Total AI errors", ["model", "error_type"], registry=registry
)

# Business metrics
usecase_executions_total = Counter(
    "usecase_executions_total",
    "Total usecase executions",
    ["usecase", "status"],
    registry=registry,
)

usecase_duration_seconds = Histogram(
    "usecase_duration_seconds",
    "Usecase execution duration",
    ["usecase"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# Cache metrics
cache_hits_total = Counter(
    "cache_hits_total", "Total cache hits", ["cache_name"], registry=registry
)

cache_misses_total = Counter(
    "cache_misses_total", "Total cache misses", ["cache_name"], registry=registry
)

cache_operation_duration_seconds = Histogram(
    "cache_operation_duration_seconds",
    "Cache operation duration",
    ["operation"],  # get, set, delete
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05],
    registry=registry,
)

# Agent metrics
agent_executions_total = Counter(
    "agent_executions_total",
    "Total agent executions",
    ["agent_name", "status"],
    registry=registry,
)

agent_execution_duration_seconds = Histogram(
    "agent_execution_duration_seconds",
    "Agent execution duration",
    ["agent_name"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
    registry=registry,
)

agent_tools_used_total = Counter(
    "agent_tools_used_total",
    "Total agent tool usages",
    ["agent_name", "tool_name"],
    registry=registry,
)


def setup_metrics(
    service_name: str = settings.SERVICE_NAME,
    service_version: str = settings.APP_VERSION,
):
    """Initialize metrics with service information."""
    service_info.info(
        {
            "name": service_name,
            "version": service_version,
            "python_version": "3.13+",
        }
    )
    logger.info(f"Metrics initialized for service: {service_name}")


def get_metrics():
    """Get current metrics in Prometheus format."""
    return generate_latest(registry)


def get_metrics_content_type():
    """Get content type for metrics endpoint."""
    return CONTENT_TYPE_LATEST


@contextmanager
def timed_metric(metric: Histogram, labels: Optional[dict] = None):
    """
    Context manager to time operations and record to histogram.

    Usage:
        with timed_metric(db_query_duration_seconds, {"operation": "select", "table": "users"}):
            result = await db.execute(query)
    """
    start = time()
    try:
        yield
    finally:
        duration = time() - start
        if labels:
            metric.labels(**labels).observe(duration)
        else:
            metric.observe(duration)


def measure_duration(metric: Histogram, labels: Optional[dict] = None):
    """
    Decorator to measure function execution duration.

    Usage:
        @measure_duration(ai_request_duration_seconds, {"model": "gpt-4"})
        async def call_llm(prompt: str):
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        import asyncio

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


class MetricsCollector:
    """
    Helper class to collect and report custom metrics.
    """

    def __init__(self, prefix: str = ""):
        self.prefix = prefix
        self.counters = {}
        self.histograms = {}
        self.gauges = {}

    def counter(self, name: str, description: str, labels: list = None):
        """Create or get a counter metric."""
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        if full_name not in self.counters:
            self.counters[full_name] = Counter(
                full_name, description, labels or [], registry=registry
            )
        return self.counters[full_name]

    def histogram(
        self, name: str, description: str, labels: list = None, buckets: list = None
    ):
        """Create or get a histogram metric."""
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        if full_name not in self.histograms:
            self.histograms[full_name] = Histogram(
                full_name,
                description,
                labels or [],
                buckets=buckets or [0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
                registry=registry,
            )
        return self.histograms[full_name]

    def gauge(self, name: str, description: str, labels: list = None):
        """Create or get a gauge metric."""
        full_name = f"{self.prefix}_{name}" if self.prefix else name
        if full_name not in self.gauges:
            self.gauges[full_name] = Gauge(
                full_name, description, labels or [], registry=registry
            )
        return self.gauges[full_name]
