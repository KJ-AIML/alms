# ALMS Release Candidate Notes

## Version 0.3.0 (Release Candidate)

This is the first release candidate for ALMS (Agentic Layer for MicroServices), a production-ready AI-first backend framework.

## Major Improvements

### 1. CLI Template System Refactor (Phase 3A)
- Migrated from inline Python string templates to Jinja2 template files
- Templates now live in `cli/src/alms_cli/templates/files/` as `.j2` files
- Separated profile/capability logic into `profiles.py`
- Added `TemplateRenderer` using Jinja2 with strict undefined checking
- Made template system testable and maintainable

### 2. CLI Architecture Sync (Phase 3B)
- Aligned generated projects with reference implementation architecture
- Three-level router pattern: `v1_router` → `api_router` → `app.include_router`
- Class-based middleware: `ErrorHandlerMiddleware`, `LoggingMiddleware`, `APIKeyMiddleware`, `SecurityHeadersMiddleware`, `ObservabilityMiddleware`
- Settings contract: `APP_NAME`, `APP_DESCRIPTION`, `APP_VERSION`
- AppResponse: `Generic[T]` with `Optional[str]` request_id (no UUID auto-generation)

### 3. Route Contract Fixes (Phase 3C + Phase 4)
- Fixed doubled-prefix bugs in health, metrics, agent, and DI endpoints
- Final route contract:
  - `/api/v1/health/live` - liveness check
  - `/api/v1/health/ready` - readiness check (includes DB if enabled)
  - `/api/v1/health` - alias for ready
  - `/api/v1/metrics` - Prometheus metrics (if observability enabled)
  - `/api/v1/agent/sample` - sample agent endpoint (if llm enabled)
  - `/api/v1/di/sample` - sample DI endpoint (if llm enabled)

### 4. Provider Boundary Alignment (Phase 2)
- Generated agent code uses `get_ai_provider().get_chat_model(tier='basic')`
- No direct `ChatOpenAI` imports in generated code
- Provider abstraction enforced across all profiles

### 5. Request ID Consolidation (Phase 2)
- `LoggingMiddleware` is single source of truth for request_id
- `ObservabilityMiddleware` reuses request_id from `request.state`
- Logs and traces now agree on request_id

### 6. Profile-Aware Generation
- All 6 profiles fully supported: `core-api`, `llm-agent`, `workflow-agent`, `db-agent`, `observable`, `full`
- Each profile generates only the capabilities it declares
- No unused imports, no missing dependencies

### 7. Testing and Verification
- 65 tests in alms root (all passing)
- 72 tests in CLI (all passing)
- Route contract regression tests for all 6 profiles
- Generated project smoke tests (compile, import, routes)
- Comprehensive release checklist

## CLI Scaffold Stability

### Import Blockers Fixed
- `SampleUseCase` class name mismatch (was `SampleUsecase`)
- `AppResponse` now properly `Generic[T]`
- `validate_production_settings()` method added to generated Settings
- `DATABASE_URL` guard in generated db connection module

### CI/CD
- GitHub Actions workflow updated to Python 3.13
- All profiles generate valid CI configs

## Jinja2 Template System

### Benefits
- Templates are now readable, editable files (not Python string literals)
- Strict undefined checking catches missing variables
- Conditional generation using Jinja2 `{% if %}` blocks
- Easy to add new templates or modify existing ones

### Template Files
- 66 Jinja2 templates in `cli/src/alms_cli/templates/files/`
- Covers: API, config, database, observability, agents, tests, Docker, CI, Alembic
- Profile-aware conditional generation

## Known Limitations

### Acceptable for RC
- Google/Anthropic provider support is deferred (only OpenAI implemented)
- Redis settings exist but no Redis client implementation
- Audit trail and long-running job lifecycle are architecture patterns only (not implemented)
- 26 pre-existing ruff lint issues in alms root (not from Phase 1-4 changes)

