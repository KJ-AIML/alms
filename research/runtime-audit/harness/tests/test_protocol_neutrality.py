"""P0.6C: cross-lane protocol-neutrality preservation + negative guarantees.

Preservation: each runtime's native lifecycle survives into the shared vocabulary as an
extension event (never collapsed, never deleted). Negative: normalizers do not fabricate
provider semantics, invent provider-native event names, infer parallel execution, turn thought
metadata into reasoning text, treat valid JSON alone as native-structured proof, zero missing
usage, discard unknown events, or mislabel framework chunks as provider events.
"""

from __future__ import annotations

import json

from alms_audit.normalizers import anthropic as anthropic_nz
from alms_audit.normalizers import gemini as gemini_nz
from alms_audit.normalizers import langchain as langchain_nz
from alms_audit.normalizers import openai as openai_nz
from alms_audit.reporting.compare import _structured_mechanism
from alms_audit.schemas import default_root, is_valid, validation_errors


def _types(out):
    return [e["type"] for e in out["events"]]


def test_shipped_neutrality_matrix_validates_against_its_schema():
    root = default_root()
    matrix = json.loads(
        (root / "reports" / "protocol-neutrality-matrix.json").read_text(encoding="utf-8")
    )
    # Five lanes as of P0.7A (litellm-sdk added to the P0.6C four).
    five_lanes = {"openai-native", "langchain", "anthropic-native", "gemini-native", "litellm-sdk"}
    six_fixtures = {"GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"}
    assert matrix["generated_offline"] is True
    assert set(matrix["lanes"]) == five_lanes
    assert validation_errors("protocol-neutrality-matrix", matrix, root) == []

    # Six-fixture coverage recorded for every lane (Task 3).
    assert set(matrix["fixture_coverage"]) == five_lanes
    for lane, cov in matrix["fixture_coverage"].items():
        assert set(cov["fixtures"]) == six_fixtures, lane
        assert "offline_mock" in cov["execution"]
        assert cov["evidence"]

    # litellm-sdk records per-fixture execution paths (P0.7A evidence-accuracy amendment); the six
    # fixtures do NOT share one path, and TOOL-001 is NOT the full completion(tools=...) path.
    ll_paths = matrix["fixture_coverage"]["litellm-sdk"]["execution_paths"]
    assert set(ll_paths) == six_fixtures
    assert ll_paths["TOOL-001"]["full_completion_tools_path_exercised"] is False
    assert ll_paths["GEN-001"]["components"] != ll_paths["TOOL-001"]["components"]
    # L-01 recorded (proposed F2), not F1.
    l01 = next(f for f in matrix["findings"] if f["id"] == "L-01")
    assert l01["severity"] == "F2"
    assert l01["status"] == "proposed"

    # Required neutrality dimensions present, each covering all five lanes.
    dims = {d["dimension"]: d for d in matrix["dimensions"]}
    for required in (
        "request_representation",
        "response_containers",
        "structured_output",
        "tool_semantics",
        "streaming",
        "usage",
        "terminal_state",
        "extensions",
        "state_and_privacy",
    ):
        assert required in dims, required
        assert set(dims[required]["by_lane"]) == five_lanes, required


# ------------------------- preservation -------------------------


def test_openai_unknown_item_lifecycle_preserved_as_provider_extension():
    # An OpenAI native event with no shared-vocab mapping is preserved, not dropped.
    events = [{"sequence": 0, "type": "response.reasoning_summary.delta", "data": {"x": 1}}]
    out = openai_nz.normalize_stream(events, "m.json", "raw/e.json")
    assert "provider_extension" in _types(out)
    assert out["events"][0]["data"]["native_type"] == "response.reasoning_summary.delta"
    assert is_valid("normalized-transcript", out)


def test_anthropic_content_block_lifecycle_is_provider_not_framework():
    env = {
        "events": [
            {"sequence": 0, "event": {"type": "message_start", "message": {"usage": {}}}},
            {
                "sequence": 1,
                "event": {"type": "content_block_start", "content_block": {"type": "text"}},
            },
            {"sequence": 2, "event": {"type": "content_block_stop"}},
            {"sequence": 3, "event": {"type": "message_stop"}},
        ]
    }
    out = anthropic_nz.normalize_stream(env, "m.json", "raw/e.json")
    t = _types(out)
    assert "provider_extension" in t  # block lifecycle retained
    assert "framework_extension" not in t  # a provider-native block is never framework-labelled


