# ALMS Development Specification v1.0

## Phase 0 — Runtime Audit Lab

### Executable Evidence Program for the Runtime-Independent Era

**Document ID:** `ALMS-DEV-P0-001`  
**Version:** 1.0 — Execution Candidate  
**Status:** Ready for KJ review; implementation must not begin until the Entry Gate is acknowledged  
**Canonical Source:** *ALMS Bible v1.0 — Strategic, Architectural, Research, and Ecosystem Canon*  
**Evidence Target:** `P0-E1`  
**Baseline:** ALMS v0.3.4 · `axtra-alms==0.3.0` · `alms-cli==0.1.10` · Agent Skill v0.4.0  
**Baseline Tag:** `v0.3.4` at release metadata commit `0043e9e`  
**Implementation Commit Recorded by the Bible:** `95592f6`  
**Date:** 10 July 2026  
**Decision Authority:** KJ (Ter), Axtra Intellion  
**Prepared with:** Gaen (GPT-5.5 Thinking) as specification co-author

---

> **Execution statement.** This document is the first Development Specification derived from the ALMS Bible. It is deliberately narrow. It does not refactor the ALMS core, freeze a public runtime API, split repositories, publish a registry, or add a second language. Its sole mission is to build a reproducible experimental laboratory that reveals how materially different model runtimes actually behave, preserves the raw evidence, normalizes only what can be normalized honestly, and produces the decision inputs required for Phase 1A.

> **Primary success criterion.** Phase 0 is not successful because the test suite is green. It is successful when the audit produces reproducible evidence and at least one unexpected finding changes a design assumption that would otherwise have shaped the Draft ModelRuntime incorrectly.

# Document Status, Authority, and Reader Guide

This DevSpec is an implementation document, not another strategy essay. The ALMS Bible remains authoritative for long-term direction and locked architectural decisions. This DevSpec is authoritative for the execution details of Phase 0. Audit evidence is authoritative for observed runtime behavior. Current repository state is authoritative for what the code actually contains at execution time.

The order of authority is therefore contextual rather than absolute:

1. **Verified repository truth** decides what exists at the start of execution.
2. **Locked Bible decisions** constrain what Phase 0 is allowed to become.
3. **This DevSpec** defines the approved experiment, file boundaries, work slices, tests, and gates.
4. **Phase 0 evidence** may invalidate provisional assumptions and must be reflected in the Phase 0 decision memo.
5. **Earlier research reports and code sketches** are supporting evidence only and may not override the Bible or this DevSpec.

If this DevSpec conflicts with a LOCKED Bible decision, implementation must stop and the DevSpec must be corrected. If the repository has drifted from the recorded v0.3.4 baseline, the drift must be recorded in the Baseline Manifest before implementation proceeds. The coding agent is not authorized to reinterpret the scope silently.

## Reader Roles

- **KJ / Ter:** decision authority, scope owner, credential owner, budget owner, and final Phase 0 gate reviewer.
- **Coding agent:** implementation executor. It may propose deviations but may not expand scope, publish releases, rename repositories, or convert provisional research structures into production APIs.
- **Gaen / Claude / other reviewers:** advisory reviewers. They may identify missing evidence, unsafe assumptions, or overfitting but do not supersede KJ's decision authority.
- **Future contributors:** should be able to reproduce the experiment from this document, the committed audit workspace, and the approved evidence revision.

## Decision Status Used in This DevSpec

- **REQUIRED:** must be implemented before Phase 0 can complete.
- **OPTIONAL:** may be implemented when the trigger condition is met.
- **FORBIDDEN IN PHASE 0:** intentionally outside scope; implementation must stop if work drifts here.
- **PROVISIONAL:** implementation detail allowed for the audit but explicitly not a future ALMS API commitment.

# Table of Contents

- **Part I — Purpose, Scope, and Traceability**
- **Part II — Baseline Preservation and Entry Gate**
- **Part III — Experimental Method and Comparison Design**
- **Part IV — Workspace and Repository Architecture**
- **Part V — Audit Data Model and Evidence Schemas**
- **Part VI — Harness and Probe Process Architecture**
- **Part VII — Runtime Lane Specifications**
- **Part VIII — Fixture Corpus and Semantic Invariants**
- **Part IX — Feature-Specific Audit Protocols**
- **Part X — Live Execution, Cost, Reproducibility, and Security**
- **Part XI — Testing Strategy and Quality Gates**
- **Part XII — Incremental Development Slices**
- **Part XIII — Findings, Synthesis, and Decision Memo**
- **Part XIV — Failure Policy, Stop Conditions, and Rollback**
- **Part XV — Phase 0 Exit and Phase 1A Handoff**
- **Part XVI — Requirement Traceability and Implementation Checklists**
- **Appendices A–J**

# Part I — Purpose, Scope, and Traceability

## 1. Mission

Phase 0 exists to answer one question with executable evidence:

> **What semantic boundary can ALMS own honestly across materially different model runtimes without merely renaming LangChain or OpenAI semantics?**

The experiment must separate four things that are often confused:

1. **Provider behavior** — what the model vendor and remote API actually do.
2. **Runtime/framework behavior** — what LangChain, LiteLLM, PydanticAI, or another layer adds, changes, retries, normalizes, or hides.
3. **Audit normalization** — the minimum common representation required to compare evidence.
4. **Future ALMS semantics** — decisions that will be made only after the evidence exists.

The audit is not allowed to begin by assuming the final `ModelRuntime` interface. The temporary audit harness must be intentionally disposable and must not become the production contract by inertia.

## 2. Bible Decisions Implemented

| Bible reference | Status | DevSpec consequence |
| --- | --- | --- |
| ADR-002 — ALMS owns internal model semantics | LOCKED | The audit must identify candidate request, response, event, capability, usage, error, structured-output, cancellation, and timeout semantics without exposing framework types. |
| ADR-003 — LangChain becomes an adapter | LOCKED | LangChain is audited as the compatibility baseline, not treated as the semantic source. |
| ADR-004 — ModelRuntime before AgentRuntime | LOCKED | Phase 0 audits model-runtime semantics only. AgentRuntime and WorkflowRuntime are forbidden scope. |
| ADR-005 — EmbeddingRuntime is separate | PROVISIONAL | Embeddings are probed separately and may be excluded from the first alpha based on evidence. |
| ADR-006 — Conformance tests semantic invariants | LOCKED | Assertions compare invariants rather than exact prose, chunk boundaries, or raw SDK objects. |
| ADR-014 — Delay repository split | LOCKED | The audit lives inside the current `alms` repository as an isolated research workspace. No repo rename or extraction. |
| ADR-020 — Broad research ends | LOCKED | Remaining semantic questions are answered by code, runs, evidence, and findings rather than another broad framework survey. |
| Bible §131 / §143 | LOCKED direction | Phase 0 must produce audit harness, fixtures, probes, raw and normalized results, finding log, cost record, and decision memo. |
| Bible Q-001 to Q-005 | OPEN | Phase 0 must produce decision inputs for structured-output shape, cancellation ownership, required event types, provider extensions, and embedding scope. |

## 3. In Scope

Phase 0 includes all of the following:

- a standalone audit workspace under the current `alms` repository;
- a language-neutral fixture format expressed as JSON-compatible data;
- an audit-only probe process protocol that isolates runtime dependencies;
- isolated runtime probes for the required lanes;
- raw artifact preservation and safe sanitization;
- a normalized transcript format for comparison;
- invariant evaluation that distinguishes semantic failure from unsupported capability;
- live-call controls, call-count controls, timeout controls, and cost recording;
- deterministic offline tests for harness behavior;
- selected live runs against real providers;
- findings with exact reproduction commands and raw evidence references;
- a machine-readable result matrix;
- a human-readable Phase 0 Audit Report;
- a Contract Implications Decision Memo;
- an explicit Phase 1A Entry Decision.

## 4. Required Runtime Lanes

The core audit set is:

1. LangChain compatibility lane.
2. OpenAI native SDK lane.
3. Anthropic native SDK lane.
4. Gemini native SDK lane.
5. LiteLLM lane.
6. PydanticAI lane.

Mirascope is optional and is activated only by a trigger defined later in this DevSpec.

## 5. Forbidden in Phase 0

The following are explicitly outside scope:

- no production `ModelRuntime` package;
- no core decoupling from LangChain;
- no public adapter package;
- no release of `axtra-alms` or `alms-cli`;
- no package or repository rename;
- no `alms-python`, `alms-typescript`, or Rust repository extraction;
- no AgentRuntime contract;
- no WorkflowRuntime contract;
- no MCP implementation;
- no A2A implementation;
- no public pack registry;
- no production skill resolver;
- no TypeScript implementation;
- no Rust experiment;
- no model intelligence benchmark;
- no framework popularity ranking;
- no promise that the audit probe API becomes the ALMS runtime API.

A coding agent that encounters a useful idea outside this scope must record it in `docs/deferred-ideas.md` and continue the current slice without implementing it.

## 6. Success Definition

Phase 0 succeeds only when all of these statements are true:

- the stable v0.3.4 baseline is preserved;
- the audit can be rerun from pinned code and recorded configuration;
- every required core lane is executed or explicitly blocked with a documented reason;
- at least one non-OpenAI native vendor lane executes successfully before Phase 1A is authorized;
- every mandatory semantic dimension has evidence;
- raw evidence is preserved separately from normalized interpretation;
- at least one finding is classified as **CONTRACT_CHANGING** and accepted by KJ;
- the finding changes a concrete assumption that would otherwise have appeared in Draft ModelRuntime v0;
- Q-001, Q-002, Q-003, and Q-005 receive evidence-backed recommendations or explicit deferrals;
- no production ALMS behavior changes;
- the Phase 1A Entry Decision names the two proof adapters and the required conformance subset.

# Part II — Baseline Preservation and Entry Gate

## 7. Stable Baseline

The experiment starts from the known-good public baseline recorded in the Bible:

```text
ALMS ecosystem release: v0.3.4
Root package:            axtra-alms==0.3.0
CLI package:             alms-cli==0.1.10
Agent skill:             v0.4.0
Release tag commit:      0043e9e
Implementation commit:   95592f6
Status:                   external-tester ready
```

The fresh-user evidence that must remain available includes:

- documented `uv sync` path: 31/31 generated tests pass;
- `uv sync --all-extras`: 31/31 pass with no real provider calls;
- tested pip-only path: 16/16 pass;
- all previously identified first-user blockers closed;
- no release-blocking issues.

Phase 0 does not need to rerun the entire public fresh-user study before every audit run. It does need a baseline manifest that records the current Git state and a pre/post regression command set sufficient to prove that research work did not alter public behavior.

## 8. Entry Gate

Implementation may begin only after the following preflight checklist is completed and recorded in `research/runtime-audit/docs/ENTRY_GATE.md`.

