from unittest.mock import AsyncMock, MagicMock, Mock
import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from src.api.main import app
from src.config.settings import settings
from src.database.connection import get_db, Base


# ============================================================================
# Basic Fixtures
# ============================================================================


@pytest.fixture
def client():
    """
    Create a TestClient with API key header if configured.
    """
    headers = {"X-API-KEY": settings.X_API_KEY} if settings.X_API_KEY else {}

    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture
def mock_session():
    """
    Create a mock async session for unit tests.
    """
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.add = Mock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_metrics():
    """
    Mock metrics collection for testing.
    """
    metrics_mock = Mock()
    metrics_mock.inc = Mock()
    metrics_mock.observe = Mock()
    metrics_mock.labels = Mock(return_value=metrics_mock)
    return metrics_mock


@pytest.fixture
def mock_tracer():
    """
    Mock tracer for testing.
    """
    tracer_mock = Mock()
    span_mock = Mock()
    span_mock.__enter__ = Mock(return_value=span_mock)
    span_mock.__exit__ = Mock(return_value=None)
    span_mock.set_attribute = Mock()
    span_mock.record_exception = Mock()
    tracer_mock.start_as_current_span = Mock(return_value=span_mock)
    return tracer_mock


# ============================================================================
# Async Database Fixtures
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def async_session():
    """
    Create a real async database session for integration tests.
    Uses actual database connection.
    """
    from src.database.connection import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session_with_cleanup(async_session):
    """
    Database session that cleans up after test.
    """
    try:
        yield async_session
    finally:
        await async_session.rollback()
        await async_session.close()


@pytest.fixture
def override_get_db(mock_session):
    """
    Override the get_db dependency with a mock session.
    """

    async def _override_get_db():
        yield mock_session

    return _override_get_db


@pytest.fixture(autouse=True)
def setup_teardown():
    """
    Global setup and teardown for each test.
    Clears dependency overrides after each test.
    """
    yield
    app.dependency_overrides.clear()


# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    Required for async tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_user_data():
    """
    Sample user data for testing.
    """
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def sample_agent_query():
    """
    Sample agent query for testing.
    """
    return {"query": "What is the weather today?", "context": None, "stream": False}


@pytest.fixture
def sample_api_response():
    """
    Sample standardized API response.
    """
    return {
        "success": True,
        "data": {"message": "Success"},
        "error": None,
        "request_id": "test-request-id-123",
    }


@pytest.fixture
def sample_error_response():
    """
    Sample error API response.
    """
    return {
        "success": False,
        "data": None,
        "error": {"code": "TEST_ERROR", "message": "Test error message", "details": {}},
        "request_id": "test-request-id-456",
    }


# ============================================================================
# Observability Fixtures
# ============================================================================


@pytest.fixture
def mock_prometheus_registry():
    """
    Mock Prometheus registry for testing.
    """
    registry_mock = Mock()
    registry_mock.collect = Mock(return_value=[])
    return registry_mock


@pytest.fixture
def mock_trace_provider():
    """
    Mock OpenTelemetry trace provider.
    """
    provider_mock = Mock()
    provider_mock.get_tracer = Mock(return_value=Mock())
    return provider_mock


@pytest.fixture
def sample_metrics_output():
    """
    Sample Prometheus metrics output.
    """
    return b"""# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/health",status_code="200"} 10

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1"} 8
http_request_duration_seconds_bucket{le="+Inf"} 10
"""


# ============================================================================
# HTTP Request Fixtures
# ============================================================================


@pytest.fixture
def mock_request():
    """
    Mock HTTP request.
    """
    request = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.headers = {}
    request.state = Mock()
    request.state.request_id = "test-request-id"
    return request


@pytest.fixture
def mock_response():
    """
    Mock HTTP response.
    """
    response = Mock()
    response.status_code = 200
    response.headers = {}
    response.body = b'{"success": true}'
    return response


# ============================================================================
# Database Model Fixtures
# ============================================================================


@pytest.fixture
def mock_model_class():
    """
    Mock SQLAlchemy model class.
    """

    class MockModel:
        __tablename__ = "test_items"
        id = 1
        name = "Test"

    return MockModel


# ============================================================================
# Client with Custom Configurations
# ============================================================================


@pytest.fixture
def client_with_auth():
    """
    Test client with authentication headers.
    """
    headers = {
        "X-API-Key": settings.X_API_KEY or "test-api-key",
        "Content-Type": "application/json",
    }

    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture
def client_without_auth():
    """
    Test client without authentication headers.
    """
    with TestClient(app) as c:
        yield c


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def benchmark_config():
    """
    Configuration for benchmark tests.
    """
    return {
        "warmup_requests": 10,
        "benchmark_requests": 100,
        "concurrent_workers": 5,
        "max_p99_latency": 0.1,  # 100ms
        "min_success_rate": 0.95,  # 95%
    }


# ============================================================================
# Async Helper Fixtures
# ============================================================================


@pytest.fixture
def async_runner():
    """
    Helper to run async functions in sync context.
    """

    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)

    return run_async


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_requests():
    """
    Clean up any pending requests after each test.
    """
    yield
    # Force garbage collection
    import gc

    gc.collect()


# ============================================================================
# Test Markers
# ============================================================================


def pytest_configure(config):
    """
    Configure custom test markers.
    """
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "asyncio: mark test as async")


# ============================================================================
# Pytest Hooks
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Setup test environment once per session.
    """
    # Set test mode
    original_debug = settings.DEBUG
    settings.DEBUG = True

    yield

    # Restore original settings
    settings.DEBUG = original_debug
