"""Fixture -> Agent operation mapping (no pydantic_ai import needed)."""

from __future__ import annotations

from conftest import load_fixture
from probe.translate import to_operation


def test_generation_maps_user_prompt():
    op, meta = to_operation(load_fixture("GEN-001"), "openai:gpt-4o")
    assert op["user_prompt"]
    assert op["instructions"] is None
    assert op["stream"] is False
    assert op["structured_output_strategy_requested"] is None
    assert meta["instruction_mapping"] == "none"


def test_roles_map_system_to_agent_instructions():
    op, meta = to_operation(load_fixture("ROLE-001"), "openai:gpt-4o")
    # A system message becomes framework Agent instructions, NOT a provider-native system message.
    assert op["instructions"]
    assert "terse" in op["instructions"]
    assert op["user_prompt"]
    assert meta["instruction_mapping"] == "system->agent_instructions(framework)"


def test_structured_requests_native_output():
    op, meta = to_operation(load_fixture("STR-001"), "openai:gpt-4o")
    assert op["output_schema"] is not None
    assert op["structured_output_strategy_requested"] == "native_output"
    assert meta["structured_mode_requested"] == "native_output"


def test_tools_flagged_deferred():
    op, meta = to_operation(load_fixture("TOOL-001"), "openai:gpt-4o")
    assert op["tools"] and op["tools"][0]["name"] == "get_weather"
    assert meta["tools_requested"] is True
    assert meta["deferred_tool_expected"] is True


def test_streaming_flag_preserved():
    op, meta = to_operation(load_fixture("STREAM-001"), "openai:gpt-4o")
    assert op["stream"] is True
    assert meta["streaming_requested"] is True


def test_model_is_recorded_verbatim():
    op, _meta = to_operation(load_fixture("GEN-001"), "openai:gpt-4o-2024-08-06")
    assert op["model"] == "openai:gpt-4o-2024-08-06"