```text
[ ] Worktree state recorded
[ ] Current branch recorded
[ ] Current HEAD recorded
[ ] v0.3.4 tag relationship recorded
[ ] Any drift from Bible baseline explained
[ ] Existing relevant tests green
[ ] No unrelated dirty files will be touched
[ ] New research branch created
[ ] Live credential owners identified
[ ] Live budget cap acknowledged
[ ] Secret handling rules acknowledged
[ ] Phase 0 non-goals acknowledged
```

## 9. Baseline Manifest

Create `research/runtime-audit/evidence/baseline-manifest.json` with at least:

```json
{
  "captured_at": "ISO-8601 timestamp",
  "repository": "alms",
  "branch": "string",
  "head": "git sha",
  "tag_relationship": "string",
  "worktree_clean": true,
  "python": "version",
  "uv": "version",
  "os": "string",
  "baseline_commands": [],
  "baseline_results": [],
  "known_non_blocking_findings": [
    "bare alms cp1252 display issue",
    "MODEL_PROVIDER missing from AI .env.example",
    "provider boundary under-explained in README"
  ]
}
```

The manifest is historical evidence. It must not be rewritten to make later results look cleaner.

## 10. Branch and Commit Policy

Recommended branch:

```text
research/runtime-audit-phase0
```

No public release is created from this branch. No package versions are bumped. No tags implying stable compatibility are created. If a research tag is needed after completion, use an explicitly non-release form such as:

```text
research/runtime-audit-p0-e1
```

Each development slice should end in a focused commit. The coding agent must not use `git add .`. It must stage only intended paths, show the staged diff summary, run the slice gate, and then commit.

## 11. Production Code Boundary

The following paths are read-only during Phase 0 unless KJ explicitly approves a deviation:

- production ALMS source code;
- current scaffold templates;
- CLI production behavior;
- package metadata used for public publishing;
- current agent skill repository;
- `agent-native-backend` repository.

The preferred implementation shape is a standalone nested research project. Root-level modifications should be unnecessary. If a root configuration change becomes necessary, implementation must stop and create a deviation proposal explaining why isolation failed.

# Part III — Experimental Method and Comparison Design

## 12. Scientific Method

The audit follows this sequence:

```text
Question
→ Assumption
→ Fixture
→ Runtime execution
→ Raw evidence
→ Normalized interpretation
→ Invariant evaluation
→ Finding
→ Contract implication
→ Decision
```

The order matters. A future contract sketch may guide what questions to ask, but it may not dictate what the evidence is allowed to show.

## 13. Experimental Units

The primary unit is not “a framework.” It is a fully identified execution lane:

```text
runtime layer + provider + model + runtime version + configuration
```

For example, these are different lanes:

```text
OpenAI native SDK + OpenAI + Model A
LangChain + OpenAI + the same Model A
LiteLLM + OpenAI + the same Model A
PydanticAI + OpenAI + the same Model A
Anthropic native SDK + Anthropic + Model B
Gemini native SDK + Google + Model C
```

This distinction lets the audit separate framework effects from provider/model effects.

## 14. Comparison Sets

### 14.1 Control Set A — Same Provider, Different Runtime Layer

Where credentials and model support allow, run the same OpenAI provider/model through:

- OpenAI native SDK;
- LangChain;
- LiteLLM;
- PydanticAI.

This set isolates runtime/framework behavior: fallback mode selection, retries, error wrapping, event transformation, usage changes, and tool-call representation.

### 14.2 Diversity Set B — Different Native Vendors

Run native probes against at least:

- one Anthropic model;
- one Gemini model.

This set exists to detect OpenAI-shape bias in messages, tool semantics, streaming, structured output, and usage.

### 14.3 Optional Control Set C — Same Non-OpenAI Provider Through an Abstraction

If budget and compatibility allow, route the same Anthropic or Gemini model through LiteLLM or PydanticAI and compare against the native lane. This is optional because the first two comparison sets are sufficient for Phase 0.

## 15. Model Selection Policy

Model IDs are not hardcoded in the committed DevSpec or fixture corpus. They are configuration values supplied at execution time and recorded in each run manifest. This avoids turning a fast-changing provider catalog into a source-code dependency.

Selection criteria:

- supports the feature being tested;
- is one of the cheapest suitable models available to the account;
- has low enough latency for repeated audit runs;
- exposes enough native semantics to create useful evidence;
- is configured identically across framework control lanes where possible.

The audit compares semantics, not intelligence. Do not select a more expensive model merely to improve prose quality.

## 16. Assumption Register

Before live execution begins, create `docs/assumptions.md`. Each assumption must have an ID and a falsification condition.

| ID | Initial assumption | What would falsify or modify it |
| --- | --- | --- |
| A-001 | Structured output can be represented as one generic capability. | Evidence shows materially different native, tool-based, prompted, or retry-backed modes that affect application semantics. |
| A-002 | Streaming can be normalized as a simple sequence of text deltas plus terminal completion. | Tool-call argument streaming, usage timing, or provider events require richer ordering semantics. |
| A-003 | Caller task cancellation is a sufficient cross-runtime cancellation model. | A runtime continues provider work, hides cancellation, or exposes a distinct cancellation handle that changes observable semantics. |
| A-004 | Timeouts can be represented as one normalized error category. | Framework retry behavior or provider-side execution creates multiple operationally distinct timeout outcomes. |
| A-005 | Usage can be attached only to the final response. | Some runtimes expose incremental or partial usage, especially during streaming or cancellation. |
| A-006 | Tool calls can be normalized as name + JSON arguments + call ID. | A provider/framework lacks stable IDs, streams ambiguous argument fragments, or supports non-JSON tool semantics. |
| A-007 | Embeddings should ship as a sibling contract in the first alpha. | Audit shows low value, incompatible lifecycle, or insufficient cross-runtime evidence for the first alpha. |
| A-008 | A small common event vocabulary will preserve useful semantics. | Important provider-native behavior cannot be represented without destructive flattening or an extension channel. |

The assumption register is frozen for history once the first live run begins. Later edits must append outcomes rather than rewrite the original assumptions.

## 17. Outcome Classification

Every fixture × lane result must use exactly one primary status:

| Status | Meaning |
| --- | --- |
| PASS | The lane satisfied the declared semantic invariants. |
| PASS_WITH_EXTENSION | The invariants passed, but important runtime-native semantics require extension metadata or a finding. |
| UNSUPPORTED_DECLARED | The runtime/provider explicitly reports that the feature is not supported. |
| UNSUPPORTED_OBSERVED | The feature is advertised or attempted but cannot be completed in the tested configuration. |
| BLOCKED_CONFIGURATION | Required credential, model access, account permission, or environment is unavailable. |
| FAIL_INVARIANT | Execution completed but violated a semantic invariant. |
| ERROR_RUNTIME | The runtime or SDK failed before a meaningful semantic result could be evaluated. |
| INCONCLUSIVE | Evidence is ambiguous or nondeterministic and requires a follow-up experiment. |

A red X is not an adequate result. `UNSUPPORTED`, `BLOCKED`, `FAIL_INVARIANT`, and `ERROR_RUNTIME` have different architectural meanings and must remain distinct.

## 18. Finding Severity

| Level | Meaning | Phase consequence |
| --- | --- | --- |
| F0 — STRATEGY_INVALIDATING | Evidence challenges a LOCKED Bible premise. | Stop Phase 0 and open a Bible revision before continuing. |
| F1 — CONTRACT_CHANGING | Evidence changes the expected shape or semantics of Draft ModelRuntime v0. | Required for successful Phase 0 exit. |
| F2 — CAPABILITY_SHAPING | Evidence changes capability levels, conformance profiles, or adapter expectations. | Record and carry into Phase 1A. |
| F3 — IMPLEMENTATION_NOTE | Runtime-specific behavior matters for adapter implementation but not the shared contract. | Preserve as adapter guidance. |
| F4 — ENVIRONMENTAL | Version, OS, credential, or provider-access issue. | Record for reproducibility; does not satisfy the unexpected-finding gate. |

The unexpected-finding gate is satisfied only by an accepted F1 finding. F2 and lower findings are valuable but do not prove that the audit challenged the contract assumptions.

# Part IV — Workspace and Repository Architecture

## 19. Location

The audit is implemented under the existing `alms` repository:

```text
alms/
└── research/
    └── runtime-audit/
```

This location is transitional and intentionally non-production. It preserves the current repository while avoiding a premature split.

## 20. Dependency Isolation Decision

Each runtime probe must run in its own isolated environment. The audit must not install LangChain, LiteLLM, PydanticAI, OpenAI, Anthropic, and Gemini SDK dependencies into one shared environment and then interpret dependency resolution side effects as runtime semantics.

The harness and each probe therefore use separate Python projects and separate lockfiles.

This is a REQUIRED design decision for Phase 0.

## 21. Canonical Workspace Layout

```text
research/runtime-audit/
├── README.md
├── LICENSE-NOTE.md
├── .gitignore
├── configs/
│   ├── audit.default.toml
│   ├── runtimes.example.toml
│   └── comparison-sets.example.toml
├── spec/
│   ├── fixture.schema.json
│   ├── probe-request.schema.json
│   ├── probe-response.schema.json
│   ├── normalized-transcript.schema.json
│   ├── result.schema.json
│   ├── finding.schema.json
│   └── run-manifest.schema.json
├── fixtures/
│   ├── generation/
│   ├── roles/
│   ├── structured/
│   ├── tools/
│   ├── streaming/
│   ├── cancellation/
│   ├── timeout/
│   ├── retry/
│   ├── errors/
│   ├── usage/
│   ├── embeddings/
│   └── multimodal/
├── harness/
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── src/alms_audit/
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── config.py
│   │   ├── planner.py
│   │   ├── runner.py
│   │   ├── protocol.py
│   │   ├── subprocess_runner.py
│   │   ├── redaction.py
│   │   ├── budget.py
│   │   ├── environment.py
│   │   ├── storage.py
│   │   ├── invariants/
│   │   ├── normalizers/
│   │   ├── reporting/
│   │   └── models/
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── fixtures/
├── probes/
│   ├── langchain/
│   ├── openai-native/
│   ├── anthropic-native/
│   ├── gemini-native/
│   ├── litellm/
│   ├── pydanticai/
│   └── mirascope/
├── tools/
│   ├── fault-server/
│   └── fixture-lint/
├── runs/                  # gitignored local execution output
├── evidence/
│   ├── baseline-manifest.json
│   └── P0-E1/             # created only after review and sanitization
└── docs/
    ├── ENTRY_GATE.md
    ├── assumptions.md
    ├── findings/
    ├── PHASE0_AUDIT_REPORT.md
    ├── CONTRACT_IMPLICATIONS.md
    ├── PHASE1_ENTRY_DECISION.md
    ├── deviations.md
    └── deferred-ideas.md
```

## 22. Why the Harness and Probes Are Separate

The harness owns experiment planning, budget checks, subprocess execution, raw artifact collection, normalization orchestration, invariant evaluation, result storage, and reports. A probe owns only runtime-specific execution and safe serialization of what happened.

This separation prevents the temporary audit interface from becoming the future `ModelRuntime` by accident. It also allows a future TypeScript or Rust probe to participate in the same audit protocol without importing Python ALMS code.

