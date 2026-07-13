"""LiteLLM SDK normalizer: LiteLLM's OpenAI-shaped abstraction output is framework-owned.

The harness reads the LiteLLM probe's plain-JSON envelope (never a litellm object) and must:
never label LiteLLM-normalized usage / model id as provider-native; preserve tool-call ids, raw
argument strings, and ordering; keep LiteLLM auxiliary metadata (hidden params, routing, tool
request translation) as framework_extension (never provider_extension); keep unknown/missing
usage absent (never 0); and map LiteLLM's exception taxonomy without flattening it.
"""

from __future__ import annotations

from alms_audit import provenance
from alms_audit.normalizers import litellm as nz
from alms_audit.schemas import default_root, is_valid

_ROOT = default_root()
_REF = "raw/litellm_response.json"


def _response(model="gpt-x", content="hi", usage=None, tool_calls=None, finish="stop"):
    message = {"role": "assistant", "content": content, "tool_calls": tool_calls}
    return {
        "capture_kind": "response",
        "response": {
            "model": model,
            "object": "chat.completion",
            "choices": [{"index": 0, "finish_reason": finish, "message": message}],
            "usage": usage,
        },
        "hidden_params": {"litellm_model_name": "openai/" + model, "response_cost": None},
        "structured": None,
        "tool_request_translation": None,
        "routing": {"resolved_provider": "openai", "resolved_model_component": model},
    }


def _normalize(envelope):
    tr = nz.normalize(envelope["capture_kind"], envelope, "m.json", _REF)
    assert is_valid("normalized-transcript", tr)
    return tr


def _types(tr):
    return [e["type"] for e in tr["events"]]


# --- source provenance: framework, never provider --------------------------------------
def test_usage_source_is_framework_native_not_provider():
    assert nz.USAGE_SOURCE == provenance.FRAMEWORK_NATIVE
    assert nz.MODEL_IDENTITY_LIVE_SOURCE == provenance.FRAMEWORK_NATIVE


def test_usage_maps_openai_shape_but_stays_framework():
    usage = {
        "prompt_tokens": 10,
        "completion_tokens": 20,
        "total_tokens": 30,
        "prompt_tokens_details": {"cached_tokens": 4},
        "completion_tokens_details": {"reasoning_tokens": 7},
    }
    summary = nz.extract_usage("response", _response(usage=usage))
    assert summary["input_tokens"] == 10
    assert summary["output_tokens"] == 20
    assert summary["cache_read_input_tokens"] == 4  # N-02: cache read survives
    assert summary["reasoning_tokens"] == 7
    assert summary["source"] == provenance.FRAMEWORK_NATIVE  # N-01: NOT provider_native


def test_absent_usage_stays_absent_never_zero():
    assert nz.extract_usage("response", _response(usage=None)) is None


# --- model identity: framework-exposed, exact string -----------------------------------
def test_model_identity_reads_modelresponse_model_exact():
    assert nz.extract_model_identity("response", _response(model="gpt-served-1")) == "gpt-served-1"


def test_model_identity_absent_is_none_not_requested():
    env = _response(model="x")
    env["response"].pop("model")
    assert nz.extract_model_identity("response", env) is None


# --- tool calls: id, raw args, order preserved -----------------------------------------
def test_tool_calls_preserve_id_name_raw_arguments_and_order():
    tool_calls = [
        {"id": "call_1", "type": "function", "function": {"name": "a", "arguments": '{"x":1}'}},
        {"id": "call_2", "type": "function", "function": {"name": "b", "arguments": '{"y":2}'}},
    ]
    tr = _normalize(_response(content=None, tool_calls=tool_calls, finish="tool_calls"))
    completed = [e for e in tr["events"] if e["type"] == "tool_call_completed"]
    assert [e["data"]["call_id"] for e in completed] == ["call_1", "call_2"]  # order + ids kept
    assert completed[0]["data"]["arguments"] == '{"x":1}'  # raw argument STRING preserved
    # a started event precedes each completed event
    assert _types(tr).count("tool_call_started") == 2


# --- auxiliary metadata is framework_extension, never provider_extension ---------------
def test_hidden_params_and_routing_are_framework_extension():
    tr = _normalize(_response())
    fx = [e for e in tr["events"] if e["type"] == "framework_extension"]
    assert len(fx) == 1
    assert "hidden_params" in fx[0]["data"]
    assert "provider_extension" not in _types(
        tr
    )  # a framework abstraction is never provider-native


# --- structured output: strategy + parsed kept distinct, no tool fallback --------------
def test_structured_output_records_strategy_and_parsed():
    env = _response(content='{"name":"Alice"}')
    env["structured"] = {
        "strategy": "response_format.json_schema",
        "parsed": {"name": "Alice"},
        "parsing_error": None,
        "provider_validation": "unverified_until_live",
    }
    tr = _normalize(env)
    so = next(e for e in tr["events"] if e["type"] == "structured_output_completed")
    assert so["data"]["strategy"] == "response_format.json_schema"
    assert so["data"]["parsed"] == {"name": "Alice"}
    assert so["data"]["provider_validation"] == "unverified_until_live"


# --- streaming: order, deltas, usage chunk, framework extensions ------------------------
def _stream():
    return {
        "capture_kind": "stream",
        "chunks": [
            {
                "sequence": 0,
                "chunk": {"model": "gpt-x", "choices": [{"delta": {"content": "one"}}]},
            },
            {
                "sequence": 1,
                "chunk": {"model": "gpt-x", "choices": [{"delta": {"content": "two"}}]},
            },
            {
                "sequence": 2,
                "chunk": {"model": "gpt-x", "choices": [{"finish_reason": "stop", "delta": {}}]},
            },
        ],
        "aggregate": {"model": "gpt-x", "choices": [{"message": {"content": "onetwo"}}]},
        "usage_chunk": {"prompt_tokens": 8, "completion_tokens": 2, "total_tokens": 10},
        "tool_request_translation": None,
        "routing": {"resolved_provider": "openai"},
    }


def test_stream_deltas_usage_and_finish_in_order():
    tr = _normalize(_stream())
    types = _types(tr)
    assert types.count("text_delta") == 2
    assert "usage_updated" in types
    assert types[-1] == "response_completed"
    assert tr["events"][-1]["data"]["finish_reason"] == "stop"


def test_stream_usage_is_framework_native():
    summary = nz.extract_usage("stream", _stream())
    assert summary["input_tokens"] == 8
    assert summary["source"] == provenance.FRAMEWORK_NATIVE


def test_stream_model_identity_from_aggregate():
    assert nz.extract_model_identity("stream", _stream()) == "gpt-x"


# --- error mapping: litellm taxonomy preserved, not flattened --------------------------
def test_error_preserves_litellm_taxonomy():
    env = {
        "capture_kind": "error",
        "litellm_exception_type": "InternalServerError",
        "cause_chain": [{"type": "MockException", "message": "boom"}],
        "llm_provider": "openai",
        "provider_status_code": 500,
        "model": "gpt-x",
        "message": "litellm.InternalServerError: ...",
    }
    tr = _normalize(env)
    err = tr["events"][0]
    assert err["type"] == "error"
    assert err["data"]["litellm_exception_type"] == "InternalServerError"
    assert err["data"]["llm_provider"] == "openai"  # provider name preserved
    assert err["data"]["cause_chain"][0]["type"] == "MockException"  # cause not flattened
