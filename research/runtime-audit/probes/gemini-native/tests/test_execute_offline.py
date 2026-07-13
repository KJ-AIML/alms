"""Offline raw-evidence capture: Interactions-native shapes preserved, not reshaped to OpenAI."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.client import FakeGeminiClient
from probe.execute import execute
from probe.__main__ import run

_STRUCT_OP = {
    "model": "gemini-x",
    "input": [{"type": "user_input", "content": [{"type": "text", "text": "Alice is 30."}]}],
    "stream": False,
    "store": False,
    "response_format": {
        "text": {
            "mime_type": "application/json",
            "jsonSchema": {"type": "object", "required": ["name", "age"]},
        }
    },
    "structured_output_strategy_requested": "response_format.text.json_schema",
}


def _run(fid: str, out: Path, stream: bool = False) -> dict:
    req = write_request(
        out / "req.json",
        corpus_fixture(fid),
        out,
        controls={
            "timeout_ms": 30000,
            "max_attempts": 1,
            "max_output_tokens": 128,
            "mock_mode": True,
            "stream": stream,
        },
    )
    code, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert code == 0
    return manifest


def _response(manifest: dict) -> dict:
    return json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))


def test_full_interaction_resource_and_returned_model_retained(tmp_path):
    m = _run("GEN-001", tmp_path)
    it = _response(m)["interaction"]
    assert it["id"] and it["object"] == "interaction"
    assert it["status"] == "completed"
    assert it["model"]  # provider-returned model on the Interaction
    assert m["model"] == "gemini-mock-model"  # requested model on the manifest (kept separate)
    assert it["steps"][0]["type"] == "model_output"
    assert m["package_versions"]["google-genai"] == "2.11.0"


def test_output_text_is_separate_from_authoritative_steps(tmp_path):
    it = _response(_run("GEN-001", tmp_path))["interaction"]
    # output_text is a convenience projection; the authoritative evidence is the full steps list.
    assert it["output_text"] == "Hello there, friend."
    assert it["steps"][0]["content"][0]["text"] == "Hello there, friend."


def test_function_call_step_preserved_native(tmp_path):
    it = _response(_run("TOOL-001", tmp_path))["interaction"]
    step = it["steps"][0]
    assert step["type"] == "function_call"  # NOT reshaped into an OpenAI function item
    assert step["id"] == "fc_mock_1" and step["name"] == "get_weather"
    assert step["arguments"] == {"city": "Paris"}
    assert it["status"] == "requires_action"  # a function call awaits a result


def test_structured_native_response_format_parse_distinct_from_raw(tmp_path):
    m = _run("STR-001", tmp_path)
    resp = _response(m)
    s = resp["structured"]
    assert s["strategy"] == "response_format.text.json_schema"
    assert s["mime_type"] == "application/json"
    assert s["raw_text"] == '{"name": "Alice", "age": 30}'  # raw, distinct
    assert s["parsed"] == {"name": "Alice", "age": 30}  # parsed, distinct
    assert s["outcome"] == "schema_validation_passed"
    req = json.loads(Path(m["request_path"]).read_text(encoding="utf-8"))
    assert req["response_format"]["text"]["mime_type"] == "application/json"  # request confirms it
    assert "tools" not in req  # no tool sent for a structured request (actual payload)
    assert "structured_output_strategy_requested" not in req  # audit-only key not in the payload


def test_incomplete_interaction_distinct_from_schema_failure():
    cap = execute(FakeGeminiClient(scenario="structured_incomplete"), _STRUCT_OP)
    assert cap.structured["outcome"] == "interaction_incomplete"  # not a schema failure
    assert cap.structured["interaction_status"] == "incomplete"


def test_parse_failure_distinct_from_schema_failure():
    cap = execute(FakeGeminiClient(scenario="structured_notjson"), _STRUCT_OP)
    assert cap.structured["outcome"] == "parse_failed"
    cap2 = execute(FakeGeminiClient(scenario="structured_schema_fail"), _STRUCT_OP)
    assert cap2.structured["outcome"] == "schema_validation_failed"


def test_usage_totals_and_cache_distinct():
    cap = execute(
        FakeGeminiClient(scenario="cache"),
        {"model": "m", "input": [], "stream": False, "store": False},
    )
    u = cap.interaction["usage"]
    assert u["total_input_tokens"] == 9 and u["total_output_tokens"] == 5
    assert u["total_cached_tokens"] == 20  # cache distinct from ordinary input tokens


def test_thought_step_retained_structurally(tmp_path):
    cap = execute(
        FakeGeminiClient(scenario="thought"),
        {"model": "m", "input": [], "stream": False, "store": False},
    )
    types = [s["type"] for s in cap.interaction["steps"]]
    assert "thought" in types  # thought step retained as native structural evidence
    thought = next(s for s in cap.interaction["steps"] if s["type"] == "thought")
    assert thought["thought_signature"]  # signature preserved as opaque protocol evidence
    assert cap.interaction["usage"]["total_thought_tokens"] == 4


def test_raw_written_and_offline_mock(tmp_path):
    m = _run("GEN-001", tmp_path)
    assert Path(m["request_path"]).is_file() and Path(m["response_path"]).is_file()
    assert m["execution_mode"] == "offline_mock"