## 23. Probe Process Protocol v0

The audit uses a tiny JSON-based subprocess protocol. This protocol is explicitly marked:

```text
PROVISIONAL — AUDIT INFRASTRUCTURE ONLY
NOT THE ALMS RUNTIME CONTRACT
```

The harness invokes each probe as a child process. The probe receives one JSON request and writes one JSON response. Logs go to stderr. Raw runtime/provider artifacts are written into a run-specific directory.

The process boundary provides:

- dependency isolation;
- crash isolation;
- timeout enforcement;
- future cross-language compatibility;
- reproducible invocation commands;
- a clear place to capture stdout, stderr, exit code, and wall-clock duration.

## 24. Probe Project Requirements

Every required probe directory contains:

```text
probe-id/
├── pyproject.toml
├── uv.lock
├── README.md
├── probe.manifest.json
├── src/probe/
│   ├── __init__.py
│   ├── __main__.py
│   ├── execute.py
│   ├── serialize.py
│   └── redact.py
└── tests/
```

Each probe must be runnable independently with a command recorded in its README.

## 25. No Shared Runtime Dependency Environment

The harness may use common utilities such as JSON Schema validation and TOML parsing. It must not import selected runtime SDKs. The OpenAI probe environment owns the OpenAI SDK. The LangChain probe environment owns LangChain. The LiteLLM probe environment owns LiteLLM. The same rule applies to all lanes.

If one probe's dependency set cannot resolve, that is recorded as a lane-specific environment finding rather than breaking the entire lab.

# Part V — Audit Data Model and Evidence Schemas

## 26. Data Model Principle

Every run has two truths:

1. **Raw evidence** — the closest safely serializable representation of the SDK/provider behavior.
2. **Normalized interpretation** — the audit's attempt to describe that behavior in a common vocabulary.

The normalized result must always point back to the raw artifact. A normalizer is not allowed to delete inconvenient semantics silently.

## 27. Fixture Schema

The fixture format is language-neutral and JSON-compatible. It describes intent, execution controls, and expected invariants rather than SDK method calls.

Required top-level fields:

```text
spec
id
feature
summary
messages or embedding_inputs
requirements
execution
expected_invariants
```

Representative shape:

```json
{
  "spec": "alms.dev/runtime-audit-fixture/v0",
  "id": "structured-person-001",
  "feature": "structured_output",
  "summary": "Extract a flat typed object",
  "messages": [
    {
      "role": "user",
      "parts": [
        {"kind": "text", "text": "Alice is 30 years old."}
      ]
    }
  ],
  "output_schema": {
    "type": "object",
    "required": ["name", "age"],
    "properties": {
      "name": {"type": "string"},
      "age": {"type": "integer"}
    },
    "additionalProperties": false
  },
  "requirements": {
    "live_required": true,
    "capabilities": ["generation", "structured_output"]
  },
  "execution": {
    "temperature": 0,
    "max_output_tokens": 128,
    "timeout_ms": 30000,
    "stream": false,
    "max_attempts": 1
  },
  "expected_invariants": {
    "schema_valid": true,
    "fields": {"name": "Alice", "age": 30}
  }
}
```

## 28. Requirement Vocabulary

A fixture may declare:

- `live_required`;
- `supports_mock_mode`;
- required capabilities;
- accepted capability modes;
- whether a provider-specific extension is allowed;
- whether the case belongs to base, stress, or optional tier.

The planner must not execute a case against a lane that is impossible by configuration unless the audit explicitly wants to test unsupported behavior.

## 29. Runtime Lane Metadata

Each run result records three independent identifiers:

```text
runtime layer
provider
model
```

Never collapse these into one `provider` string.

Example:

```json
{
  "runtime_layer": "langchain",
  "runtime_version": "captured at run time",
  "provider": "openai",
  "model": "configured model id",
  "transport": "direct"
}
```

## 30. Raw Run Manifest

A raw run must preserve:

- fixture ID and hash;
- probe ID and version;
- package versions;
- provider and model;
- start/end timestamps;
- exit code;
- stdout path;
- stderr path;
- serialized request path;
- serialized response/event path;
- retry count observed by the probe where measurable;
- timeout or cancellation action;
- redaction summary.

The raw manifest is not the normalized transcript.

## 31. Normalized Transcript v0

The transcript is an audit comparison tool. It is not the future ALMS event contract.

Candidate event types:

```text
response_started
text_delta
tool_call_started
tool_call_arguments_delta
tool_call_completed
structured_output_completed
usage_updated
response_completed
cancelled
error
provider_extension
```

Every event contains:

```text
sequence
type
timestamp_relative_ms
data
raw_ref
```

`provider_extension` exists so the normalizer can preserve semantically important evidence without pretending it already belongs in the common contract.

## 32. Usage Record

Usage fields are nullable and provenance-aware:

```text
input_tokens
output_tokens
total_tokens
cached_input_tokens
reasoning_tokens
other_provider_tokens
cost_reported
cost_estimated
currency
provenance
finality
```

Missing usage is not converted to zero. Partial usage after cancellation must be marked partial.

## 33. Error Candidate Taxonomy

The audit uses a candidate taxonomy for comparison:

```text
authentication
authorization
rate_limit
invalid_request
model_not_found
timeout
network
provider_server
content_policy
schema_validation
cancelled
unsupported
unknown
```

This taxonomy is provisional. The audit must preserve native exception class, status code, provider error code, retry headers where safe, and raw reference.

## 34. Result Record

Each fixture × lane execution produces:

```json
{
  "spec": "alms.dev/runtime-audit-result/v0",
  "run_id": "string",
  "fixture_id": "string",
  "lane_id": "string",
  "status": "PASS",
  "observed_capabilities": {},
  "normalized_transcript": "path",
  "raw_manifest": "path",
  "invariants": [],
  "timing": {},
  "usage": {},
  "cost": {},
  "notes": [],
  "finding_refs": []
}
```

## 35. Run Manifest

Every audit run receives an immutable manifest including:

- run ID;
- Git SHA;
- harness lock hash;
- probe lock hashes;
- fixture corpus hash;
- OS and Python versions;
- selected lanes;
- selected fixtures;
- model configuration;
- credential presence booleans only;
- budget configuration;
- command line;
- start/end time.

The manifest must never contain secret values.

## 36. Finding Schema

Every finding includes:

```text
id
severity
status
runtime lanes
fixture IDs
assumption ID
expected behavior
observed behavior
reproduction command
raw evidence refs
normalized evidence refs
semantic impact
contract implication
confidence
follow-up experiment
KJ decision
```

A finding is not accepted merely because the coding agent wrote it. F1 and F0 findings require human review.

# Part VI — Harness and Probe Process Architecture

## 37. Harness Pipeline

```text
Config Loader
    ↓
Fixture Validator
    ↓
Matrix Planner
    ↓
Credential / Budget Preflight
    ↓
Probe Subprocess Runner
    ↓
Raw Artifact Recorder
    ↓
Runtime-Specific Normalizer
    ↓
Invariant Evaluator
    ↓
Result Store
    ↓
Matrix Summarizer
    ↓
Finding Workflow
```

## 38. Harness CLI

The harness exposes one internal executable, recommended command name:

```text
alms-audit
```

Required commands:

```text
alms-audit validate
alms-audit list-fixtures
alms-audit list-lanes
alms-audit plan
alms-audit run
alms-audit normalize
alms-audit evaluate
alms-audit summarize
alms-audit verify-evidence
```

The CLI is internal research tooling. It is not added to the public `alms` CLI.

## 39. Plan Command

`plan` must show, without making live calls:

- selected fixtures;
- selected lanes;
- expected call count;
- skipped cases and reasons;
- missing credentials;
- configured models;
- hard budget;
- maximum output tokens;
- timeout settings.

A live run must be previewable before spending money.

## 40. Run Command Safety

A live run requires an explicit flag such as:

```text
--live --confirm-live
```

Without both, the runner may execute only offline or mockable cases.

The runner refuses to start when:

- hard budget is zero or absent for a live run;
- estimated call count exceeds the configured cap;
- required result directories are not writable;
- fixture or schema validation fails;
- the branch/worktree policy is violated unless an override is recorded.

## 41. Subprocess Invocation

The harness invokes a probe with a command equivalent to:

```text
uv run --project probes/<probe-id> python -m probe <request.json>
```

The request contains:

- protocol version;
- run ID;
- fixture path;
- lane configuration;
- output directory;
- timeout/cancellation controls;
- redaction mode.

The probe writes only one machine-readable response to stdout. Diagnostic logs go to stderr. The harness captures both.

## 42. Probe Responsibilities

A probe must:

- load the fixture;
- translate it to runtime-native calls;
- execute exactly the configured number of attempts;
- avoid hidden audit-level fallback;
- capture runtime-native responses and events;
- serialize raw evidence safely;
- report observed attempt count where possible;
- return a probe response manifest.

A probe must not:

- decide whether the lane passed the ALMS invariant;
- rewrite a failed runtime call into a fake success;
- silently choose a different provider/model;
- hide framework retries;
- discard native events because the normalized vocabulary lacks a field.

## 43. Normalizer Responsibilities

A normalizer converts serialized raw evidence into the candidate audit vocabulary. It may be runtime-specific. It must preserve raw references and emit `provider_extension` events when meaningful semantics do not fit.

The normalizer must not:

- invent missing usage;
- claim a native structured-output mode when a framework used prompting or tools;
- claim cancellation stopped provider work unless evidence supports that statement;
- convert every exception into a generic error before native details are stored;
- merge tool calls that have distinct provider call IDs.

## 44. Invariant Evaluation

Invariants are pure functions over fixture + normalized result + selected raw metadata. They must be deterministic and unit-tested.

Examples:

```text
schema_valid
expected_fields_equal
non_empty_assistant_content
expected_tool_name
expected_tool_arguments
tool_call_count
terminal_state_present
stream_has_monotonic_sequence
usage_not_fabricated
error_category_present
```

The evaluator does not judge prose style or model intelligence.

## 45. Planner Rules

The planner builds the matrix from:

- fixture requirements;
- lane configuration;
- probe manifest;
- comparison-set selection;
- cost tier;
- credential availability.

The planner must explain every skip. A missing result with no explanation is a harness failure.

## 46. Evidence Directories

`runs/` is gitignored and contains complete local execution output. After review, a selected sanitized evidence revision is copied into:

```text
evidence/P0-E1/
```

The committed revision contains:

- run manifests;
- sanitized raw artifacts required to support findings;
- normalized results;
- matrix JSON/CSV;
- cost ledger;
- package/environment snapshots;
- accepted findings;
- audit report;
- contract implications;
- phase-entry decision.

Do not commit every noisy raw run automatically.

# Part VII — Runtime Lane Specifications

## 47. Lane Taxonomy

Each lane is defined by:

```text
lane_id
runtime_layer
provider
model_config_key
probe_id
comparison_set
credential_requirements
feature expectations
```

The exact model ID is supplied through execution configuration and captured in the run manifest.

## 48. LangChain Lane

