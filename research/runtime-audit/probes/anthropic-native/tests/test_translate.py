"""Fixture -> Anthropic Messages request translation (pure data; no SDK import needed)."""

from __future__ import annotations

import json

from conftest import corpus_fixture
from probe.translate import to_operation


def _fx(fid: str) -> dict:
    return json.loads(corpus_fixture(fid).read_text(encoding="utf-8"))


def test_basic_generation_uses_content_blocks():
    op, meta = to_operation(_fx("GEN-001"), "claude-x")
    assert op["model"] == "claude-x"
    assert op["messages"] == [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Reply with a short friendly greeting."}],
        }
    ]
    assert op["max_tokens"] == 32  # required Messages API param, mapped from the fixture
    assert op["system"] is None


def test_system_is_top_level_not_a_message():
    op, meta = to_operation(_fx("ROLE-001"), "claude-x")
    assert op["system"] == "You are a terse assistant. Answer in exactly one word."
    assert [m["role"] for m in op["messages"]] == ["user"]  # no invented system/assistant message
    assert meta["system_mapping"] == "system->top_level_system"


def test_structured_uses_output_config_format_not_a_tool():
    op, meta = to_operation(_fx("STR-001"), "claude-x")
    # Native JSON structured output via output_config.format — NOT a forced/synthetic tool.
    assert op["structured_output_strategy_requested"] == "output_config.format"
    assert op["output_config"] == {
        "format": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "required": ["name", "age"],
                "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
                "additionalProperties": False,
            },
        }
    }
    assert op["tools"] is None  # STR-001 defines no extraction tool
    assert op["tool_choice"] is None
    assert meta["structured_mode_requested"] == "output_config.format"


def test_structured_preserves_raw_fixture_schema_verbatim():
    op, _ = to_operation(_fx("STR-001"), "claude-x")
    sent = op["output_config"]["format"]["schema"]
    assert sent == _fx("STR-001")["output_schema"]  # raw schema preserved, not transformed


def test_tool_use_is_strict_and_separate_from_structured():
    op, _ = to_operation(_fx("TOOL-001"), "claude-x")
    assert op["tools"][0]["name"] == "get_weather"
    assert "input_schema" in op["tools"][0]  # native input_schema (tool INPUT constraint)
    assert op["tools"][0]["strict"] is True  # strict tool validation, tool-specific
    assert op["tool_choice"] == {"type": "auto"}
    assert op["output_config"] is None  # tool use is not structured output


def test_stream_selection_recorded():
    op, meta = to_operation(_fx("STREAM-001"), "claude-x")
    assert op["stream"] is True
    assert meta["streaming_requested"] is True


def test_explicit_model_no_hidden_default():
    op, _ = to_operation(_fx("USAGE-001"), "explicit-claude-id")
    assert op["model"] == "explicit-claude-id"
