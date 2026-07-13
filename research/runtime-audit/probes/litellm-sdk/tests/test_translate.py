"""Fixture -> LiteLLM operation translation (pure data; no litellm import needed)."""

from __future__ import annotations

import json

from conftest import corpus_fixture
from probe.translate import to_operation


def _fx(fid: str) -> dict:
    return json.loads(corpus_fixture(fid).read_text(encoding="utf-8"))


def test_basic_generation_maps_user_message():
    op, meta = to_operation(_fx("GEN-001"), "openai/gpt-x")
    assert op["model"] == "openai/gpt-x"  # provider-qualified, verbatim
    assert op["messages"] == [{"role": "user", "content": "Reply with a short friendly greeting."}]
    assert op["stream"] is False
    assert meta["instruction_mapping"] == "none"


def test_model_provider_prefix_recorded():
    _, meta = to_operation(_fx("GEN-001"), "openai/gpt-x")
    assert meta["model_provider_prefix"] == "openai"
    assert meta["model_provider_component"] == "gpt-x"


def test_system_and_user_roles_both_present():
    op, meta = to_operation(_fx("ROLE-001"), "openai/gpt-x")
    roles = [m["role"] for m in op["messages"]]
    assert roles == ["system", "user"]  # neither role dropped
    assert meta["instruction_mapping"] == "system->system_message"


def test_structured_strategy_recorded_response_format():
    op, meta = to_operation(_fx("STR-001"), "openai/gpt-x")
    assert op["structured_output_strategy_requested"] == "response_format.json_schema"
    assert op["response_format"]["type"] == "json_schema"
    assert op["response_format"]["json_schema"]["name"] == "str_001"
    assert op["response_format"]["json_schema"]["schema"]["required"] == ["name", "age"]


def test_tool_schema_converted_to_openai_shape():
    op, _ = to_operation(_fx("TOOL-001"), "openai/gpt-x")
    assert op["tools"][0]["type"] == "function"
    assert op["tools"][0]["function"]["name"] == "get_weather"
    assert op["tool_choice"] == "auto"


def test_stream_selection_recorded():
    op, meta = to_operation(_fx("STREAM-001"), "openai/gpt-x")
    assert op["stream"] is True
    assert meta["streaming_requested"] is True


def test_explicit_model_propagates_no_hidden_default():
    op, _ = to_operation(_fx("USAGE-001"), "openai/explicit-model-id")
    assert op["model"] == "openai/explicit-model-id"  # exactly what was passed, never defaulted


def test_max_output_tokens_override_wins():
    op, _ = to_operation(_fx("GEN-001"), "openai/gpt-x", max_output_tokens=17)
    assert op["max_output_tokens"] == 17
