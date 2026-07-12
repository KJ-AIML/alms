"""Offline streaming capture."""

from __future__ import annotations

from probe.client import MockResponsesClient
from probe.execute import execute


def _types(cap):
    return [e["type"] for e in cap.events]


def test_text_stream_ordered_with_terminal():
    cap = execute(MockResponsesClient("stream_text"), {"model": "m", "stream": True})
    assert cap.kind == "stream"
    assert [e["sequence"] for e in cap.events] == list(range(len(cap.events)))
    types = _types(cap)
    assert types[0] == "response.created"
    assert types[-1] == "response.completed"
    assert types.count("response.output_text.delta") == 2


def test_text_deltas_distinct_from_done():
    cap = execute(MockResponsesClient("stream_text"), {"model": "m", "stream": True})
    types = _types(cap)
    assert "response.output_text.delta" in types
    assert "response.output_text.done" in types  # completed text preserved separately


def test_tool_argument_stream():
    cap = execute(
        MockResponsesClient("stream_tools"),
        {"model": "m", "stream": True, "tools": [{"type": "function", "name": "get_weather"}]},
    )
    types = _types(cap)
    assert "response.function_call_arguments.delta" in types
    assert "response.function_call_arguments.done" in types


def test_unknown_event_retained():
    cap = execute(MockResponsesClient("stream_unknown"), {"model": "m", "stream": True})
    assert "response.some_future_event" in _types(cap)  # not discarded
