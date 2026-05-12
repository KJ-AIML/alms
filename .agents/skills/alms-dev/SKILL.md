---
name: alms-dev
description: Develop, refactor, review, or document Python FastAPI services that follow ALMS (Agentic Layer for Microservices). Use when adding endpoints, usecases, actions, repositories, providers, settings, middleware, tests, docs, or non-agent business features in an ALMS repo. For LangGraph-specific agent workflows, pair this with the separate alms-langgraph-agent skill.
---

# ALMS Development

Use this skill to work inside an ALMS project without losing the architecture. ALMS is a pragmatic AI-first layered backend style: simple enough to move fast, strict enough that features stay maintainable.

Read [references/alms-dev-patterns.md](references/alms-dev-patterns.md) when adding files, moving logic across layers, or deciding where a feature belongs.

## Default Flow

1. Inspect the project before editing:
   - `docs/05-Project-Structure.md`
   - `rules/project_rules.md`
   - existing files in the target layer
   - existing tests for the same API version or feature type

2. Keep dependencies flowing downward:
   - API -> Execution -> Agent or Provider/Repository
   - Execution -> Actions -> Providers/Repositories/Agents
   - Providers, Database, Config, Core, and Utils stay infrastructure/shared

3. Put code in the right layer:
   - HTTP shape, request/response schemas, auth dependencies: `src/api/`
   - Business orchestration: `src/execution/usecases/`
   - Single operations: `src/execution/actions/`
   - LLM prompts/tools/workflows: `src/agents/`
   - Agent markdown prompts: `src/agents/prompts/agents/`
   - Prompt loading: `src/agents/prompts/prompt_manager.py`
   - Structured agent outputs: `src/agents/schemas/`
   - External services: `src/providers/`
   - Database access: `src/database/repositories/`
   - Domain models: `src/models/`
   - Settings and logging: `src/config/`
   - Shared exceptions/base logic: `src/core/`
   - Pure helpers: `src/utils/`

4. Add features with the ALMS recipe:
   - Define request/response schemas near the endpoint or in `schemas/`.
   - Add an endpoint in `src/api/endpoints/v1/`.
   - Add or reuse dependencies in `src/api/endpoints/v1/dependencies.py`.
   - Add a usecase for orchestration.
   - Add actions for discrete reusable operations.
   - Add providers/repositories only when infrastructure or persistence is involved.
   - Register routers in `src/api/endpoints/v1/routers.py` and root router if needed.
   - Add focused tests under `src/tests/`.

## Style Rules

- Prefer explicit, boring names over clever abstractions.
- Use `snake_case.py`, `PascalCase` classes, `snake_case` functions, `UPPER_CASE` constants.
- Use async/await for I/O work.
- Use custom exceptions from `src/core/exceptions.py`; avoid raw `HTTPException` in business logic.
- Keep endpoints thin; they should not talk directly to database, providers, LangChain, or LangGraph.
- Keep usecases readable; they describe the business flow.
- Keep actions focused; they perform one operation and can be reused.
- Keep providers swappable; they hide external service details.
- Keep repositories responsible for persistence; do not write SQL in endpoints.

## Verify

Use the repo's existing commands:

```bash
uv sync
uv run -m src.api.main
uv run pytest src/tests
uv run pytest src/tests/v1 -v
uv run ruff check src
uv run ruff format src
```

For narrow changes, run the closest tests first. If no test exists, add one at the layer you touched or run an import-level smoke check.
