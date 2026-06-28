# ALMS Changelog - Version 0.3.4

**Release Date:** 2026-06-28  
**ALMS Version:** 0.3.0 (unchanged)  
**CLI Version:** 0.1.10  
**Codename:** "Dependency/Env/Test Correctness"

---

## Overview

ALMS v0.3.4 is a CLI-only dependency, environment, and test correctness patch. The root package (`axtra-alms`) remains at version 0.3.0 because no root source code changed. Only CLI templates, CLI tests, and CLI generator were updated.

This release fixes issues discovered during a full fresh external usability test of ALMS v0.3.3. The primary problems were: generated projects could not start with documented instructions (missing deps, env var mismatches), and generated agent tests made real API calls when AI dependencies were installed.

---

## Changes

### F-01: .env.example Matches Settings (P1)

**Problem:** Generated `.env.example` contained environment variables (`LOG_SAVE_TO_FILE`, `LOG_FILE`, `LOG_AUTO_SETUP`, `REDIS_PASSWORD`, `REDIS_DB`) that were not defined in the generated Settings class. When users copied `.env.example` to `.env` and ran the app, Pydantic raised `ValidationError: Extra inputs are not permitted`.

**Solution:** Added missing fields to `settings.py.j2`:

- `LOG_SAVE_TO_FILE: bool = False`
- `LOG_FILE: str = "src/logs/app.log"`
- `LOG_AUTO_SETUP: bool = True`
- `REDIS_PASSWORD: str | None = None` (in redis-capable profiles)
- `REDIS_DB: int = 0` (in redis-capable profiles)

**Impact:**

- `cp .env.example .env && uv run python -m src.api.main` now works without ValidationError
- All 6 profiles generate matching .env.example and Settings

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/config/settings.py.j2`

### F-02: Profile Dependencies in Base Dependencies (P1)

**Problem:** Profile-required dependencies (prometheus_client, langchain, scalar-fastapi, sqlalchemy, etc.) were only in `[project.optional-dependencies]`, requiring `uv sync --all-extras`. The documented `uv sync` command failed to install necessary packages for observable and full profiles.

**Solution:** Changed `pyproject.toml.j2` to include profile-required dependencies in base `dependencies`. The generator now computes `all_deps = core_deps + profile_extra_deps` and the template uses this directly.

**Impact:**

- `uv sync` (documented path) now installs everything needed for each profile
- observable/full profiles work without `--all-extras`
- scalar-fastapi installed for scalar_docs-capable profiles (fixes F-04)
- All 31 generated tests pass with documented setup path

**Files Changed:**

- `cli/src/alms_cli/templates/files/pyproject.toml.j2`
- `cli/src/alms_cli/templates/generator.py`

### F-03: Agent Tests Mock Provider (P1)

**Problem:** Generated `test_agent.py` made real API calls when AI dependencies were installed, failing with `openai.OpenAIError: Missing credentials`. Tests should never require API keys.

**Solution:** Updated `test_agent.py.j2` to use `app.dependency_overrides` with `AsyncMock` to mock the usecase. No real API call is made regardless of whether AI deps are installed.

**Impact:**

- Agent tests pass without API keys in all AI-capable profiles
- Tests are deterministic and fast
- No network calls during test execution

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/tests/v1/test_agent.py.j2`

### F-04: Scalar Docs Dependencies Installed (P2)

**Problem:** scalar-fastapi was in optional extras, so `/docs` returned 404 after `uv sync` for scalar_docs-capable profiles.

**Solution:** Automatically resolved by F-02 — scalar-fastapi is now in base dependencies for scalar_docs-capable profiles.

**Impact:**

- `/docs` route works after `uv sync` for llm-agent, workflow-agent, full profiles

### F-05: Generated README Includes Architecture Docs (P2)

**Problem:** Generated README was minimal (~20 lines) with no explanation of architecture, capabilities, or testing patterns.

**Solution:** Rewrote `README.md.j2` with comprehensive sections:

- Quick Start (uv + pip paths)
- Profile & Capabilities (table explaining each capability)
- Architecture (endpoint → usecase → action → agent → provider)
- Testing (ASGITransport note, provider mocking note)
- Environment (production warnings)

**Impact:**

- First-time users understand the generated project structure
- Capability system is documented
- Testing patterns are explained

**Files Changed:**

- `cli/src/alms_cli/templates/files/README.md.j2`

### F-06: pip Dev Dependencies Supported (P2)

**Problem:** `pip install -e ".[dev]"` didn't work because dev dependencies were only in `[dependency-groups]` (PEP 735), which pip doesn't support.

**Solution:** Added `[project.optional-dependencies]` with `dev = [...]` group alongside `[dependency-groups]`. Both uv and pip can now install dev dependencies.

**Impact:**

- pip users can run `pip install -e ".[dev]"`
- uv users continue to use `uv sync`
- Both paths install pytest, pytest-asyncio, httpx, ruff

