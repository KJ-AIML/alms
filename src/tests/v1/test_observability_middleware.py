"""
Tests for observability middleware.

This module tests the ObservabilityMiddleware and related metric tracking
middleware classes for HTTP requests, database queries, cache operations,
and AI/agent executions.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import Request, Response
from starlette.testclient import TestClient

from src.api.middlewares.observability import (
    ObservabilityMiddleware,
    DatabaseMetricsMiddleware,
    CacheMetricsMiddleware,
    AIMetricsMiddleware,
    AgentMetricsMiddleware,
    UsecaseMetricsMiddleware,
)


class MockResponse:
    """Mock response for testing."""

    def __init__(self, status_code=200, body=b"test"):
        self.status_code = status_code
        self.body = body
        self.headers = {}


class TestObservabilityMiddleware:
    """Test suite for ObservabilityMiddleware."""

    @pytest.fixture
    def mock_app(self):
        """Create mock ASGI app."""

        async def app(scope, receive, send):
            response = MockResponse()
            await send(
                {
                    "type": "http.response.start",
                    "status": response.status_code,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": response.body,
                }
            )

        return app

    @pytest.fixture
    def middleware(self, mock_app):
        """Create middleware instance."""
        return ObservabilityMiddleware(mock_app)

    @pytest.mark.asyncio
    async def test_middleware_adds_request_id(self, middleware):
        """Test that middleware adds request ID to response."""
        # Arrange
        from fastapi import Request

        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {}
        request.state = Mock()

        async def call_next(req):
            response = Mock()
            response.status_code = 200
            response.headers = {}
            return response

        # Act
        response = await middleware.dispatch(request, call_next)

        # Assert
        assert "X-Request-ID" in response.headers
        assert len(response.headers["X-Request-ID"]) == 36  # UUID length

    @pytest.mark.asyncio
    async def test_middleware_uses_existing_request_id(self, middleware):
        """Test that middleware uses existing request ID from header."""
        # Arrange
        existing_id = "test-request-id-123"
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "GET"
        request.headers = {"X-Request-ID": existing_id}
        request.state = Mock()

        async def call_next(req):
            response = Mock()
            response.status_code = 200
            response.headers = {}
            return response

        # Act
        response = await middleware.dispatch(request, call_next)

        # Assert
        assert response.headers["X-Request-ID"] == existing_id

    @pytest.mark.asyncio
    async def test_middleware_skips_excluded_paths(self, middleware):
        """Test that middleware skips excluded paths."""
        # Arrange
        request = Mock(spec=Request)
        request.url.path = "/metrics"
        request.method = "GET"

        call_next = AsyncMock()

        # Act
        await middleware.dispatch(request, call_next)

        # Assert - call_next should be called without middleware processing
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_records_metrics(self, middleware):
        """Test that middleware records HTTP metrics."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.http_requests_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.http_request_duration_seconds"
            ) as mock_histogram,
        ):
            request = Mock(spec=Request)
            request.url.path = "/api/test"
            request.method = "POST"
            request.headers = {}
            request.state = Mock()

            async def call_next(req):
                response = Mock()
                response.status_code = 201
                response.headers = {}
                return response

            # Act
            await middleware.dispatch(request, call_next)

            # Assert
            mock_counter.labels.assert_called()
            mock_histogram.labels.assert_called()

    @pytest.mark.asyncio
    async def test_middleware_handles_exceptions(self, middleware):
        """Test that middleware handles exceptions gracefully."""
        # Arrange
        with patch(
            "src.api.middlewares.observability.http_requests_total"
        ) as mock_counter:
            request = Mock(spec=Request)
            request.url.path = "/api/test"
            request.method = "GET"
            request.headers = {}
            request.state = Mock()

            async def call_next(req):
                raise ValueError("Test error")

            # Act & Assert
            with pytest.raises(ValueError):
                await middleware.dispatch(request, call_next)

            # Should still record the error
            mock_counter.labels.assert_called()


