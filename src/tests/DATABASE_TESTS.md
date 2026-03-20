# Running Tests with Database

## Cold Start vs Warm Start

### Without Database (Cold Start) ❄️
```
Health Check: 4+ seconds
  ↓
App tries to connect to PostgreSQL
  ↓
Waits 4 seconds (timeout)
  ↓
Returns "healthy" (DB check failed but app is running)
```

### With Database (Warm Start) 🔥
```
Health Check: < 100ms
  ↓
App connects to PostgreSQL instantly
  ↓
Returns "healthy" with DB status
```

---

## Start Database for Tests

### Option 1: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d db redis

# Wait for PostgreSQL to be ready
sleep 5

# Run tests (now fast!)
uv run pytest src/tests -v

# Stop services when done
docker-compose down
```

### Option 2: Docker Only PostgreSQL

```bash
# Start PostgreSQL
docker run -d \
  --name test-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=db \
  -p 5432:5432 \
  postgres:15-alpine

# Wait for it
sleep 5

# Run tests
uv run pytest src/tests -v

# Cleanup
docker stop test-postgres && docker rm test-postgres
```

### Option 3: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Create test database
createdb fastapi_test

# Update .env
export DATABASE_HOST=localhost
export DATABASE_USER=postgres
export DATABASE_PASSWORD=postgres
export DATABASE_NAME=fastapi_test

# Run tests
uv run pytest src/tests -v
```

---

## Expected Performance

### With Database Running 🔥

```bash
$ uv run pytest src/tests/v1/test_health.py -v

test_root_health_check PASSED     [ 50%]  # ~20ms
test_v1_health_check PASSED       [100%]  # ~30ms

============================== 2 passed in 0.15s ==============================
```

### Without Database ❄️

```bash
$ uv run pytest src/tests/v1/test_health.py -v

test_root_health_check PASSED     [ 50%]  # ~4000ms (DB timeout)
test_v1_health_check PASSED       [100%]  # ~4000ms (DB timeout)

============================== 2 passed in 8.2s ==============================
```

**10x faster with database!**

---

## Quick Test Commands

```bash
# Fast tests only (no DB required)
uv run pytest src/tests/v1/test_metrics.py -v

# Full test suite (recommend with DB)
uv run pytest src/tests -v

# Skip slow tests (DB timeout tests)
uv run pytest src/tests -m "not slow" -v

# Performance tests (requires DB)
uv run pytest src/tests -m performance -v
```

---

## CI/CD Configuration

For GitHub Actions or other CI:

```yaml
services:
  postgres:
    image: postgres:15-alpine
    env:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: test_db
    ports:
      - 5432:5432
    options: >-
      --health-cmd pg_isready
      --health-interval 10s
      --health-timeout 5s
      --health-retries 5
```

This ensures tests run fast in CI/CD pipelines.

---

## Summary

| Environment | Test Speed | Recommendation |
|-------------|-----------|----------------|
| **With DB** | < 1 second | ✅ Development & CI/CD |
| **Without DB** | 5+ minutes | ✅ Quick checks only |

**Pro Tip:** Always run tests with database for accurate performance benchmarks!
