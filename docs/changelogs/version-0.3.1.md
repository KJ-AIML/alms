# ALMS Changelog - Version 0.3.1

**Release Date:** Unreleased  
**Version:** 0.3.1  
**Codename:** "Post-Release Cleanup"

---

## Overview

This release addresses post-release validation follow-ups from ALMS 0.3.0. The changes improve generated project test compatibility with httpx 1.x, clean up CLI formatting issues, and document the root ruff policy for future cleanup.

---

## Changes

### Generated Test httpx 1.x Compatibility

**Problem:** Generated project tests used the old httpx API `AsyncClient(app=app, ...)` which is incompatible with httpx 1.x. Users had to pin httpx<1.0 or manually update the conftest.py.

**Solution:** Updated the `conftest.py.j2` template to use `ASGITransport`:

```python
from httpx import ASGITransport, AsyncClient

transport = ASGITransport(app=app)
async with AsyncClient(transport=transport, base_url="http://test") as client:
    yield client
```

**Impact:**

- All newly generated projects now support httpx 1.x out of the box
- No breaking changes to existing generated projects
- Tests pass with httpx 1.x without requiring version pins

**Files Changed:**

- `cli/src/alms_cli/templates/files/src/tests/conftest.py.j2`

### CLI Formatting Cleanup

Applied `ruff format` to 4 CLI source files that had formatting inconsistencies:

- `cli/src/alms_cli/commands/init.py`
- `cli/src/alms_cli/main.py`
- `cli/tests/conftest.py`
- `cli/tests/test_smoke_imports.py`

**Impact:**

- All CLI source files now pass `ruff format --check`
- No functional changes, only formatting
- All 72 CLI tests continue to pass

### Root Ruff Policy Documentation

Created `docs/ROOT_RUFF_ISSUES.md` to track 30 pre-existing ruff linting issues in the root source code.

**Issue Breakdown:**

- 13 F401 (unused imports)
- 10 E402 (module import not at top of file) - intentional in test files
- 5 F841 (unused variables)
- 2 F811 (redefined while unused)

**Decision:** Defer to future release. Issues are pre-existing, not release-blocking, and primarily in test files where strict linting is less critical.

**Files Changed:**

- `docs/ROOT_RUFF_ISSUES.md` (new)

---

## Validation

### Generated Profile Matrix

All 6 profiles validated:

| Profile | Files | Compile | Import | Routes | Tests | httpx Fix |
|---------|-------|---------|--------|--------|-------|-----------|
| core-api | 45 | PASS | PASS | PASS | PASS | PASS |
| llm-agent | 61 | PASS | PASS | PASS | N/A | PASS |
| workflow-agent | 61 | PASS | PASS | PASS | N/A | PASS |
| db-agent | 55 | PASS | PASS | PASS | N/A | PASS |
| observable | 54 | PASS | PASS | PASS | PASS | PASS |
| full | 87 | PASS | PASS | PASS | PARTIAL | PASS |

**Note:** The `full` profile has 2 test failures unrelated to httpx (database not configured in test environment).

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

- **Tests:** 72/72 passed
- **Ruff check:** All checks passed
- **Ruff format:** 16 files already formatted

---

## Compatibility

This release is fully backward compatible with ALMS 0.3.0.

- No changes to public APIs
- No changes to generated project structure
- No changes to CLI commands or options
- Existing generated projects are unaffected
- Only new generated projects benefit from the httpx 1.x fix

---

## Known Limitations

1. **Existing Generated Projects:** Projects generated with ALMS 0.3.0 or earlier still use the old httpx API. Users must manually update `conftest.py` or regenerate the project.

2. **Root Ruff Issues:** 30 pre-existing ruff issues in root source remain unresolved. See `docs/ROOT_RUFF_ISSUES.md` for details.

3. **Full Profile Tests:** The `full` profile has 2 test failures when database is not configured. These tests require `DATABASE_URL` or a configured test database to run successfully. The failures are pre-existing, unrelated to the httpx 1.x fix, and are not route/import/compile blockers (all routes compile and import correctly).

---

## Upgrade Guide

### For Users

No action required for existing projects. To benefit from the httpx 1.x compatibility:

1. Regenerate your project with ALMS CLI 0.3.1:

   ```bash
   alms init my-project --profile <profile>
   ```

2. Or manually update `src/tests/conftest.py` in existing projects:

   ```python
   from httpx import ASGITransport, AsyncClient
   
   @pytest.fixture
   async def client():
       transport = ASGITransport(app=app)
       async with AsyncClient(transport=transport, base_url="http://test") as client:
           yield client
   ```

### For Developers

No changes required. The CLI formatting cleanup is transparent to users.

---

## Related

- Full-scale validation report: `docs/release/full-scale-validation-report.md`
- Root ruff issues tracking: `docs/ROOT_RUFF_ISSUES.md`
- ALMS 0.3.0 release: `docs/changelogs/version-0.3.0.md`
