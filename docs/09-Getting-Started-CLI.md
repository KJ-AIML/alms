# Getting Started with ALMS CLI

> **For:** First-time users generating a new ALMS project  
> **Prerequisites:** Python 3.13+

## Installation

```bash
# Install the CLI
pip install alms-cli

# Or use without installing
uvx --from alms-cli alms init my-project
```

## Create a Project

```bash
# Interactive mode (prompts for name and features)
alms init my-project

# Non-interactive with profile
alms init my-project --profile core-api

# See available profiles
alms init --help
```

## Choose a Profile

| Profile | Use Case | Capabilities |
|---------|----------|--------------|
| `core-api` | REST API without AI/DB | Health, auth, tests |
| `llm-agent` | AI agent with LLM calls | + LangChain, OpenAI, Scalar docs |
| `workflow-agent` | Multi-step AI workflows | + LangGraph orchestration |
| `db-agent` | Database-backed API | + SQLAlchemy, asyncpg, Alembic |
| `observable` | Metrics and tracing | + OpenTelemetry, Prometheus |
| `full` | All capabilities | Everything above |

**Recommendation:** Start with `core-api` for simple APIs, `llm-agent` for AI features, `full` to explore everything.

## Run Your Project

```bash
cd my-project

# Install dependencies (uv recommended)
uv sync
# Or with pip:
pip install -e ".[full]"  # or specific extras: pip install -e ".[ai,docs]"

# Run the server
uv run uvicorn src.api.main:app --reload
# Or with pip:
python -m uvicorn src.api.main:app --reload

# Run tests
uv run pytest src/tests
# Or with pip:
pytest src/tests
```

## Project Structure

```
my-project/
├── src/
│   ├── api/              # Endpoints, middleware, dependencies
│   ├── agents/           # AI agent definitions (llm-agent+)
│   ├── config/           # Settings, logging
│   ├── execution/        # Use cases and actions
│   ├── providers/        # AI provider boundary
│   └── tests/            # Test suite
├── .env.example          # Environment template
├── pyproject.toml        # Dependencies with [tool.alms] metadata
└── README.md
```

## Layering Pattern

ALMS follows a clean separation of concerns:

```
Endpoint (API layer)
  → UseCase (orchestrates business flow)
    → Action (discrete operation)
      → Agent (AI reasoning, llm-agent+)
        → Provider (model access boundary)
```

**Example:** `POST /api/v1/agent/sample`

- Endpoint receives `SampleRequest` body
- UseCase orchestrates the flow
- Action performs the operation
- Agent calls the LLM via provider
- Provider abstracts model access (`get_ai_provider().get_chat_model(tier=...)`)

## Capability System

Your project's `pyproject.toml` declares active capabilities:

```toml
[tool.alms]
profile = "llm-agent"
capabilities = ["llm", "runtime_auth", "scalar_docs", "tests"]
```

Capabilities control what code is generated and what patterns are available:

- `llm` — LangChain, OpenAI integration
- `langgraph` — Multi-step workflow orchestration
- `database` — SQLAlchemy, asyncpg, repositories
- `observability` — OpenTelemetry, Prometheus metrics
- `scalar_docs` — Scalar API documentation at `/docs`
- `runtime_auth` — API key middleware
- `tests` — pytest scaffold with ASGITransport

## Testing with Mocked Providers

Generated tests use `httpx` with `ASGITransport` for async testing:

```python
from httpx import ASGITransport, AsyncClient

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

To mock the AI provider in tests:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_with_mock(client):
    mock_model = AsyncMock()
    mock_model.ainvoke.return_value = Mock(content="mocked response")
    
    with patch("src.providers.ai.langchain_model_loader.LangchainModelLoader.get_chat_model", return_value=mock_model):
        response = await client.post("/api/v1/agent/sample", json={"query": "test"})
        assert response.status_code == 200
```

## Troubleshooting

### Windows: UnicodeEncodeError on `alms init`

**Problem:** CLI crashes with `UnicodeEncodeError: 'charmap' codec can't encode character` on Windows terminals.

**Solution:** ALMS CLI v0.1.9+ automatically detects terminal encoding and uses ASCII-safe symbols on cp1252 terminals. If you still see issues:

```powershell
# Set UTF-8 encoding for the session
$env:PYTHONIOENCODING="utf-8"
alms init my-project
```

### Tests fail with "Database is not enabled"

**Problem:** Generated tests for `full` profile fail because no PostgreSQL is running.

**Solution:** The health test handles both healthy and degraded states. If you want to skip DB-dependent tests:

```bash
# Set DATABASE_ENABLED=False in test environment
DATABASE_ENABLED=false pytest src/tests
```

### Import errors for optional dependencies

**Problem:** `ImportError: No module named 'langchain'` when running AI endpoints.

**Solution:** Install the required extras:

```bash
uv sync --extra ai --extra docs
# Or with pip:
pip install -e ".[ai,docs]"
```

## Next Steps

1. Explore the generated code structure
2. Add your own endpoints following the layering pattern
3. Configure your AI provider in `.env` (set `OPENAI_API_KEY`)
4. Read the skill guidance if using an AI coding assistant
5. Check `docs/` for architecture and design pattern details