**Files Changed:**

- `cli/src/alms_cli/templates/files/pyproject.toml.j2`

### F-08: Duplicate pytest Config Removed (P3)

**Problem:** Both `pytest.ini` and `pyproject.toml` defined pytest config, causing `WARNING: ignoring pytest config in pyproject.toml!`.

**Solution:** Removed `pytest.ini.j2` from templates. pytest config now only in `pyproject.toml` (`[tool.pytest.ini_options]`).

**Impact:**

- No duplicate config warning
- Single source of truth for pytest settings

**Files Changed:**

- `cli/src/alms_cli/templates/files/pytest.ini.j2` (deleted)
- `cli/src/alms_cli/templates/generator.py`

### Regression Tests

Added 6 new regression tests to `cli/tests/test_template_system.py`:

1. `test_env_example_vars_all_in_settings` — F-01: .env.example vars all in Settings
2. `test_profile_deps_in_base_dependencies` — F-02: profile deps in base deps
3. `test_agent_test_uses_dependency_overrides` — F-03: agent test mocks provider
4. `test_no_pytest_ini_generated` — F-08: no duplicate pytest config
5. `test_pip_dev_optional_deps` — F-06: pip dev path works
6. `test_readme_has_architecture_sections` — F-05: README has docs

**Test count:** 81 → 87 (all passing)

**Files Changed:**

- `cli/tests/test_template_system.py`
- `cli/tests/test_generator.py` (updated for new pyproject structure)

---

## Validation

### Generated Profile Matrix

All 6 profiles validated with documented setup path (`uv sync`):

| Profile | Files | Compile | Import | Routes | Tests | .env OK | Deps OK | README OK |
|---------|-------|---------|--------|--------|-------|---------|---------|-----------|
| core-api | 52 | PASS | PASS | PASS | 3/3 | PASS | PASS | PASS |
| llm-agent | 68 | PASS | PASS | PASS | 4/4 | PASS | PASS | PASS |
| workflow-agent | 70 | PASS | PASS | PASS | 4/4 | PASS | PASS | PASS |
| db-agent | 63 | PASS | PASS | PASS | 4/4 | PASS | PASS | PASS |
| observable | 61 | PASS | PASS | PASS | 7/7 | PASS | PASS | PASS |
| full | 98 | PASS | PASS | PASS | 9/9 | PASS | PASS | PASS |

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
- `/docs` (llm-agent, workflow-agent, full)

**Forbidden routes absent:**

- `/api/v1/health/health`
- `/api/v1/agent/agent/sample`
- `/api/v1/di/di/sample`
- `/api/v1/metrics/metrics`

### CLI Validation

- **Tests:** 87/87 passed
- **Ruff check:** All checks passed
- **Ruff format:** 17 files already formatted

---

## Compatibility

This release is fully backward compatible with ALMS 0.3.0, 0.3.1, 0.3.2, and 0.3.3.

- No changes to public APIs
- No changes to generated project structure
- No changes to CLI commands or options
- Existing generated projects are unaffected
- Only new generated projects benefit from the fixes

---

## Known Limitations

1. **Google/Anthropic Providers:** Remain deferred. Only OpenAI is implemented in the generated provider layer.

2. **Redis Client, Audit Trail, Long-Running Job Lifecycle:** Remain planned/deferred. These are documented patterns, not fully implemented features.

3. **workflow-agent LangGraph Sample:** The workflow-agent profile does not yet demonstrate a LangGraph StateGraph example. The sample agent is identical to llm-agent. Deferred to a future minor release.

4. **Root Package Version:** Remains at 0.3.0 because root source code (`src/`) did not change. Only CLI templates were updated.

5. **Existing Generated Projects:** Projects generated with earlier versions retain their original templates. Users must regenerate to benefit from these fixes.

---

## Upgrade Guide

### For Users

To benefit from the dependency/env/test correctness fixes:

1. Install ALMS CLI 0.1.10:

   ```bash
   pip install alms-cli==0.1.10
   ```

2. Generate a new project:

   ```bash
   alms init my-project --profile full
   ```

3. Run tests (no DB/Redis/API keys required):

   ```bash
   cd my-project
   uv sync
   uv run pytest src/tests
   ```

### For Developers

No changes required. The scaffold improvements are transparent to users.

---

## Related

- Evaluation report: `C:\KJ\Sample\EX2\alms-fresh-test\FULL_FRESH_ALMS_V033_TEST_REPORT.md`
- Patch prep report: `ALMS_V034_PATCH_PREP_REPORT.md`
- ALMS 0.3.3 release: `docs/changelogs/version-0.3.3.md`
- ALMS 0.3.2 release: `docs/changelogs/version-0.3.2.md`
- ALMS 0.3.1 release: `docs/changelogs/version-0.3.1.md`
- ALMS 0.3.0 release: `docs/changelogs/version-0.3.0.md`