**Role:** compatibility baseline and current-assumption detector.

Required observations:

- message conversion behavior;
- structured-output strategy selection;
- tool binding and tool-call representation;
- streaming chunk/event transformation;
- callback or tracing side effects if enabled by default;
- retry behavior;
- exception wrapping;
- usage propagation;
- cancellation behavior at the async task boundary.

Special rule: the probe must record the concrete LangChain types encountered in raw evidence, but normalized results must not expose them as common audit types.

## 49. OpenAI Native Lane

**Role:** direct SDK proof candidate and control-provider anchor.

Required observations:

- direct message/request semantics;
- native structured output mode;
- function/tool calls and call IDs;
- parallel tool calls where the configured model supports them;
- streaming event categories;
- usage timing;
- cancellation and timeout behavior;
- native exception taxonomy.

The DevSpec does not assume this lane becomes the Phase 1 native proof adapter. Official selection happens after Phase 0.

## 50. Anthropic Native Lane

**Role:** non-OpenAI vendor diversity.

Required observations:

- system/message role differences;
- content block semantics;
- tool-use blocks and IDs;
- structured-output path actually used in the selected SDK/model configuration;
- streaming block/event ordering;
- usage and cache metadata;
- error taxonomy;
- cancellation and timeout behavior.

A successful live Anthropic or Gemini lane is required before Phase 1A to reduce vendor-shape bias.

## 51. Gemini Native Lane

**Role:** schema, multimodal, message, and tool diversity.

Required observations:

- role/content-part mapping;
- structured response behavior;
- function/tool semantics;
- streaming chunk behavior;
- usage metadata availability;
- multimodal input handling;
- error and timeout behavior.

The multimodal fixture is optional for the base gate but required if the configured model supports it and cost remains within budget.

## 52. LiteLLM Lane

**Role:** broad routing/normalization layer.

The primary comparison should use the same underlying provider/model as a native lane. Required observations:

- what fields are normalized to OpenAI-like shapes;
- what provider-specific semantics remain available;
- structured-output behavior and fallbacks;
- tool-call normalization;
- exception mapping;
- retry behavior;
- usage and cost fields;
- streaming behavior.

The lane must record whether it is using LiteLLM as an in-process SDK or a proxy/gateway. Phase 0 should choose one mode for the primary lane and may test the other only as a follow-up.

## 53. PydanticAI Lane

**Role:** typed-output and higher-level framework stress test.

Required observations:

- model/provider abstraction boundary;
- output modes used;
- validation and retry behavior;
- tool execution ownership;
- streaming partial-output behavior;
- cancellation behavior;
- error wrapping;
- how much of the result is agent-level rather than model-level semantics.

This lane is especially important for detecting overlap between ALMS and a framework that already owns typed AI application semantics. It is not presumed to become an official Phase 1 adapter.

## 54. Optional Mirascope Lane Trigger

Implement Mirascope only when one of these conditions is true:

1. the six required lanes produce no accepted F1 finding;
2. framework diversity is still too OpenAI-shaped to answer a key question;
3. a Phase 0 finding specifically requires another lightweight abstraction for confirmation.

Do not implement it merely to increase the number of logos in the matrix.

## 55. Probe Manifest Requirements

Every probe declares:

- audit protocol version;
- runtime layer;
- runtime package(s);
- credential env variable names;
- configuration keys;
- claimed feature support;
- supported live/offline modes;
- known limitations;
- command used to run it.

Claimed feature support is evidence input, not final truth. The result matrix may contradict the manifest.

# Part VIII — Fixture Corpus and Semantic Invariants

## 56. Fixture Tiering

Fixtures are grouped into three tiers:

- **BASE:** cheapest cases required to establish minimum semantics.
- **STRESS:** cases intended to break assumptions and reveal event/cancellation/retry complexity.
- **OPTIONAL:** useful evidence that does not block Phase 0 unless activated by a finding.

## 57. Canonical Fixture Catalog

| ID | Tier | Feature | Case | Primary invariant |
| --- | --- | --- | --- | --- |
| GEN-001 | BASE | generation | Basic text generation | Non-empty assistant semantic content; terminal result exists |
| ROLE-001 | BASE | roles | System + user roles | Instructions and user input can be represented without silent loss |
| ROLE-002 | OPTIONAL | roles | Developer role / fallback | Record native support, remapping, rejection, or fallback |
| CONTENT-001 | OPTIONAL | generation | Multiple text parts | Part order and content preserved |
| STR-001 | BASE | structured_output | Flat object extraction | Schema valid; exact expected fields |
| STR-002 | BASE | structured_output | Nested object + array | Schema valid; nested values preserved |
| STR-003 | STRESS | structured_output | Enum and constraints | Record strict enforcement versus loose validation |
| STR-004 | STRESS | structured_output | Unsupported/edge schema keyword | Record request rejection, fallback, or schema reduction |
| STR-005 | STRESS | structured_output | Validation ambiguity | Reveal hidden framework retries or parser loops |
| TOOL-001 | BASE | tools | Single auto tool call | Expected name and parsed arguments |
| TOOL-002 | BASE | tools | Forced/required tool call | Record runtime control semantics |
| TOOL-003 | BASE | tools | Tool result round trip | Stable call linkage and continuation |
| TOOL-004 | STRESS | tools | Parallel independent tool calls | Count, IDs, ordering, parallel support |
| STREAM-001 | BASE | streaming | Text stream | Ordered deltas and terminal state |
| STREAM-002 | STRESS | streaming | Tool-call argument stream | Preserve call identity and argument fragments |
| STREAM-003 | OPTIONAL | streaming | Structured output stream | Record partial validation semantics |
| CANCEL-001 | STRESS | cancellation | Cancel after first useful delta | Caller termination, provider work evidence, final status, usage |
| TIMEOUT-001 | STRESS | timeout | Deadline during slow response | Timeout category and retry interaction |
| RETRY-001 | STRESS | retry | Fault-injected transient failure | Observed outbound attempt count and backoff behavior |
| ERROR-001 | BASE | errors | Invalid model identifier | Native error + normalized candidate category |
| ERROR-002 | OPTIONAL | errors | Authentication failure through safe local/mock path | Error wrapping without leaking secret material |
| USAGE-001 | BASE | usage | Non-stream usage | Presence, provenance, completeness |
| USAGE-002 | STRESS | usage | Streaming and cancelled usage | Timing, partial/final semantics |
| EMBED-001 | OPTIONAL | embeddings | Single text embedding | Vector output shape and usage metadata |
| EMBED-002 | OPTIONAL | embeddings | Batch embedding | Ordering and batch semantics |
| MM-001 | OPTIONAL | multimodal | Synthetic image + text | Content-part mapping and result semantics |

## 58. Fixture Design Rules

Every fixture must:

- use synthetic, non-sensitive data;
- fit within a small prompt and output budget;
- specify semantic invariants, not exact prose;
- declare whether the case is live-required;
- declare acceptable capability modes where appropriate;
- declare maximum attempts;
- avoid provider-specific fields in the common fixture unless inside an explicit extension object;
- be validated against the fixture schema before execution.

## 59. Structured Output Invariants

The audit must distinguish at least these observed modes:

```text
native_schema
tool_schema
prompted_json
parser_validation
framework_retry
unknown
```

A lane that returns schema-valid data through prompting is not equivalent to a lane with provider-enforced native structured output. Both may satisfy an application invariant, but the capability profile and failure semantics differ.

For each structured-output result record:

- requested mode if the runtime exposes one;
- observed or inferred mode;
- schema submitted to the provider/runtime;
- schema transformations performed by the framework;
- validation location;
- retry count;
- raw response before parsing where available.

## 60. Tool-Calling Invariants

The audit records:

- tool name;
- provider/runtime call ID if any;
- arguments as raw text and parsed JSON when available;
- whether schema validation occurred;
- whether tool choice was auto/required/forced;
- number of calls;
- ordering;
- parallelism claim;
- tool result linkage.

The future ALMS contract must not assume stable call IDs until the audit confirms what can be required.

## 61. Streaming Invariants

The audit does not require identical chunk sizes or event sequences. It requires enough evidence to answer:

- did the stream start;
- did semantic content arrive incrementally;
- were event sequences ordered;
- could tool-call arguments be associated with the correct call;
- when did usage become available;
- what terminal state was observed;
- what happened during cancellation or timeout.

## 62. Cancellation Invariants

The audit must separate:

1. caller coroutine/task cancellation;
2. SDK stream closure;
3. network request abortion;
4. provider-side work cessation, if observable;
5. billing/usage evidence;
6. final normalized status.

A runtime is not declared “fully cancelled” merely because the local task raised `CancelledError`.

## 63. Timeout Invariants

Record:

- timeout owner: harness, SDK, HTTP client, or provider;
- timeout duration requested;
- actual wall time;
- number of attempts;
- final exception type;
- whether the runtime retried;
- whether partial output existed;
- whether usage existed.

## 64. Retry Invariants

Hidden retries are a first-class finding source. The audit must attempt to observe:

- number of outbound attempts;
- retry trigger;
- backoff;
- whether validation failures trigger retries;
- whether retries are configurable;
- whether retry counts appear in logs or metadata.

The primary `RETRY-001` case should use an offline fault-injection server when possible so the audit can trigger deterministic 429/500/transient sequences without depending on a real provider incident.

## 65. Error Invariants

Every error result preserves:

- native exception class;
- provider/runtime error code;
- HTTP status where applicable;
- retryability hints;
- candidate normalized category;
- raw reference;
- redaction summary.

The candidate normalized category is not allowed to replace the native details.

## 66. Embedding Invariants

Embedding probes are separate from model-generation invariants. Record:

- vector count;
- dimensions;
- ordering;
- batch behavior;
- model/provider;
- usage;
- error semantics.

Phase 0 will use this evidence to decide Q-005: whether EmbeddingRuntime belongs in the first alpha or a later sibling DevSpec.

# Part IX — Feature-Specific Audit Protocols

## 67. Basic Generation Protocol

Run `GEN-001` on all required lanes first. This is the minimum live smoke test. The case should use a short prompt with an unambiguous small response. Do not evaluate wording quality.

Required evidence:

- request snapshot;
- raw response;
- normalized semantic content;
- terminal state;
- usage if available;
- timing;
- retries.

A lane that cannot complete basic generation is blocked from later live features until the cause is understood.

## 68. Role Mapping Protocol

`ROLE-001` tests the portable baseline of system and user roles. `ROLE-002` is optional and investigates developer-role support or fallback.

The probe must record runtime-native message objects. The normalizer must not silently relabel unsupported roles without recording the transformation.

## 69. Structured Output Protocol

Run in this order:

1. `STR-001` flat object;
2. `STR-002` nested structure;
3. `STR-003` enum/constraint stress;
4. `STR-004` schema edge case;
5. `STR-005` validation/retry ambiguity.

The first two establish capability. The later cases exist to reveal mode selection, schema reduction, silent fallback, and hidden retries.

The audit should answer Q-001 with evidence:

