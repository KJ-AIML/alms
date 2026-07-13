"""ALMS Phase 0 PydanticAI Agent framework audit probe.

Research/audit infrastructure ONLY. Implements Probe Process Protocol v0 (DevSpec
Section 23), which is NOT the future ModelRuntime contract. PydanticAI is used only inside
this isolated probe; the central harness never imports pydantic_ai / pydantic_graph / logfire.

BOUNDARY (DevSpec Section 53): this lane audits the PydanticAI Agent — the Agent graph, the
framework message/part model, structured-output strategies, tool and deferred-tool behavior,
framework retry ownership, stream events, usage aggregation, model identity, framework terminal
states, and framework exceptions. It does NOT audit the Pydantic AI Gateway, Pydantic Evals,
Pydantic Graph as a standalone product, MCP servers, durable-execution integrations, Logfire,
OpenTelemetry export, or provider-native semantics. PydanticAI's Agent output (messages, parts,
usage aggregation, terminal states) is FRAMEWORK-owned (framework_native / framework_extension),
never provider-native merely because a value resembles a provider's.

OFFLINE MODEL BOUNDARY: the only model used is FunctionModel (PydanticAI's own explicit-control
test seam), never a real provider model. `pydantic_ai.models.ALLOW_MODEL_REQUESTS` is set False
before any Agent execution, and a process-level network tripwire is installed. FunctionModel
gives explicit control over ModelRequest, ModelResponse, parts, stream events, usage, model_name,
tool calls, structured output, and errors. TestModel is deliberately NOT the primary evidence
generator (it auto-synthesizes schema-valid data and auto-calls tools, hiding framework behavior).
"""

__version__ = "0.0.0"
PROBE_ID = "pydantic-ai-agent"
PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"
