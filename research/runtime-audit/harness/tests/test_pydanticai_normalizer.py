"""PydanticAI normalizer: the Agent's framework-owned output is never labelled provider-native.

The harness reads the PydanticAI probe's plain-JSON envelope (never a pydantic_ai object) and must:
never label Agent RunUsage aggregation or the framework model_name as provider-native; keep graph
nodes / Agent info / synthetic profile / deferred-tool requests as framework_extension (never
provider_extension); preserve deferred-tool name/id/args without executing anything; keep missing
usage absent (never 0); and map framework errors without flattening them into provider errors.
"""

from __future__ import annotations

from alms_audit import provenance
from alms_audit.normalizers import pydanticai as nz
from alms_audit.schemas import default_root, is_valid

_ROOT = default_root()
_REF = "raw/pydanticai_response.json"

_RUN_USAGE = {
    "input_tokens": 11,
    "output_tokens": 5,
    "cache_read_tokens": 0,
    "cache_write_tokens": 0,
    "details": {},
    "requests": 1,
    "tool_calls": 0,
}


def _base(**over):
    env = {
        "capture_kind": "response",
        "scenario": "generation",
        "agent_info": {"output_mode": "text", "instructions": None, "function_tools": []},
        "graph_nodes": [{"node_type": "UserPromptNode"}, {"node_type": "End"}],
        "model_response": {"model_name": "function:offline-synthetic-model"},
        "model_response_usage": {"input_tokens": 11, "output_tokens": 5},
        "agent_run_usage": dict(_RUN_USAGE),
        "output": "Hello there, friend.",
        "output_type": "str",
        "deferred": None,
        "finish_reason": "stop",
        "model_name": "function:offline-synthetic-model",
        "structured": None,
        "synthetic_profile": None,
        "tools_evidence": None,
    }
    env.update(over)
    return env


def _normalize(env):
    tr = nz.normalize(env["capture_kind"], env, "m.json", _REF)
    assert is_valid("normalized-transcript", tr)
    return tr


def _types(tr):
    return [e["type"] for e in tr["events"]]


def test_usage_source_is_framework_native_never_provider():
    assert nz.USAGE_SOURCE == provenance.FRAMEWORK_NATIVE
    assert nz.MODEL_IDENTITY_LIVE_SOURCE == provenance.FRAMEWORK_NATIVE
    assert nz.USAGE_SOURCE != provenance.PROVIDER_NATIVE


def test_extract_usage_maps_run_aggregate():
    summary = nz.extract_usage("response", _base())
    assert summary["input_tokens"] == 11
    assert summary["output_tokens"] == 5
    assert summary["total_tokens"] == 16
    assert summary["source"] == provenance.FRAMEWORK_NATIVE


def test_extract_usage_absent_stays_none():
    assert nz.extract_usage("response", {"agent_run_usage": None}) is None
    assert nz.extract_usage("error", _base()) is None


def test_cache_split_mapping():
    env = _base(agent_run_usage={**_RUN_USAGE, "cache_read_tokens": 3, "cache_write_tokens": 7})
    summary = nz.extract_usage("response", env)
    assert summary["cache_read_input_tokens"] == 3
    assert summary["cache_creation_input_tokens"] == 7


def test_extract_model_identity_is_exact_model_name():
    assert nz.extract_model_identity("response", _base()) == "function:offline-synthetic-model"
    assert nz.extract_model_identity("response", {"model_name": None}) is None


def test_text_response_events():
    tr = _normalize(_base())
    types = _types(tr)
    assert types[0] == "response_started"
    assert "text_delta" in types
    assert "usage_updated" in types
    assert types[-1] == "response_completed"
    # Framework metadata (graph nodes, Agent info) is preserved as framework_extension.
    assert "framework_extension" in types
    assert "provider_extension" not in types


def test_structured_output_is_framework_mediated_not_provider_validated():
    env = _base(
        scenario="structured",
        output_type="dict",
        structured={
            "strategy_requested": "native_output",
            "output_mode_observed": "native",
            "is_native": True,
            "parsed_output": {"name": "Alice", "age": 30},
            "generated_json_schema": {"required": ["name", "age"]},
            "parse_error": None,
            "synthetic_model_profile": {"inferred_from_real_provider": False},
            "provider_validation": "unverified_until_live",
        },
    )
    tr = _normalize(env)
    so = next(e for e in tr["events"] if e["type"] == "structured_output_completed")
    assert so["data"]["output_mode_observed"] == "native"
    assert so["data"]["is_native"] is True
    # Offline native selection is NOT proof of provider validation.
    assert so["data"]["provider_validation"] == "unverified_until_live"
    assert so["data"]["synthetic_model_profile"]["inferred_from_real_provider"] is False


def test_deferred_tool_preserved_and_not_executed():
    env = _base(
        scenario="tools",
        output="deferred",
        output_type="DeferredToolRequests",
        finish_reason="tool_call",
        deferred={
            "approvals": [
                {"tool_name": "get_weather", "tool_call_id": "c1", "args": {"city": "Paris"}}
            ],
            "calls": [],
            "metadata": None,
        },
    )
    tr = _normalize(env)
    types = _types(tr)
    assert "tool_call_started" in types
    completed = next(e for e in tr["events"] if e["type"] == "tool_call_completed")
    assert completed["data"]["call_id"] == "c1"
    assert completed["data"]["name"] == "get_weather"
    assert completed["data"]["arguments"] == {"city": "Paris"}
    assert completed["data"]["deferred"] is True
    # The deferral is preserved as a framework_extension, never provider_extension.
    fw = [e for e in tr["events"] if e["type"] == "framework_extension"]
    assert any(e["data"].get("native_type") == "pydanticai_deferred_tool_requests" for e in fw)
    assert "provider_extension" not in types


def test_stream_text_deltas_from_events():
    env = _base(
        capture_kind="stream",
        scenario="stream",
        stream_events=[
            {
                "event_type": "PartStartEvent",
                "event": {"part": {"part_kind": "text", "content": "one\n"}},
            },
            {"event_type": "PartDeltaEvent", "event": {"delta": {"content_delta": "two\n"}}},
            {"event_type": "AgentRunResultEvent", "final_output_type": "str"},
        ],
        graph_iteration_note="two distinct exercises",
    )
    tr = _normalize(env)
    deltas = [e for e in tr["events"] if e["type"] == "text_delta"]
    assert [d["data"]["text"] for d in deltas] == ["one\n", "two\n"]
    assert _types(tr)[-1] == "response_completed"


def test_error_not_labelled_provider():
    env = {
        "capture_kind": "error",
        "exception_type": "UnexpectedModelBehavior",
        "exception_module": "pydantic_ai.exceptions",
        "message": "synthetic",
        "cause_chain": [{"type": "UnexpectedModelBehavior", "message": "synthetic"}],
    }
    tr = _normalize(env)
    err = tr["events"][0]
    assert err["type"] == "error"
    assert err["data"]["exception_type"] == "UnexpectedModelBehavior"
    assert err["data"]["native_type"] == "framework_error"


def test_graph_nodes_preserved_as_framework_extension():
    tr = _normalize(_base())
    fw = next(e for e in tr["events"] if e["type"] == "framework_extension")
    assert fw["data"]["native_type"] == "pydanticai_agent"
    assert [n["node_type"] for n in fw["data"]["graph_nodes"]] == ["UserPromptNode", "End"]
