from unittest.mock import AsyncMock, MagicMock, Mock
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from src.api.main import app
from src.config.settings import settings

# --- Optional SQLAlchemy imports (guarded for core-api profiles) ---
try:
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSessionType
    _sqlalchemy_available = True
except ImportError:  # pragma: no cover
    _sqlalchemy_available = False
    _AsyncSessionType = None  # type: ignore

if _sqlalchemy_available:
    from src.database.connection import get_db
else:
    get_db = None  # type: ignore


# ============================================================================
# Basic Fixtures
# ============================================================================


@pytest.fixture
def client():
    api_key = settings.X_API_KEY or "test-api-key"
    headers = {"X-API-Key": api_key}
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture
def client_no_auth():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_session():
    session = AsyncMock()
    if _sqlalchemy_available and _AsyncSessionType is not None:
        session = AsyncMock(spec=_AsyncSessionType)
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
    metrics_mock = Mock()
    metrics_mock.inc = Mock()
    metrics_mock.observe = Mock()
    metrics_mock.labels = Mock(return_value=metrics_mock)
    return metrics_mock


@pytest.fixture
def mock_tracer():
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
    if not _sqlalchemy_available:
        pytest.skip("SQLAlchemy not installed")
    from src.database.connection import _get_session_local
    _Local = _get_session_local()
    async with _Local() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session_with_cleanup(async_session):
    try:
        yield async_session
    finally:
        await async_session.rollback()
        await async_session.close()


@pytest.fixture
def override_get_db(mock_session):
    async def _override_get_db():
        yield mock_session
    return _override_get_db


@pytest.fixture(autouse=True)
def setup_teardown():
    yield
    app.dependency_overrides.clear()


# ============================================================================
# Event Loop Fixture
# ============================================================================


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_user_data():
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "name": "Test User",
    }


@pytest.fixture
def sample_agent_query():
    return {"query": "What is the weather today?", "context": None, "stream": False}


@pytest.fixture
def sample_api_response():
    return {
        "success": True,
        "data": {"message": "Success"},
        "error": None,
        "request_id": "test-request-id-123",
    }


@pytest.fixture
def sample_error_response():
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
    registry_mock = Mock()
    registry_mock.collect = Mock(return_value=[])
    return registry_mock


@pytest.fixture
def mock_trace_provider():
    provider_mock = Mock()
    provider_mock.get_tracer = Mock(return_value=Mock())
    return provider_mock


@pytest.fixture
def sample_metrics_output():
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
    request = Mock()
    request.url.path = "/api/v1/test"
    request.method = "GET"
    request.headers = {}
    request.state = Mock()
    request.state.request_id = "test-request-id"
    return request


@pytest.fixture
def mock_response():
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
    headers = {
        "X-API-Key": settings.X_API_KEY or "test-api-key",
        "Content-Type": "application/json",
    }
    with TestClient(app, headers=headers) as c:
        yield c


@pytest.fixture
def client_without_auth():
    with TestClient(app) as c:
        yield c


# ============================================================================
# Performance Test Fixtures
# ============================================================================


@pytest.fixture
def benchmark_config():
    return {
        "warmup_requests": 10,
        "benchmark_requests": 100,
        "concurrent_workers": 5,
        "max_p99_latency": 0.1,
        "min_success_rate": 0.95,
    }


# ============================================================================
# Async Helper Fixtures
# ============================================================================


@pytest.fixture
def async_runner():
    def run_async(coro):
        return asyncio.get_event_loop().run_until_complete(coro)
    return run_async


# ============================================================================
# Cleanup Fixtures
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_requests():
    yield
    import gc
    gc.collect()


# ============================================================================
# Test Markers
# ============================================================================


def pytest_configure(config):
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
    original_debug = settings.DEBUG
    settings.DEBUG = True
    yield
    settings.DEBUG = original_debug