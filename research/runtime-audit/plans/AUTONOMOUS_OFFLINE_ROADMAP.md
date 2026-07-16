# Autonomous Offline Roadmap

Authority: DevSpec Phase 0 Part XII; P0.7C exit-gap assessment; gate matrix; finding ledger; Bible ADR-002, ADR-006, Section 52; campaign mandate (no live providers).

Generated: 2026-07-16 from repository truth at HEAD `5d3ebbb`.
Self-reviewed: yes (Specification Analyst + orchestrator).

## Naming clarification

DevSpec **Slice P0.8 = Stress Semantics** (G5). It is **not** Draft ModelRuntime.
Draft ModelRuntime v0 is **Phase 1A** and is forbidden until Phase 0 exit.

## Phase 0 gate snapshot

| Gate | Status |
| --- | --- |
| G0 | satisfied |
| G1 | satisfied_offline |
| G2 | blocked_credential |
| G3 | blocked_credential |
| G4 | satisfied_offline |
| G5 | pending_live |
| G6 | satisfied_offline (N-01, N-02) |
| G7 | not_started (downstream of live + P0-E1) |
| Phase 0 exit | NOT complete |

## Candidate slices

### P0.7D-assumptions

| Field | Value |
| --- | --- |
| Title | Freeze Assumption Register |
| Goal | Create `docs/assumptions.md` with A-001..A-008 and falsification conditions; freeze for first live run |
| Source | DevSpec Section 16; P0.3 deliverable P0-021 |
| Dependencies | none |
| Files | `docs/assumptions.md`, slice report |
| Production code | no |
| Credential | no |
| Network | no |
| Risk | low |
| Tests | schema/doc presence check optional; no executable change required |
| Deliverables | assumptions.md; report |
| Eligible now | **yes** |
| Reason | Required before live; missing from repo |

### P0.7D-deferred-ideas

| Field | Value |
| --- | --- |
| Title | Deferred Ideas Register |
| Goal | Create `docs/deferred-ideas.md` per DevSpec Section 109 |
| Source | DevSpec Sections 5, 109 |
| Dependencies | none |
| Production / cred / network | no |
| Risk | low |
| Eligible now | **yes** |

### P0.7D-fixture-lint

| Field | Value |
| --- | --- |
| Title | Fixture Lint Tool |
| Goal | Implement `tools/fixture-lint/` validating all fixtures against schema + invariant key presence |
| Source | DevSpec Sections 21, 79; P0.3 |
| Dependencies | none (soft: assumptions) |
| Production / cred / network | no |
| Risk | low |
| Tests | unit tests for lint pass/fail |
| Eligible now | **yes** |

### P0.7D-invariants

| Field | Value |
| --- | --- |
| Title | Deterministic Invariant Evaluators |
| Goal | Implement `harness/src/alms_audit/invariants/` pure functions per DevSpec Section 44 |
| Source | DevSpec Section 44; P0-020 |
| Dependencies | soft: assumptions |
| Production / cred / network | no |
| Risk | medium — must not invent live semantics |
| Tests | T-INV-* unit tests |
| Eligible now | **yes** |

### P0.7D-harness-cli

| Field | Value |
| --- | --- |
| Title | Missing Harness CLI Commands |
| Goal | Add `normalize`, `evaluate`, `summarize`, `verify-evidence` per DevSpec Section 38 |
| Source | DevSpec Section 38 |
| Dependencies | P0.7D-invariants for evaluate |
| Production / cred / network | no |
| Risk | medium |
| Eligible now | **yes** (after invariants) |

### P0.9-q005-deferral

| Field | Value |
| --- | --- |
| Title | Q-005 Evidence-Backed Deferral |
| Goal | Explicit deferral of EmbeddingRuntime to post-Phase-0 sibling DevSpec |
| Source | DevSpec EXIT-12; Bible Q-005 |
| Production / cred / network | no |
| Risk | low |
| Eligible now | **yes** |

### P0.8-design

| Field | Value |
| --- | --- |
| Title | Stress Semantics Design Notes (offline) |
| Goal | Document cancel/timeout/retry mechanics per lane without executing stress |
| Source | DevSpec Slice P0.8 goal (design subset) |
| Eligible now | **yes** (design-only; does NOT satisfy G5) |
| Reason | Implementation of fault-server blocked until live gates per P0.7C |

### P0.10-offline-matrix

| Field | Value |
| --- | --- |
| Title | Offline Result Matrix Expansion |
| Goal | Fixture x lane status matrix with offline vs unverified_until_live labels |
| Source | DevSpec Section 99 |
| Eligible now | **yes** |

### P0.11-prep-skeletons

| Field | Value |
| --- | --- |
| Title | Synthesis Doc Skeletons |
| Goal | Scaffold PHASE0_AUDIT_REPORT, CONTRACT_IMPLICATIONS, PHASE1_ENTRY_DECISION with TBD |
| Source | DevSpec P0.11 |
| Eligible now | **yes** (prep only; no premature conclusions) |

### P0.9-optional-corpus

| Field | Value |
| --- | --- |
| Title | Optional Fixture Additions |
| Goal | OPTIONAL tier fixtures if justified |
| Eligible now | **yes** (optional; lowest priority) |

## Blocked (not eligible)

| Slice | Reason |
| --- | --- |
| live-tranche-A | blocked_credential G2 |
| live-tranche-B | blocked_credential G3 |
| P0.8-fault-server | policy: READY_AFTER_LIVE_GATES |
| P0.8-offline-retry | depends on fault-server |
| P0.8-live-stress | live_required fixtures |
| P0-E1 / G7 | needs live evidence |
| Phase 1A ModelRuntime | Phase 0 exit incomplete |
| mirascope lane | DevSpec trigger not met |

## Dependency-ordered execution queue

```text
P0.7D-assumptions
P0.7D-deferred-ideas
P0.7D-fixture-lint
P0.7D-invariants
P0.7D-harness-cli
P0.9-q005-deferral
P0.8-design
P0.10-offline-matrix
P0.11-prep-skeletons
P0.9-optional-corpus
```

## Findings inventory

| ID | Status | Action |
| --- | --- | --- |
| N-01..N-05 | accepted; offline mitigated | live validation deferred |
| L-01 | proposed F2 | leave unchanged; human decision |

## Production-facing work

None eligible. Production ModelRuntime gated by Phase 0 exit.

## Self-review checklist

- [x] Live work not listed as offline-eligible
- [x] P0.8 implementation blocked pending live
- [x] ModelRuntime not scheduled in Phase 0
- [x] First slice is DevSpec-mandatory gap (assumptions)
- [x] L-01 not auto-accepted
- [x] Gate statuses match phase0-gate-matrix.json
