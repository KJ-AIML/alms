# Phase 0 Entry Gate

Preflight checklist per ALMS_DEVSPEC_PHASE0_v1.0 §8. Recorded before implementation
work beyond P0.0. Times are UTC.

Captured: 2026-07-12T16:05:49Z
Repository: alms (`repos/alms`)
Operator session: ALMS Phase 0 — Slice P0.0 (implement mode, risk tier S2)

## Checklist

- [x] **Worktree state recorded** — clean at session start; `git status --short` empty for all three repos. Post-baseline-command status also clean (`.venv/`, `.pytest_cache/` are gitignored).
- [x] **Current branch recorded** — session start branch `main`; work branch `research/runtime-audit-phase0` created from it.
- [x] **Current HEAD recorded** — `04624bf` (`04624bfeb83d47f0f442e317995795cb2a9dc1c2`), equal to `origin/main` (ahead/behind 0/0).
- [x] **v0.3.4 tag relationship recorded** — `git describe` = `v0.3.4-2-g04624bf`. Tag `v0.3.4` = `0043e9ecc875a988eb2344f4cdfb3e40461934bb` (matches Bible `0043e9e`) and is an ancestor of HEAD. Bible implementation commit `95592f6` is present in history.
- [x] **Any drift from Bible baseline explained** — HEAD is **2 commits ahead** of the `v0.3.4` release tag:
  - `741fd85` fix(security): timing-safe API key comparison + resolve all ruff issues + improve CI
  - `04624bf` Merge pull request #17 (fix/security-lint-ci-improvements)
  Both are post-release security/lint/CI hardening merged to `main`; neither is a public re-release. Drift is intentional and non-behavioral to the public API surface.
- [~] **Existing relevant tests green** — PARTIAL / recorded, see baseline manifest:
  - `ruff check src/` → PASS (exit 0, "All checks passed!").
  - `uv run pytest src/tests` (base `uv sync` env) → **9 failed, 46 passed, 4 skipped** (exit 1).
  - The 9 failures are all `integration`/`e2e` tests in `test_full_stack.py` / `test_workflows.py` that require the `db` + `observability` optional extras and a live database (health readiness returns 503 = no DB). Those extras are absent from the base offline env (`sqlalchemy`, `asyncpg`, `opentelemetry`, `prometheus_client` all not installed). Classification: **environment/dependency**, not a baseline code regression. The Bible's "31/31" green claim (§7) is contingent on the appropriate extras + running services and/or a narrower generated-test subset; this discrepancy is recorded, not smoothed over.
- [x] **No unrelated dirty files will be touched** — all changes are additive under `research/runtime-audit/`. Production ALMS source, CLI, scaffold templates, and package metadata untouched (DevSpec §11).
- [x] **New research branch created** — `research/runtime-audit-phase0`. No public release/tag/version bump from it (DevSpec §10).
- [x] **Live credential owners identified** — KJ owns live provider credentials. No credentials were used, created, or read this session.
- [x] **Live budget cap acknowledged** — no live provider runs occurred (Tier 0/1 only). Budget policy DevSpec §80; the runner must fail closed when the hard cap is absent or exceeded (not implemented until P0.2).
- [x] **Secret handling rules acknowledged** — DevSpec §83/§85. `runs/` and `.env*` gitignored; no secrets committed, printed, or inferred.
- [x] **Phase 0 non-goals acknowledged** — DevSpec §5: no `ModelRuntime`/`AgentRuntime`/`WorkflowRuntime`, no LangChain→adapter migration, no repo rename/split, no publish. Acknowledged and honored.

## Gate verdict

G0 entry conditions satisfied for continuing Phase 0 **with one recorded caveat**: the
full offline test suite is not all-green at current HEAD under base dependencies; failures
are environment-class (missing optional extras + no live DB), not code regressions.
Resolving/confirming the Bible's green-baseline claim (extras + services, or the exact
generated-test subset) is tracked as a non-blocking follow-up, not a P0.0 blocker.
