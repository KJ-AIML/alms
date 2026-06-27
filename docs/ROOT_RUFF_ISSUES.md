# Root Ruff Issues Tracking

**Status:** Pre-existing, not release-blocking  
**Target Cleanup:** Future release (post-0.3.1)  
**Last Updated:** 2026-06-27

## Summary

The root source code (`src/`) has 30 pre-existing ruff linting issues that were present before the 0.3.0 release. These issues are primarily in test files and do not affect functionality or the public API.

**Command to reproduce:**

```bash
uv run ruff check src/
```

## Issue Breakdown

| Code | Count | Description | Fixable | Action |
|------|-------|-------------|---------|--------|
| F401 | 13 | Unused imports | Yes | Defer |
| E402 | 10 | Module import not at top of file | No | Intentional |
| F841 | 5 | Unused variables | Partial | Defer |
| F811 | 2 | Redefinition of unused names | Partial | Defer |

**Total:** 30 errors (15 auto-fixable)

## Affected Files

| File | Issue Count | Primary Issues |
|------|-------------|----------------|
| `src/tests/v1/test_observability_middleware.py` | 11 | F841, F811, F401 |
| `src/tests/v1/test_sqlalchemy_repository.py` | 7 | F841, F401 |
| `src/tests/conftest.py` | 6 | E402, F401 |
| `src/tests/v1/test_tracing.py` | 3 | F401 |
| `src/observability/tracing.py` | 1 | F401 |
| `src/api/middlewares/observability.py` | 1 | F401 |
| `src/api/endpoints/v1/dependencies.py` | 1 | E402 |

## Rationale for Deferral

1. **Test Files:** Most issues are in test files where code clarity and test structure take precedence over strict linting rules.

2. **Intentional Patterns:**
   - E402 errors in `conftest.py` are intentional (sys.path manipulation before imports)
   - Some F841 errors assign variables for clarity even if not used in assertions
   - Test files often have different linting requirements than production code

3. **Not Release-Blocking:** These issues do not affect:
   - Functionality
   - Public API
   - Generated project quality
   - Security
   - Performance

4. **Risk of Changes:** Auto-fixing some issues (especially in test files) could:
   - Break test structure
   - Reduce code clarity
   - Introduce subtle bugs

## Recommended Future Actions

### Option 1: Selective Fix (Low Risk)

Fix only the clearly safe issues:

- F401 (unused imports) in non-test files
- F401 in test files where the import is truly unused

**Estimated effort:** 30 minutes  
**Risk:** Low

### Option 2: Comprehensive Cleanup (Medium Risk)

Fix all auto-fixable issues and manually review the rest:

- Apply `ruff check --fix` to all safe fixes
- Manually review E402, F841, F811 errors
- Add `# noqa` comments where patterns are intentional

**Estimated effort:** 2-3 hours  
**Risk:** Medium (could affect test structure)

### Option 3: Configure Ruff for Test Files (Recommended)

Add ruff configuration to relax rules for test files:

```toml
[tool.ruff.lint.per-file-ignores]
"src/tests/**/*.py" = ["E402", "F841", "F401"]
```

**Estimated effort:** 15 minutes  
**Risk:** Very low

## Decision

**Defer to future release.** The issues are pre-existing, not release-blocking, and most are in test files where strict linting is less critical.

For v0.3.1, focus on:

- ✅ Generated test httpx 1.x compatibility (completed)
- ✅ CLI formatting cleanup (completed)
- ⏸️ Root ruff issues (deferred)

## Related

- Full-scale validation report: `docs/release/full-scale-validation-report.md`
- Phase 3B report: `PHASE_3B_REPORT.md` (documents pre-existing issues)