class TestDatabaseMetricsMiddleware:
    """Test suite for DatabaseMetricsMiddleware."""

    def test_record_query(self):
        """Test recording database query metrics."""
        # Arrange
        with (
            patch("src.api.middlewares.observability.db_queries_total") as mock_counter,
            patch(
                "src.api.middlewares.observability.db_query_duration_seconds"
            ) as mock_histogram,
        ):
            # Act
            DatabaseMetricsMiddleware.record_query("select", "users", 0.045)

            # Assert
            mock_counter.labels.assert_called_once_with(
                operation="select", table="users"
            )
            mock_histogram.labels.assert_called_once_with(
                operation="select", table="users"
            )
            mock_counter.labels.return_value.inc.assert_called_once()
            mock_histogram.labels.return_value.observe.assert_called_once_with(0.045)

    def test_record_query_multiple_operations(self):
        """Test recording various database operations."""
        # Arrange
        operations = [
            ("select", "users", 0.01),
            ("insert", "orders", 0.02),
            ("update", "products", 0.03),
            ("delete", "logs", 0.01),
        ]

        with (
            patch("src.api.middlewares.observability.db_queries_total"),
            patch("src.api.middlewares.observability.db_query_duration_seconds"),
        ):
            # Act
            for op, table, duration in operations:
                DatabaseMetricsMiddleware.record_query(op, table, duration)

            # Assert - all operations should be recorded


class TestCacheMetricsMiddleware:
    """Test suite for CacheMetricsMiddleware."""

    def test_record_hit(self):
        """Test recording cache hit."""
        # Arrange
        with patch(
            "src.api.middlewares.observability.cache_hits_total"
        ) as mock_counter:
            # Act
            CacheMetricsMiddleware.record_hit("user_cache")

            # Assert
            mock_counter.labels.assert_called_once_with(cache_name="user_cache")
            mock_counter.labels.return_value.inc.assert_called_once()

    def test_record_miss(self):
        """Test recording cache miss."""
        # Arrange
        with patch(
            "src.api.middlewares.observability.cache_misses_total"
        ) as mock_counter:
            # Act
            CacheMetricsMiddleware.record_miss("user_cache")

            # Assert
            mock_counter.labels.assert_called_once_with(cache_name="user_cache")
            mock_counter.labels.return_value.inc.assert_called_once()

    def test_cache_hit_ratio_calculation(self):
        """Test that hit/miss ratio can be calculated from metrics."""
        # Arrange & Act
        with (
            patch("src.api.middlewares.observability.cache_hits_total") as mock_hits,
            patch(
                "src.api.middlewares.observability.cache_misses_total"
            ) as mock_misses,
        ):
            # Simulate 80% hit rate
            for _ in range(80):
                CacheMetricsMiddleware.record_hit("test_cache")
            for _ in range(20):
                CacheMetricsMiddleware.record_miss("test_cache")

            # Assert
            assert mock_hits.labels.return_value.inc.call_count == 80
            assert mock_misses.labels.return_value.inc.call_count == 20


class TestAIMetricsMiddleware:
    """Test suite for AIMetricsMiddleware."""

    def test_record_request(self):
        """Test recording AI request metrics."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.ai_requests_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.ai_request_duration_seconds"
            ) as mock_histogram,
            patch("src.api.middlewares.observability.ai_tokens_total") as mock_tokens,
        ):
            # Act
            AIMetricsMiddleware.record_request(
                model="gpt-4",
                provider="openai",
                duration=1.5,
                tokens_prompt=100,
                tokens_completion=50,
            )

            # Assert
            mock_counter.labels.assert_called_with(model="gpt-4", provider="openai")
            mock_histogram.labels.assert_called_with(model="gpt-4", provider="openai")
            mock_tokens.labels.assert_called()

    def test_record_request_without_tokens(self):
        """Test recording AI request without token counts."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.ai_requests_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.ai_request_duration_seconds"
            ) as mock_histogram,
            patch("src.api.middlewares.observability.ai_tokens_total") as mock_tokens,
        ):
            # Act
            AIMetricsMiddleware.record_request(
                model="gpt-3.5-turbo", provider="openai", duration=0.8
            )

            # Assert
            mock_counter.labels.assert_called()
            mock_histogram.labels.assert_called()
            # Token metrics should not be called when tokens are 0

    def test_record_error(self):
        """Test recording AI error."""
        # Arrange
        with patch("src.api.middlewares.observability.ai_errors_total") as mock_counter:
            # Act
            AIMetricsMiddleware.record_error(model="gpt-4", error_type="RateLimitError")

            # Assert
            mock_counter.labels.assert_called_once_with(
                model="gpt-4", error_type="RateLimitError"
            )
            mock_counter.labels.return_value.inc.assert_called_once()


