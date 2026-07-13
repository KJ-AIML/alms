"""Deferred tool (TOOL-001): approval-required tool -> DeferredToolRequests, no body execution."""

from __future__ import annotations

from conftest import run_fixture


def test_output_is_deferred_tool_requests():
    capture, _op, _scenario = run_fixture("TOOL-001")
    assert capture.output_type == "DeferredToolRequests"


def test_single_tool_call_preserved():
    capture, _op, _scenario = run_fixture("TOOL-001")
    approvals = capture.deferred["approvals"]
    assert len(approvals) == 1
    call = approvals[0]
    assert call["tool_name"] == "get_weather"
    assert call["tool_call_id"] == "call_pydanticai_tool_1"
    assert call["args"] == {"city": "Paris"}


def test_tool_body_not_executed_and_one_model_turn():
    capture, _op, _scenario = run_fixture("TOOL-001")
    assert capture.tool_executions == 0  # RunUsage.tool_calls: no tool body ran
    assert capture.invocations == 1  # exactly one model request
    # If the tool body had executed, the raising tool would have surfaced an error capture.
    assert capture.kind == "response"


def test_deferred_is_terminal_not_failure():
    capture, _op, _scenario = run_fixture("TOOL-001")
    # A deferred request is a normal terminal output, never an error capture.
    assert capture.error is None
    assert capture.finish_reason == "tool_call"


def test_tool_definition_registered_with_schema():
    capture, _op, _scenario = run_fixture("TOOL-001")
    tools = capture.agent_info["function_tools"]
    assert any(t["name"] == "get_weather" for t in tools)
    weather = next(t for t in tools if t["name"] == "get_weather")
    assert "city" in weather["parameters_json_schema"].get("properties", {})
