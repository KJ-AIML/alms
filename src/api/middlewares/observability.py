"""Observability middleware for FastAPI.

Optional observability imports are guarded so the module can be imported
when observability dependencies are not installed. When deps are missing
the middleware class is still defined but metric/tracing helpers are no-ops.
"""

import time
import uuid
from typing import Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.config.logs_config import get_logger
from src.config.settings import settings

logger = get_logger(__name__)

# --- Optional observability imports ---
try:
    from src.observability.metrics import (
        http_requests_total,
        http_request_duration_seconds,
        http_request_size_bytes,
        http_response_size_bytes,
    )
    _metrics_available = True
except ImportError:  # pragma: no cover
    _metrics_available = False

try:
    from src.observability.tracing import tracer
    _tracing_available = True
except ImportError:  # pragma: no cover
    _tracing_available = False
    tracer = None  # type: ignore[assignment]


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """Middleware to collect metrics and traces for HTTP requests."""

    def __init__(self, app: ASGIApp, exclude_paths: Optional[list] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/metrics",
            "/docs",
            "/openapi.json",
        ]

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(f"{settings.API_PREFIX}/v1/health") or any(
            path.startswith(excluded) for excluded in self.exclude_paths
        ):
            return await call_next(request)

        # Reuse request_id set by LoggingMiddleware (single source of truth).
        # Only generate a new one if no middleware upstream has set it yet.
        request_id = getattr(request.state, "request_id", None)
        if not request_id:
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            request.state.request_id = request_id
        start_time = time.time()
        method = request.method
        endpoint = self._get_endpoint_name(request)
        content_length = request.headers.get("content-length", "0")
        request_size = int(content_length) if content_length.isdigit() else 0

        span_ctx = (
            tracer.start_as_current_span(
                f"{method} {path}",
                attributes={
                    "http.method": method,
                    "http.url": str(request.url),
                    "http.path": path,
                    "http.request_id": request_id,
                    "http.target": endpoint,
                },
            )
            if _tracing_available
            else _null_context()
        )

        with span_ctx as span:
            try:
                response = await call_next(request)
                duration = time.time() - start_time
                status_code = response.status_code

                if _tracing_available:
                    span.set_attribute("http.status_code", status_code)
                    span.set_attribute("http.duration", duration)
                    span.set_attribute("http.success", 200 <= status_code < 400)

                response.headers["X-Request-ID"] = request_id
                response_size = len(response.body) if hasattr(response, "body") else 0

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
                duration = time.time() - start_time
                if _tracing_available:
                    span.set_attribute("error", True)
                    span.set_attribute("error.type", type(e).__name__)
                    span.set_attribute("error.message", str(e))
                    span.record_exception(e)
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
        if hasattr(request.state, "route") and request.state.route:
            route = request.state.route
            if hasattr(route, "name") and route.name:
                return route.name
            if hasattr(route, "path"):
                return route.path
        path = request.url.path
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
        if not _metrics_available:
            return
        status = str(status_code)
        http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status
        ).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(
            duration
        )
        http_request_size_bytes.labels(method=method, endpoint=endpoint).observe(
            request_size
        )
        http_response_size_bytes.labels(method=method, endpoint=endpoint).observe(
            response_size
        )


def _null_context():
    """Return a no-op context manager when tracing is unavailable."""
    from contextlib import nullcontext
    return nullcontext()


class DatabaseMetricsMiddleware:
    """Middleware to track database metrics (used in repository layer)."""

    @staticmethod
    def record_query(operation: str, table: str, duration: float):
        if not _metrics_available:
            return
        from src.observability.metrics import db_queries_total, db_query_duration_seconds
        db_queries_total.labels(operation=operation, table=table).inc()
        db_query_duration_seconds.labels(operation=operation, table=table).observe(duration)


class CacheMetricsMiddleware:
    """Middleware to track cache metrics."""

    @staticmethod
    def record_hit(cache_name: str):
        if not _metrics_available:
            return
        from src.observability.metrics import cache_hits_total
        cache_hits_total.labels(cache_name=cache_name).inc()

    @staticmethod
    def record_miss(cache_name: str):
        if not _metrics_available:
            return
        from src.observability.metrics import cache_misses_total
        cache_misses_total.labels(cache_name=cache_name).inc()


class AIMetricsMiddleware:
    """Middleware to track AI/LLM operation metrics."""

    @staticmethod
    def record_request(
        model: str, provider: str, duration: float,
        tokens_prompt: int = 0, tokens_completion: int = 0,
    ):
        if not _metrics_available:
            return
        from src.observability.metrics import (
            ai_requests_total, ai_request_duration_seconds, ai_tokens_total,
        )
        ai_requests_total.labels(model=model, provider=provider).inc()
        ai_request_duration_seconds.labels(model=model, provider=provider).observe(duration)
        if tokens_prompt > 0:
            ai_tokens_total.labels(model=model, type="prompt").inc(tokens_prompt)
        if tokens_completion > 0:
            ai_tokens_total.labels(model=model, type="completion").inc(tokens_completion)

    @staticmethod
    def record_error(model: str, error_type: str):
        if not _metrics_available:
            return
        from src.observability.metrics import ai_errors_total
        ai_errors_total.labels(model=model, error_type=error_type).inc()


class AgentMetricsMiddleware:
    """Middleware to track agent execution metrics."""

    @staticmethod
    def record_execution(agent_name: str, duration: float, status: str = "success"):
        if not _metrics_available:
            return
        from src.observability.metrics import (
            agent_executions_total, agent_execution_duration_seconds,
        )
        agent_executions_total.labels(agent_name=agent_name, status=status).inc()
        agent_execution_duration_seconds.labels(agent_name=agent_name).observe(duration)

    @staticmethod
    def record_tool_usage(agent_name: str, tool_name: str):
        if not _metrics_available:
            return
        from src.observability.metrics import agent_tools_used_total
        agent_tools_used_total.labels(agent_name=agent_name, tool_name=tool_name).inc()


class UsecaseMetricsMiddleware:
    """Middleware to track usecase execution metrics."""

    @staticmethod
    def record_execution(usecase_name: str, duration: float, status: str = "success"):
        if not _metrics_available:
            return
        from src.observability.metrics import (
            usecase_executions_total, usecase_duration_seconds,
        )
        usecase_executions_total.labels(usecase=usecase_name, status=status).inc()
        usecase_duration_seconds.labels(usecase=usecase_name).observe(duration)