def test_gemini_step_lifecycle_is_provider_not_framework():
    env = {
        "events": [
            {"sequence": 0, "event": {"event_type": "interaction.created"}},
            {"sequence": 1, "event": {"event_type": "step.start", "step_type": "model_output"}},
            {"sequence": 2, "event": {"event_type": "step.stop"}},
            {
                "sequence": 3,
                "event": {
                    "event_type": "interaction.completed",
                    "interaction": {"status": "completed"},
                },
            },
        ]
    }
    out = gemini_nz.normalize_stream(env, "m.json", "raw/e.json")
    t = _types(out)
    assert t.count("provider_extension") >= 2  # step_start + step_stop retained
    assert "framework_extension" not in t


def test_langchain_framework_chunk_is_framework_extension_not_provider():
    env = {"chunks": [{"sequence": 0, "chunk": {"response_metadata": {"finish_reason": "stop"}}}]}
    out = langchain_nz.normalize_stream(env, "m.json", "raw/e.json")
    t = _types(out)
    assert "framework_extension" in t  # a synthesized framework chunk is preserved as framework
    assert "provider_extension" not in t  # and NEVER as a provider-native event


# ------------------------- structured-output honesty -------------------------


def test_valid_json_alone_is_not_native_structured_proof():
    # Structured presence with no explicit strategy/probe signal is NOT classified native.
    assert _structured_mechanism(None, None, has_structured=True) == "unknown"
    # Only an explicit native strategy earns the native_json_schema label.
    assert (
        _structured_mechanism("langchain", "function_calling", True) == "framework_function_calling"
    )
    assert _structured_mechanism(None, "output_config.format", True).startswith(
        "native_json_schema"
    )


# ------------------------- negative guarantees -------------------------


def test_no_lane_fabricates_missing_usage():
    assert openai_nz.extract_usage("response", {"status": "completed"}) is None
    assert anthropic_nz.extract_usage("response", {"message": {"usage": None}}) is None
    assert gemini_nz.extract_usage("response", {"interaction": {}}) is None
    assert langchain_nz.extract_usage("response", {"message": {}}) is None


def test_langchain_never_emits_a_provider_native_event_name():
    # Framework transformations must not masquerade as provider-native semantics.
    env = {"message": {"content": "hi", "additional_kwargs": {"x": 1}, "response_metadata": {}}}
    out = langchain_nz.normalize_response(env, "m.json", "raw/r.json")
    assert "provider_extension" not in _types(out)


def test_tool_calls_are_not_merged_or_marked_parallel():
    env = {
        "message": {
            "role": "assistant",
            "content": [
                {"type": "tool_use", "id": "toolu_a", "name": "f", "input": {}},
                {"type": "tool_use", "id": "toolu_b", "name": "g", "input": {}},
            ],
            "stop_reason": "tool_use",
        },
        "structured": None,
    }
    out = anthropic_nz.normalize_response(env, "m.json", "raw/r.json")
    completed = [e for e in out["events"] if e["type"] == "tool_call_completed"]
    assert len(completed) == 2  # distinct call IDs kept distinct, not merged (DevSpec S43)
    assert {c["data"]["call_id"] for c in completed} == {"toolu_a", "toolu_b"}
    assert all("parallel" not in e["data"] for e in out["events"])  # execution model not inferred


def test_gemini_thought_is_structural_only_no_reasoning_text():
    env = {
        "interaction": {
            "status": "completed",
            "steps": [
                {"type": "thought", "thought_signature": "opaque-sig"},
                {"type": "model_output", "content": [{"type": "text", "text": "answer"}]},
            ],
        }
    }
    out = gemini_nz.normalize_response(env, "m.json", "raw/r.json")
    thought = next(e for e in out["events"] if e["data"].get("native_type") == "thought_step")
    assert thought["type"] == "provider_extension"
    assert thought["data"] == {"native_type": "thought_step", "thought_signature_present": True}
    assert "text" not in thought["data"] and "reasoning" not in thought["data"]


def test_unknown_events_are_never_discarded():
    events = [
        {"sequence": 0, "type": "response.created", "data": {}},
        {"sequence": 1, "type": "totally.unknown.event", "data": {"a": 1}},
    ]
    out = openai_nz.normalize_stream(events, "m.json", "raw/e.json")
    # No input event is lost: the unknown one is preserved as a provider_extension.
    assert len(out["events"]) >= 2
    assert any(
        e["type"] == "provider_extension" and e["data"]["native_type"] == "totally.unknown.event"
        for e in out["events"]
    )
