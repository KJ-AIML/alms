# fixture-lint

Tier-0 offline validation for the Phase 0 runtime-audit fixture corpus (DevSpec
Sections 21, 44, 79). No network access and no runtime SDK imports.

Implementation lives in the harness package so schema loading stays shared and no
extra dependencies are required:

| Entrypoint | Command |
|---|---|
| CLI subcommand | `uv run --project harness alms-audit lint-fixtures` |
| Module | `uv run --project harness python -m alms_audit.fixture_lint` |
| Comprehensive validate | `uv run --project harness alms-audit validate` (includes fixture lint) |

Source: `harness/src/alms_audit/fixture_lint.py`

## Checks

1. Every `fixtures/**/*.json` file validates against `spec/fixture.schema.json`.
2. Fixture IDs are unique across the corpus.
3. `expected_invariants` is a non-empty object.
4. Every invariant key is an allowed evaluator name.

## Allowed evaluator names

- DevSpec Section 44 examples (`schema_valid`, `expected_fields_equal`, …).
- Every key currently used in the committed fixture corpus (union collected at lint time).
- Names listed in `PENDING_EVALUATORS` inside `fixture_lint.py` (declared but not yet
  implemented as harness evaluators).
- Names listed in `MANUAL_REVIEW` (require explicit human review, not automation).

To introduce a new invariant key before it appears elsewhere in the corpus, add it to
`PENDING_EVALUATORS` or `MANUAL_REVIEW` in `harness/src/alms_audit/fixture_lint.py`.
