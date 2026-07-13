# pydantic-ai-agent probe

ALMS Phase 0 Runtime Audit Lab — PydanticAI **Agent** framework stress lane.

Research/audit infrastructure only. Implements Probe Process Protocol v0 (DevSpec Section 23),
which is NOT the future ModelRuntime contract.

## Boundary: the Agent, not the Gateway

This lane audits the PydanticAI **Agent** (DevSpec Section 53): the Agent graph, the framework
message/part model, structured-output strategies, tool and deferred-tool behavior, framework
retry ownership, stream events, usage aggregation, model identity, framework terminal states, and
framework exceptions. It does **not** audit the Pydantic AI Gateway, Pydantic Evals, Pydantic
Graph as a standalone product, MCP servers, durable-execution integrations, Logfire, OpenTelemetry
export, or provider-native semantics. No custom provider endpoint is configured and no
Router / FallbackModel is used. The `Agent` API is the primary surface; the low-level `direct` API
is not used as the primary lane because it omits much of the framework-owned behavior under audit.

## Isolation and the offline model boundary

`pydantic_ai` lives ONLY in this probe env (DevSpec Sections 20 and 25); the central harness never
imports `pydantic_ai` / `pydantic_graph` / `logfire`. The only model used offline is
**FunctionModel** — PydanticAI's own explicit-control test seam. Before any Agent runs the probe
sets `pydantic_ai.models.ALLOW_MODEL_REQUESTS = False` (FunctionModel is exempt; every real
provider model is blocked) and installs a network tripwire that blocks all outbound sockets while
allowing only the asyncio loopback self-pipe (127.0.0.1) an async run needs. Every retry budget is
zero (output-validation retries, tool retries, per-tool retries) and a one-model-request usage
limit is applied. Instrumentation is never enabled: full `logfire` and the OpenTelemetry
SDK/exporter are not installed (only the inert `logfire-api` / `opentelemetry-api` interface shims
are present transitively), and no Gateway client is constructed. Provider model integrations
(openai/anthropic/google) require vendor SDKs that are absent in this slim install, so a real
provider model cannot be constructed.

`TestModel` is deliberately NOT the primary evidence generator: it auto-synthesizes schema-valid
data and auto-calls tools, hiding the framework behavior this lane measures.

## Offline injection

FunctionModel runs the real Agent graph, message/part model, output-strategy selection
(NativeOutput), validation, deferred-tool handling, usage aggregation, and stream events with zero
network. The probe returns raw framework evidence, never a prebuilt response or a normalized
transcript; the harness `pydanticai` normalizer interprets it. Real provider request/response
semantics stay `unverified_until_live`.

## What PydanticAI does to the evidence (measured offline)

- **Model identity**: the offline FunctionModel exposes a synthetic `model_name` distinct from the
  requested model, so requested != observed is recorded (`model_identity_match=false`),
  non-failing, offline source `fixture_expected`. Framework-owned, never provider-native.
- **Instructions**: a fixture `system` message becomes Agent `instructions` -> a framework
  `InstructionPart`, distinguished from provider-native system instructions and never relabelled.
- **Structured output**: `NativeOutput` is selected explicitly (`output_mode == 'native'`) only
  because a SYNTHETIC model profile advertises `supports_json_schema_output`; the generated JSON
  Schema and framework parse/validate are recorded. There is no silent fallback to
  `ToolOutput`/`PromptedOutput`, and valid JSON offline is not proof a real provider requested or
  followed native JSON schema.
- **Deferred tools**: an approval-required tool yields `DeferredToolRequests` (the approval, tool
  name, call id, and validated arguments preserved); the tool body is never executed; model
  invocations = 1, second model turn = 0. A deferred request is a terminal state, not a failure.
- **Streaming**: `run_stream_events` exposes the framework event lifecycle
  (PartStartEvent/PartDeltaEvent/PartEndEvent/FinalResultEvent/AgentRunResultEvent); `agent.iter`
  is a separate exercise for Agent graph nodes (UserPromptNode/ModelRequestNode/CallToolsNode/End).
- **Usage**: ModelResponse `RequestUsage` (offline `fixture_expected`) is kept distinct from Agent
  `RunUsage` aggregation (`framework_native`); missing usage stays absent, never coerced to zero.
- **Errors**: PydanticAI's own exception hierarchy is captured as evidence, never labelled
  provider-native.

## Run

```
uv sync --frozen
uv run pytest
uv run --project probes/pydantic-ai-agent python -m probe <request.json>
```

No live provider request is made offline. The Pydantic AI Gateway and Logfire are not used, and no
tool is executed.
