# Contributing

## Setup

```bash
uv sync --extra full   # or a narrower extra: ai / db / cache / observability / docs
```

## Before opening a PR

```bash
uv run ruff check src
uv run pytest src/tests/v1
DATABASE_ENABLED=False uv run pytest src/tests/e2e src/tests/integration
```

All three run in CI (`.github/workflows/ci.yml`) and must pass.

## Scope

- Keep the layer boundaries intact: `API -> UseCase -> Action -> Agent/Workflow -> Provider`. See `docs/02-Design-Patterns.md` and `rules/project_rules.md`.
- New optional capabilities (a new provider, a new extra) should degrade gracefully when their dependency isn't installed -- follow the existing `try/except ImportError` guard pattern used throughout `src/api/main.py` and `src/api/endpoints/v1/dependencies.py`, and keep `src/tests/v1/test_core_api_smoke.py` passing without that extra installed.
- Add or update tests for behavior you change. Match the existing test's profile assumptions (e.g. DB-dependent tests belong under `src/tests/integration`, not `src/tests/v1`).

## Pull requests

Use the PR template. Small, focused PRs are easier to review than large ones bundling unrelated changes.

## Reporting bugs / requesting features

Use the GitHub issue templates (`.github/ISSUE_TEMPLATE/`).
