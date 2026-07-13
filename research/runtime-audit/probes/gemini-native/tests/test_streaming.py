"""Native streaming lifecycle: every native event and its order preserved, not collapsed."""

from __future__ import annotations

from probe.client import FakeGeminiClient
from probe.execute import execute

_STREAM_OP = {"model": "gemini-x", "input": [], "stream": True, "store": False}


def _types(cap):
    return [e["event"]["event_type"] for e in cap.events]


def test_text_stream_lifecycle_in_order():
    cap = execute(FakeGeminiClient(scenario="stream"), _STREAM_OP)
    types = _types(cap)
    # Native lifecycle preserved, NOT collapsed into text chunks.
    assert types[0] == "interaction.created"
    assert "step.start" in types
    assert types.count("step.delta") == 3
    assert "step.stop" in types
    assert types[-1] == "interaction.completed"
    assert [e["sequence"] for e in cap.events] == sorted(e["sequence"] for e in cap.events)


def test_text_deltas_are_native_text_delta_subtype():
    cap = execute(FakeGeminiClient(scenario="stream"), _STREAM_OP)
    deltas = [e["event"]["delta"] for e in cap.events if e["event"]["event_type"] == "step.delta"]
    assert all(d["type"] == "text_delta" for d in deltas)
    assert cap.reconstructed["text"] == "one\ntwo\nthree\n"
    assert cap.reconstructed["status"] == "completed"


def test_function_call_delta_retained():
    cap = execute(FakeGeminiClient(scenario="stream_tools"), _STREAM_OP)
    subtypes = [
        e["event"]["delta"]["type"] for e in cap.events if e["event"]["event_type"] == "step.delta"
    ]
    assert subtypes == ["arguments_delta", "arguments_delta"]
    start = next(e for e in cap.events if e["event"]["event_type"] == "step.start")
    assert start["event"]["step_type"] == "function_call"


def test_thought_signature_delta_retained_structurally():
    cap = execute(FakeGeminiClient(scenario="stream_thought"), _STREAM_OP)
    deltas = [e["event"]["delta"] for e in cap.events if e["event"]["event_type"] == "step.delta"]
    assert deltas[0]["type"] == "thought_signature_delta"
    assert deltas[0]["thought_signature"]  # opaque signature kept, no reasoning text


def test_unknown_native_event_retained():
    cap = execute(FakeGeminiClient(scenario="stream"), _STREAM_OP)
    assert "gemini.unknown_native_event" in _types(cap)  # kept, not dropped


def test_terminal_interaction_carries_usage():
    cap = execute(FakeGeminiClient(scenario="stream"), _STREAM_OP)
    completed = next(e for e in cap.events if e["event"]["event_type"] == "interaction.completed")
    assert completed["event"]["interaction"]["usage"]["total_output_tokens"] == 5


def test_stream_error_captured_not_raised():
    cap = execute(FakeGeminiClient(scenario="error"), _STREAM_OP)
    assert cap.kind == "error"
    assert cap.error["exception_type"] == "FakeGeminiError"
    assert cap.error["code"] == 404
