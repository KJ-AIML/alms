"""Offline raw-evidence capture: Anthropic-native shapes preserved, not reshaped to OpenAI."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.client import FakeAnthropicClient
from probe.execute import execute
from probe.__main__ import run

_MIN_OP = {
    "model": "claude-x",
    "max_tokens": 64,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
    "stream": False,
    "structured_output_strategy_requested": None,
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


def test_text_block_and_usage_and_returned_model_retained(tmp_path):
    m = _run("GEN-001", tmp_path)
    resp = _response(m)
    msg = resp["message"]
    assert msg["content"][0]["type"] == "text"
    assert msg["content"][0]["text"] == "Hello there, friend."
    assert msg["stop_reason"] == "end_turn"  # native stop_reason retained
    assert msg["usage"]["input_tokens"] == 9
    assert msg["model"]  # provider-returned model retained on the message
    assert m["package_versions"]["anthropic"] == "0.116.0"
    assert m["model"] == "claude-mock-model"  # requested model on the manifest (kept separate)


def test_multiple_content_blocks_retained_in_order():
    cap = execute(FakeAnthropicClient(scenario="multi"), _MIN_OP)
    types = [b["type"] for b in cap.message["content"]]
    texts = [b["text"] for b in cap.message["content"]]
    assert types == ["text", "text"]
    assert texts == ["First block.", "Second block."]  # order preserved


def test_tool_use_id_name_input_retained(tmp_path):
    resp = _response(_run("TOOL-001", tmp_path))
    block = resp["message"]["content"][0]
    assert block["type"] == "tool_use"  # NOT reshaped into an OpenAI function_call
    assert block["id"] and block["name"] == "get_weather"
    assert block["input"] == {"city": "Paris"}
    assert resp["message"]["stop_reason"] == "tool_use"


_STRUCT_OP = {
    "model": "claude-x",
    "max_tokens": 64,
    "messages": [{"role": "user", "content": [{"type": "text", "text": "Alice is 30."}]}],
    "stream": False,
    "structured_output_strategy_requested": "output_config.format",
    "structured_output_format": "json_schema",
    "output_config": {
        "format": {
            "type": "json_schema",
            "schema": {"type": "object", "required": ["name", "age"], "properties": {}},
        }
    },
}


def test_structured_uses_output_config_format_native_text_block(tmp_path):
    m = _run("STR-001", tmp_path)
    resp = _response(m)
    # Native JSON structured output: strategy is output_config.format, the response is a native
    # TEXT block (not a tool_use block), and raw text stays distinct from the parsed value.
    assert resp["structured"]["strategy"] == "output_config.format"
    assert resp["structured"]["format"] == "json_schema"
    assert resp["message"]["content"][0]["type"] == "text"
    assert resp["structured"]["raw_text"] == '{"name": "Alice", "age": 30}'  # raw, distinct
    assert resp["structured"]["parsed"] == {"name": "Alice", "age": 30}  # parsed, distinct
    assert resp["structured"]["schema_validation"] == "passed"
    assert resp["structured"]["outcome"] == "schema_validation_passed"
    # The request evidence confirms output_config.format was actually sent.
    req = json.loads(Path(m["request_path"]).read_text(encoding="utf-8"))
    assert req["output_config"]["format"]["type"] == "json_schema"
    assert req["tools"] is None


def test_structured_schema_failure_distinct_from_parse_and_pass():
    cap = execute(FakeAnthropicClient(scenario="structured_schema_fail"), _STRUCT_OP)
    assert cap.structured["outcome"] == "schema_validation_failed"
    assert cap.structured["schema_validation"] == "failed"
    assert cap.structured["parsed"] == {"name": "Alice"}  # parsed ok, but missing required "age"


def test_structured_non_json_is_parse_failed_not_schema_failed():
    cap = execute(FakeAnthropicClient(scenario="structured_notjson"), _STRUCT_OP)
    assert cap.structured["outcome"] == "parse_failed"
    assert cap.structured["parse_error"]
    assert cap.structured["schema_validation"] == "not_performed"


def test_structured_refusal_distinct_from_schema_failure():
    cap = execute(FakeAnthropicClient(scenario="structured_refusal"), _STRUCT_OP)
    assert cap.structured["outcome"] == "provider_refusal"  # a refusal, not a schema failure
    assert cap.structured["stop_reason"] == "refusal"
    assert cap.structured["schema_validation"] == "not_performed"


def test_structured_max_tokens_distinct_from_schema_failure():
    cap = execute(FakeAnthropicClient(scenario="structured_max_tokens"), _STRUCT_OP)
    assert cap.structured["outcome"] == "max_tokens_truncation"  # truncation, not schema failure
    assert cap.structured["stop_reason"] == "max_tokens"


def test_cache_usage_is_distinguishable():
    cap = execute(FakeAnthropicClient(scenario="cache"), _MIN_OP)
    usage = cap.message["usage"]
    assert usage["cache_creation_input_tokens"] == 20  # cache != ordinary input usage
    assert usage["cache_read_input_tokens"] == 5
    assert usage["input_tokens"] == 10


def test_usage_absent_stays_absent_shape():
    # A plain generation reports usage; cache fields are None (absent), never fabricated as 0.
    cap = execute(FakeAnthropicClient(scenario="generation"), _MIN_OP)
    assert cap.message["usage"]["cache_read_input_tokens"] is None


def test_raw_artifacts_written_offline_mock(tmp_path):
    m = _run("GEN-001", tmp_path)
    assert Path(m["request_path"]).is_file()
    assert Path(m["response_path"]).is_file()
    assert m["execution_mode"] == "offline_mock"  # never live
