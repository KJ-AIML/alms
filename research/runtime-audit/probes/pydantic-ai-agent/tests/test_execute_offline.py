"""Offline raw-evidence capture through the Agent + FunctionModel: framework semantics preserved.

FunctionModel runs the real Agent graph, message/part model, usage aggregation, and terminal
handling with zero network. Evidence is captured as PydanticAI produced it, not flattened.
"""

from __future__ import annotations

from conftest import run_fixture
from probe.client import SYNTHETIC_MODEL_NAME


def test_generation_single_invocation_and_graph():
    capture, _op, _scenario = run_fixture("GEN-001")
    assert capture.kind == "response"
    assert capture.invocations == 1  # exactly one FunctionModel invocation (RunUsage.requests)
    assert capture.tool_executions == 0
    # The Agent graph is explicitly exercised via agent.iter.
    node_types = [n["node_type"] for n in capture.graph_nodes]
    assert node_types[0] == "UserPromptNode"
    assert "ModelRequestNode" in node_types
    assert node_types[-1] == "End"


def test_roles_instructions_are_framework_owned():
    capture, _op, _scenario = run_fixture("ROLE-001")
    # The system instruction is carried on Agent info as framework instructions, distinguished
    # from a provider-native system message.
    assert capture.agent_info["instructions"]
    assert "terse" in capture.agent_info["instructions"]
    # The user prompt is preserved as a framework request part.
    kinds = [
        p.get("part_kind")
        for m in capture.messages_json
        if m.get("kind") == "request"
        for p in m.get("parts", [])
    ]
    assert "user-prompt" in kinds


def test_message_order_request_then_response():
    capture, _op, _scenario = run_fixture("GEN-001")
    kinds = [m.get("kind") for m in capture.messages_json]
    assert kinds == ["request", "response"]


def test_model_identity_requested_differs_from_observed():
    capture, op, _scenario = run_fixture("GEN-001", model="openai:gpt-4o-mini")
    # Observed returned model is the offline FunctionModel synthetic name, NOT the requested model.
    assert capture.model_name == SYNTHETIC_MODEL_NAME
    assert op["model"] == "openai:gpt-4o-mini"
    assert capture.model_name != op["model"]


def test_usage_model_response_and_run_aggregate_are_distinct():
    capture, _op, _scenario = run_fixture("USAGE-001")
    # ModelResponse usage (RequestUsage) has NO run-level aggregation fields...
    assert capture.model_response_usage is not None
    assert "requests" not in capture.model_response_usage
    # ...while the Agent run usage (RunUsage) carries the framework aggregation.
    assert capture.agent_run_usage["requests"] == 1
    assert capture.agent_run_usage["tool_calls"] == 0
    assert capture.model_response_usage["input_tokens"] == capture.agent_run_usage["input_tokens"]


def test_terminal_finish_reason_preserved():
    gen, _o, _s = run_fixture("GEN-001")
    tool, _o2, _s2 = run_fixture("TOOL-001")
    assert gen.finish_reason == "stop"
    assert tool.finish_reason == "tool_call"
