# ALMS Release Checklist

Use this checklist before publishing a new release of ALMS, ALMS CLI, or the ALMS LangGraph Agent Skill.

## Pre-Release Checks

### Tests

- [ ] `uv run pytest src/tests/v1 -v` passes from alms root
- [ ] `uv run pytest tests/ -v` passes from alms/cli
- [ ] `uv run ruff check src/` passes from alms root
- [ ] `uv run ruff check src/ tests/` passes from alms/cli
- [ ] No skipped tests unless optional dependencies are missing

### Generated Profile Smoke Matrix

For each profile (core-api, llm-agent, workflow-agent, db-agent, observable, full):

- [ ] Generate temp project: `alms init test-project --profile <profile> --no-interactive`
- [ ] Compile check: `python -m py_compile $(find src -name "*.py")`
- [ ] Import check: `python -c "from src.api.main import app; print(type(app).__name__)"`
- [ ] Route check: Verify expected routes exist, no doubled-prefix bugs
- [ ] README quickstart works
- [ ] `.env.example` matches generated settings

### Route Contract

Verify these routes for all profiles:

- [ ] `/api/v1/health/live` exists
- [ ] `/api/v1/health/ready` exists
- [ ] `/api/v1/health` exists
- [ ] `/api/v1/health/health` does NOT exist (doubled-prefix bug)
- [ ] `/api/v1/metrics` exists (if observability enabled)
- [ ] `/api/v1/metrics/metrics` does NOT exist (doubled-prefix bug)
- [ ] `/api/v1/agent/sample` exists (if llm enabled)
- [ ] `/api/v1/agent/agent/sample` does NOT exist (doubled-prefix bug)
- [ ] `/api/v1/di/sample` exists (if llm enabled)
- [ ] `/api/v1/di/di/sample` does NOT exist (doubled-prefix bug)

### Version Sync

- [ ] alms root: `pyproject.toml` version matches `settings.APP_VERSION`
- [ ] alms root: `.env.example` APP_VERSION matches
- [ ] alms/cli: `pyproject.toml` version matches `__init__.py` `__version__`
- [ ] alms-langgraph-agent-skill: `SKILL.md` version matches `CHANGELOG.md`
- [ ] Skill compatibility claim matches alms version (e.g., `alms >=0.3.0`)

### Documentation

- [ ] alms README quickstart works
- [ ] alms CLI README installation works
- [ ] agent-native-backend links to alms and skill
- [ ] skill README compatibility section is accurate
- [ ] No references to unimplemented features (e.g., Google provider)
- [ ] `.env.example` has deferred features commented out

### Security and Production Claims

- [ ] `.env.example` SECRET_KEY is a placeholder, not a real secret
- [ ] `.env.example` ALLOWED_HOSTS is `["*"]` for dev, documented for production
- [ ] `.env.example` API keys are placeholders (sk-..., AIza...)
- [ ] Production validation docs mention `validate_production_settings()`
- [ ] Unimplemented features are marked as "deferred" or "future"
- [ ] No claims about audit trail or long-running jobs unless implemented

## Release Steps

### ALMS Root Package

1. Update version in `pyproject.toml`
2. Update `APP_VERSION` in `src/config/settings.py`
3. Update `APP_VERSION` in `.env.example`
4. Update CHANGELOG (if present)
5. Run all tests
6. Commit changes
7. Tag release: `git tag v<version>`
8. Push tag: `git push origin v<version>`
9. (Optional) Publish to PyPI: `uv build && twine upload dist/*`

### ALMS CLI

1. Update version in `cli/pyproject.toml`
2. Update `__version__` in `cli/src/alms_cli/__init__.py`
3. Run all CLI tests
4. Run generated profile smoke matrix
5. Commit changes
6. Tag release: `git tag cli-v<version>`
7. Push tag: `git push origin cli-v<version>`
8. (Optional) Publish to PyPI: `cd cli && uv build && twine upload dist/*`

### ALMS LangGraph Agent Skill

1. Update version in `SKILL.md` frontmatter
2. Update `CHANGELOG.md` with release notes
3. Update compatibility claim if needed
4. Commit changes
5. Tag release: `git tag skill-v<version>`
6. Push tag: `git push origin skill-v<version>`
7. (Optional) Publish to skills registry

## Post-Release

- [ ] Create GitHub release with release notes
- [ ] Update repo descriptions if needed
- [ ] Announce release (LinkedIn, X, etc.)
- [ ] Update agent-native-backend reference if alms version changed

## Rollback Plan

If a release has issues:

1. Tag the previous stable version
2. Update PyPI to yank the bad release (if published)
3. Create a hotfix branch
4. Fix the issue
5. Re-release with a patch version bump

## Notes

- Do not publish without running the full smoke matrix
- Do not skip route contract checks (doubled-prefix bugs are common)
- Do not release with uncommitted changes
- Always test generated projects, not just the reference implementation
- Keep `.env.example` safe: no real secrets, no production defaults