> Should future ALMS structured output be a request mode, a separate method, a capability-specific operation, or a combination?

No code API is frozen in Phase 0.

## 70. Tool Protocol

Run `TOOL-001` and `TOOL-003` on all lanes that claim tool support. `TOOL-002` records forced-tool control. `TOOL-004` is the parallel stress case.

The fixture tool implementation is deterministic and local. It must not call the network or use secrets.

## 71. Streaming Protocol

For text streaming:

- record every raw event/chunk with relative time;
- normalize semantic deltas;
- record first-byte/first-delta latency;
- record terminal completion;
- preserve final aggregated content if the runtime exposes it.

For tool-call streaming:

- preserve argument fragments;
- preserve call identity;
- record when the tool name becomes known;
- record when arguments become parseable;
- record terminal tool-call completion.

## 72. Cancellation Protocol

`CANCEL-001` starts a stream, waits for the first meaningful delta, then triggers cancellation through the lane's supported caller mechanism.

Measure:

- time from cancel request to caller return;
- exception/result observed;
- additional raw events after cancel request;
- network/SDK evidence if available;
- usage reported;
- process cleanup.

The case may need lane-specific execution mechanics. The common comparison is the outcome semantics, not identical cancellation code.

## 73. Timeout Protocol

`TIMEOUT-001` should use a deadline intentionally shorter than a known slow path or a controllable local fault server. A real provider timeout case should be used only when deterministic enough and within budget.

The result must identify the timeout owner.

## 74. Retry Protocol

Use a local fault-injection server where the runtime can target a compatible endpoint. The server should support scripted responses such as:

```text
attempt 1 → 429
attempt 2 → 500
attempt 3 → success
```

The audit records whether the runtime makes one, two, three, or more attempts and whether the behavior is configurable.

When a runtime cannot use the common fault server, document a lane-specific equivalent or mark the case unsupported/inconclusive. Do not fake identical coverage.

## 75. Usage Protocol

Usage is audited in non-streaming, streaming, and cancellation contexts. Record provenance and finality.

Questions:

- Is usage provider-reported or framework-estimated?
- Is it available only at completion?
- Does streaming require an option to include usage?
- Does cancellation return partial usage?
- Are cache or reasoning token fields preserved?

## 76. Error Protocol

Prefer safe, deterministic errors:

- invalid model identifier;
- malformed schema;
- unsupported feature request;
- local mock authentication failure.

Avoid deliberately hammering rate limits or sending many paid failing calls.

## 77. Embedding Protocol

Run embeddings only after core generation semantics are captured. Use small fixed inputs and the cheapest configured embedding model.

The output of this protocol is a scope decision, not a benchmark.

## 78. Multimodal Protocol

Use one tiny synthetic image generated locally and a short text instruction. No user photo, external download, or copyrighted asset is needed.

The audit records:

- content-part representation;
- upload/encoding method;
- provider/runtime transformations;
- result semantics;
- unsupported behavior.

# Part X — Live Execution, Cost, Reproducibility, and Security

## 79. Execution Tiers

### Tier 0 — Static

- schema validation;
- config validation;
- fixture linting;
- probe manifest validation;
- no runtime SDK execution.

### Tier 1 — Offline

- harness unit tests;
- subprocess protocol tests;
- normalizer tests with recorded fixtures;
- invariant tests;
- fault-server retry tests;
- no provider credentials.

### Tier 2 — Live Core

- base fixtures on selected lanes;
- structured output;
- single tool call;
- basic streaming;
- usage;
- basic errors.

### Tier 3 — Live Stress

- parallel tools;
- streamed tool calls;
- cancellation;
- timeout;
- ambiguous structured output;
- optional multimodal.

A developer should not jump directly to Tier 3 before Tier 0–2 are healthy.

## 80. Budget Policy

Default Phase 0 controls:

```text
Hard study budget:          USD 15
Default single-run soft cap: USD 2
Default max live calls/run:  80
Default max output tokens:   256
Automatic audit retries:     0, except the specific retry experiment
```

KJ may change these values before execution, but the configured values must be recorded in the run manifest. The runner must fail closed when the hard cap is absent or exceeded.

Because provider pricing changes, committed source code must not contain assumed permanent prices. A run may use a dated rate snapshot for estimates. Where trustworthy actual cost is unavailable, the audit must at least enforce call count and token limits.

## 81. Cost Strategy

Cost is reduced by:

- using small deterministic prompts;
- using the cheapest suitable model in each lane;
- reusing the same provider/model across framework control lanes;
- running base cases before stress cases;
- rerunning only ambiguous cases;
- using offline fault injection for retries;
- not repeating successful deterministic cases without reason.

## 82. Repeat Policy

Default is one live attempt per case. A result may be repeated up to three total attempts only when:

- the first result is nondeterministic or ambiguous;
- the fixture explicitly studies variability;
- a provider transient error prevents evaluation.

All repeats are visible. The audit must not average away meaningful semantic differences.

## 83. Credential Policy

Secrets are provided only through environment variables or the user's secure local mechanism. The repository contains names, never values.

Required rules:

- no `.env` with real values committed;
- no environment dump in logs;
- no Authorization headers in raw artifacts;
- no secret values in exceptions or subprocess arguments;
- credential presence recorded only as booleans;
- rotate any credential immediately if a leak is suspected.

## 84. Synthetic Data Policy

All prompts, tool data, embeddings, and images use synthetic fixed content. The audit must not process user conversations, private company data, customer data, or production secrets.

## 85. Raw Artifact Redaction

The redaction layer must remove or mask:

- API keys;
- authorization headers;
- signed URLs;
- cookies;
- bearer tokens;
- secret query parameters;
- environment values matching configured secret names.

Provider request IDs, timestamps, model IDs, usage, status codes, and synthetic prompt content may be preserved.

## 86. Reproducibility Snapshot

Each evidence revision records:

- Git SHA;
- Python version;
- OS;
- uv version;
- harness lock hash;
- each probe lock hash;
- package versions;
- fixture corpus hash;
- config hash;
- model IDs;
- provider endpoints if non-default;
- run commands.

## 87. Operating System Policy

Primary execution environment is Windows, matching the project's current development reality. The harness must use portable paths and subprocess APIs. At least the offline harness test suite should also pass in Linux CI if practical, but live provider parity across operating systems is not a Phase 0 gate.

## 88. Python Version Policy

Primary audit execution should begin on Python 3.13.x because the fresh external validation used Python 3.13.14. If a selected runtime SDK cannot install or operate on 3.13, do not silently downgrade the entire lab. Record the compatibility issue and, if needed, run that isolated probe on Python 3.12.x. The probe manifest must record the interpreter used.

## 89. Live Run Review

Before each Tier 2 or Tier 3 run, the operator reviews:

```text
selected lanes
selected fixtures
configured models
expected call count
budget caps
missing credentials
output directory
```

The runner prints the plan and requires explicit confirmation.

# Part XI — Testing Strategy and Quality Gates

## 90. Test Pyramid

Phase 0 has four test layers:

1. **Schema tests** — audit documents validate.
2. **Harness unit tests** — planning, redaction, budget, normalization, invariants.
3. **Probe integration tests** — each probe can execute against mock/recorded data or safe local stubs.
4. **Live audit runs** — real provider evidence.

A live pass does not replace unit tests. A unit pass does not prove runtime semantics.

## 91. Required Offline Commands

From the harness project:

