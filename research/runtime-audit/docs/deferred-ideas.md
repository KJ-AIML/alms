# Phase 0 Deferred Ideas Register

## Status

Initial register created offline.

- Created offline: 2026-07-16
- No live run has begun yet
- Phase 0 remains open

## Authority

- DevSpec Section 5 (Forbidden in Phase 0)
- DevSpec Section 109 (Deferred-Idea Process)
- Task P0.7D-deferred-ideas

## Rules

Useful ideas outside Phase 0 scope are recorded here and not implemented in the current slice.
Each entry includes: idea, why deferred, likely future DevSpec, and evidence trigger.

Coding agents must append new entries when they encounter out-of-scope ideas and continue the
current slice without implementing them.

## Deferred entries

| ID | Idea | Why deferred | Likely future DevSpec | Evidence trigger |
| --- | --- | --- | --- | --- |
| D-001 | Draft ModelRuntime v0 (production `ModelRuntime` package) | DevSpec Section 5 forbids production `ModelRuntime` in Phase 0. Phase 0 exit is incomplete; `PHASE1_ENTRY_DECISION.md` not approved. | Phase 1A ModelRuntime DevSpec (post Phase 0 exit) | Phase 0 exit gate (DevSpec Section 110) satisfied; two proof adapters named; required semantic conformance subset selected; KJ approves Phase 1 Entry Decision |
| D-002 | P0.8 Stress Semantics execution (fault-server; CANCEL-001 / TIMEOUT-001 / RETRY-001 live) | P0.7C readiness decision: `READY_AFTER_LIVE_GATES`. Fault-server implementation blocked until G2/G3 live gates pass. First-live tranche explicitly excludes stress fixtures. | P0.8 Stress Semantics (execution slice); feeds Q-002 / Q-004 inputs | Minimum live core tranche complete; direct native credentials available; G5 gate evidence for cancellation, timeout, and retry semantics |
| D-003 | LiteLLM Proxy Server lane (server boundary) | Six required lanes (DevSpec Section 4) cover the LiteLLM Python SDK (`litellm-sdk`), not the Proxy Server. `litellm-sdk` probe manifest and P0.7A scope exclude virtual keys, gateway auth, router, and proxy administration. Proxy Server was never started in Phase 0 offline work. | Separate server-boundary DevSpec or optional audit extension | Finding or product need that SDK-only evidence cannot answer (e.g. virtual-key routing, proxy MCP tool path requiring FastAPI); explicit scope authorization beyond six-lane matrix |
| D-004 | Pydantic AI Gateway and Logfire audit | `pydantic-ai-agent` lane audits the Agent surface only, by design. P0.7B documents Gateway, Logfire, OpenTelemetry export, and Evals as out of boundary. Slim install lacks exporter/SDK; no Gateway client is constructed. | Post-Phase-0 instrumentation / gateway audit DevSpec (if justified) | Product decision to support Pydantic AI Gateway as a runtime path; live credential and endpoint policy authorized; instrumentation requirements defined |
| D-005 | Mirascope optional lane | DevSpec Section 54 trigger not met: accepted F1 findings N-01 and N-02 already exist (G6 satisfied offline); six lanes provide framework diversity; no finding requires another lightweight abstraction for confirmation. Roadmap marks mirascope lane blocked. | Optional Mirascope lane per DevSpec Section 54 | Condition 1 fails (F1 accepted); revisit only if conditions 2 or 3 become true (insufficient diversity for a key question, or a finding requires Mirascope confirmation) |
| D-006 | Custom `base_url` / gateway-routed compatibility lanes | Authorized and implemented as separate compatibility track (Compatibility Lab C0; evidence class `custom_endpoint_compatibility`). Not native evidence. Must not substitute for G2 or G3. | `research/compatibility-lab/docs/C0_DEVSPEC_v0.1.md` | Explicit authorization received; offline C0 complete; live remains blocked until fresh `ALMS_COMPAT_*` configuration |
| D-007 | EmbeddingRuntime sibling DevSpec (Q-005) | Explicit evidence-backed deferral recorded in `docs/P0.9_Q005_EMBEDDING_DEFERRAL.md` (P0.9-q005). EMBED-001 remains OPTIONAL / live_required without offline mock. A-007 stays open. EmbeddingRuntime not required for Phase 0 exit. | Sibling `EmbeddingRuntime` DevSpec (first alpha or later) per Q-005 outcome | Live EMBED-001 if authorized; product demand for first-alpha embeddings; A-007 outcome update |
| D-008 | L-01 human acceptance decision (LiteLLM SDK tool path) | Finding L-01 is proposed F2, not auto-accepted. `litellm.completion(tools=...)` couples to proxy MCP utilities requiring FastAPI, absent in SDK-only probe. Partial TOOL-001 path documented; no shared contract loss observed offline. Human review required per roadmap. | Resolution recorded in finding ledger; may affect litellm-sdk live tranche scope | KJ accepts, rejects, or defers L-01; follow-up live `completion(tools=...)` experiment if accepted; `litellm-sdk` live tranche gated on decision (per P0.7C) |

## Scope disclaimers

This document:

- does **not** authorize live runs
- does **not** close Phase 0
- does **not** change finding ledger status (including L-01 `proposed`)
- does **not** begin P0.8 implementation or Draft ModelRuntime v0
