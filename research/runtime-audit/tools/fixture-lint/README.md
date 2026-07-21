# tools/fixture-lint

Tier-0 offline validation for the Phase 0 runtime-audit fixture corpus
(DevSpec Sections 21, 44, 79; P0.3 acceptance). No network access and no runtime
SDK imports.

## Layout decision

DevSpec Section 21 shows `tools/fixture-lint/` as the canonical directory.
Implementation lives in the harness package so JSON Schema validation reuses
existing helpers and no second lint engine is introduced:

| Entrypoint | Command |
| --- | --- |
| CLI subcommand | `uv run --project harness alms-audit lint-fixtures` |
| Module | `uv run --project harness python -m alms_audit.fixture_lint` |
| Comprehensive validate | `uv run --project harness alms-audit validate` (includes fixture lint) |

Source: `harness/src/alms_audit/fixture_lint.py`

Introduced: commit `5d87869` (`feat(audit): add offline fixture lint tool`).
P0.7E closed the P0.3 explicit-marker gap (no silent corpus-key auto-allow).

## Checks

1. Every `fixtures/**/*.json` validates against `spec/fixture.schema.json`.
2. Fixture IDs are unique.
3. `expected_invariants` is a non-empty object.
4. Every invariant key is in `DEVSPEC_EVALUATORS`, `PENDING_EVALUATORS`, or
   `MANUAL_REVIEW` (explicit — corpus keys are not auto-allowed).
5. No provider-specific SDK method syntax in common fixture fields.
6. Capability names use the committed vocabulary.
7. `cost_class=offline` requires `live_required=false`.
8. Lint output is sorted (deterministic).
9. Exit code is non-zero on failure.

## Registry

To introduce a new invariant key before an evaluator exists, add it to
`PENDING_EVALUATORS` or `MANUAL_REVIEW` in
`harness/src/alms_audit/fixture_lint.py`.