### Must Fix Before Stable Release
- Consider implementing Redis client if cache capability is advertised
- Document audit trail and long-running job patterns as "future extensions"
- Address ruff lint issues or document as known issues

## Upgrade Notes

### From Previous Versions
- If you have a generated ALMS project, you can regenerate with the new CLI to get the updated architecture
- The `[tool.alms]` metadata in `pyproject.toml` is now required for profile-aware code generation
- Route structure has changed (doubled-prefix bugs fixed) - update any hardcoded routes

### Migration Steps
1. Update CLI: `pip install --upgrade alms-cli`
2. Regenerate project: `alms init my-project --profile full --no-interactive`
3. Copy your custom code from old project to new project
4. Update any hardcoded route paths
5. Run tests: `uv run pytest src/tests/v1 -v`

## Not-Yet-Implemented Production Features

The following are described in the agent-native-backend architecture guide but not yet implemented in the ALMS reference scaffold:

- **Audit Trail**: Ledger-based evidence recording for auditable decisions
- **Long-Running Job Lifecycle**: Background job status, retries, failure handling
- **Human Review Queue**: Review decision APIs and review loops
- **Multi-Provider Support**: Google Gemini and Anthropic Claude providers
- **Redis Client**: Cache provider implementation (settings exist but no client)

These are recommended patterns for production ALMS deployments and can be implemented as extensions.

## Testing

### Test Coverage
- Health endpoints (live, ready, health alias)
- Metrics endpoint and Prometheus format
- Observability middleware (request_id, tracing)
- SQLAlchemy repository (CRUD, pagination, count)
- Settings validation (production checks)
- Core API smoke tests
- CLI template system (all 6 profiles)
- Route contract verification

### Running Tests
```bash
# From alms root
uv run pytest src/tests/v1 -v

# From alms/cli
uv run pytest tests/ -v
```

## Documentation

### Updated Docs
- `alms/README.md` - added optional extras, [tool.alms], route structure
- `alms/docs/release-checklist.md` - comprehensive release checklist
- `agent-native-backend/references/alms-python-fastapi.md` - added profiles section
- `alms-langgraph-agent-skill/README.md` - profile support documentation

### Release Checklist
See `docs/release-checklist.md` for the full release checklist covering:
- Pre-release checks (tests, smoke matrix, route contracts, version sync)
- Release steps (alms, CLI, skill)
- Post-release tasks
- Rollback plan

## Compatibility

### ALMS 0.3.0
- Python 3.13+
- FastAPI 0.122.0+
- Pydantic 2.12.5+
- Optional: LangChain, LangGraph, SQLAlchemy, OpenTelemetry, Prometheus

### ALMS CLI 0.1.5
- Python 3.13+
- Jinja2 3.1.0+
- Typer, Rich, Questionary for UI

### ALMS LangGraph Agent Skill 0.4.0
- Compatible with ALMS >= 0.3.0
- Profile-aware code generation
- Reads `[tool.alms]` from pyproject.toml

## Acknowledgments

This release represents the culmination of Phases 1-4 of the ALMS optimization project:
- Phase 1: P0 import/CI/scaffold stabilization
- Phase 2: P1 contract stabilization
- Phase 3A: Template system refactor
- Phase 3B: CLI architecture sync
- Phase 3C: Health route contract fix
- Phase 4: Release readiness and docs polish

## Next Steps

1. Tag release candidate: `git tag v0.3.0-rc1`
2. Wait for CI validation
3. (Deferred) Publish to PyPI after RC validation: `uv build && twine upload dist/*`
3. Create GitHub release with release notes
4. Announce release
5. Gather feedback
6. Address any issues
7. Tag stable release: `git tag v0.3.0`

## Support

- GitHub Issues: https://github.com/KJ-AIML/alms/issues
- Documentation: See README.md and docs/
- Architecture Guide: https://github.com/KJ-AIML/agent-native-backend
- Agent Skill: https://github.com/KJ-AIML/alms-langgraph-agent-skill
