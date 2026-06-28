# ALMS Changelog - Version 0.3.2

**Release Date:** 2026-06-28  
**ALMS Version:** 0.3.0 (unchanged)  
**CLI Version:** 0.1.8  
**Codename:** "Scaffold Correctness"

---

## Overview

ALMS v0.3.2 is a CLI-only scaffold correctness patch. The root package (`axtra-alms`) remains at version 0.3.0 because no root source code changed. Only the CLI templates and CLI tests were updated.

This release fixes four scaffold generation issues discovered during the ecosystem review and adds five regression tests to prevent recurrence.

---

## Changes

### F-01: Scalar Docs Route Registration (P1)

**Problem:** The generated `main.py.j2` placed the Scalar docs route (`{% if has_scalar %}` block) after the `if __name__ == "__main__":` guard. When running via `uvicorn src.api.main:app` (the standard import path), the Scalar `/docs` route was never registered — dead code.

**Solution:** Moved the Scalar docs route registration inside `create_app()`, before `return app`.

**Impact:**

- `/docs` route now works correctly when running via `uvicorn src.api.main:app`
- Only affects profiles with `scalar_docs` capability (llm-agent, full)
- No change to profiles without Scalar docs

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/api/main.py.j2`

### F-02: MODEL_PROVIDER in Generated Settings (P2)

**Problem:** The reference ALMS has `MODEL_PROVIDER: str = "openai"` in settings, but the generated `settings.py.j2` omitted this field. Generated projects lacked the settings-driven provider switch.

**Solution:** Added `MODEL_PROVIDER: str = "openai"` to the generated settings template, gated behind `{% if has_ai %}`. Includes a comment noting it is reserved for future provider selection.

**Impact:**

- AI-capable profiles (llm-agent, workflow-agent, full) now generate `MODEL_PROVIDER`
- Non-AI profiles (core-api, db-agent, observable) remain unaffected
- Aligns generated code with reference implementation

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/config/settings.py.j2`

### F-03: Provider Naming Alignment (P2)

**Problem:** Generated provider class was named `LangChainModelProvider` while the filename was `langchain_model_loader.py` — inconsistent with both the filename and the reference implementation class name `LangchainModelLoader`. The factory also returned the concrete type instead of the abstract `AIModelProvider`.

**Solution:**

- Renamed generated class from `LangChainModelProvider` to `LangchainModelLoader`
- Changed factory return type from concrete `LangChainModelProvider` to abstract `AIModelProvider`
- Removed `@lru_cache` from factory to match reference

**Impact:**

- Class name now matches filename and reference implementation
- Factory contract (`get_ai_provider()` → `AIModelProvider` → `get_chat_model(tier)`) matches reference
- Skill documentation references to `LangchainModelLoader` now resolve correctly
- No breaking changes to the stable contract

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/providers/ai/langchain_model_loader.py.j2`
- `cli/src/alms_cli/templates/files/src/providers/ai/factory.py.j2`

### F-04: CORS Uses settings.ALLOWED_HOSTS (P2)

**Problem:** Generated `main.py.j2` hardcoded `allow_origins=["*"]` for CORS middleware instead of using `settings.ALLOWED_HOSTS`. The reference ALMS uses `settings.ALLOWED_HOSTS`.

**Solution:** Changed generated CORS configuration to use `allow_origins=settings.ALLOWED_HOSTS`.

**Impact:**

- All generated profiles now use settings-driven CORS configuration
- Production deployments can control allowed hosts via environment variables
- Aligns generated code with reference implementation

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/api/main.py.j2`

### Regression Tests

Added 5 new regression tests to `cli/tests/test_template_system.py`:

1. `test_scalar_docs_route_inside_create_app` — verifies scalar_html is inside create_app() for llm-agent and full profiles
2. `test_cors_uses_settings_allowed_hosts` — verifies all profiles use settings.ALLOWED_HOSTS
3. `test_model_provider_in_ai_capable_settings` — verifies MODEL_PROVIDER in llm-agent, workflow-agent, full
4. `test_model_provider_absent_in_non_ai_profiles` — verifies MODEL_PROVIDER absent in core-api, db-agent, observable
5. `test_provider_class_name_aligned_with_reference` — verifies LangchainModelLoader class name and AIModelProvider return type

**Test count:** 72 → 77 (all passing)

**Files Changed:**

- `cli/tests/test_template_system.py`

---

## Validation

### Generated Profile Matrix

All 6 profiles validated:

| Profile | Files | Compile | Import | Routes | CORS | MODEL_PROVIDER | Scalar Docs | Provider Name |
|---------|-------|---------|--------|--------|------|----------------|-------------|---------------|
| core-api | 45 | PASS | PASS | PASS | PASS | N/A | N/A | N/A |
| llm-agent | 61 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| workflow-agent | 61 | PASS | PASS | PASS | PASS | PASS | N/A | PASS |
| db-agent | 55 | PASS | PASS | PASS | PASS | N/A | N/A | N/A |
| observable | 54 | PASS | PASS | PASS | PASS | N/A | N/A | N/A |
| full | 87 | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

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

- **Tests:** 77/77 passed
- **Ruff check:** All checks passed
- **Ruff format:** 16 files already formatted

---

## Compatibility

This release is fully backward compatible with ALMS 0.3.0 and 0.3.1.

- No changes to public APIs
- No changes to generated project structure
- No changes to CLI commands or options
- Existing generated projects are unaffected
- Only new generated projects benefit from the fixes

---

## Known Limitations

1. **Google/Anthropic Providers:** Remain deferred. Only OpenAI is implemented in the generated provider layer.

2. **Redis Client, Audit Trail, Long-Running Job Lifecycle:** Remain planned/deferred. These are documented patterns, not fully implemented features.

3. **Full Profile DB-Dependent Tests:** Require `DATABASE_URL` or a configured test database. These tests fail in environments without database access. This is pre-existing and unrelated to the scaffold fixes.

4. **Root Package Version:** Remains at 0.3.0 because root source code (`src/`) did not change. Only CLI templates were updated.

5. **Existing Generated Projects:** Projects generated with earlier versions retain their original templates. Users must regenerate to benefit from these fixes.

---

## Upgrade Guide

### For Users

To benefit from the scaffold correctness fixes:

1. Install ALMS CLI 0.1.8:

   ```bash
   pip install alms-cli==0.1.8
   ```

2. Generate a new project:

   ```bash
   alms init my-project --profile full
   ```

3. Or regenerate an existing project (backup first):

   ```bash
   alms init my-project --profile full --path ./my-project
   ```

### For Developers

No changes required. The scaffold fixes are transparent to users.

---

## Related

- Ecosystem review report: `LLM_ECOSYSTEM_REVIEW_REPORT.md`
- Patch prep report: `ALMS_V032_PATCH_PREP_REPORT.md`
- ALMS 0.3.1 release: `docs/changelogs/version-0.3.1.md`
- ALMS 0.3.0 release: `docs/changelogs/version-0.3.0.md`
