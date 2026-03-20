# Testing Guide for ALMS

Comprehensive testing guide for the FastAPI Agentic Starter project.

## Quick Start

```bash
# Run all tests
uv run pytest src/tests

# Run with verbose output
uv run pytest src/tests -v

# Run specific test file
uv run pytest src/tests/v1/test_health.py -v
```

## Test Structure

```
src/tests/
├── conftest.py              # Shared fixtures and configuration
├── README.md                # This guide
├── v1/                      # API v1 tests
│   ├── test_health.py       # Health endpoint tests
│   ├── test_agent.py        # Agent endpoint tests
│   ├── test_sqlalchemy_repository.py  # Database repository tests
│   ├── test_tracing.py      # OpenTelemetry tracing tests
│   ├── test_metrics.py      # Prometheus metrics tests
│   ├── test_observability_middleware.py  # Middleware tests
│   └── test_metrics_endpoint.py  # Metrics endpoint tests
├── integration/             # Integration tests
│   └── test_full_stack.py   # Full stack integration tests
└── e2e/                     # End-to-end tests
    └── test_workflows.py    # Complete workflow tests
```

## Test Categories

### 1. Unit Tests (`v1/`)

Fast, isolated tests for individual components.

```bash
# Run unit tests only
uv run pytest src/tests/v1 -m unit -v
```

**Test Files:**
- `test_health.py` - Health check endpoints
- `test_agent.py` - Agent execution endpoints
- `test_sqlalchemy_repository.py` - Database repository with mocked sessions
- `test_tracing.py` - OpenTelemetry tracing (mocked)
- `test_metrics.py` - Prometheus metrics (mocked)
- `test_observability_middleware.py` - HTTP middleware
- `test_metrics_endpoint.py` - /api/v1/metrics endpoint

### 2. Integration Tests (`integration/`)

Tests that verify multiple components work together.

```bash
# Run integration tests
uv run pytest src/tests/integration -m integration -v

# Integration tests with real database
uv run pytest src/tests/integration -m integration --asyncio-mode=auto
```

**Test File:**
- `test_full_stack.py` - Complete stack verification
  - API layer → Execution layer → Database layer
  - Real database operations
  - Observability integration
  - Performance benchmarks

### 3. End-to-End Tests (`e2e/`)

Full workflow tests simulating real user scenarios.

```bash
# Run e2e tests
uv run pytest src/tests/e2e -m e2e -v
```

**Test File:**
- `test_workflows.py` - Complete business workflows
  - Request lifecycle
  - Database CRUD operations
  - Agent execution flow
  - Error recovery
  - Performance benchmarks

## Running Tests

### Run All Tests

```bash
# Full test suite
uv run pytest src/tests --asyncio-mode=auto

# With coverage
uv run pytest src/tests --cov=src --cov-report=html
```

### Run by Category

```bash
# Unit tests only
uv run pytest src/tests -m unit -v

# Integration tests
uv run pytest src/tests -m integration -v

# E2E tests
uv run pytest src/tests -m e2e -v

# Performance tests
uv run pytest src/tests -m performance -v

# Skip slow tests
uv run pytest src/tests -m "not slow" -v
```

### Run Specific Test Files

```bash
# Repository tests
uv run pytest src/tests/v1/test_sqlalchemy_repository.py -v

# Tracing tests
uv run pytest src/tests/v1/test_tracing.py -v

# Metrics tests
uv run pytest src/tests/v1/test_metrics.py -v

# Full stack integration
uv run pytest src/tests/integration/test_full_stack.py -v
```

### Run by Test Name

```bash
# Run specific test
uv run pytest src/tests/v1/test_health.py::test_health_check -v

# Run all tests in a class
uv run pytest src/tests/v1/test_metrics.py::TestHTTPMetrics -v
```

## Test Configuration

### pytest.ini (recommended)

Create `pytest.ini` in project root:

```ini
[pytest]
testpaths = src/tests
asyncio_mode = auto
markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (database, external services)
    e2e: End-to-end tests (full workflows)
    performance: Performance benchmarks
    slow: Slow running tests
addopts = -v --tb=short
```

### Environment Variables

```bash
# Use test database
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_db

# Disable external services for tests
export OTLP_ENDPOINT=
export OPENAI_API_KEY=test-key

# Run in debug mode
export DEBUG=true
```

## Test Prerequisites

### 1. Install Dependencies

```bash
# Install all dependencies including dev
uv sync

# Or install test dependencies
uv add --dev pytest pytest-asyncio httpx
```

### 2. Start Test Services (for integration/e2e tests)

```bash
# Start PostgreSQL (if running locally)
docker-compose up -d db

# Or use Docker
docker run -d \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=test_db \
  -p 5432:5432 \
  postgres:15-alpine
```

