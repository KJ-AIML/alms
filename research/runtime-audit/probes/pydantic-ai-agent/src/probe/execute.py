"""Drive one translated operation through a PydanticAI Agent + FunctionModel and capture NATIVE
framework evidence. The probe does not flatten PydanticAI semantics: the Agent messages/parts,
ModelResponse, stream events, graph nodes, run-level usage, deferred-tool requests, model_name,
and terminal output are preserved as PydanticAI produced them. Interpretation into ALMS audit
vocabulary is the harness's job.

Every retry owner is zero (client.AGENT_RETRIES output=0/tools=0) and a one-model-request usage
limit is applied, so a validation or tool failure can never trigger a second FunctionModel
invocation. Invocation count is MEASURED from RunUsage.requests, never inferred from config.

Two streaming dimensions are kept distinct (DevSpec Section 53):
  * run_stream_events -> framework stream events + final AgentRunResultEvent.
  * agent.iter        -> Agent graph nodes + graph execution lifecycle.
Non-stream fixtures are driven by agent.iter (which yields both the graph nodes and the final
result in one run); the stream fixture is driven by run_stream_events for events plus a separate,
explicitly-labelled agent.iter exercise for graph-node evidence (each is a single model request).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic_ai import (
    Agent,
    ApprovalRequiredToolset,
    DeferredToolRequests,
    FunctionToolset,
    NativeOutput,
    StructuredDict,
    Tool,
)
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.usage import RequestUsage
from pydantic_core import to_jsonable_python

from .client import (
    AGENT_RETRIES,
    SYNTHETIC_MODEL_NAME,
    isolation_introspection,
    native_output_profile,
    usage_limits,
)

# Offline mock content. These are SYNTHETIC values injected through FunctionModel; the harness
# checks them. They are not provider output. Structured/tool content matches the BASE fixtures
# (STR-001 -> {name: Alice, age: 30}; TOOL-001 -> get_weather({city: Paris})).
_TEXT_CONTENT = "Blue."
_STRUCTURED_CONTENT = '{"name": "Alice", "age": 30}'
_TOOL_ARGS = {"city": "Paris"}
_TOOL_CALL_ID = "call_pydanticai_tool_1"
_STREAM_DELTAS = ["one\n", "two\n", "three\n", "four\n", "five\n"]


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    scenario: str
    duration_ms: int
    invocations: int = 0  # RunUsage.requests for the primary run (FunctionModel invocation count)
    tool_executions: int = 0  # RunUsage.tool_calls (executed tool bodies) - zero for deferred
    agent_info: dict | None = None
    messages_json: Any = None  # result.all_messages_json() parsed (ModelRequest/ModelResponse)
    model_response: dict | None = None  # the final ModelResponse
    model_response_usage: dict | None = (
        None  # ModelResponse usage (RequestUsage) - fixture_expected
    )
    agent_run_usage: dict | None = None  # result.usage (RunUsage) - framework aggregation
    output: Any = None
    output_type: str | None = None
    deferred: dict | None = None
    finish_reason: str | None = None
    model_name: str | None = None  # observed returned model (ModelResponse.model_name)
    graph_nodes: list | None = None
    graph_iteration_requests: int | None = None
    graph_iteration_note: str | None = None
    stream_events: list | None = None
    structured: dict | None = None
    synthetic_profile: dict | None = None
    tools_evidence: list | None = None
    isolation: dict = field(default_factory=dict)
    retry_budgets: dict | None = None
    error: dict | None = None


@dataclass
class _Recorder:
    agent_infos: list = field(default_factory=list)
    invocations: int = 0


def _jsonable(obj: Any) -> Any:
    try:
        return to_jsonable_python(obj, fallback=str)
    except Exception:  # noqa: BLE001 - a stubborn object still yields evidence via repr
        return {"repr": str(obj)}


def _capture_agent_info(info: AgentInfo) -> dict:
    """What the framework asked the model for: output mode/object, tools, instructions.

    This is the proof surface for NativeOutput selection (output_mode == 'native') and for the
    generated JSON Schema (output_object.json_schema) - both are framework decisions, recorded
    verbatim, never inferred by the harness.
    """
    mrp = info.model_request_parameters
    oo = mrp.output_object
    data = {
        "output_mode": mrp.output_mode,
        "allow_text_output": mrp.allow_text_output,
        "output_object": None
        if oo is None
        else {
            "name": getattr(oo, "name", None),
            "json_schema": getattr(oo, "json_schema", None),
            "strict": getattr(oo, "strict", None),
        },
        "function_tools": [
            {
                "name": t.name,
                "description": t.description,
                "parameters_json_schema": t.parameters_json_schema,
            }
            for t in mrp.function_tools
        ],
        "output_tools": [t.name for t in mrp.output_tools],
        "instructions": info.instructions,
    }
    return _jsonable(data)


def _make_text_function(recorder: _Recorder, content: str, usage: RequestUsage):
    def fn(messages, info: AgentInfo) -> ModelResponse:
        recorder.invocations += 1
        recorder.agent_infos.append(_capture_agent_info(info))
        return ModelResponse(
            parts=[TextPart(content=content)],
            usage=usage,
            model_name=SYNTHETIC_MODEL_NAME,
            finish_reason="stop",
        )

    return fn


def _make_structured_function(recorder: _Recorder, content: str, usage: RequestUsage):
    def fn(messages, info: AgentInfo) -> ModelResponse:
        recorder.invocations += 1
        recorder.agent_infos.append(_capture_agent_info(info))
        # A plain text part carrying JSON: PydanticAI parses + validates it under NativeOutput.
        return ModelResponse(
            parts=[TextPart(content=content)],
            usage=usage,
            model_name=SYNTHETIC_MODEL_NAME,
            finish_reason="stop",
        )

    return fn


def _make_tool_function(recorder: _Recorder, tool_name: str, usage: RequestUsage):
    def fn(messages, info: AgentInfo) -> ModelResponse:
        recorder.invocations += 1
        recorder.agent_infos.append(_capture_agent_info(info))
        return ModelResponse(
            parts=[ToolCallPart(tool_name=tool_name, args=_TOOL_ARGS, tool_call_id=_TOOL_CALL_ID)],
            usage=usage,
            model_name=SYNTHETIC_MODEL_NAME,
            finish_reason="tool_call",
        )

    return fn


def _make_stream_function(recorder: _Recorder, deltas: list[str]):
    async def sfn(messages, info: AgentInfo):
        recorder.invocations += 1
        recorder.agent_infos.append(_capture_agent_info(info))
        for delta in deltas:
            yield delta

    return sfn


def _never_execute(**kwargs: Any) -> Any:
    # A registered tool whose body must NEVER run in P0.7B (it is approval-required / deferred).
    # If PydanticAI ever executed it, this hard failure would surface it in the evidence.
    raise AssertionError(
        "P0.7B invariant: tool body must NOT execute (deferred / approval-required)"
    )


def _build_tools(tool_specs: list[dict]) -> tuple[list, list]:
    objs = []
    evidence = []
    for spec in tool_specs:
        obj = Tool.from_schema(
            _never_execute,
            name=spec["name"],
            description=spec.get("description"),
            json_schema=spec.get("parameters", {}),
        )
        objs.append(obj)
        evidence.append({"name": spec["name"], "parameters": spec.get("parameters", {})})
    return objs, evidence


def _build(operation: dict, scenario: str, recorder: _Recorder):
    """Construct the Agent + FunctionModel for a scenario. Returns (agent, profile_record,
    tools_evidence)."""
    profile_record = None
    tools_evidence = None
    output_type: Any = str
    toolsets = None

    if scenario == "structured":
        profile, profile_record = native_output_profile()
        structured = StructuredDict(operation["output_schema"], name="structured_output")
        output_type = NativeOutput(structured)
        fn = _make_structured_function(
            recorder, _STRUCTURED_CONTENT, RequestUsage(input_tokens=12, output_tokens=8)
        )
        model = FunctionModel(fn, model_name=SYNTHETIC_MODEL_NAME, profile=profile)
    elif scenario == "tools":
        output_type = [str, DeferredToolRequests]
        tool_objs, tools_evidence = _build_tools(operation["tools"])
        # ApprovalRequiredToolset marks every wrapped tool approval-required, so the model's tool
        # call surfaces as a DeferredToolRequests approval rather than executing.
        toolsets = [ApprovalRequiredToolset(FunctionToolset(tools=tool_objs))]
        tool_name = operation["tools"][0]["name"]
        fn = _make_tool_function(recorder, tool_name, RequestUsage(input_tokens=9, output_tokens=5))
        model = FunctionModel(fn, model_name=SYNTHETIC_MODEL_NAME)
    elif scenario == "stream":
        # BOTH a non-stream function (for agent.iter graph nodes) and a stream_function (for
        # run_stream_events framework events) so both streaming dimensions can be exercised.
        fn = _make_text_function(
            recorder, "".join(_STREAM_DELTAS), RequestUsage(input_tokens=11, output_tokens=6)
        )
        sfn = _make_stream_function(recorder, _STREAM_DELTAS)
        model = FunctionModel(fn, stream_function=sfn, model_name=SYNTHETIC_MODEL_NAME)
    else:  # generation, roles, usage
        fn = _make_text_function(
            recorder, _TEXT_CONTENT, RequestUsage(input_tokens=11, output_tokens=5)
        )
        model = FunctionModel(fn, model_name=SYNTHETIC_MODEL_NAME)

    agent = Agent(
        model,
        instructions=operation.get("instructions"),
        output_type=output_type,
        toolsets=toolsets,
        retries=AGENT_RETRIES,
    )
    return agent, profile_record, tools_evidence


def _node_dump(node: Any) -> dict:
    return {"node_type": type(node).__name__}


def _event_dump(ev: Any) -> dict:
    from pydantic_ai import AgentRunResultEvent

    name = type(ev).__name__
    if isinstance(ev, AgentRunResultEvent):
        # The final result is captured in full separately; here record only that it arrived and
        # the terminal output type, so the event log is not a second giant copy of the result.
        return {"event_type": name, "final_output_type": type(ev.result.output).__name__}
    return {"event_type": name, "event": _jsonable(ev)}


async def _iter_run(agent: Agent, user_prompt: str):
    nodes: list[dict] = []
    async with agent.iter(user_prompt, usage_limits=usage_limits()) as run:
        async for node in run:
            nodes.append(_node_dump(node))
    return nodes, run.result


async def _stream_run(agent: Agent, user_prompt: str):
    from pydantic_ai import AgentRunResultEvent

    events: list[dict] = []
    result = None
    async with agent.run_stream_events(user_prompt, usage_limits=usage_limits()) as stream:
        async for ev in stream:
            events.append(_event_dump(ev))
            if isinstance(ev, AgentRunResultEvent):
                result = ev.result
    return events, result


def _structured_evidence(agent_info: dict | None, output: Any, profile_record: dict | None) -> dict:
    generated_schema = None
    output_mode = None
    if agent_info:
        output_mode = agent_info.get("output_mode")
        oo = agent_info.get("output_object") or {}
        generated_schema = oo.get("json_schema")
    return {
        "strategy_requested": "native_output",
        # Proof the framework selected NATIVE structured output, not a tool/prompted fallback.
        "output_mode_observed": output_mode,
        "is_native": output_mode == "native",
        "generated_json_schema": generated_schema,
        "synthetic_model_profile": profile_record,
        "parsed_output": _jsonable(output),
        "parse_error": None,
        "schema_validation": "framework_validated_offline",
        # Offline validity is NOT proof a real provider requested or followed native JSON schema.
        "provider_validation": "unverified_until_live",
    }


def _capture_result(cap: RawCapture, result: Any) -> None:
    cap.invocations = result.usage.requests
    cap.tool_executions = result.usage.tool_calls
    cap.agent_run_usage = _jsonable(result.usage)
    resp = result.response
    cap.model_response = _jsonable(resp)
    cap.model_response_usage = _jsonable(resp.usage) if resp.usage is not None else None
    cap.model_name = resp.model_name
    cap.finish_reason = resp.finish_reason
    cap.messages_json = json.loads(result.all_messages_json())
    out = result.output
    cap.output_type = type(out).__name__
    if isinstance(out, DeferredToolRequests):
        cap.deferred = {
            "approvals": [
                {"tool_name": c.tool_name, "tool_call_id": c.tool_call_id, "args": c.args}
                for c in out.approvals
            ],
            "calls": [
                {"tool_name": c.tool_name, "tool_call_id": c.tool_call_id, "args": c.args}
                for c in out.calls
            ],
            "metadata": _jsonable(out.metadata),
        }
        cap.output = {"kind": "deferred_tool_requests"}
    else:
        cap.output = _jsonable(out)


def _cause_chain(exc: BaseException) -> list[dict]:
    chain: list[dict] = []
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chain.append({"type": type(cur).__name__, "message": str(cur)})
        cur = cur.__cause__ or cur.__context__
    return chain


def _error_evidence(exc: BaseException) -> dict:
    return {
        "exception_type": type(exc).__name__,
        "exception_module": type(exc).__module__,
        "message": str(exc),
        "cause_chain": _cause_chain(exc),
    }


async def _run(operation: dict, scenario: str) -> RawCapture:
    recorder = _Recorder()
    agent, profile_record, tools_evidence = _build(operation, scenario, recorder)
    isolation = isolation_introspection()
    user_prompt = operation.get("user_prompt") or ""

    if scenario == "stream":
        events, result = await _stream_run(agent, user_prompt)
        graph_nodes, iter_result = await _iter_run(agent, user_prompt)
        if result is None:
            result = iter_result
        cap = RawCapture(
            kind="stream",
            scenario=scenario,
            duration_ms=0,
            stream_events=events,
            graph_nodes=graph_nodes,
            graph_iteration_requests=iter_result.usage.requests,
            graph_iteration_note=(
                "run_stream_events and agent.iter are two DISTINCT single-request exercises of "
                "the same fixture: the former proves framework stream events + final result, the "
                "latter proves Agent graph nodes + lifecycle. Neither is a retry of the other."
            ),
            isolation=isolation,
        )
    else:
        graph_nodes, result = await _iter_run(agent, user_prompt)
        cap = RawCapture(
            kind="response",
            scenario=scenario,
            duration_ms=0,
            graph_nodes=graph_nodes,
            isolation=isolation,
        )

    _capture_result(cap, result)
    cap.agent_info = recorder.agent_infos[0] if recorder.agent_infos else None
    cap.retry_budgets = isolation.get("retry_budgets")
    if scenario == "structured":
        cap.synthetic_profile = profile_record
        cap.structured = _structured_evidence(cap.agent_info, result.output, profile_record)
    if tools_evidence is not None:
        cap.tools_evidence = tools_evidence
    return cap


def execute(operation: dict, scenario: str) -> RawCapture:
    """Run one operation through a PydanticAI Agent; capture raw evidence or a framework error.

    A single primary run is made per fixture; retries are zero and a one-request usage limit is
    applied, so no second model turn can occur. A framework exception is captured as evidence
    (kind='error'), never raised out of the probe as a crash.
    """
    start = time.monotonic()
    try:
        cap = asyncio.run(_run(operation, scenario))
        cap.duration_ms = _ms(start)
        return cap
    except Exception as exc:  # noqa: BLE001 - a framework error is recorded evidence, not a crash
        return RawCapture(
            kind="error",
            scenario=scenario,
            duration_ms=_ms(start),
            error=_error_evidence(exc),
            isolation=isolation_introspection(),
        )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
