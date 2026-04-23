# ALMS Development Patterns

ALMS means Agentic Layer for Microservices. It is an AI-first backend architecture for FastAPI services that keeps development simple while preserving clean separation of concerns.

## Layer Map

```text
src/
  api/                         # HTTP layer
    main.py                    # FastAPI app factory
    middlewares/               # global request/error/security/observability middleware
    router/                    # top-level router aggregation
    endpoints/
      v1/                      # versioned endpoints
        dependencies.py        # version-specific dependency injection
        routers.py             # v1 router aggregation
        schemas/               # endpoint request/response schemas
  execution/                   # business execution layer
    usecases/                  # orchestration and business flow
    actions/                   # discrete operations
  agents/                      # AI agent layer
    agent_manager/             # agent definitions/managers
    prompts/                   # prompt templates
    tools/                     # agent tools
    workflows/                 # LangGraph workflows
  providers/                   # external service integrations
    ai/
    cache/
    vectordb/
  database/                    # persistence layer
    connection.py
    repositories/
    migrations/
  core/                        # shared exceptions/base logic
  config/                      # settings and logging
  models/                      # domain models
  observability/               # metrics/tracing when enabled
  utils/                       # pure helper functions
  tests/                       # pytest suite
```

## Layer Responsibilities

API layer:
- Parse HTTP input.
- Apply FastAPI dependencies.
- Return `AppResponse` or the repo's standard response shape.
- Register routes and tags.
- Never contain business rules, SQL, provider calls, or LLM calls.

Execution layer:
- Usecases orchestrate a business flow.
- Actions execute single focused operations.
- Usecases may coordinate multiple actions, repositories, providers, or agents.
- Actions should be reusable and small enough to test directly.

Agent layer:
- Own LLM behavior, prompts, tools, and workflows.
- Use this layer only when the feature truly needs AI behavior.
- For detailed LangGraph work, use the separate `alms-langgraph-agent` skill.

Provider layer:
- Wrap external services like LLM providers, Redis, vector DBs, email, storage, or HTTP APIs.
- Keep provider implementation details out of usecases and endpoints.

Database layer:
- Use repositories for persistence.
- Use `src/database/connection.py` for sessions/engine.
- Keep migrations under Alembic.

Core/config/utils:
- `core` is shared application primitives and exceptions.
- `config` is environment and logging.
- `utils` is pure reusable helper code.

## Dependency Rules

Correct flow:

```text
API endpoint -> UseCase -> Action -> Provider/Repository/Agent
```

Avoid:

```text
API endpoint -> Provider
API endpoint -> Repository
API endpoint -> Agent
UseCase -> raw SQL
Provider -> API
Repository -> UseCase
```

Infrastructure can be used by higher layers, but infrastructure should not know about API or usecase code.

## Feature Recipe

For a new normal backend feature named `<thing>`:

1. Add endpoint schemas:
   - `src/api/endpoints/v1/schemas/<thing>.py` for reusable schemas, or local classes in the endpoint for tiny features.
2. Add endpoint:
   - `src/api/endpoints/v1/<thing>.py` or `process_<thing>.py`.
3. Add dependencies:
   - `src/api/endpoints/v1/dependencies.py` when dependency construction is shared.
4. Add usecase:
   - `src/execution/usecases/<thing>_usecase.py`.
5. Add actions:
   - `src/execution/actions/<verb>_<thing>_action.py` or `process_<thing>_action.py`.
6. Add repository/provider/model only if required.
7. Register route:
   - `src/api/endpoints/v1/routers.py`.
8. Add tests:
   - endpoint tests in `src/tests/v1/`
   - action/usecase tests in `src/tests/` or a matching subfolder.
9. Update docs when public behavior, setup, architecture, or API shape changes.

## Endpoint Template

```python
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from src.api.endpoints.v1.schemas.base import AppResponse
from src.config.logs_config import get_logger
from src.execution.usecases.thing_usecase import ThingUseCase

router = APIRouter()
logger = get_logger(__name__)


class ThingRequest(BaseModel):
    name: str


async def get_thing_usecase() -> ThingUseCase:
    return ThingUseCase()


@router.post("/thing", status_code=status.HTTP_200_OK)
async def create_thing(
    payload: ThingRequest,
    usecase: ThingUseCase = Depends(get_thing_usecase),
) -> AppResponse:
    logger.info("Received thing request")
    result = await usecase.execute(payload)
    return AppResponse(success=True, data=result)
```

