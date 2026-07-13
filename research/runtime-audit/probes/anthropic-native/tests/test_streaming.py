"""Native streaming lifecycle: every native event and its order preserved, not collapsed."""

from __future__ import annotations

from probe.client import FakeAnthropicClient
from probe.execute import execute

_STREAM_OP = {
    "model": "claude-x",
    "max_tokens": 64,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "count"}]}],
    "stream": True,
    "structured_output_strategy_requested": None,
}


def _event_types(cap):
    return [e["event"]["type"] for e in cap.events]


def test_text_stream_lifecycle_preserved_in_order():
    cap = execute(FakeAnthropicClient(scenario="stream"), _STREAM_OP)
    types = _event_types(cap)
    # Native block lifecycle is preserved, NOT collapsed into a single text stream.
    assert types[0] == "message_start"
    assert "content_block_start" in types
    assert types.count("content_block_delta") == 3
    assert "content_block_stop" in types
    assert types[-1] == "message_stop"
    # sequence is monotonic
    seqs = [e["sequence"] for e in cap.events]
    assert seqs == sorted(seqs)


def test_text_deltas_are_native_text_delta_subtype():
    cap = execute(FakeAnthropicClient(scenario="stream"), _STREAM_OP)
    deltas = [
        e["event"]["delta"] for e in cap.events if e["event"]["type"] == "content_block_delta"
    ]
    assert all(d["type"] == "text_delta" for d in deltas)
    assert "".join(d["text"] for d in deltas) == "one\ntwo\nthree\n"


def test_unknown_native_event_retained():
    cap = execute(FakeAnthropicClient(scenario="stream"), _STREAM_OP)
    assert "ping" in _event_types(cap)  # a vocabulary-less native event is kept, not dropped


def test_message_terminal_and_reconstructed_usage():
    cap = execute(FakeAnthropicClient(scenario="stream"), _STREAM_OP)
    assert cap.reconstructed["stop_reason"] == "end_turn"  # from message_delta
    assert cap.reconstructed["usage"]["output_tokens"] == 5


def test_tool_input_deltas_preserved():
    cap = execute(
        FakeAnthropicClient(scenario="stream_tools"),
        {**_STREAM_OP, "tools": [{"name": "get_weather"}]},
    )
    subtypes = [
        e["event"]["delta"]["type"]
        for e in cap.events
        if e["event"]["type"] == "content_block_delta"
    ]
    assert subtypes == ["input_json_delta", "input_json_delta"]  # tool-input deltas kept distinct
    starts = [e for e in cap.events if e["event"]["type"] == "content_block_start"]
    assert starts[0]["event"]["content_block"]["type"] == "tool_use"


def test_stream_error_is_captured_not_raised():
    cap = execute(FakeAnthropicClient(scenario="error"), _STREAM_OP)
    assert cap.kind == "error"
    assert cap.error["exception_type"] == "FakeAnthropicError"
    assert cap.error["status_code"] == 404