```text
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Every probe must have an equivalent minimal command set documented in its README.

## 92. Harness Unit Test Categories

| Category | Required tests |
| --- | --- |
| Config | valid config, missing required keys, env substitution, unknown lane, invalid budget |
| Schema | valid fixtures, invalid fixtures, version mismatch, unknown fields policy |
| Planner | lane selection, capability skip, missing credential, call-count estimate, stress-tier selection |
| Budget | hard cap refusal, call cap refusal, zero-budget live refusal, offline allowance |
| Subprocess | success, non-zero exit, timeout, malformed stdout, stderr capture, path with spaces on Windows |
| Redaction | authorization header, bearer token, env secret, signed URL, false-positive resistance |
| Storage | immutable run manifest, raw path references, atomic writes, failed run preservation |
| Normalization | recorded raw samples per lane, extension preservation, missing usage remains null |
| Invariants | pass/fail determinism, unsupported distinction, schema evaluation, tool call count |
| Reporting | matrix generation, no missing statuses, finding links, cost totals |

## 93. Probe Test Requirements

Each required probe must prove:

- manifest validates;
- request parsing works;
- missing credential returns a structured blocked response;
- SDK import/version capture works;
- raw serialization works;
- secret redaction works;
- unsupported fixture kind returns explicit status;
- a recorded sample can be normalized by the harness.

## 94. Golden Test Policy

Golden files may be used for raw serialized SDK examples and normalized transcripts, but tests must not assert provider-generated prose. Golden files should cover structural shapes and known event ordering.

## 95. Live Result Acceptance

A live fixture is accepted when:

- raw evidence exists;
- normalization succeeds or records an explicit normalization failure;
- every expected invariant has a result;
- status is one of the defined outcome categories;
- timing and run metadata exist;
- cost/usage fields are recorded when available;
- secrets are absent.

## 96. Regression Protection

Before Phase 0 completion, rerun the stable baseline regression commands recorded in the Baseline Manifest. No public generated-project behavior may regress due to research work.

## 97. Quality Gate Matrix

| Gate | Required evidence | Blocks |
| --- | --- | --- |
| G0 Entry | Baseline manifest + clean scope acknowledgment | All implementation |
| G1 Harness Foundation | Offline tests green; schemas validate; live runner fail-closed | Probe implementation |
| G2 Control Pair | OpenAI native + LangChain base live cases captured | Vendor/framework expansion |
| G3 Vendor Diversity | At least one non-OpenAI native lane live | Phase 1A authorization |
| G4 Core Matrix | All required base feature groups executed or blocked with reason | Stress synthesis |
| G5 Stress Evidence | Cancellation/timeout/parallel/retry evidence captured where applicable | Final synthesis |
| G6 Unexpected Finding | At least one KJ-accepted F1 finding | Phase 0 exit |
| G7 Evidence Revision | Sanitized P0-E1 verifies; reports complete; baseline still green | Phase 1A DevSpec |

# Part XII — Incremental Development Slices

The work is intentionally divided into small slices. A slice may not silently absorb the next slice. Each slice ends with a focused report containing files changed, commands run, results, open issues, and whether the gate passed.

## Slice P0.0 — Baseline Freeze and Research Skeleton

### Goal

Create the isolated research workspace without changing production behavior.

### Deliverables

- branch created;
- `ENTRY_GATE.md`;
- baseline manifest;
- directory skeleton;
- `.gitignore` for `runs/` and local secrets;
- DevSpec copied or linked from docs;
- no runtime SDK dependencies yet.

### Acceptance

```text
[ ] Existing baseline commands green
[ ] New research files only
[ ] No public package metadata changed
[ ] Git diff reviewed
[ ] G0 passed
```

### Suggested commit

```text
research(audit): establish phase-0 baseline and workspace
```

## Slice P0.1 — Schemas and Harness Foundation

### Goal

Define audit documents and the minimal internal harness models.

### Deliverables

- fixture schema;
- probe request/response schemas;
- normalized transcript schema;
- result schema;
- run manifest schema;
- finding schema;
- harness project and lockfile;
- CLI `validate`, `list-fixtures`, `list-lanes`.

### Acceptance

```text
[ ] Schemas have positive and negative tests
[ ] CLI works on Windows paths with spaces
[ ] No live network code exists yet
[ ] Ruff and pytest green
```

### Suggested commit

```text
research(audit): define audit schemas and harness foundation
```

## Slice P0.2 — Planner, Budget, Runner, and Evidence Storage

### Goal

Make the experiment safe before adding live probes.

### Deliverables

- config loader;
- matrix planner;
- budget guard;
- subprocess runner;
- raw artifact storage;
- redaction;
- run manifest creation;
- CLI `plan` and offline `run`.

### Acceptance

```text
[ ] Live run without budget is refused
[ ] Live run without --confirm-live is refused
[ ] Subprocess timeout works
[ ] Secret redaction tests pass
[ ] Failed runs preserve diagnostics
[ ] G1 passed
```

### Suggested commit

```text
research(audit): add safe runner and evidence pipeline
```

## Slice P0.3 — Fixture Corpus v0

### Goal

Create the base and stress fixtures before runtime-specific tuning.

### Deliverables

- all BASE fixtures;
- all STRESS fixtures except optional multimodal/embedding cases may remain placeholders;
- invariant evaluators;
- fixture linting;
- assumptions register frozen for first live run.

### Acceptance

```text
[ ] Every fixture validates
[ ] Every expected invariant has a deterministic evaluator or an explicit manual-review marker
[ ] No provider-specific method syntax in common fixtures
```

### Suggested commit

```text
research(audit): add language-neutral runtime fixture corpus
```

## Slice P0.4 — OpenAI Native Control Lane

### Goal

Prove the first direct SDK lane and capture raw native semantics.

### Deliverables

- isolated probe project;
- probe manifest;
- base generation, structured output, tools, streaming, usage, error support;
- raw serializer;
- normalizer;
- live core evidence.

### Acceptance

```text
[ ] Probe tests green
[ ] GEN-001 live result complete
[ ] STR-001 live result complete
[ ] TOOL-001 live result complete
[ ] STREAM-001 live result complete
[ ] USAGE-001 live result complete
[ ] ERROR-001 live result complete
```

### Suggested commit

```text
research(audit): add openai native probe lane
```

## Slice P0.5 — LangChain Compatibility Lane

### Goal

Run the same control provider/model through LangChain and expose framework transformations.

### Deliverables

- isolated LangChain probe;
- same-provider comparison configuration;
- raw type capture;
- normalizer;
- comparison report against OpenAI native.

### Acceptance

```text
[ ] Same underlying provider/model used where possible
[ ] Base live cases complete
[ ] Framework retries and structured-output strategy recorded
[ ] No LangChain type appears in common audit schemas
[ ] G2 passed
```

### Suggested commit

```text
research(audit): add langchain compatibility probe
```

## Slice P0.6 — Native Vendor Diversity

### Goal

Add Anthropic and Gemini native probes to challenge OpenAI-shaped assumptions.

### Deliverables

- Anthropic isolated probe;
- Gemini isolated probe;
- base live cases;
- role/content/tool/stream notes;
- vendor-diversity findings.

### Acceptance

```text
[ ] Both probes build and validate independently
[ ] At least one non-OpenAI native lane executes live successfully
[ ] Any blocked lane has an exact reason
[ ] G3 passed
```

### Suggested commits

```text
research(audit): add anthropic native probe
research(audit): add gemini native probe
```

## Slice P0.7 — LiteLLM and PydanticAI Stress Lanes

### Goal

Measure what abstraction layers normalize, retry, hide, or own.

### Deliverables

- isolated LiteLLM probe;
- isolated PydanticAI probe;
- same-provider control runs where possible;
- structured-output mode analysis;
- retry/validation ownership notes.

### Acceptance

```text
[ ] Control-model comparison is documented
[ ] Framework-owned semantics separated from provider semantics
[ ] Base cases complete or explicitly unsupported
[ ] G4 passed
```

### Suggested commits

```text
research(audit): add litellm routing probe
research(audit): add pydanticai stress probe
```

## Slice P0.8 — Stress Semantics

### Goal

Run the experiments most likely to change the future contract.

### Deliverables

- parallel tool case;
- tool-call streaming case;
- cancellation case;
- timeout case;
- fault-injected retry case;
- streaming usage/cancelled usage case;
- structured-output edge cases.

### Acceptance

```text
[ ] Raw evidence preserved for each attempted stress dimension
[ ] Inconclusive results have follow-up experiments
[ ] Hidden retries are measured where technically possible
[ ] G5 passed
```

### Suggested commit

```text
research(audit): capture cross-runtime stress semantics
```

## Slice P0.9 — Embedding and Multimodal Scope Evidence

### Goal

Collect enough evidence to decide whether embeddings enter the first alpha and whether the content model needs immediate multimodal pressure.

### Deliverables

- embedding fixtures and selected probes;
- optional multimodal fixture;
- Q-005 recommendation.

### Acceptance

```text
[ ] Embedding evidence exists for at least two materially different access paths, or deferral reason is documented
[ ] Multimodal case is run where suitable or explicitly deferred
```

### Suggested commit

```text
research(audit): evaluate embedding and multimodal scope
```

## Slice P0.10 — Findings and Unexpected-Finding Gate

### Goal

Convert evidence into accepted findings.

### Deliverables

- result matrix;
- accepted findings;
- at least one F1 candidate;
- follow-up experiment if no F1 exists initially.

### Escalation Order When No F1 Exists

1. streamed parallel tool calls;
2. cancellation immediately after first tool-argument delta;
3. invalid/unsupported structured schema;
4. hidden validation retry detection;
5. same provider through native vs framework with identical model/config;
6. optional Mirascope lane if framework diversity remains insufficient.

### Acceptance

```text
[ ] KJ reviews F1 candidate
[ ] At least one F1 accepted
[ ] Assumption register updated with outcomes, not rewritten
[ ] G6 passed
```

### Suggested commit

```text
research(audit): document contract-changing runtime findings
```

## Slice P0.11 — Phase 0 Synthesis and Evidence Revision

### Goal

Publish the evidence package and decide Phase 1A entry.

### Deliverables

- `PHASE0_AUDIT_REPORT.md`;
- `CONTRACT_IMPLICATIONS.md`;
- `PHASE1_ENTRY_DECISION.md`;
- sanitized `evidence/P0-E1/`;
- matrix JSON/CSV;
- cost ledger;
- environment snapshots;
- baseline regression result.

### Acceptance

```text
[ ] P0-E1 verifies from committed evidence
[ ] Q-001, Q-002, Q-003, Q-005 addressed
[ ] Two Phase 1A proof adapters selected
[ ] Required conformance subset named
[ ] Baseline still green
[ ] G7 passed
```

### Suggested commit

```text
research(audit): publish phase-0 evidence revision p0-e1
```

# Part XIII — Findings, Synthesis, and Decision Memo

## 98. Audit Report Structure

`PHASE0_AUDIT_REPORT.md` must contain:

1. Executive summary.
2. Baseline and environment.
3. Runtime lane inventory.
4. Fixture coverage.
5. Comparison-set results.
6. Structured-output findings.
7. Tool-call findings.
8. Streaming findings.
9. Cancellation and timeout findings.
10. Retry findings.
11. Usage and error findings.
12. Embedding/multimodal findings.
13. Cost summary.
14. Unexpected findings.
15. Limitations.
16. Reproduction commands.
17. Contract implications summary.

## 99. Matrix Requirements

The human matrix and machine result must distinguish:

```text
pass
pass with extension
unsupported declared
unsupported observed
blocked configuration
fail invariant
runtime error
inconclusive
not selected
```

No blank cell is allowed.

## 100. Finding Template

```text
Finding ID:
Severity:
Status:
Assumption ID:
Runtime lane(s):
Fixture(s):

Expected assumption:
Observed behavior:

Reproduction command:
Raw evidence:
Normalized evidence:

Why this matters:
Contract implication:
Capability implication:
Adapter-only implication:

Confidence:
Follow-up experiment:
KJ decision:
```

## 101. Contract Implications Memo

`CONTRACT_IMPLICATIONS.md` is not `contract.py`. It is a decision document that answers the following.

### Q-001 — Structured Output Shape

Evaluate at least:

- request option on `generate`;
- separate `generate_structured` operation;
- capability-specific operation with modes;
- hybrid approach.

The memo must cite actual mode and failure evidence.

### Q-002 — Cancellation Ownership

Evaluate at least:

- task/coroutine cancellation;
- request context/token;
- returned stream handle;
- runtime operation handle;
- out-of-band cancellation.

The memo must distinguish caller cancellation from provider work cessation.

### Q-003 — Event Vocabulary

Propose:

- required base events;
- optional capability events;
- extension channel;
- events that should not be normalized.

The memo must use evidence from text streaming and tool-call streaming.

### Q-004 — Provider Extensions

Phase 0 may not fully decide the cross-language type system, but the memo should state what extension evidence must survive Phase 1A.

### Q-005 — Embedding Scope

Recommend:

- include sibling `EmbeddingRuntime` in first alpha;
- defer to a later DevSpec;
- gather additional evidence.

## 102. Phase 1 Entry Decision

`PHASE1_ENTRY_DECISION.md` must state one of:

```text
GO
GO WITH CONDITIONS
NO-GO — MORE PHASE 0 EVIDENCE REQUIRED
NO-GO — BIBLE DECISION REVISIT REQUIRED
```

If GO or GO WITH CONDITIONS, it names:

- native proof adapter;
- LangChain compatibility adapter;
- required conformance subset;
- draft semantic areas allowed in Phase 1A;
- semantic areas still deferred;
- required compatibility checks;
- expected Bible update.

## 103. Evidence Revision P0-E1

The evidence revision is immutable after approval. Corrections create `P0-E1.1` or a later revision rather than rewriting history.

The revision includes a manifest with hashes of every included artifact.

# Part XIV — Failure Policy, Stop Conditions, and Rollback

## 104. General Failure Principle

The audit is allowed to fail. A provider or framework failure can be valuable evidence. What is not allowed is an experiment whose failure cannot be interpreted because logs, raw artifacts, configuration, or reproduction commands are missing.

## 105. Stop Conditions

Implementation or execution stops immediately when:

- a secret may have been written to the repository or committed artifact;
- live spend exceeds the hard budget cap;
- the audit requires production core changes to proceed;
- the coding agent starts defining AgentRuntime or WorkflowRuntime;
- the audit-only protocol is being promoted as the final ALMS runtime API without Phase 1A evidence;
- a LOCKED Bible premise appears invalidated;
- baseline public behavior regresses and the research workspace is the cause;
- raw evidence cannot be preserved safely.

## 106. Failure Classification

A failing live case must be triaged as:

```text
fixture defect
harness defect
probe defect
runtime/framework behavior
provider/model behavior
environment/configuration
nondeterminism
unknown
```

Do not fix the fixture merely to make a runtime pass unless the fixture itself violates the experiment design.

## 107. Rollback Strategy

Because Phase 0 is isolated under `research/runtime-audit/`, the default rollback is simple:

- abandon the research branch;
- remove the research directory;
- restore any explicitly approved root changes;
- return to the stable baseline tag/branch.

No database migration, public package migration, or user-facing rollback should be required.

## 108. Deviation Process

Any deviation from REQUIRED architecture is recorded in `docs/deviations.md` with:

```text
Deviation ID
Original requirement
Reason
Alternatives considered
Risk
Temporary or permanent
KJ approval
Expiry/revisit gate
```

The coding agent may propose but not self-approve a deviation.

## 109. Deferred-Idea Process

Useful ideas outside Phase 0 go to `docs/deferred-ideas.md`. Each entry includes:

- idea;
- why it is out of scope;
- likely future DevSpec;
- evidence trigger.

This prevents scope creep while preserving insight.

# Part XV — Phase 0 Exit and Phase 1A Handoff

## 110. Phase 0 Exit Gate

All required conditions:

```text
[ ] Stable baseline preserved
[ ] Required lanes executed or blocked with reasons
[ ] At least one non-OpenAI native lane executed live
[ ] Mandatory feature groups have evidence
[ ] Raw and normalized evidence preserved
[ ] Cost ledger complete
[ ] Result matrix complete with no blank cells
[ ] At least one F1 CONTRACT_CHANGING finding accepted by KJ
[ ] Q-001 recommendation complete
[ ] Q-002 recommendation complete
[ ] Q-003 recommendation complete
[ ] Q-005 recommendation complete or explicit evidence-backed deferral
[ ] Two proof adapters selected for Phase 1A
[ ] Required semantic conformance subset selected
[ ] Evidence revision P0-E1 verifies
[ ] Baseline regression commands green
[ ] Phase 1 Entry Decision approved
```

## 111. What Phase 0 Must Not Deliver

Even after successful completion, Phase 0 must not claim:

- stable public runtime API;
- official runtime adapter support;
- runtime feature parity;
- AgentRuntime design;
- WorkflowRuntime design;
- multi-language conformance;
- public registry readiness.

## 112. Expected Phase 1A Input

Phase 1A receives:

- accepted evidence revision;
- selected two proof adapters;
- draft semantic requirements;
- required event subset;
- capability distinctions;
- error categories worth prototyping;
- structured-output decision;
- cancellation decision or narrowed options;
- explicit deferred items;
- compatibility obligations to v0.3.4.

## 113. Phase 1A DevSpec Scope Preview

The next DevSpec should be limited to:

```text
Draft ModelRuntime v0
+ ALMS-owned request/response/events/capabilities/errors
+ LangChain proof adapter
+ one native proof adapter
+ semantic conformance subset
+ no core decoupling yet
```

Core decoupling belongs to a later DevSpec after the two proof adapters validate the draft boundary.

## 114. Bible Update

After Phase 0, prepare ALMS Bible v1.1 or the appropriate next revision:

- add actual findings;
- resolve or update hypotheses;
- mark changed assumptions;
- link P0-E1;
- record Phase 1A decision.

The Bible is not edited commit-by-commit.

# Part XVI — Requirement Traceability and Implementation Checklists

## 115. Requirement IDs

Every REQUIRED statement in implementation work should map to one of these top-level requirement groups.

| Requirement | Requirement summary | Trace |
| --- | --- | --- |
| R-BAS-001 | Preserve the stable v0.3.4 public path | Bible §131, ADR-014 |
| R-SCP-001 | Keep Phase 0 isolated from production runtime/core work | Bible §167 |
| R-DAT-001 | Preserve raw evidence separately from normalized interpretation | Bible §61 |
| R-DAT-002 | Use language-neutral JSON-compatible fixtures | Bible §60 |
| R-HAR-001 | Isolate runtime probe dependencies | DevSpec decision; supports unbiased evidence |
| R-HAR-002 | Use an audit-only subprocess protocol, not a future runtime API | Bible §166 |
| R-RUN-001 | Audit required runtime lanes | Bible §58 |
| R-CMP-001 | Use same-provider control lanes where possible | Derived experimental control requirement |
| R-CMP-002 | Execute at least one non-OpenAI native vendor lane | ADR-002 anti-bias gate |
| R-SEM-001 | Evaluate semantic invariants, not identical behavior | ADR-006 |
| R-SEM-002 | Distinguish unsupported, blocked, failed, errored, and inconclusive | Bible §67 |
| R-CST-001 | Fail closed on live budget/call caps | Bible §63 |
| R-SEC-001 | Prevent secret leakage in requests, logs, artifacts, and commits | Bible security canon |
| R-EVD-001 | Produce at least one accepted F1 finding | Bible §65/§66 |
| R-EVD-002 | Publish immutable evidence revision P0-E1 | Bible §167 handoff requirement |
| R-DEC-001 | Answer Q-001 structured-output decision | Bible Appendix F |
| R-DEC-002 | Answer Q-002 cancellation decision | Bible Appendix F |
| R-DEC-003 | Answer Q-003 event-vocabulary decision | Bible Appendix F |
| R-DEC-005 | Answer or defer Q-005 embedding scope with evidence | Bible Appendix F |
| R-HOF-001 | Select Phase 1A proof adapters and conformance subset | Bible §132/§166 |

## 116. Coding Agent Operating Protocol

Before editing each slice, the coding agent reports:

```text
current repository
current branch
current HEAD
worktree status
slice ID
files expected to change
commands expected to run
```

During implementation:

- do not modify unrelated files;
- do not run `git add .`;
- do not auto-release;
- do not auto-merge;
- do not hide failing tests;
- do not replace live evidence with mocks;
- do not make external calls outside explicit live runs;
- do not use real customer/user data.

At slice completion, report:

```text
files changed
why each file changed
tests run
results
live calls made
approximate spend
findings/deviations
remaining risks
recommended next slice
```

## 117. Human Review Checkpoints

KJ review is mandatory at:

1. Entry Gate.
2. First live run plan.
3. G2 control-pair comparison.
4. G3 vendor-diversity evidence.
5. Any F0/F1 finding.
6. P0-E1 publication.
7. Phase 1 Entry Decision.

## 118. Definition of Done

Phase 0 is done when the Exit Gate is satisfied, not when the directory contains all planned files.

The final one-line test is:

> **Can another developer inspect P0-E1, rerun the important cases, understand where runtime semantics differ, and see exactly why the next ModelRuntime design changed?**

If the answer is no, Phase 0 is not complete.

# Appendix A — Recommended Commands

## A.1 Windows PowerShell Preflight

```powershell
cd C:\KJ\Repos\alms-lab\alms

git status --short
git branch --show-current
git rev-parse HEAD
git tag --points-at HEAD

# Do not reset or discard work automatically.
# Record drift before creating the research branch.

git switch -c research/runtime-audit-phase0
```

## A.2 Harness Setup

```powershell
cd research\runtime-audit\harness
uv sync --frozen
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

## A.3 Validate and Plan

```powershell
uv run alms-audit validate
uv run alms-audit list-fixtures
uv run alms-audit list-lanes
uv run alms-audit plan --tier live-core
```

## A.4 Live Run

```powershell
uv run alms-audit run `
  --tier live-core `
  --live `
  --confirm-live
```

## A.5 Targeted Run

```powershell
uv run alms-audit run `
  --lane openai-native `
  --fixture STR-001 `
  --live `
  --confirm-live
```

## A.6 Summarize

```powershell
uv run alms-audit summarize --run <RUN_ID>
uv run alms-audit verify-evidence --revision P0-E1
```

## A.7 Bash Equivalent

The same commands should work with path separators adjusted. The harness must not depend on PowerShell-specific behavior.

# Appendix B — Configuration Examples

## B.1 `audit.default.toml`

```toml
[audit]
spec = "alms.dev/runtime-audit-config/v0"
hard_budget_usd = 15.0
single_run_soft_budget_usd = 2.0
max_live_calls = 80
default_timeout_ms = 30000
default_max_output_tokens = 256
automatic_retries = 0

[evidence]
runs_dir = "../runs"
commit_dir = "../evidence"
redaction = "strict"

[execution]
primary_python = "3.13"
allow_probe_python_fallback = true
```

## B.2 `runtimes.example.toml`

```toml
[runtimes.openai-native]
enabled = true
probe = "openai-native"
provider = "openai"
model_env = "ALMS_AUDIT_OPENAI_MODEL"
credential_env = ["OPENAI_API_KEY"]
comparison_set = "openai-control"

[runtimes.langchain-openai]
enabled = true
probe = "langchain"
provider = "openai"
model_env = "ALMS_AUDIT_OPENAI_MODEL"
credential_env = ["OPENAI_API_KEY"]
comparison_set = "openai-control"

[runtimes.litellm-openai]
enabled = true
probe = "litellm"
provider = "openai"
model_env = "ALMS_AUDIT_OPENAI_MODEL"
credential_env = ["OPENAI_API_KEY"]
comparison_set = "openai-control"

[runtimes.pydanticai-openai]
enabled = true
probe = "pydanticai"
provider = "openai"
model_env = "ALMS_AUDIT_OPENAI_MODEL"
credential_env = ["OPENAI_API_KEY"]
comparison_set = "openai-control"

[runtimes.anthropic-native]
enabled = true
probe = "anthropic-native"
provider = "anthropic"
model_env = "ALMS_AUDIT_ANTHROPIC_MODEL"
credential_env = ["ANTHROPIC_API_KEY"]
comparison_set = "vendor-diversity"

[runtimes.gemini-native]
enabled = true
probe = "gemini-native"
provider = "google"
model_env = "ALMS_AUDIT_GEMINI_MODEL"
credential_env = ["GOOGLE_API_KEY"]
comparison_set = "vendor-diversity"
```

## B.3 Environment Variable Names

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
ALMS_AUDIT_OPENAI_MODEL
ALMS_AUDIT_ANTHROPIC_MODEL
ALMS_AUDIT_GEMINI_MODEL
ALMS_AUDIT_HARD_BUDGET_USD
```

No model ID or key is committed as a secret-bearing default.

# Appendix C — Probe Process Protocol Example

## C.1 Request

```json
{
  "protocol": "alms.audit.probe/v0",
  "run_id": "20260710T120000Z-abc123",
  "lane_id": "openai-native",
  "fixture_path": ".../fixtures/structured/STR-001.json",
  "output_dir": ".../runs/.../raw/openai-native/STR-001",
  "config": {
    "provider": "openai",
    "model": "resolved-at-runtime",
    "timeout_ms": 30000,
    "cancel_after": null
  }
}
```

## C.2 Response