### 3. Run Database Migrations

```bash
# Apply migrations to test database
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
alembic upgrade head
```

## Test Examples

### Unit Test Example

```python
# tests/v1/test_example.py
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.unit
class TestExample:
    def test_sync_function(self):
        # Arrange
        expected = 42
        
        # Act
        result = some_function()
        
        # Assert
        assert result == expected
    
    @pytest.mark.asyncio
    async def test_async_function(self):
        # Arrange
        mock = AsyncMock()
        mock.execute.return_value = Mock(scalar=Mock(return_value=42))
        
        # Act
        result = await some_async_function(mock)
        
        # Assert
        assert result == 42
```

### Integration Test Example

```python
# tests/integration/test_example.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestDatabaseIntegration:
    def test_database_connection(self, client):
        # Act
        response = client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
```

## Performance Benchmarks

### Run Performance Tests

```bash
# Run all performance tests
uv run pytest src/tests -m performance -v

# Run with timing
uv run pytest src/tests/integration/test_full_stack.py::TestPerformanceBenchmarks -v --durations=10
```

### Expected Performance

- **Health Endpoint**: < 100ms p99 latency
- **Metrics Endpoint**: < 500ms response time
- **Concurrent Requests**: 95%+ success rate under load
- **Memory Growth**: < 1000 objects per 100 requests

## Debugging Tests

### Verbose Output

```bash
# Maximum verbosity
uv run pytest src/tests -vvv --tb=long

# Show print statements
uv run pytest src/tests -v -s

# Stop on first failure
uv run pytest src/tests -x

# Run last failed
uv run pytest src/tests --lf
```

### Debugging with PDB

```bash
# Drop into debugger on failure
uv run pytest src/tests --pdb

# Use IPDB (better debugger)
uv run pytest src/tests --ipdb
```

## Coverage

### Generate Coverage Report

```bash
# Run with coverage
uv run pytest src/tests --cov=src --cov-report=term

# HTML report
uv run pytest src/tests --cov=src --cov-report=html

# View report
open htmlcov/index.html
```

### Coverage Configuration

Create `.coveragerc`:

```ini
[run]
source = src
omit = 
    src/tests/*
    */conftest.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise NotImplementedError
```

## Continuous Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_db
        ports:
          - 5432:5432
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install uv
        uses: astral-sh/setup-uv@v3
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run unit tests
        run: uv run pytest src/tests/v1 -v
      
      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
        run: uv run pytest src/tests/integration -v
```

## Troubleshooting

### Common Issues

**1. Async Test Failures**
```bash
# Install pytest-asyncio
uv add --dev pytest-asyncio

# Use proper marker
@pytest.mark.asyncio
async def test_async():
    pass
```

**2. Database Connection Errors**
```bash
# Check database is running
docker-compose ps

# Verify connection string
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test_db
```

**3. Import Errors**
```bash
# Ensure uv sync completed
uv sync

# Check Python path
export PYTHONPATH="${PYTHONPATH}:./src"
```

**4. Test Isolation Issues**
```bash
# Run tests with isolation
uv run pytest src/tests --forked

# Or run sequentially
uv run pytest src/tests -p no:randomly
```

### Getting Help

- Check test output: `uv run pytest src/tests -v --tb=long`
- Review fixtures: `uv run pytest src/tests --fixtures`
- Debug specific test: `uv run pytest src/tests/test_file.py::test_name -v --pdb`

## Best Practices

### 1. Test Naming
```python
# Good: descriptive
async def test_repository_create_record_successfully()

# Bad: vague
async def test_create()
```

### 2. Test Structure (AAA)
```python
def test_example():
    # Arrange
    input_data = {"key": "value"}
    
    # Act
    result = process_data(input_data)
    
    # Assert
    assert result["success"] is True
```

### 3. Use Fixtures
```python
# Use shared fixtures from conftest.py
@pytest.fixture
def sample_user():
    return {"id": 1, "name": "Test User"}

def test_with_user(sample_user):
    assert sample_user["id"] == 1
```

### 4. Mark Tests Appropriately
```python
@pytest.mark.unit  # Fast, isolated
@pytest.mark.integration  # Requires database
@pytest.mark.slow  # Takes > 1 second
@pytest.mark.asyncio  # Async test
```

## Next Steps

1. **Run the test suite**: `uv run pytest src/tests -v`
2. **Check coverage**: `uv run pytest src/tests --cov=src`
3. **Add new tests**: Follow the patterns in existing test files
4. **Update fixtures**: Add shared fixtures to `conftest.py`
5. **Document changes**: Update this README with new test patterns

---

**Happy Testing! 🧪**
