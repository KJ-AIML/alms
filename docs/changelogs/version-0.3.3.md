# ALMS Changelog - Version 0.3.3

**Release Date:** 2026-06-28  
**ALMS Version:** 0.3.0 (unchanged)  
**CLI Version:** 0.1.9  
**Codename:** "First-User UX"

---

## Overview

ALMS v0.3.3 is a CLI-only first-user UX and generated-test correctness patch. The root package (`axtra-alms`) remains at version 0.3.0 because no root source code changed. Only the CLI templates, CLI tests, and CLI UI were updated.

This release fixes six issues that blocked first-time users from successfully running generated projects out of the box, and adds comprehensive first-user documentation.

---

## Changes

### P1: Windows Unicode-Safe CLI Output

**Problem:** `alms init` crashed with `UnicodeEncodeError: 'charmap' codec can't encode character '\u2139'` on Windows cp1252 terminals. This blocked first-run experience for Windows users.

**Solution:** CLI UI now detects stdout encoding at module load and uses ASCII-safe fallback symbols (`[OK]`, `[X]`, `[i]`, `[!]`) when the terminal cannot handle Unicode glyphs.

**Impact:**

- CLI no longer crashes on Windows cp1252 terminals
- UTF-8 terminals continue to see Unicode symbols (✓, ✗, ℹ, ⚠)
- No user configuration required — automatic detection

**Files Changed:**

- `cli/src/alms_cli/ui/components.py`
- `cli/tests/test_ui_components.py` (new)

### P2: Generated Tests Pass Out of Box

**Problem:** Generated tests for llm-agent, workflow-agent, and full profiles failed without local PostgreSQL, Redis, or OpenAI API keys. Health tests asserted `success is True` but endpoint returned 503 when dependencies were unavailable.

**Solution:**

- Health endpoint `ImportError` path now returns 503 (was returning 200 with `success=False`)
- Generated tests accept both 200 (healthy) and 503 (degraded) responses
- Tests check response structure rather than hard-coding success expectations

**Impact:**

- All 6 profiles generate tests that pass without external dependencies
- 31 generated tests pass out of box (was 22/31)
- No DB, Redis, or API keys required for basic validation

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/api/endpoints/v1/health.py.j2`
- `cli/src/alms_cli/templates/files/src/tests/v1/test_health.py.j2`
- `cli/src/alms_cli/templates/files/src/tests/v1/test_agent.py.j2`
- `cli/src/alms_cli/templates/files/src/tests/integration/test_full_stack.py.j2`
- `cli/src/alms_cli/templates/files/src/tests/v1/test_observability_middleware.py.j2`

### P2: Agent Endpoint Uses Request Body Model

**Problem:** Generated agent test sent `json={"query": "test"}` but endpoint expected `query: str` as query parameter → 422 validation error.

**Solution:** Changed generated agent endpoint to accept `SampleRequest` Pydantic body model, matching the reference implementation pattern.

**Impact:**

- POST `/api/v1/agent/sample` now accepts JSON body
- OpenAPI schema correctly documents request body
- Generated test passes without modification

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/api/endpoints/v1/sample_agent.py.j2`

### P3: Sample Agent Endpoint Uses DI Chain

**Problem:** Generated agent endpoint directly instantiated `SampleUseCase()` instead of using the dependency injection chain (`Depends(get_sample_usecase)`).

**Solution:** Endpoint now uses `Depends(get_sample_usecase)` consistent with the reference implementation.

**Impact:**

- Demonstrates proper DI pattern to users
- Lazy-loads AI dependencies only when endpoint is called
- Consistent with reference ALMS architecture

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/api/endpoints/v1/sample_agent.py.j2`

### P3: Pydantic v2 ConfigDict

**Problem:** Generated settings used `class Config:` which triggers `PydanticDeprecatedSince20` warning.

**Solution:** Replaced with `model_config = ConfigDict(env_file=".env", case_sensitive=True)`.

**Impact:**

- No deprecation warnings on generated project startup
- Aligns with Pydantic v2 best practices

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/config/settings.py.j2`

### P3: pytest-asyncio Configuration

**Problem:** Generated tests used `@pytest.mark.asyncio` but no `asyncio_mode` config → warnings and errors.

