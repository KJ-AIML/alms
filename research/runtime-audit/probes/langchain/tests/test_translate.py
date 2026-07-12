"""Fixture -> LangChain operation translation (pure data; no framework import needed)."""

from __future__ import annotations

import json

from conftest import corpus_fixture
from probe.translate import to_operation


def _fx(fid: str) -> dict:
    return json.loads(corpus_fixture(fid).read_text(encoding="utf-8"))


def test_basic_generation_maps_user_message():
    op, meta = to_operation(_fx("GEN-001"), "gpt-x")
    assert op["model"] == "gpt-x"
    assert op["messages"] == [{"role": "user", "text": "Reply with a short friendly greeting."}]
    assert op["stream"] is False
    assert meta["instruction_mapping"] == "none"


def test_system_and_user_roles_both_present():
    op, meta = to_operation(_fx("ROLE-001"), "gpt-x")
    roles = [m["role"] for m in op["messages"]]
    assert roles == ["system", "user"]  # neither role dropped
    assert meta["instruction_mapping"] == "system->SystemMessage"


def test_structured_strategy_recorded_and_title_injected():
    op, meta = to_operation(_fx("STR-001"), "gpt-x")
    assert op["structured_output_strategy_requested"] == "function_calling"
    assert meta["structured_schema_title_injected"] is True
    # A title (the function name LangChain requires) was injected into the submitted schema.
    assert op["output_schema"]["title"] == "str_001"
    assert op["output_schema"]["required"] == ["name", "age"]


def test_tool_schema_preserved():
    op, _ = to_operation(_fx("TOOL-001"), "gpt-x")
    assert op["tools"][0]["name"] == "get_weather"
    assert op["tool_choice"] == "auto"


def test_stream_selection_recorded():
    op, meta = to_operation(_fx("STREAM-001"), "gpt-x")
    assert op["stream"] is True
    assert meta["streaming_requested"] is True


def test_explicit_model_propagates_no_hidden_default():
    op, _ = to_operation(_fx("USAGE-001"), "explicit-model-id")
    assert op["model"] == "explicit-model-id"  # exactly what was passed, never defaulted


def test_max_output_tokens_override_wins():
    op, _ = to_operation(_fx("GEN-001"), "gpt-x", max_output_tokens=17)
    assert op["max_output_tokens"] == 17
