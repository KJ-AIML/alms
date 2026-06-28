# 06 - API Documentation

> **Last Updated:** March 20, 2026  
> **Version:** 0.2.0  
> **Status:** ✅ Active

## Base URL

```
Development: http://localhost:3000/api/v1
Production:  https://your-domain.com/api/v1
Documentation: http://localhost:3000/docs (Scalar UI)
```

## Response Format

All API responses use the standardized `AppResponse` wrapper:

### Success Response

```json
{
  "success": true,
  "data": {
    "message": "Operation completed",
    "result": {...}
  },
  "error": null,
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### Error Response

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Health Check

### GET /api/v1/health

Check service health status.

**Request:**

```bash
curl http://localhost:3000/api/v1/health
```

**Response:**

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "0.1.0",
    "timestamp": "2026-03-20T10:30:00Z"
  },
  "error": null,
  "request_id": "uuid-string"
}
```

## Agent Endpoints

### POST /api/v1/agent

Execute an AI agent with the provided query.

**Request:**

```bash
curl -X POST http://localhost:3000/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the weather like today?"
  }'
```

**Request Body:**

```json
{
  "query": "string (required) - The query to send to the agent"
}
```

**Response:**

```json
{
  "success": true,
  "data": {
    "response": "I don't have access to real-time weather data...",
    "agent_type": "sample_agent",
    "processing_time": 1.234
  },
  "error": null,
  "request_id": "uuid-string"
}
```

**Error Responses:**

- `400` - Validation error (missing query)
- `500` - Agent execution error

## Metrics Endpoint

### GET /api/v1/metrics

Prometheus-compatible metrics endpoint for observability and monitoring.

**Request:**

```bash
curl http://localhost:3000/api/v1/metrics
```

**Response:**

```text
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/api/v1/health",status="200"} 42

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.1",method="GET",endpoint="/api/v1/health"} 40
http_request_duration_seconds_sum{method="GET",endpoint="/api/v1/health"} 1.234
http_request_duration_seconds_count{method="GET",endpoint="/api/v1/health"} 42

# HELP db_queries_total Total database queries
# TYPE db_queries_total counter
db_queries_total{operation="SELECT",table="users"} 156

# HELP cache_hits_total Total cache hits
# TYPE cache_hits_total counter
cache_hits_total{operation="get"} 89
```

**Metrics Available:**

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `db_queries_total` | Counter | Database queries by operation and table |
| `db_query_duration_seconds` | Histogram | Database query latency |
| `cache_operations_total` | Counter | Cache operations by type (get/set/delete) |
| `cache_hits_total` | Counter | Cache hit count |
| `cache_misses_total` | Counter | Cache miss count |
| `ai_requests_total` | Counter | AI/LLM API calls by model |
| `ai_tokens_total` | Counter | Token usage by type (input/output) |
| `ai_request_duration_seconds` | Histogram | AI API call latency |
| `agent_executions_total` | Counter | Agent executions by type |
| `agent_execution_duration_seconds` | Histogram | Agent execution time |

**Environment Variables:**

| Variable | Description | Default |
|----------|-------------|---------|
| `METRICS_ENABLED` | Enable metrics collection | `true` |
| `TRACING_ENABLED` | Enable distributed tracing | `true` |
| `OTLP_ENDPOINT` | OpenTelemetry collector endpoint | - |

## Sample Endpoints

### GET /api/v1/sample_di

Demonstrate dependency injection with message service.

**Request:**

```bash
curl http://localhost:3000/api/v1/sample_di
```

**Response:**

```json
{
  "success": true,
  "data": {
    "message": "Hello from DI!"
  },
  "error": null,
  "request_id": "uuid-string"
}
```

### GET /api/v1/sample_di/{message_id}

Get a specific message by ID.

**Request:**

```bash
curl http://localhost:3000/api/v1/sample_di/123
```

**Path Parameters:**

- `message_id` (int, required) - The message ID

**Response:**

```json
{
  "success": true,
  "data": {
    "id": 123,
    "message": "Message #123 from DI!"
  },
  "error": null,
  "request_id": "uuid-string"
}
```

**Error Responses:**

- `404` - Message not found

## Error Codes

| Code | Status | Description |
|------|--------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `DOMAIN_ERROR` | 400 | Business logic violation |
| `NOT_FOUND` | 404 | Resource not found |
| `INTERNAL_SERVER_ERROR` | 500 | Unexpected server error |

## HTTP Status Codes

| Status | Meaning | Usage |
|--------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Permission denied |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Validation error (Pydantic) |
| 500 | Internal Server Error | Server error |

## Rate Limiting

⏳ **Planned for v0.3.0**

Rate limiting will be implemented using Redis:

```
- 100 requests per minute per IP
- 1000 requests per hour per API key
```

## Authentication

⏳ **Planned for v0.3.0**

Authentication will use JWT tokens:

```http
Authorization: Bearer <jwt_token>
```

### Authentication Endpoints (Planned)

#### POST /api/v1/auth/login

Authenticate user and get JWT token.

**Request:**

```bash
curl -X POST http://localhost:3000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

**Response:**

```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 3600
  },
  "error": null,
  "request_id": "uuid-string"
}
```

## Request/Response Examples

### Python (httpx)

```python
import httpx

async with httpx.AsyncClient() as client:
    # Health check
    response = await client.get("http://localhost:3000/api/v1/health")
    print(response.json())
    
    # Agent query
    response = await client.post(
        "http://localhost:3000/api/v1/agent",
        json={"query": "Hello, agent!"}
    )
    print(response.json())
```

### JavaScript (fetch)

```javascript
// Health check
const response = await fetch('http://localhost:3000/api/v1/health');
const data = await response.json();
console.log(data);

// Agent query
const response = await fetch('http://localhost:3000/api/v1/agent', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'Hello, agent!'
  })
});
const data = await response.json();
console.log(data);
```

### cURL

```bash
# Health check
curl http://localhost:3000/api/v1/health

# Agent query
curl -X POST http://localhost:3000/api/v1/agent \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello, agent!"}'
```

## Testing with Scalar

The API documentation is available at `http://localhost:3000/docs` (powered by Scalar).

Features:

- Interactive API explorer
- Request/response examples
- Try it out functionality
- Auto-generated from OpenAPI spec

## Versioning

API versioning follows URL path versioning:

```
/api/v1/...     # Current version
/api/v2/...     # Future version (breaking changes)
```

When v2 is released, v1 will be supported for 6 months before deprecation.

## WebSocket Support

⏳ **Planned for v0.4.0**

Real-time communication for streaming agent responses:

```
ws://localhost:3000/ws/agent
```

## Reference vs Generated Scaffold Routes

The ALMS repository contains two sets of sample routes:

**Reference Implementation** (this repo's `src/`):

- `/api/v1/agent/execute` — Agent execution endpoint
- `/api/v1/sample_di/sample-di` — Dependency injection demo

**Generated Scaffold** (from `alms init`):

- `/api/v1/agent/sample` — Agent execution endpoint
- `/api/v1/di/sample` — Dependency injection demo

The generated scaffold uses shorter, simpler route names. When creating new projects with `alms init`, the generated routes are the contract. The reference implementation may show richer demo routes for documentation purposes.

**Updated:** v0.3.2 - Clarified reference vs generated scaffold routes
