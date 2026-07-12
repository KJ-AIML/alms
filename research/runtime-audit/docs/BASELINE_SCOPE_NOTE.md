# Baseline Scope Clarification

Added in P0.1. This note clarifies scope; it does **not** rewrite
`evidence/baseline-manifest.json` (DevSpec Section 9: the manifest is historical evidence and
must not be rewritten). No production code is changed by this note.

## The "31/31" figure

The `31/31` result referenced in the Bible/DevSpec (Section 7) is the **generated scaffold
fresh-user validation scope** for ALMS v0.3.4 — i.e. the tests a fresh external user gets
after scaffolding, exercised along the documented `uv sync` / `uv sync --all-extras` /
pip-only install paths, with no real provider calls.

It is **not** the root repository's full internal `uv run pytest src/tests` result under
base dependencies at the current HEAD.

## Accepted P0.0 baseline result

At HEAD `04624bf` (`v0.3.4-2-g04624bf`), with the base `uv sync` env, the accepted
baseline is:

```text
uv sync              PASS
ruff check src/      PASS
pytest src/tests     PARTIAL — 9 failed / 46 passed / 4 skipped
```

The 9 failures are all `integration`/`e2e` tests requiring the `db` + `observability`
optional extras and a **live database** (health readiness returns 503). Those extras are
absent from the base offline env. This is an **environment/integration dependency**
condition, not a baseline code regression.

## Decision

Per KJ direction, this discrepancy is **not** chased or fixed during P0.1. The P0.0
baseline stands as recorded. The Runtime Audit Lab does not depend on the root repo's
integration/e2e suite; the lab has its own isolated harness tests (see
`harness/tests/`). Confirming the full green baseline (extras + running services, or the
exact generated-test subset) remains a non-blocking follow-up for a later slice.