class TestAgentMetricsMiddleware:
    """Test suite for AgentMetricsMiddleware."""

    def test_record_execution(self):
        """Test recording agent execution."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.agent_executions_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.agent_execution_duration_seconds"
            ) as mock_histogram,
        ):
            # Act
            AgentMetricsMiddleware.record_execution(
                agent_name="sample_agent", duration=2.5, status="success"
            )

            # Assert
            mock_counter.labels.assert_called_with(
                agent_name="sample_agent", status="success"
            )
            mock_histogram.labels.assert_called_with(agent_name="sample_agent")

    def test_record_execution_failure(self):
        """Test recording failed agent execution."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.agent_executions_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.agent_execution_duration_seconds"
            ) as mock_histogram,
        ):
            # Act
            AgentMetricsMiddleware.record_execution(
                agent_name="sample_agent", duration=0.5, status="error"
            )

            # Assert
            mock_counter.labels.assert_called_with(
                agent_name="sample_agent", status="error"
            )

    def test_record_tool_usage(self):
        """Test recording agent tool usage."""
        # Arrange
        with patch(
            "src.api.middlewares.observability.agent_tools_used_total"
        ) as mock_counter:
            # Act
            AgentMetricsMiddleware.record_tool_usage(
                agent_name="sample_agent", tool_name="web_search"
            )

            # Assert
            mock_counter.labels.assert_called_once_with(
                agent_name="sample_agent", tool_name="web_search"
            )
            mock_counter.labels.return_value.inc.assert_called_once()


class TestUsecaseMetricsMiddleware:
    """Test suite for UsecaseMetricsMiddleware."""

    def test_record_execution(self):
        """Test recording usecase execution."""
        # Arrange
        with (
            patch(
                "src.api.middlewares.observability.usecase_executions_total"
            ) as mock_counter,
            patch(
                "src.api.middlewares.observability.usecase_duration_seconds"
            ) as mock_histogram,
        ):
            # Act
            UsecaseMetricsMiddleware.record_execution(
                usecase_name="ProcessPayment", duration=0.5, status="success"
            )

            # Assert
            mock_counter.labels.assert_called_with(
                usecase="ProcessPayment", status="success"
            )
            mock_histogram.labels.assert_called_with(usecase="ProcessPayment")
            mock_counter.labels.return_value.inc.assert_called_once()
            mock_histogram.labels.return_value.observe.assert_called_once_with(0.5)

    def test_record_multiple_executions(self):
        """Test recording multiple usecase executions."""
        # Arrange
        usecases = [
            ("CreateUser", 0.3, "success"),
            ("CreateUser", 0.4, "success"),
            ("CreateUser", 0.2, "validation_error"),
            ("UpdateProfile", 0.5, "success"),
        ]

        with (
            patch(
                "src.api.middlewares.observability.usecase_executions_total"
            ) as mock_counter,
            patch("src.api.middlewares.observability.usecase_duration_seconds"),
        ):
            # Act
            for usecase, duration, status in usecases:
                UsecaseMetricsMiddleware.record_execution(usecase, duration, status)

            # Assert - should record all executions
            assert mock_counter.labels.call_count == len(usecases)


class TestMiddlewareIntegration:
    """Integration tests for middleware."""

    @pytest.mark.asyncio
    async def test_full_request_lifecycle(self):
        """Test complete request lifecycle with all middleware."""
        # This would test a full request going through the middleware
        # with all metrics being recorded
        pass

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test middleware with concurrent requests."""
        import asyncio

        # Arrange
        # This would test that middleware handles concurrent requests correctly
        pass


# Test fixtures for dependency injection
@pytest.fixture
def mock_request():
    """Create mock request for testing."""
    request = Mock(spec=Request)
    request.url.path = "/api/test"
    request.method = "GET"
    request.headers = {}
    request.state = Mock()
    return request


@pytest.fixture
def mock_response():
    """Create mock response for testing."""
    response = Mock(spec=Response)
    response.status_code = 200
    response.headers = {}
    return response


pytestmark = pytest.mark.asyncio
