"""Fixture -> Gemini Interactions request translation (pure data; no SDK import needed)."""

from __future__ import annotations

import json

from conftest import corpus_fixture
from probe.translate import to_operation


def _fx(fid: str) -> dict:
    return json.loads(corpus_fixture(fid).read_text(encoding="utf-8"))


def test_basic_generation_creates_user_input_step():
    op, meta = to_operation(_fx("GEN-001"), "gemini-x")
    assert op["model"] == "gemini-x"
    assert op["input"] == [
        {
            "type": "user_input",
            "content": [{"type": "text", "text": "Reply with a short friendly greeting."}],
        }
    ]
    assert op["system_instruction"] is None


def test_system_is_top_level_instruction_not_a_user_step():
    op, meta = to_operation(_fx("ROLE-001"), "gemini-x")
    assert op["system_instruction"] == "You are a terse assistant. Answer in exactly one word."
    assert [s["type"] for s in op["input"]] == ["user_input"]  # system not turned into input
    assert meta["system_mapping"] == "system->top_level_system_instruction"


def test_store_is_always_false_and_no_previous_interaction_id():
    for fid in ("GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"):
        op, meta = to_operation(_fx(fid), "gemini-x")
        assert op["store"] is False  # server-side retention never enabled
        assert "previous_interaction_id" not in op  # stateless single-turn
        assert meta["previous_interaction_id_used"] is False


def test_structured_uses_native_response_format_not_a_tool():
    op, meta = to_operation(_fx("STR-001"), "gemini-x")
    assert op["structured_output_strategy_requested"] == "response_format.text.json_schema"
    assert op["response_format"]["text"]["mime_type"] == "application/json"
    assert (
        op["response_format"]["text"]["jsonSchema"] == _fx("STR-001")["output_schema"]
    )  # raw schema
    assert op["tools"] is None  # no synthetic extraction tool


def test_content_part_order_preserved():
    fx = {
        "id": "MULTI",
        "feature": "generation",
        "execution": {"max_output_tokens": 32},
        "messages": [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "one"}, {"kind": "text", "text": "two"}],
            }
        ],
    }
    op, _ = to_operation(fx, "gemini-x")
    assert [p["text"] for p in op["input"][0]["content"]] == ["one", "two"]


def test_function_tool_translation():
    op, _ = to_operation(_fx("TOOL-001"), "gemini-x")
    assert op["tools"][0]["function"]["name"] == "get_weather"
    assert op["response_format"] is None


def test_stream_selection_and_explicit_model():
    op, meta = to_operation(_fx("STREAM-001"), "explicit-gemini-id")
    assert op["stream"] is True
    assert op["model"] == "explicit-gemini-id"  # no hidden default
    assert meta["streaming_requested"] is True