**Solution:** Added `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` to generated `pyproject.toml`.

**Impact:**

- Async fixtures work without explicit markers
- No pytest-asyncio warnings

**Files Changed:**

- `cli/src/alms_cli/templates/files/pyproject.toml.j2`

### Documentation: First-User Getting Started Guide

**Added:** `docs/09-Getting-Started-CLI.md` covering:

- pip and uv installation paths
- Profile selection guide with use cases
- Capability system overview
- Layering pattern (endpoint → usecase → action → agent → provider)
- Testing with mocked providers
- Windows troubleshooting
- DB-dependent test troubleshooting

---

## Validation

### Generated Profile Matrix

All 6 profiles validated:

| Profile | Files | Compile | Import | Routes | Tests | ASGITransport | CORS | MODEL_PROVIDER | ConfigDict |
|---------|-------|---------|--------|--------|-------|---------------|------|----------------|------------|
| core-api | 53 | PASS | PASS | PASS | 3/3 | PASS | PASS | N/A | PASS |
| llm-agent | 69 | PASS | PASS | PASS | 4/4 | PASS | PASS | PASS | PASS |
| workflow-agent | 71 | PASS | PASS | PASS | 4/4 | PASS | PASS | PASS | PASS |
| db-agent | 64 | PASS | PASS | PASS | 4/4 | PASS | PASS | N/A | PASS |
| observable | 62 | PASS | PASS | PASS | 7/7 | PASS | PASS | N/A | PASS |
| full | 99 | PASS | PASS | PASS | 9/9 | PASS | PASS | PASS | PASS |

**Total generated tests: 31/31 pass out of box (no DB, Redis, or API keys required)**

### Route Contract Validation

All profiles maintain correct route contracts:

**Required routes present:**

- `/api/v1/health/live`
- `/api/v1/health/ready`
- `/api/v1/health`
- `/api/v1/agent/sample` (llm-agent, workflow-agent, full)
- `/api/v1/di/sample` (llm-agent, workflow-agent, full)
- `/api/v1/metrics` (observable, full)

**Forbidden routes absent:**

- `/api/v1/health/health`
- `/api/v1/agent/agent/sample`
- `/api/v1/di/di/sample`
- `/api/v1/metrics/metrics`

### CLI Validation

- **Tests:** 81/81 passed (77 from v0.3.2 + 4 new)
- **Ruff check:** All checks passed
- **Ruff format:** 17 files already formatted

---

## Compatibility

This release is fully backward compatible with ALMS 0.3.0, 0.3.1, and 0.3.2.

- No changes to public APIs
- No changes to generated project structure
- No changes to CLI commands or options
- Existing generated projects are unaffected
- Only new generated projects benefit from the fixes

---

## Known Limitations

1. **Google/Anthropic Providers:** Remain deferred. Only OpenAI is implemented in the generated provider layer.

2. **Redis Client, Audit Trail, Long-Running Job Lifecycle:** Remain planned/deferred. These are documented patterns, not fully implemented features.

3. **Root Package Version:** Remains at 0.3.0 because root source code (`src/`) did not change. Only CLI templates were updated.

4. **Existing Generated Projects:** Projects generated with earlier versions retain their original templates. Users must regenerate to benefit from these fixes.

---

## Upgrade Guide

### For Users

To benefit from the first-user UX improvements:

1. Install ALMS CLI 0.1.9:

   ```bash
   pip install alms-cli==0.1.9
   ```

2. Generate a new project:

   ```bash
   alms init my-project --profile full
   ```

3. Run tests (no DB/Redis/API keys required for basic validation):

   ```bash
   cd my-project
   uv sync
   uv run pytest src/tests
   ```

### For Developers

No changes required. The scaffold improvements are transparent to users.

---

## Related

- Evaluation report: `C:\KJ\Sample\EX1\alms-eval\EVALUATION-REPORT.md`
- Patch prep report: `ALMS_V033_PATCH_PREP_REPORT.md`
- ALMS 0.3.2 release: `docs/changelogs/version-0.3.2.md`
- ALMS 0.3.1 release: `docs/changelogs/version-0.3.1.md`
- ALMS 0.3.0 release: `docs/changelogs/version-0.3.0.md`
