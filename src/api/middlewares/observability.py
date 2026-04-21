"""
Observability middleware for FastAPI.

This middleware automatically:
- Traces HTTP requests
- Records Prometheus metrics
- Adds request IDs for correlation
"""

import time
import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config.logs_config import get_logger
from src.config.settings import settings
from src.observability.metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    http_response_size_bytes,
)
from src.observability.tracing import tracer

logger = get_logger(__name__)


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect metrics and traces for all HTTP requests.

    Features:
    - Request/response timing
    - Request/response size tracking
    - Status code tracking
    - Distributed tracing via OpenTelemetry
    - Request ID injection for correlation
    """

    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/metrics",
            "/docs",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next):
        # Skip observability for excluded paths
        path = request.url.path
        if path.startswith(f"{settings.API_PREFIX}/v1/health") or any(
            path.startswith(excluded) for excluded in self.exclude_paths
        ):
            return await call_next(request)

        # Generate or get request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        # Start timing
        start_time = time.time()

        # Get request info
        method = request.method
        endpoint = self._get_endpoint_name(request)

        # Estimate request size
        content_length = request.headers.get("content-length", "0")
        request_size = int(content_length) if content_length.isdigit() else 0

        # Create span for tracing
        with tracer.start_as_current_span(
            f"{method} {path}",
            attributes={
                "http.method": method,
                "http.url": str(request.url),
                "http.path": path,
                "http.request_id": request_id,
                "http.target": endpoint,
            },
        ) as span:
            try:
                # Process request
                response = await call_next(request)

                # Calculate duration
                duration = time.time() - start_time
                status_code = response.status_code

                # Update span with response info
                span.set_attribute("http.status_code", status_code)
                span.set_attribute("http.duration", duration)
                span.set_attribute("http.success", 200 <= status_code < 400)

                # Add request ID to response
                response.headers["X-Request-ID"] = request_id

                # Estimate response size
                response_size = len(response.body) if hasattr(response, "body") else 0

                # Record metrics
                self._record_metrics(
                    method=method,
                    endpoint=endpoint,
                    status_code=status_code,
                    duration=duration,
                    request_size=request_size,
                    response_size=response_size,
                )

                return response

            except Exception as e:
                # Calculate duration even on error
                duration = time.time() - start_time

                # Record span error
                span.set_attribute("error", True)
                span.set_attribute("error.type", type(e).__name__)
                span.set_attribute("error.message", str(e))
                span.record_exception(e)

                # Record error metrics
                self._record_metrics(
                    method=method,
                    endpoint=endpoint,
                    status_code=500,
                    duration=duration,
                    request_size=request_size,
                    response_size=0,
                )

                raise

    def _get_endpoint_name(self, request: Request) -> str:
        """Get a normalized endpoint name for metrics."""
        # Try to get the route name
        if hasattr(request.state, "route") and request.state.route:
            route = request.state.route
            if hasattr(route, "name") and route.name:
                return route.name
            if hasattr(route, "path"):
                return route.path

        # Fallback to path with normalized IDs
        path = request.url.path
        # Replace UUIDs and numeric IDs with placeholders
        import re

        path = re.sub(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            "{id}",
            path,
        )
        path = re.sub(r"/\d+", "/{id}", path)
        return path

    def _record_metrics(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: int,
        response_size: int,
    ):
        """Record all metrics for the request."""
        status = str(status_code)

        # Increment request counter
        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status
        ).inc()

        # Record duration
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )

        # Record sizes
        http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(
            request_size
        )

        http_response_size_bytes.labels(method=method, endpoint=endpoint).observe(
            response_size
        )


class DatabaseMetricsMiddleware:
    """
    Middleware to track database metrics (used in repository layer).
    This is not a Starlette middleware but a helper class.
    """

    @staticmethod
    def record_query(operation: str, table: str, duration: float):
        """Record database query metrics."""
        from src.observability.metrics import (
            db_queries_total,
            db_query_duration_seconds,
        )

        db_queries_total.labels(operation=operation, table=table).inc()

        db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )


class CacheMetricsMiddleware:
    """
    Middleware to track cache metrics.
    """

    @staticmethod
    def record_hit(cache_name: str):
        """Record a cache hit."""
        from src.observability.metrics import cache_hits_total

        cache_hits_total.labels(cache_name=cache_name).inc()

    @staticmethod
    def record_miss(cache_name: str):
        """Record a cache miss."""
        from src.observability.metrics import cache_misses_total

        cache_misses_total.labels(cache_name=cache_name).inc()


class AIMetricsMiddleware:
    """
    Middleware to track AI/LLM operation metrics.
    """

    @staticmethod
    def record_request(
        model: str,
        provider: str,
        duration: float,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
    ):
        """Record an AI request."""
        from src.observability.metrics import (
            ai_requests_total,
            ai_request_duration_seconds,
            ai_tokens_total,
        )

        ai_requests_total.labels(model=model, provider=provider).inc()

        ai_request_duration_seconds.labels(model=model, provider=provider).observe(
            duration
        )

        if tokens_prompt > 0:
            ai_tokens_total.labels(model=model, type="prompt").inc(tokens_prompt)

        if tokens_completion > 0:
            ai_tokens_total.labels(model=model, type="completion").inc(
                tokens_completion
            )

    @staticmethod
    def record_error(model: str, error_type: str):
        """Record an AI error."""
        from src.observability.metrics import ai_errors_total

        ai_errors_total.labels(model=model, error_type=error_type).inc()


class AgentMetricsMiddleware:
    """
    Middleware to track agent execution metrics.
    """

    @staticmethod
    def record_execution(agent_name: str, duration: float, status: str = "success"):
        """Record agent execution."""
        from src.observability.metrics import (
            agent_executions_total,
            agent_execution_duration_seconds,
        )

        agent_executions_total.labels(agent_name=agent_name, status=status).inc()

        agent_execution_duration_seconds.labels(agent_name=agent_name).observe(duration)

    @staticmethod
    def record_tool_usage(agent_name: str, tool_name: str):
        """Record agent tool usage."""
        from src.observability.metrics import agent_tools_used_total

        agent_tools_used_total.labels(agent_name=agent_name, tool_name=tool_name).inc()


class UsecaseMetricsMiddleware:
    """
    Middleware to track usecase execution metrics.
    """

    @staticmethod
    def record_execution(usecase_name: str, duration: float, status: str = "success"):
        """Record usecase execution."""
        from src.observability.metrics import (
            usecase_executions_total,
            usecase_duration_seconds,
        )

        usecase_executions_total.labels(usecase=usecase_name, status=status).inc()

        usecase_duration_seconds.labels(usecase=usecase_name).observe(duration)
