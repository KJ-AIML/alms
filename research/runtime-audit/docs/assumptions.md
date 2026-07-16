# Phase 0 Assumption Register

## Status

Initial register frozen for first live run history.

- Created offline: 2026-07-16
- No live run has begun yet

## Authority

- DevSpec Section 16 (Assumption Register)
- Task P0-021 (Freeze initial assumptions register)
- P0.3 deliverable

## Rules

Once the first live run begins, later edits **append** outcomes (status changes, live evidence
references, and conclusion notes). Do **not** rewrite the original assumption text in the table
below.

## Assumptions

| ID | Initial assumption | Falsification condition | Status |
| --- | --- | --- | --- |
| A-001 | Structured output can be represented as one generic capability. | Evidence shows materially different native, tool-based, prompted, or retry-backed modes that affect application semantics. | challenged_offline |
| A-002 | Streaming can be normalized as a simple sequence of text deltas plus terminal completion. | Tool-call argument streaming, usage timing, or provider events require richer ordering semantics. | challenged_offline |
| A-003 | Caller task cancellation is a sufficient cross-runtime cancellation model. | A runtime continues provider work, hides cancellation, or exposes a distinct cancellation handle that changes observable semantics. | open |
| A-004 | Timeouts can be represented as one normalized error category. | Framework retry behavior or provider-side execution creates multiple operationally distinct timeout outcomes. | open |
| A-005 | Usage can be attached only to the final response. | Some runtimes expose incremental or partial usage, especially during streaming or cancellation. | challenged_offline |
| A-006 | Tool calls can be normalized as name + JSON arguments + call ID. | A provider/framework lacks stable IDs, streams ambiguous argument fragments, or supports non-JSON tool semantics. | challenged_offline |
| A-007 | Embeddings should ship as a sibling contract in the first alpha. | Audit shows low value, incompatible lifecycle, or insufficient cross-runtime evidence for the first alpha. | open |
| A-008 | A small common event vocabulary will preserve useful semantics. | Important provider-native behavior cannot be represented without destructive flattening or an extension channel. | challenged_offline |

No assumption is `falsified_live` or `modified` at register creation.

## Offline provisional observations

The notes below link offline evidence that **may** challenge assumptions. They are labelled
`offline_mock` / not live. They do **not** claim permanent falsification without live evidence.

### A-001

- **Source:** P0.6C protocol-neutrality matrix; P0.7A/P0.7B six-lane comparison (`STR-001`).
- **Observation (offline_mock):** Six lanes show distinct structured strategies:
  `native_json_schema` (openai-native, anthropic-native, gemini-native) vs
  `framework_function_calling` (langchain) vs `framework_response_format` (litellm-sdk) vs
  `framework_native_output` (pydantic-ai-agent).
- **Live adherence:** `unverified_until_live`.

### A-002

- **Source:** P0.6C streaming fixtures (`STREAM-001`, `STREAM-002`); six-lane offline mocks.
- **Observation (offline_mock):** Streaming marked `unverified_until_live`; framework vs provider
  event lifecycles differ offline (e.g. LangChain synthesized stream chunks as
  `framework_extension` vs native provider block lifecycle as `provider_extension`).
- **Live adherence:** `unverified_until_live`.

### A-005

- **Source:** P0.6C findings N-01/N-02 (usage provenance); `USAGE-001`/`USAGE-002` fixtures.
- **Observation (offline_mock):** Usage provenance mitigated offline via `usage.source` and
  neutral `extract_usage`; N-01/N-02 accepted F1 with offline regression locks.
- **Incremental stream usage:** `unverified_until_live`.

### A-006

- **Source:** P0.6C tool-call comparison; P0.7A L-01; P0.7B PydanticAI deferred tools.
- **Observation (offline_mock):** L-01 documents LiteLLM SDK partial tool path
  (`completion(tools=...)` couples to proxy MCP utilities). PydanticAI lane records deferred
  tool semantics offline. Call ID provenance differs by lane (native vs framework-synthesized).
- **Live adherence:** `unverified_until_live`.

### A-008

- **Source:** P0.6C protocol-neutrality audit; `protocol-neutrality-matrix.json`.
- **Observation (offline_mock):** `provider_extension` and `framework_extension` escape hatches
  already used extensively offline (OpenAI unknown item events, Anthropic content-block lifecycle,
  Gemini thought steps, LangChain synthesized chunks). Extensions preserve semantics that the
  common vocabulary does not flatten.
- **Interpretation:** Extensions may be required companions to the small vocabulary; live
  destructive-flattening risk remains `unverified_until_live`.

## Scope disclaimers

This document:

- does **not** authorize live runs
- does **not** close Phase 0
- does **not** begin P0.8 (ModelRuntime implementation)
