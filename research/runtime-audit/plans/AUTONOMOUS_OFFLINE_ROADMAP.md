# Autonomous Offline Roadmap

Authority: DevSpec Phase 0 Part XII; P0.7C exit-gap assessment; gate matrix; finding ledger;
Bible ADR-002, ADR-006, Section 52; campaign mandate (no live providers).

Generated: 2026-07-16 from repository truth at HEAD `5d3ebbb`.
Updated: 2026-07-21 (P0.7E offline backlog closure).

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

## Completed offline slices

| Slice | Commit | Notes |
| --- | --- | --- |
| P0.7D-assumptions | `39a84f2` | assumptions.md frozen |
| P0.7D-deferred-ideas | `78e67b1` | deferred-ideas.md |
| P0.7D-fixture-lint | `5d87869` (+ P0.7E explicit-marker closure) | harness `fixture_lint.py`; tools/ pointer |
| P0.7D-invariants | `cbb911f` | ten DevSpec evaluators |
| P0.7D-harness-cli | `0cf3b45` | normalize/evaluate/summarize/verify-evidence |
| P0.9-q005-deferral | `0700898` | EmbeddingRuntime deferred |
| P0.8-design | `d7f4869` | design notes only — does NOT satisfy G5 |
| P0.10-offline-matrix | `d7f4869` | offline-result-matrix.json |
| P0.11-prep-skeletons | `d7f4869` | TBD skeletons only — finals are downstream_of_live_evidence (P0-045..P0-047) |

## Eligible now

**None** for mandatory offline work after P0.7E (see
`docs/P0.7E_OFFLINE_BACKLOG_CLOSURE.md`).

Optional only:

| Slice | Status |
| --- | --- |
| P0.9-optional-corpus | optional_not_triggered — do not implement merely to consume time |

## Blocked (not eligible offline)

| Slice | Reason |
| --- | --- |
| live-tranche-A | blocked_credential G2 |
| live-tranche-B | blocked_credential G3 |
| P0.8-fault-server | policy: READY_AFTER_LIVE_GATES |
| P0.8-offline-retry / live-stress | depends on fault-server + live |
| P0-E1 / G7 | needs live evidence |
| Phase 1A ModelRuntime | Phase 0 exit incomplete |
| mirascope lane | DevSpec trigger not met |

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
- [x] Fixture-lint proven complete (P0.7E)
- [x] L-01 not auto-accepted
- [x] Gate statuses match phase0-gate-matrix.json
- [x] Stale "fixture-lint next" pointers corrected
