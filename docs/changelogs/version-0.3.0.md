# ALMS Changelog - Version 0.3.0

**Release Date:** June 16, 2026  
**Version:** 0.3.0  
**Codename:** "Production Readiness"

---

## Overview

This release improves ALMS across three phases: the external LangGraph agent skill gains clearer guidance on when not to use production patterns; the ALMS repo gains optional feature flags, a production configuration validator, and a clean provider abstraction; and all documentation is aligned with the new code behavior.

The core ALMS identity is unchanged:

```text
API Endpoint -> UseCase -> Action -> Agent / LangGraph Workflow / Provider
```

Simple agents stay simple. Production workflows gain stronger guardrails.

---

## Phase 1 — Skill Updates (`alms-langgraph-agent-skill` v0.3.0)

### Do Not Overbuild

Added a "Do Not Overbuild" section to `SKILL.md` and `references/alms-patterns.md` with a decision table that maps task type to the minimum required pattern. AI coding agents now have an explicit gate before reaching for ledgers, approved memory, conflict checks, or human review.

| Task Type | Pattern | Ledger | Memory | Human Review |
|---|---|:---:|:---:|:---:|
| Simple Q&A | Endpoint → UseCase → Action → Agent | — | — | — |
| One-step extraction | Endpoint → UseCase → Action → Structured Agent | maybe | — | — |
| Batch classification | UseCase → Action → Workflow | yes | maybe | maybe |
| Auditable decision | Production Workflow | yes | yes | yes |
| Long-running background job | Process + Status + Display APIs | yes | maybe | maybe |

### Factory Compatibility

Added "Factory Compatibility" section to `SKILL.md`. AI coding agents are instructed not to replace `create_*_agent()` function factories with `AgentManager`. Both patterns are compatible. `create_*_agent()` factories remain supported and should not be replaced unless explicitly requested.

### Future Domain-Module Compatibility

Added "Future Domain-Module Compatibility" section to `SKILL.md` documenting the potential migration path from layer-first to domain-module structure. The current layer-first structure is preserved. Domain-module reorganization is future-compatible only and is not required now.

### Final Response Format

Added "Final Response Format" section to `SKILL.md` so AI coding agents end every change set with a structured report: Summary, Files Changed, Architecture Impact, Verification, Known Limitations, Next Recommended Step.

---

## Phase 2 — ALMS Code Updates

### Feature Flags

Added four new settings to `src/config/settings.py`:

| Setting | Default | Purpose |
|---|---|---|
| `AI_ENABLED` | `False` | Enable AI agents; gates AI key validation in production |
| `DATABASE_ENABLED` | `True` | Enable database; readiness check is skipped when `False` |
| `REDIS_ENABLED` | `False` | Enable Redis dependency |
| `MODEL_PROVIDER` | `openai` | AI provider selection (Google/Anthropic support is deferred) |

### Production Configuration Validation

Added `validate_production_settings()` method to `Settings`. Called automatically in the FastAPI lifespan at startup, before observability initializes. In production mode (`DEBUG=False`) the app refuses to start if:

- `SECRET_KEY` is still the default placeholder value
- `ALLOWED_HOSTS` contains `*`
- `AI_ENABLED=True` and `MODEL_PROVIDER=openai` but `OPENAI_API_KEY` is not set

Dev and test environments are not affected: `DEBUG=True` causes the method to return immediately without checking anything.

### Provider Abstraction

Added two new files under `src/providers/ai/`:

- `base.py` — `AIModelProvider` abstract base with `get_chat_model(tier: str)` interface
- `factory.py` — `get_ai_provider()` factory that returns a configured `AIModelProvider`

`LangchainModelLoader` now extends `AIModelProvider` and implements `get_chat_model(tier)`. Nodes and agents should call `get_ai_provider().get_chat_model("basic")` or `"reasoning"` rather than instantiating `LangchainModelLoader` directly. Provider switching stays in `.env` and `settings`, not in agent code.

> **Google and Anthropic providers are deferred.** `MODEL_PROVIDER` is the switch point in `factory.py` reserved for future vendor support. Only `openai` is implemented.

### Readiness Behavior

`/api/v1/health/ready` now skips the database connection check when `DATABASE_ENABLED=False`, returning `ready` immediately. When `DATABASE_ENABLED=True` (the default), behavior is unchanged from v0.2.1.

### Tests

Added `src/tests/v1/test_settings.py` with five tests covering all branches of `validate_production_settings()`.

---

## Phase 3 — Documentation Alignment

### `alms/README.md`

- Fixed stale clone URL: `fastapi-agentic-starter.git` → `alms.git`
- Fixed stale project tree root name: `fastapi-agentic-starter/` → `alms/`
- Added `base.py` and `factory.py` to `src/providers/ai/` in the project tree
- `OPENAI_API_KEY` now documented as required only when `AI_ENABLED=True`
- Added feature flag configuration block with all four flags
- Added Production Configuration section documenting `validate_production_settings()` behavior
- Fixed "Creating a New Agent" example to use `get_ai_provider().get_chat_model()` instead of direct `ChatOpenAI`

### `alms/docs/07-Setup-Installation.md`

- Updated version header to 0.3.0
- Added Feature Flags table with all four new settings
- `OPENAI_API_KEY` moved from unconditional "Required" to a conditional AI section
- Added production fail-fast callout under Security settings

### `alms/docs/05-Project-Structure.md`

- Updated version header to 0.3.0
- Added `base.py` and `factory.py` under `src/providers/ai/`
- Expanded test listing to reflect current test files

### `alms/docs/02-Design-Patterns.md`

- Updated version header to 0.3.0

### `alms-langgraph-agent-skill/README.md`

- Added `base.py` and `factory.py` to the Project Structure tree
- Split "Architecture Preference" into two explicit paths: simple agent and production LangGraph workflow
- Added reference to `SKILL.md` "Do Not Overbuild" for the decision table

### `alms-langgraph-agent-skill/references/alms-patterns.md`

- Added `base.py` and `factory.py` to the Project Shape tree
- Updated preferred provider entry point from direct `LangchainModelLoader` to `get_ai_provider()` / `AIModelProvider`
- Replaced Model Loader Pattern section: now shows `AIModelProvider` base, `factory.py`, and `get_chat_model(tier)` usage with a deferred-vendor callout
- Added `AI_ENABLED`, `DATABASE_ENABLED`, `REDIS_ENABLED` to the common settings list

---

## Compatibility

This release is fully backward compatible.

- `create_*_agent()` function factories remain supported and are not replaced
- Layer-first directory structure is preserved; domain-module structure is future-compatible only
- Existing sample endpoint behavior is unchanged
- `DATABASE_ENABLED=True` is the default; existing readiness probe behavior is unchanged for existing deployments
- `AI_ENABLED=False` is the default; `OPENAI_API_KEY` is no longer required to start the app when AI is not in use
- The skill remains compatible with `alms >=0.2.1`

---

## Non-Goals (Explicitly Deferred)

- Google and Anthropic provider implementations (reserved switch point in `factory.py`)
- Domain-module directory structure migration
- Forced `AgentManager` replacement of existing `create_*_agent()` factories
- Ledger, approved memory, or human review added to simple agents