Keep endpoint error handling consistent with the existing middleware. If the repo has global exception handling, prefer raising app exceptions from lower layers instead of returning ad hoc error dictionaries.

## Usecase Template

```python
from src.execution.actions.create_thing_action import CreateThingAction


class ThingUseCase:
    def __init__(self, create_thing_action: CreateThingAction | None = None):
        self.create_thing_action = create_thing_action or CreateThingAction()

    async def execute(self, payload) -> dict:
        thing = await self.create_thing_action.run(payload)
        return {"thing": thing}
```

Usecases should read like the business process. If a method becomes mostly implementation details, move those details into actions, repositories, providers, or utils.

## Action Template

```python
from src.core.exceptions import ValidationException


class CreateThingAction:
    async def run(self, payload) -> dict:
        if not payload.name:
            raise ValidationException(
                message="Name is required",
                error_code="NAME_REQUIRED",
                details={"field": "name"},
            )

        return {"name": payload.name}
```

Actions can depend on providers, repositories, or agents. They should not know about FastAPI request/response details.

## Repository Template

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories.base import BaseRepository
from src.models.thing import Thing


class ThingRepository(BaseRepository[Thing]):
    def __init__(self, session: AsyncSession):
        super().__init__(Thing, session)

    async def get_by_name(self, name: str) -> Thing | None:
        result = await self.session.execute(select(Thing).where(Thing.name == name))
        return result.scalar_one_or_none()
```

Prefer repository methods with business-readable names instead of duplicating queries in actions.

## Provider Template

```python
from src.config.settings import settings


class ExternalThingProvider:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.EXTERNAL_THING_URL

    async def fetch_thing(self, thing_id: str) -> dict:
        # Use the repo's HTTP client pattern if one exists.
        raise NotImplementedError
```

Providers should hide credentials, URLs, retry settings, and SDK-specific details.

## Response And Exceptions

Use `AppResponse` for normal API responses:

```python
return AppResponse(success=True, data=result)
```

Use app exceptions for failures:

```python
from src.core.exceptions import NotFoundException, ValidationException

raise NotFoundException(
    message="Thing not found",
    error_code="THING_NOT_FOUND",
    details={"thing_id": thing_id},
)
```

Do not raise raw `HTTPException` from usecases/actions. Keep HTTP concerns in API/middleware.

## Naming

- Endpoint modules: `health.py`, `metrics.py`, `sample_agent.py`, `process_<thing>.py`
- Usecases: `<thing>_usecase.py`, class `<Thing>UseCase`
- Actions: `<verb>_<thing>_action.py` or `process_<thing>_action.py`, class `<Verb><Thing>Action`
- Repositories: `<thing>_repository.py`, class `<Thing>Repository`
- Providers: `<service>_provider.py` or local established name
- Schemas: `<thing>.py` under `schemas/` for reusable endpoint schemas
- Tests: `test_<thing>.py`

## Tests

Prefer focused tests by layer:

- Endpoint test: request validation, status code, response envelope.
- Usecase test: orchestration and business decisions with mocked actions.
- Action test: single operation behavior and exception cases.
- Repository test: database behavior with fixtures.
- Provider test: request construction and failure handling with mocked network/SDK.

Run:

```bash
uv run pytest src/tests
uv run pytest src/tests/v1/test_<thing>.py -v
uv run ruff check src
```

## Documentation Updates

Update docs when the change affects public or architectural behavior:

- `docs/05-Project-Structure.md` for new directories or layer changes.
- `docs/06-API-Documentation.md` for endpoint changes.
- `docs/02-Design-Patterns.md` for new recurring patterns.
- `docs/04-Tech-Stack.md` for dependency changes.
- `docs/07-Setup-Installation.md` for setup or env changes.
- `docs/UPDATE-SUMMARY.md` and changelogs for release-oriented work.

## Decision Checklist

Before finalizing a change, verify:

- The endpoint is thin.
- Business rules live in usecases/actions.
- External services are behind providers.
- Persistence is behind repositories.
- Shared exceptions are used.
- Settings come from `src/config/settings.py`.
- Tests cover the layer changed.
- Docs are updated when behavior changes.
