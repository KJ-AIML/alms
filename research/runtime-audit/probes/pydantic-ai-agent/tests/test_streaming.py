"""Streaming: run_stream_events framework event lifecycle + separate agent.iter graph nodes."""

from __future__ import annotations

from conftest import run_fixture


def test_stream_event_lifecycle_order():
    capture, _op, _scenario = run_fixture("STREAM-001")
    assert capture.kind == "stream"
    types = [e["event_type"] for e in capture.stream_events]
    # The framework event lifecycle: a part starts, deltas arrive, the part ends, the result event
    # is the terminal event.
    assert types[0] == "PartStartEvent"
    assert "PartDeltaEvent" in types
    assert "PartEndEvent" in types
    assert types[-1] == "AgentRunResultEvent"


def test_final_agent_run_result_event_present():
    capture, _op, _scenario = run_fixture("STREAM-001")
    finals = [e for e in capture.stream_events if e["event_type"] == "AgentRunResultEvent"]
    assert len(finals) == 1
    assert finals[0]["final_output_type"] == "str"


def test_text_deltas_captured():
    capture, _op, _scenario = run_fixture("STREAM-001")
    deltas = [e for e in capture.stream_events if e["event_type"] == "PartDeltaEvent"]
    assert len(deltas) >= 2  # incremental, multiple deltas


def test_graph_nodes_captured_separately():
    capture, _op, _scenario = run_fixture("STREAM-001")
    # agent.iter is a DISTINCT exercise for graph-node evidence, not the same call as the events.
    node_types = [n["node_type"] for n in capture.graph_nodes]
    assert node_types[0] == "UserPromptNode"
    assert node_types[-1] == "End"
    assert capture.graph_iteration_note is not None


def test_streaming_makes_one_model_request():
    capture, _op, _scenario = run_fixture("STREAM-001")
    # Both the events run and the separate graph-iteration run are single-request (no retry).
    assert capture.invocations == 1
    assert capture.graph_iteration_requests == 1


def test_usage_present_after_stream():
    capture, _op, _scenario = run_fixture("STREAM-001")
    assert capture.agent_run_usage["requests"] == 1
