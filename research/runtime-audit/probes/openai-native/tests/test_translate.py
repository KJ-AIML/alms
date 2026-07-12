"""Fixture -> OpenAI Responses request translation."""

from __future__ import annotations

from probe.translate import to_responses_request


def _fx(**kw):
    base = {"id": "X-001", "feature": "generation", "execution": {}, "messages": []}
    base.update(kw)
    return base


def test_generation_maps_user_to_input():
    fx = _fx(
        messages=[{"role": "user", "parts": [{"kind": "text", "text": "hi"}]}],
        execution={"temperature": 0, "max_output_tokens": 32},
    )
    kwargs, meta = to_responses_request(fx, "model-x")
    assert kwargs["model"] == "model-x"
    assert kwargs["input"][0]["role"] == "user"
    assert kwargs["input"][0]["content"][0] == {"type": "input_text", "text": "hi"}
    assert kwargs["max_output_tokens"] == 32
    assert "instructions" not in kwargs


def test_system_maps_to_instructions():
    fx = _fx(
        feature="roles",
        messages=[
            {"role": "system", "parts": [{"kind": "text", "text": "Be terse."}]},
            {"role": "user", "parts": [{"kind": "text", "text": "hi"}]},
        ],
    )
    kwargs, meta = to_responses_request(fx, "m")
    assert kwargs["instructions"] == "Be terse."
    assert kwargs["input"][0]["role"] == "user"
    assert meta["instruction_mapping"] == "system->instructions"


def test_structured_sets_json_schema_format():
    fx = _fx(
        feature="structured_output",
        output_schema={"type": "object"},
        messages=[{"role": "user", "parts": [{"kind": "text", "text": "x"}]}],
    )
    kwargs, meta = to_responses_request(fx, "m")
    assert kwargs["text"]["format"]["type"] == "json_schema"
    assert kwargs["text"]["format"]["strict"] is True
    assert meta["structured_mode_requested"] == "native_schema"


def test_tools_and_choice():
    fx = _fx(
        feature="tools",
        messages=[{"role": "user", "parts": [{"kind": "text", "text": "weather?"}]}],
        tools=[{"name": "get_weather", "description": "d", "parameters": {"type": "object"}}],
        execution={"tool_choice": "required"},
    )
    kwargs, _ = to_responses_request(fx, "m")
    assert kwargs["tools"][0]["type"] == "function"
    assert kwargs["tools"][0]["name"] == "get_weather"
    assert kwargs["tool_choice"] == "required"


def test_forced_maps_to_required():
    fx = _fx(
        feature="tools",
        messages=[{"role": "user", "parts": [{"kind": "text", "text": "x"}]}],
        tools=[{"name": "t"}],
        execution={"tool_choice": "forced"},
    )
    kwargs, _ = to_responses_request(fx, "m")
    assert kwargs["tool_choice"] == "required"


def test_stream_flag_and_no_hardcoded_model():
    fx = _fx(
        messages=[{"role": "user", "parts": [{"kind": "text", "text": "x"}]}],
        execution={"stream": True},
    )
    kwargs, _ = to_responses_request(fx, "whatever-model")
    assert kwargs["stream"] is True
    assert kwargs["model"] == "whatever-model"
