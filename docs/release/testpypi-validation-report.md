# TestPyPI Validation Report

> **Superseded release-name note:** A later real-PyPI preflight found `alms` unavailable as a distribution name and `alms-cli==0.1.5` already uploaded. The release package names are now `axtra-alms==0.3.0` for the root framework and `alms-cli==0.1.6` for the CLI. This report is preserved as historical TestPyPI evidence.

**Date:** 2026-06-26  
**RC Tag:** v0.3.0-rc1  
**Commit:** 2b12093ed5a86d1ecb0e26697eaf350367ef52ca

## Executive Summary

**Status: BLOCKED** - TestPyPI upload failed, but local validation passed completely.

The ALMS 0.3.0 RC1 artifacts are ready for release, but TestPyPI validation encountered two blockers:

1. The `alms` package name is already taken on TestPyPI by an unrelated project
2. The `alms-cli` upload failed with 403 Forbidden (token permission issue)

However, all local validation steps passed successfully, confirming the artifacts are correct and ready for real PyPI release.

## Test Results

### 1. Preflight Checks ✅

- **Branch:** main
- **Commit:** 2b12093ed5a86d1ecb0e26697eaf350367ef52ca
- **Tag:** v0.3.0-rc1 (points to correct commit)
- **Working tree:** Clean
- **Versions:**
  - alms: 0.3.0 ✅
  - alms-cli: 0.1.5 ✅

### 2. Build Artifacts ✅

All 4 artifacts built successfully:

```
dist/alms-0.3.0-py3-none-any.whl       (54 KB)
dist/alms-0.3.0.tar.gz                 (49 KB)
cli/dist/alms_cli-0.1.5-py3-none-any.whl  (45 KB)
cli/dist/alms_cli-0.1.5.tar.gz            (22 KB)
```

### 3. Twine Validation ✅

All artifacts passed twine check:

- ✅ alms-0.3.0-py3-none-any.whl: PASSED
- ✅ alms-0.3.0.tar.gz: PASSED
- ✅ alms_cli-0.1.5-py3-none-any.whl: PASSED
- ✅ alms_cli-0.1.5.tar.gz: PASSED

### 4. Template Validation ✅

CLI wheel includes **66 Jinja2 templates** (requirement: ≥60)

Templates verified:

- .env.example.j2
- .github/ISSUE_TEMPLATE/bug_report.yml.j2
- .github/ISSUE_TEMPLATE/feature_request.yml.j2
- .github/dependabot.yml.j2
- .github/pull_request_template.md.j2
- .github/workflows/ci.yml.j2
- .gitignore.j2
- Dockerfile.j2
- README.md.j2
- alembic.ini.j2
- docker-compose.yml.j2
- pyproject.toml.j2
- pytest.ini.j2
- rules/project_rules.md.j2
- src/agents/agent_manager/agent.py.j2
- src/agents/prompts/sample_agent_prompt.py.j2
- src/api/endpoints/v1/dependencies.py.j2
- src/api/endpoints/v1/health.py.j2
- src/api/endpoints/v1/metrics.py.j2
- src/api/endpoints/v1/routers.py.j2
- src/api/endpoints/v1/sample_agent.py.j2
- src/api/endpoints/v1/sample_di.py.j2
- src/api/endpoints/v1/schemas/base.py.j2
- src/api/endpoints/v1/schemas/sample.py.j2
- src/api/main.py.j2
- src/api/middlewares/error_handler.py.j2
- src/api/middlewares/logging.py.j2
- src/api/middlewares/observability.py.j2
- src/api/middlewares/security.py.j2
- src/api/router/routers.py.j2
- src/config/logs_config.py.j2
- src/config/settings.py.j2
- src/core/exceptions.py.j2
- src/database/connection.py.j2
- src/database/repositories/base.py.j2
- src/database/repositories/sqlalchemy_repository.py.j2
- src/execution/actions/sample_action.py.j2
- src/execution/usecases/sample_usecase.py.j2
- src/observability/**init**.py.j2
- src/observability/metrics.py.j2
- src/observability/tracing.py.j2
- src/providers/ai/base.py.j2
- src/providers/ai/factory.py.j2
- src/providers/ai/langchain_model_loader.py.j2
- src/tests/README.md.j2
- src/tests/conftest.py.j2
- src/tests/e2e/test_workflows.py.j2
- src/tests/integration/test_full_stack.py.j2
- src/tests/v1/test_agent.py.j2
- src/tests/v1/test_core_api_smoke.py.j2
- src/tests/v1/test_health.py.j2
- src/tests/v1/test_metrics.py.j2
- src/tests/v1/test_metrics_endpoint.py.j2
- src/tests/v1/test_observability_middleware.py.j2
- src/tests/v1/test_sqlalchemy_repository.py.j2
- src/tests/v1/test_tracing.py.j2
- docs/*.md.j2 (8 documentation files)
- alembic/*.j2 (3 Alembic configuration files)

### 5. TestPyPI Upload ❌ BLOCKED

#### Issue 1: `alms` Package Name Conflict

**Error:** 403 Forbidden  
**Root Cause:** The `alms` package name is already registered on TestPyPI by an unrelated project (Django-based library management system from 2016).

**TestPyPI Package Info:**

- Name: alms
- Owner: ahk
- Version: 1.0.1 (uploaded 2016-03-20)
- Description: "A Django Based Library Management Software written for Nepali reading users"

**Impact:** We cannot upload our `alms` package to TestPyPI because the name is taken.

**Options:**

1. Use a different package name for TestPyPI (e.g., `alms-framework`, `alms-ai`)
2. Contact the owner to request name transfer (unlikely to succeed)
3. Skip TestPyPI validation for `alms` and proceed to real PyPI (name may be available there)

#### Issue 2: `alms-cli` Upload Permission Error

**Error:** 403 Forbidden  
**Root Cause:** The TestPyPI token does not have permission to create new projects.

**Token Scope:** The token is scoped to the `alms-cli` project, but the project doesn't exist on TestPyPI yet. The token needs "Entire account" scope or explicit permission to create new projects.

**Impact:** Cannot upload `alms-cli` to TestPyPI.

**Options:**

1. Create a new TestPyPI token with "Entire account" scope
2. Manually create the `alms-cli` project on TestPyPI first (via web UI)
3. Skip TestPyPI validation and proceed to real PyPI

### 6. Local Install Validation ✅

Successfully installed `alms-cli` from local wheel:

```
Name: alms-cli
Version: 0.1.5
Location: C:\Users\iceph\AppData\Local\Temp\alms-test-install\Lib\site-packages
Requires: jinja2, questionary, rich, typer
```

### 7. CLI Command Validation ✅

All CLI commands work correctly:

- ✅ `alms --help` - Shows help with init and info commands
- ✅ `alms init --help` - Shows all 6 profiles and options
- ✅ `alms info` - Displays project information

### 8. Project Generation Validation ✅

#### Core-API Profile

**Generated:** 45 files  
**Features:** runtime_auth, tests

**Key Files Verified:**

- ✅ src/api/main.py
- ✅ src/api/endpoints/v1/health.py
- ✅ src/api/endpoints/v1/routers.py
- ✅ src/config/settings.py
- ✅ pyproject.toml (with [tool.alms] metadata)

**Route Contract:**

- ✅ `/api/v1/health/live` - Liveness check
- ✅ `/api/v1/health/ready` - Readiness check
- ✅ `/api/v1/health` - Health alias
- ✅ No doubled prefixes (e.g., no `/api/v1/health/health`)

**Compilation:** ✅ All Python files compile successfully

#### Full Profile

**Generated:** 87 files  
**Features:** ci, database, docker, langgraph, llm, observability, redis, runtime_auth, scalar_docs, tests

**Key Files Verified:**

- ✅ src/api/main.py
- ✅ src/api/endpoints/v1/health.py
- ✅ src/api/endpoints/v1/metrics.py
- ✅ src/api/endpoints/v1/sample_agent.py
- ✅ src/api/endpoints/v1/sample_di.py
- ✅ src/api/endpoints/v1/routers.py
- ✅ src/config/settings.py
- ✅ src/database/connection.py
- ✅ src/observability/metrics.py
- ✅ src/providers/ai/base.py
- ✅ src/providers/ai/factory.py
- ✅ pyproject.toml (with all capabilities)

**Route Contract:**

- ✅ `/api/v1/health/live` - Liveness check
- ✅ `/api/v1/health/ready` - Readiness check
- ✅ `/api/v1/health` - Health alias
- ✅ `/api/v1/metrics` - Prometheus metrics (not `/api/v1/metrics/metrics`)
- ✅ `/api/v1/agent/sample` - Sample agent (not `/api/v1/agent/agent/sample`)
- ✅ `/api/v1/di/sample` - Sample DI (not `/api/v1/di/di/sample`)
- ✅ No doubled prefixes

**Compilation:** ✅ All Python files compile successfully

### 9. Route Contract Validation ✅

All generated projects follow the correct three-level router pattern:

```
app.include_router(api_router, prefix="/api")
  └─ api_router.include_router(v1_router, prefix="/v1")
      └─ v1_router.include_router(health.router, prefix="/health")
          ├─ @router.get("/live")    → /api/v1/health/live
          ├─ @router.get("/ready")   → /api/v1/health/ready
          └─ @router.get("")         → /api/v1/health
```

**Verified Routes:**

- ✅ Health routes use correct prefixes
- ✅ Metrics endpoint uses `@router.get("")` (not `/metrics`)
- ✅ Agent endpoint uses `@router.post("/sample")` (not `/agent/sample`)
- ✅ DI endpoint uses `@router.get("/sample")` (not `/di/sample`)
- ✅ No doubled prefixes in any endpoint

## Conclusions

### What Passed ✅

1. **Build System:** All artifacts build correctly
2. **Package Metadata:** All packages pass twine validation
3. **Template System:** 66 Jinja2 templates correctly included in CLI wheel
4. **CLI Installation:** CLI installs and runs from local wheel
5. **Project Generation:** Both core-api and full profiles generate correctly
6. **Route Contract:** All routes follow the correct pattern without doubled prefixes
7. **Code Quality:** All generated Python files compile successfully

### What Failed ❌

1. **TestPyPI Upload - `alms`:** Package name already taken by unrelated project
2. **TestPyPI Upload - `alms-cli`:** Token lacks permission to create new projects

### Recommendations

#### For TestPyPI Validation

**Option A: Fix TestPyPI Issues**

1. For `alms`: Check if the name is available on real PyPI (likely yes, since the TestPyPI project is from 2016 and unrelated)
2. For `alms-cli`: Create a new TestPyPI token with "Entire account" scope, or manually create the project via TestPyPI web UI

**Option B: Skip TestPyPI, Proceed to Real PyPI**
Since all local validation passed, we can proceed directly to real PyPI:

1. Verify `alms` and `alms-cli` names are available on real PyPI
2. Create PyPI tokens with appropriate permissions
3. Upload to real PyPI
4. Validate installation from real PyPI

#### For Real PyPI Release

The artifacts are **ready for real PyPI release**. All validation steps passed:

- ✅ Package structure is correct
- ✅ Metadata is valid
- ✅ Templates are included
- ✅ CLI works correctly
- ✅ Generated projects are valid
- ✅ Route contracts are correct

## Next Steps

### Immediate Actions

1. **Check Real PyPI Availability:**

   ```bash
   curl -s https://pypi.org/pypi/alms/json | jq '.info.name'
   curl -s https://pypi.org/pypi/alms-cli/json | jq '.info.name'
   ```

2. **If Names Available:**
   - Create PyPI API tokens with "Entire account" scope
   - Upload to real PyPI:

     ```bash
     uvx twine upload --repository pypi dist/*
     cd cli && uvx twine upload --repository pypi dist/*
     ```

3. **Validate Real PyPI Install:**

   ```bash
   python -m venv /tmp/alms-pypi-test
   source /tmp/alms-pypi-test/bin/activate
   pip install alms-cli==0.1.5
   alms init test-project --profile core-api
   ```

### If Real PyPI Names Are Taken

If `alms` or `alms-cli` are also taken on real PyPI, consider:

- `alms-framework` / `alms-cli-framework`
- `alms-ai` / `alms-cli-ai`
- `alms-backend` / `alms-cli-backend`

## Security Notes

⚠️ **Token Exposure:** The TestPyPI token was exposed in chat history. Even though it's a test token, it should be revoked after this validation to prevent misuse.

## Appendix: Validation Commands

### Build Validation

```bash
cd /c/KJ/Repos/alms-lab/alms
rm -rf dist cli/dist
uv build
cd cli && uv build
```

### Twine Validation

```bash
uvx twine check dist/*
uvx twine check cli/dist/*
```

### Template Validation

```python
from zipfile import ZipFile
from pathlib import Path

wheel = next(Path("cli/dist").glob("alms_cli-0.1.5-*.whl"))
with ZipFile(wheel) as z:
    names = z.namelist()
    templates = [n for n in names if "alms_cli/templates/files/" in n and n.endswith(".j2")]
    print(f"Template count: {len(templates)}")
    assert len(templates) >= 60, f"Expected at least 60 templates, found {len(templates)}"
```

### Local Install Validation

```bash
cd /tmp
python -m venv alms-test-install
cd alms-test-install
source Scripts/activate  # Windows
pip install /c/KJ/Repos/alms-lab/alms/cli/dist/alms_cli-0.1.5-py3-none-any.whl
alms --help
alms init test-project --profile core-api
```

### Route Validation

```bash
cd test-project
python -m py_compile $(find src -name "*.py")
# Verify routes in src/api/endpoints/v1/*.py
```

## Final Verdict

**LOCAL VALIDATION: PASS ✅**  
**TESTPYPI UPLOAD: BLOCKED ❌**  
**READY FOR REAL PYPI: YES ✅**

The ALMS 0.3.0 RC1 artifacts are production-ready. The TestPyPI blockers are administrative (name conflicts, token permissions) and do not reflect any issues with the code or packaging.

**Recommendation:** Proceed to real PyPI release after verifying name availability.
