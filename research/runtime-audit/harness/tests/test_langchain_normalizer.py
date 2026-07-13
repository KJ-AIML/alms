"""LangChain normalizer unit tests: framework shapes -> shared vocab + framework_extension."""

from __future__ import annotations

from alms_audit.normalizers import langchain as nz
from alms_audit.normalizers import select
from alms_audit.results import interpret
from alms_audit.schemas import default_root, is_valid


def _response_envelope(message, structured=None):
    return {"capture_kind": "response", "message": message, "structured": structured, "retry": {}}


def test_select_returns_langchain_for_langchain_layer():
    assert select("langchain") is nz
    from alms_audit.normalizers import openai as onz

    assert select("openai") is onz
    assert select(None) is onz  # default


def test_text_response_maps_to_text_delta_and_completed():
    env = _response_envelope(
        {"content": "hi there", "response_metadata": {"finish_reason": "stop"}}
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    types = [e["type"] for e in out["events"]]
    assert types == ["response_started", "text_delta", "response_completed"]
    assert is_valid("normalized-transcript", out)


def test_usage_metadata_maps_to_usage_updated():
    env = _response_envelope({"content": "x", "usage_metadata": {"input_tokens": 3}})
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    assert any(e["type"] == "usage_updated" for e in out["events"])
    # Neutral summary shape; LangChain usage_metadata is FRAMEWORK-normalized, not provider-native.
    usage = nz.extract_usage("response", env)
    assert usage["input_tokens"] == 3
    assert usage["source"] == "framework_native"


def test_missing_usage_extracts_none():
    env = _response_envelope({"content": "x"})
    assert nz.extract_usage("response", env) is None  # absent, never coerced to 0


def test_tool_calls_map_to_started_and_completed():
    env = _response_envelope(
        {
            "content": "",
            "tool_calls": [{"name": "get_weather", "args": {"city": "Paris"}, "id": "c1"}],
        }
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    types = [e["type"] for e in out["events"]]
    assert "tool_call_started" in types and "tool_call_completed" in types
    completed = next(e for e in out["events"] if e["type"] == "tool_call_completed")
    assert completed["data"]["call_id"] == "c1"
    assert completed["data"]["arguments"] == {"city": "Paris"}


def test_structured_output_records_strategy_and_parsed():
    env = _response_envelope(
        {"content": "", "tool_calls": [{"name": "s", "args": {"name": "Alice"}, "id": "c"}]},
        structured={
            "strategy": "function_calling",
            "parsed": {"name": "Alice"},
            "parsing_error": None,
        },
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    so = next(e for e in out["events"] if e["type"] == "structured_output_completed")
    assert so["data"]["strategy"] == "function_calling"
    assert so["data"]["parsed"] == {"name": "Alice"}


def test_invalid_tool_calls_become_framework_extension_not_provider():
    env = _response_envelope(
        {"content": "", "invalid_tool_calls": [{"name": "broken", "error": "bad json"}]}
    )
    out = nz.normalize_response(env, "m.json", "raw/r.json")
    types = [e["type"] for e in out["events"]]
    assert "framework_extension" in types
    assert "provider_extension" not in types  # a framework artifact is not provider-native


def test_stream_synthesized_empty_chunk_is_framework_extension():
    env = {
        "capture_kind": "stream",
        "chunks": [
            {"sequence": 0, "chunk": {"content": "one"}},
            {"sequence": 1, "chunk": {"content": ""}},  # framework-synthesized terminal chunk
        ],
        "final_message": {"usage_metadata": {"input_tokens": 1}, "response_metadata": {}},
        "retry": {},
    }
    out = nz.normalize_stream(env, "m.json", "raw/e.json")
    types = [e["type"] for e in out["events"]]
    assert types.count("text_delta") == 1
    assert types.count("framework_extension") == 1
    assert is_valid("normalized-transcript", out)


def test_error_envelope_preserves_cause_chain():
    env = {
        "capture_kind": "error",
        "framework_exception_type": "OutputParserException",
        "cause_chain": [
            {"type": "OutputParserException", "message": "x"},
            {"type": "ValueError", "message": "y"},
        ],
        "message": "parse failed",
        "retry": {},
    }
    out = nz.normalize_error(env, "m.json", "raw/err.json")
    assert out["events"][0]["type"] == "error"
    assert out["events"][0]["data"]["cause_chain"][1]["type"] == "ValueError"


def test_interpret_with_langchain_normalizer_flags_framework_extension():
    env = {
        "capture_kind": "stream",
        "chunks": [
            {"sequence": 0, "chunk": {"content": "hi"}},
            {"sequence": 1, "chunk": {"content": ""}},
        ],
        "final_message": {"usage_metadata": None, "response_metadata": {}},
        "retry": {},
    }
    out = interpret(
        capture_kind="stream",
        raw_obj=env,
        run_id="r",
        fixture_id="STREAM-001",
        lane_id="langchain-openai",
        raw_manifest_ref="m.json",
        response_ref="raw/e.json",
        normalized_ref="n.json",
        pricing=None,
        root=default_root(),
        normalizer=nz,
    )
    assert out.status == "PASS_WITH_EXTENSION"
    assert "framework_extension" in out.notes
    assert is_valid("result", out.result)