```json
{
  "protocol": "alms.audit.probe/v0",
  "status": "ok",
  "probe_id": "openai-native",
  "probe_version": "git-or-package-version",
  "raw_manifest": "raw-manifest.json",
  "observed_attempts": 1,
  "warnings": []
}
```

All logs go to stderr. A malformed stdout response is a probe protocol failure.

# Appendix D — Result Matrix Example

```text
Fixture   OpenAI Native   LangChain   LiteLLM   PydanticAI   Anthropic Native   Gemini Native
GEN-001   PASS            PASS        PASS       PASS          PASS               PASS
STR-001   PASS            PASS        PASS       PASS          PASS               PASS
STR-004   ...             ...         ...        ...           ...                ...
TOOL-004  ...             ...         ...        ...           ...                ...
CANCEL-001...             ...         ...        ...           ...                ...
```

The final matrix must use the full status vocabulary and link every non-PASS result to evidence or an explanation.

# Appendix E — Work Breakdown Structure

| Task | Deliverable | Slice | Gate |
| --- | --- | --- | --- |
| P0-001 | Capture entry gate and baseline manifest | P0.0 | G0 |
| P0-002 | Create isolated research directory and gitignore | P0.0 | G0 |
| P0-003 | Create harness project and lockfile | P0.1 | G1 |
| P0-004 | Implement fixture schema and validators | P0.1 | G1 |
| P0-005 | Implement probe request/response schemas | P0.1 | G1 |
| P0-006 | Implement normalized transcript and result schemas | P0.1 | G1 |
| P0-007 | Implement finding and run manifest schemas | P0.1 | G1 |
| P0-008 | Implement config loader and env substitution | P0.2 | G1 |
| P0-009 | Implement matrix planner | P0.2 | G1 |
| P0-010 | Implement budget and live-run guard | P0.2 | G1 |
| P0-011 | Implement subprocess runner | P0.2 | G1 |
| P0-012 | Implement raw artifact store | P0.2 | G1 |
| P0-013 | Implement strict redaction | P0.2 | G1 |
| P0-014 | Implement result store and run manifest | P0.2 | G1 |
| P0-015 | Create base generation/role fixtures | P0.3 | G1 |
| P0-016 | Create structured output fixtures | P0.3 | G1 |
| P0-017 | Create tool fixtures | P0.3 | G1 |
| P0-018 | Create streaming/cancel/timeout fixtures | P0.3 | G1 |
| P0-019 | Create error/usage fixtures | P0.3 | G1 |
| P0-020 | Implement invariant evaluators | P0.3 | G1 |
| P0-021 | Freeze initial assumptions register | P0.3 | G1 |
| P0-022 | Implement OpenAI native probe | P0.4 | G2 |
| P0-023 | Implement OpenAI normalizer | P0.4 | G2 |
| P0-024 | Capture OpenAI live core evidence | P0.4 | G2 |
| P0-025 | Implement LangChain probe | P0.5 | G2 |
| P0-026 | Implement LangChain normalizer | P0.5 | G2 |
| P0-027 | Capture same-model control comparison | P0.5 | G2 |
| P0-028 | Implement Anthropic native probe | P0.6 | G3 |
| P0-029 | Implement Gemini native probe | P0.6 | G3 |
| P0-030 | Capture non-OpenAI native live evidence | P0.6 | G3 |
| P0-031 | Implement LiteLLM probe | P0.7 | G4 |
| P0-032 | Implement PydanticAI probe | P0.7 | G4 |
| P0-033 | Capture abstraction-layer comparison | P0.7 | G4 |
| P0-034 | Implement local fault-injection server | P0.8 | G5 |
| P0-035 | Run structured edge cases | P0.8 | G5 |
| P0-036 | Run parallel tool cases | P0.8 | G5 |
| P0-037 | Run tool streaming cases | P0.8 | G5 |
| P0-038 | Run cancellation and timeout cases | P0.8 | G5 |
| P0-039 | Run retry and usage stress cases | P0.8 | G5 |
| P0-040 | Run embedding probes | P0.9 | G5 |
| P0-041 | Run optional multimodal probe | P0.9 | G5 |
| P0-042 | Generate matrix and cost summary | P0.10 | G6 |
| P0-043 | Write and review findings | P0.10 | G6 |
| P0-044 | Execute escalation experiment if no F1 exists | P0.10 | G6 |
| P0-045 | Write Phase 0 Audit Report | P0.11 | G7 |
| P0-046 | Write Contract Implications Memo | P0.11 | G7 |
| P0-047 | Write Phase 1 Entry Decision | P0.11 | G7 |
| P0-048 | Assemble and verify P0-E1 evidence revision | P0.11 | G7 |
| P0-049 | Rerun stable baseline regression | P0.11 | G7 |
| P0-050 | Prepare Bible revision inputs | P0.11 | G7 |

# Appendix F — Test Catalog

| Test ID | Purpose |
| --- | --- |
| T-SCHEMA-001 | Fixture schema accepts valid base fixture |
| T-SCHEMA-002 | Fixture schema rejects unknown spec version |
| T-SCHEMA-003 | Result schema requires explicit status |
| T-CONFIG-001 | Missing live budget blocks live plan |
| T-CONFIG-002 | Missing credential marks lane blocked, not passed |
| T-PLAN-001 | Planner emits no unexplained missing matrix cells |
| T-PLAN-002 | Planner preserves same-model control set |
| T-BUDGET-001 | Hard call cap blocks run |
| T-BUDGET-002 | Offline run ignores live credential absence |
| T-PROC-001 | Probe success response parsed |
| T-PROC-002 | Probe non-zero exit preserved |
| T-PROC-003 | Probe timeout kills child process |
| T-PROC-004 | Windows path with spaces succeeds |
| T-REDACT-001 | Authorization header removed |
| T-REDACT-002 | Bearer token removed |
| T-REDACT-003 | Environment secret value removed |
| T-STORE-001 | Run manifest immutable after completion |
| T-STORE-002 | Failed run preserves raw diagnostics |
| T-NORM-001 | Missing usage remains null |
| T-NORM-002 | Unknown native event becomes provider_extension |
| T-INV-001 | Structured invariant validates expected fields |
| T-INV-002 | Tool invariant compares parsed arguments |
| T-INV-003 | Stream invariant ignores chunk size |
| T-INV-004 | Unsupported is distinct from failure |
| T-REPORT-001 | Matrix contains status for every planned cell |
| T-REPORT-002 | Finding links resolve to evidence |
| T-EVID-001 | P0-E1 manifest hashes verify |
| T-LIVE-001 | OpenAI native GEN-001 captured |
| T-LIVE-002 | LangChain same-model GEN-001 captured |
| T-LIVE-003 | Non-OpenAI native lane captured |
| T-GATE-001 | Phase exit fails without accepted F1 finding |

# Appendix G — Finding Examples

## G.1 Example F1 Pattern

```text
Assumption A-002:
A small stream vocabulary of text delta + terminal completion is sufficient.

Observed:
Two runtimes stream tool-call arguments with materially different identity and boundary behavior. One exposes stable call IDs before arguments; another reveals argument fragments before stable call association.

Contract implication:
Draft event semantics must model call identity as provisional or allow late binding. A simple text-only iterator is insufficient.
```

This is an example pattern only. It must not be pre-declared as the real finding.

## G.2 Example F2 Pattern

```text
Observed:
A framework retries structured-output validation automatically while the native SDK returns the first invalid result.

Capability implication:
Structured output requires explicit retry-policy provenance or framework-owned retry metadata.
```

Again, the real evidence decides the finding.

# Appendix H — Review Checklists

## H.1 Before First Live Call

```text
[ ] ENTRY_GATE.md approved
[ ] Assumptions register frozen
[ ] Fixtures validate
[ ] Budget guard tested
[ ] Redaction tests green
[ ] Probe dry run works
[ ] Plan output reviewed
[ ] Selected models recorded
[ ] No customer data in fixtures
```

## H.2 Before Accepting an F1 Finding

```text
[ ] Reproduced or strongly evidenced
[ ] Raw artifact exists
[ ] Normalization did not create the difference
[ ] Fixture defect ruled out
[ ] Provider/model confound considered
[ ] Same-provider control compared where possible
[ ] Contract assumption named explicitly
[ ] Contract change stated explicitly
[ ] KJ reviewed
```

## H.3 Before Publishing P0-E1

```text
[ ] Secrets scan clean
[ ] Every matrix cell accounted for
[ ] Cost ledger complete
[ ] Environment snapshots present
[ ] Accepted findings linked
[ ] Contract implications complete
[ ] Phase 1 decision complete
[ ] Baseline regression green
[ ] Evidence hashes verify
```

# Appendix I — Future DevSpec Sequence

The expected sequence after this document is:

```text
DevSpec P0 — Runtime Audit Lab
    ↓ evidence P0-E1
DevSpec P1A — Draft ModelRuntime v0 + two proof adapters
    ↓ conformance evidence
DevSpec P1B — Python core decoupling
    ↓ compatibility evidence
DevSpec P2 — Official Python runtime adapters
    ↓ working semantics
DevSpec P3 — Extract language-independent spec
    ↓ alpha spec
DevSpec P4 — TypeScript reference candidate
```

Parallel future tracks:

```text
Pack/Skill resolver prototype
Rust R1–R4 research
Later AgentRuntime/WorkflowRuntime research
```

None of those tracks are authorized by this DevSpec.

# Appendix J — One-Page Execution Canon

```text
SOURCE
ALMS Bible v1.0

BASELINE
ALMS v0.3.4 is stable and external-tester ready.
Do not break it.

MISSION
Learn real runtime semantics before designing ModelRuntime.

WORK LOCATION
current alms repo
research/runtime-audit/

DO
language-neutral fixtures
isolated probe environments
raw evidence
normalized transcripts
semantic invariants
cost controls
unexpected findings
contract decision memo

DO NOT
refactor core
freeze public API
split repos
publish adapters
build AgentRuntime
build WorkflowRuntime
build registry

REQUIRED LANES
LangChain
OpenAI native
Anthropic native
Gemini native
LiteLLM
PydanticAI

OPTIONAL
Mirascope only by trigger

CONTROL DESIGN
same provider/model through multiple runtime layers
+
non-OpenAI native vendor diversity

CONFORMANCE PRINCIPLE
same semantic invariants
not identical raw behavior

EXIT REQUIREMENT
at least one accepted F1 CONTRACT_CHANGING finding

PHASE 0 OUTPUT
P0-E1 evidence revision
Audit Report
Contract Implications Memo
Phase 1 Entry Decision

NEXT
Draft ModelRuntime v0
+ LangChain proof adapter
+ one native proof adapter
+ required conformance subset
```

---

# Final Specification Statement

This DevSpec turns the next ALMS step into a controlled evidence program. It protects the stable v0.3.4 product, avoids premature repository or API commitments, and forces the team to learn from runtime behavior before freezing semantics. The most important deliverable is not the harness code. It is the chain of evidence from raw runtime behavior to an accepted contract-changing finding and then to a narrower, more honest Phase 1A design.

The implementation should remain reversible until that evidence exists.

