# ALMS Runtime Audit Lab

> Phase 0 — Runtime Audit Lab. Transitional, **non-production** research workspace.
> This is an audit harness, **not** the ALMS runtime. Nothing here defines the
> future `ModelRuntime` contract.

## What this is

An isolated, evidence-first lab that runs the same semantic fixtures across multiple
LLM runtime layers (LangChain, native OpenAI/Anthropic/Gemini, LiteLLM, PydanticAI)
and records what each actually does. The goal is executable evidence for the
runtime-independent architecture decisions in Phase 1 — not a refactor of ALMS core.

Authority: [`docs/ALMS_DEVSPEC_PHASE0_v1.0.md`](docs/ALMS_DEVSPEC_PHASE0_v1.0.md)
(copied spec of record). The Bible is strategic context; the DevSpec is execution authority.

## Ground rules (Phase 0)

- Production ALMS source, CLI behavior, and public package metadata are **read-only** (DevSpec Section 11).
- Each runtime probe runs in its **own** isolated Python project + lockfile. No shared runtime-SDK env (DevSpec Section 20, Section 25).
- No live provider calls without explicit confirmation **and** budget controls (DevSpec Section 80, Section 83).
- No secrets are created, committed, printed, or inferred. `runs/` and `.env*` are gitignored.
- No public release, version bump, or stable-compatibility tag from this branch (DevSpec Section 10).

## Layout

```text
research/runtime-audit/
├── configs/     # audit + runtime + comparison-set configuration (P0.1+)
├── spec/        # JSON Schemas: fixture, probe req/resp, transcript, result, finding, run-manifest (P0.1)
├── fixtures/    # semantic fixture corpus (P0.3)
├── harness/     # alms_audit harness project: planner, runner, invariants, reporting (P0.1+)
├── probes/      # one isolated project per runtime lane (P0.4+)
├── tools/       # fault-server, fixture-lint (P0.2+)
├── runs/        # gitignored local execution output
├── evidence/    # baseline-manifest.json, and P0-E1 revision (post-review)
└── docs/        # ENTRY_GATE, assumptions, findings, audit report, decision memos
```

## Status

Slice **P0.0 — Baseline Freeze** complete: workspace skeleton, entry gate, and baseline
manifest established. Harness and probe projects are intentionally empty (no runtime SDK
dependencies yet). See [`evidence/baseline-manifest.json`](evidence/baseline-manifest.json)
and [`docs/ENTRY_GATE.md`](docs/ENTRY_GATE.md).
