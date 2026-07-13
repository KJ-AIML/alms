"""Gemini normalizer unit tests: Interactions-native shapes -> shared vocab + provider_extension."""

from __future__ import annotations

from alms_audit.normalizers import gemini as nz
from alms_audit.normalizers import select
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid

_USAGE = {
    "total_input_tokens": 9,
    "total_output_tokens": 5,
    "total_tokens": 14,
    "total_thought_tokens": 0,
    "total_cached_tokens": 0,
}


def _resp(steps, status="completed", structured=None, usage=None):
    return {
        "capture_kind": "response",
        "interaction": {
            "id": "i1",
            "object": "interaction",
            "status": status,
            "model": "gemini-x",
            "steps": steps,
            "usage": usage,
        },
        "structured": structured,
        "retry": {},
    }


def test_select_returns_gemini_for_google_genai_layer():
    assert select("google-genai") is nz
    from alms_audit.normalizers import openai as onz

    assert select("openai") is onz  # unchanged default/dispatch


def test_model_output_maps_to_text_delta_and_completed():
    out = nz.normalize_response(
        _resp([{"type": "model_output", "content": [{"type": "text", "text": "hi"}]}]), "m", "r"
    )
    types = [e["type"] for e in out["events"]]
    assert types == ["response_started", "text_delta", "response_completed"]
    assert out["events"][-1]["data"]["status"] == "completed"  # status observable
    assert is_valid("normalized-transcript", out)


def test_function_call_step_and_requires_action():
    env = _resp(
        [
            {
                "type": "function_call",
                "id": "fc1",
                "name": "get_weather",
                "arguments": {"city": "Paris"},
            }
        ],
        status="requires_action",
    )
    out = nz.normalize_response(env, "m", "r")
    types = [e["type"] for e in out["events"]]
    assert "tool_call_started" in types and "tool_call_completed" in types
    completed = next(e for e in out["events"] if e["type"] == "tool_call_completed")
    assert completed["data"]["call_id"] == "fc1"  # native function_call step id preserved
    assert any(
        e["data"].get("native_type") == "requires_action"
        for e in out["events"]
        if e["type"] == "provider_extension"
    )


def test_structured_records_response_format_strategy():
    env = _resp(
        [{"type": "model_output", "content": [{"type": "text", "text": '{"name": "Alice"}'}]}],
        structured={
            "strategy": "response_format.text.json_schema",
            "parsed": {"name": "Alice"},
            "schema_validation": "passed",
            "outcome": "schema_validation_passed",
        },
    )
    out = nz.normalize_response(env, "m", "r")
    so = next(e for e in out["events"] if e["type"] == "structured_output_completed")
    assert so["data"]["strategy"] == "response_format.text.json_schema"
    assert "text_delta" not in [e["type"] for e in out["events"]]  # carrier not duplicated


def test_thought_step_is_provider_extension_structural_only():
    env = _resp(
        [
            {"type": "thought", "thought_signature": "sig_opaque"},
            {"type": "model_output", "content": [{"type": "text", "text": "hi"}]},
        ]
    )
    out = nz.normalize_response(env, "m", "r")
    thought = next(
        e
        for e in out["events"]
        if e["type"] == "provider_extension" and e["data"].get("native_type") == "thought_step"
    )
    assert thought["data"]["thought_signature_present"] is True
    # only presence is recorded, never the (absent) reasoning text
    assert "thought_signature" not in thought["data"]
    assert "framework_extension" not in [e["type"] for e in out["events"]]


def test_usage_mapped_for_summary_native_kept_in_event():
    env = _resp(
        [{"type": "model_output", "content": [{"type": "text", "text": "x"}]}], usage=_USAGE
    )
    # mapped shared names for the result summary
    mapped = nz.extract_usage("response", env)
    assert mapped["input_tokens"] == 9 and mapped["output_tokens"] == 5
    # native usage object preserved in the usage_updated event
    out = nz.normalize_response(env, "m", "r")
    ue = next(e for e in out["events"] if e["type"] == "usage_updated")
    assert ue["data"]["usage"]["total_input_tokens"] == 9


def test_missing_usage_extracts_none():
    assert (
        nz.extract_usage("response", _resp([{"type": "model_output", "content": []}], usage=None))
        is None
    )


def test_stream_lifecycle_is_provider_extension_not_framework():
    env = {
        "capture_kind": "stream",
        "events": [
            {"sequence": 0, "event": {"event_type": "interaction.created"}},
            {"sequence": 1, "event": {"event_type": "step.start", "step_type": "model_output"}},
            {
                "sequence": 2,
                "event": {
                    "event_type": "step.delta",
                    "delta": {"type": "text_delta", "text": "hi"},
                },
            },
            {"sequence": 3, "event": {"event_type": "step.stop"}},
            {"sequence": 4, "event": {"event_type": "gemini.unknown_native_event"}},
            {
                "sequence": 5,
                "event": {
                    "event_type": "interaction.completed",
                    "interaction": {"status": "completed", "usage": _USAGE},
                },
            },
        ],
        "reconstructed": {"usage": _USAGE},
        "retry": {},
    }
    out = nz.normalize_stream(env, "m", "e")
    types = [e["type"] for e in out["events"]]
    assert "text_delta" in types
    assert types.count("provider_extension") >= 3  # step.start/stop + unknown lifecycle kept
    assert "framework_extension" not in types
    assert types[-1] == "response_completed"
    assert is_valid("normalized-transcript", out)
    assert nz.extract_usage("stream", env)["input_tokens"] == 9


def test_error_envelope_preserves_code_and_cause():
    env = {
        "capture_kind": "error",
        "exception_type": "FakeGeminiError",
        "cause_chain": [{"type": "FakeGeminiError", "message": "x"}],
        "code": 404,
        "status": "NOT_FOUND",
        "message": "x",
        "retry": {},
    }
    out = nz.normalize_error(env, "m", "e")
    assert out["events"][0]["type"] == "error"
    assert out["events"][0]["data"]["code"] == 404


def test_interpret_with_gemini_normalizer_valid_result():
    env = _resp(
        [{"type": "model_output", "content": [{"type": "text", "text": "hi"}]}], usage=_USAGE
    )
    out = interpret(
        capture_kind="response",
        raw_obj=env,
        run_id="r",
        fixture_id="GEN-001",
        lane_id="gemini-native",
        raw_manifest_ref="m",
        response_ref="r",
        normalized_ref="n",
        pricing=None,
        root=default_root(),
        normalizer=nz,
    )
    assert out.status == "PASS"
    assert out.result["usage"]["input_tokens"] == 9  # mapped from total_input_tokens
    assert is_valid("result", out.result)
