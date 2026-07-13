"""Anthropic normalizer unit tests: native shapes -> shared vocab + provider_extension."""

from __future__ import annotations

from alms_audit.normalizers import anthropic as nz
from alms_audit.normalizers import select
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid


def _resp(content, structured=None, usage=None, stop_reason="end_turn"):
    return {
        "capture_kind": "response",
        "message": {
            "role": "assistant",
            "content": content,
            "stop_reason": stop_reason,
            "stop_sequence": None,
            "usage": usage,
        },
        "structured": structured,
        "retry": {},
    }


def test_select_returns_anthropic_for_anthropic_layer():
    assert select("anthropic") is nz
    from alms_audit.normalizers import openai as onz

    assert select("openai") is onz  # unchanged default/dispatch


def test_text_block_maps_to_text_delta_and_completed():
    out = nz.normalize_response(_resp([{"type": "text", "text": "hi"}]), "m.json", "raw/r.json")
    types = [e["type"] for e in out["events"]]
    assert types == ["response_started", "text_delta", "response_completed"]
    assert out["events"][-1]["data"]["stop_reason"] == "end_turn"  # stop_reason observable
    assert is_valid("normalized-transcript", out)


def test_tool_use_block_maps_to_tool_call_not_openai_function():
    env = _resp(
        [{"type": "tool_use", "id": "toolu_1", "name": "get_weather", "input": {"city": "Paris"}}],
        stop_reason="tool_use",
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    completed = next(e for e in out["events"] if e["type"] == "tool_call_completed")
    assert completed["data"]["call_id"] == "toolu_1"  # native tool_use id preserved
    assert completed["data"]["arguments"] == {"city": "Paris"}


def test_structured_output_config_format_from_native_text_block():
    # STR-001 native JSON structured output arrives as a TEXT block plus a structured envelope.
    env = _resp(
        [{"type": "text", "text": '{"name": "Alice", "age": 30}'}],
        structured={
            "strategy": "output_config.format",
            "format": "json_schema",
            "parsed": {"name": "Alice", "age": 30},
            "schema_validation": "passed",
            "outcome": "schema_validation_passed",
        },
        stop_reason="end_turn",
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    so = next(e for e in out["events"] if e["type"] == "structured_output_completed")
    assert so["data"]["strategy"] == "output_config.format"  # native, not strict tool use
    assert so["data"]["parsed"] == {"name": "Alice", "age": 30}
    assert so["data"]["schema_validation"] == "passed"
    # The carrier text block is represented as structured output, not a duplicate text_delta.
    assert "text_delta" not in [e["type"] for e in out["events"]]
    assert is_valid("normalized-transcript", out)


def test_cache_usage_kept_distinguishable_in_usage_event():
    usage = {
        "input_tokens": 10,
        "output_tokens": 3,
        "cache_creation_input_tokens": 20,
        "cache_read_input_tokens": 5,
    }
    out = nz.normalize_response(_resp([{"type": "text", "text": "x"}], usage=usage), "m.json", "r")
    ue = next(e for e in out["events"] if e["type"] == "usage_updated")
    assert ue["data"]["usage"]["cache_read_input_tokens"] == 5  # cache != ordinary input usage


def test_missing_usage_extracts_none():
    assert nz.extract_usage("response", _resp([{"type": "text", "text": "x"}], usage=None)) is None


def test_refusal_stop_reason_becomes_provider_extension():
    out = nz.normalize_response(
        _resp([{"type": "text", "text": ""}], stop_reason="refusal"), "m", "r"
    )
    assert any(
        e["type"] == "provider_extension" and e["data"].get("native_type") == "refusal"
        for e in out["events"]
    )


def test_stream_lifecycle_and_ping_are_provider_extension_not_framework():
    env = {
        "capture_kind": "stream",
        "events": [
            {
                "sequence": 0,
                "event": {"type": "message_start", "message": {"usage": {"input_tokens": 9}}},
            },
            {
                "sequence": 1,
                "event": {"type": "content_block_start", "content_block": {"type": "text"}},
            },
            {
                "sequence": 2,
                "event": {
                    "type": "content_block_delta",
                    "delta": {"type": "text_delta", "text": "hi"},
                },
            },
            {"sequence": 3, "event": {"type": "content_block_stop"}},
            {"sequence": 4, "event": {"type": "ping"}},
            {
                "sequence": 5,
                "event": {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn"},
                    "usage": {"output_tokens": 5},
                },
            },
            {"sequence": 6, "event": {"type": "message_stop"}},
        ],
        "reconstructed": {},
        "retry": {},
    }
    out = nz.normalize_stream(env, "m.json", "raw/e.json")
    types = [e["type"] for e in out["events"]]
    assert "text_delta" in types
    assert types.count("provider_extension") >= 3  # content_block_start/stop + ping lifecycle kept
    assert "framework_extension" not in types  # a provider-native event is NOT a framework one
    assert types[-1] == "response_completed"
    assert is_valid("normalized-transcript", out)
    # merged usage: input from message_start, output from message_delta. Neutral summary shape;
    # Anthropic usage is provider-native and reports no total/reasoning here (stays null, not 0).
    usage = nz.extract_usage("stream", env)
    assert usage["input_tokens"] == 9
    assert usage["output_tokens"] == 5
    assert usage["total_tokens"] is None
    assert usage["reasoning_tokens"] is None
    assert usage["source"] == "provider_native"


def test_error_envelope_preserves_status_and_cause_chain():
    env = {
        "capture_kind": "error",
        "exception_type": "APIStatusError",
        "cause_chain": [{"type": "APIStatusError", "message": "not found"}],
        "status_code": 404,
        "request_id": "req_1",
        "message": "not found",
        "retry": {},
    }
    out = nz.normalize_error(env, "m.json", "raw/err.json")
    assert out["events"][0]["type"] == "error"
    assert out["events"][0]["data"]["status_code"] == 404


def test_interpret_with_anthropic_normalizer_produces_valid_result():
    env = _resp([{"type": "text", "text": "hi"}], usage={"input_tokens": 9, "output_tokens": 5})
    out = interpret(
        capture_kind="response",
        raw_obj=env,
        run_id="r",
        fixture_id="GEN-001",
        lane_id="anthropic-native",
        raw_manifest_ref="m.json",
        response_ref="raw/r.json",
        normalized_ref="n.json",
        pricing=None,
        root=default_root(),
        normalizer=nz,
    )
    assert out.status == "PASS"
    assert out.result["usage"]["input_tokens"] == 9
    assert out.result["usage"]["provenance"] == "reported"
    assert is_valid("result", out.result)
