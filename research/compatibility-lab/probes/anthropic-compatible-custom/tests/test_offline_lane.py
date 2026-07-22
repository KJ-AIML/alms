"""Offline Anthropic-compatible custom endpoint tests."""

from __future__ import annotations

import json
from pathlib import Path

from probe.client import build_offline_client, client_retry_config, supports_custom_base_url
from probe.execute import execute
from probe.serialize import write_capture
from probe.translate import to_messages_request
from probe.transport import build_mock_transport

RESEARCH = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = RESEARCH / "runtime-audit" / "fixtures"


def _fixture(rel: str) -> dict:
    return json.loads((FIXTURE_ROOT / rel).read_text(encoding="utf-8"))


def _run(scenario: str, fixture: dict, model: str = "synthetic-model"):
    transport, wire = build_mock_transport(scenario=scenario, expected_host="compat.example.test")
    client = build_offline_client(transport=transport, base_url="https://compat.example.test")
    kwargs, meta = to_messages_request(fixture, model)
    capture = execute(client, kwargs)
    capture.attempt_count = len(wire.attempts)
    return client, wire, kwargs, meta, capture


def test_sdk_supports_custom_base_url() -> None:
    support = supports_custom_base_url()
    assert support["status"] == "SUPPORTED"
    assert support["base_url_param_present"] is True


def test_actual_sdk_request_construction_content_blocks() -> None:
    fixture = _fixture("roles/ROLE-001.json")
    client, wire, kwargs, _, capture = _run("generation", fixture)
    assert client.max_retries == 0
    assert wire.attempts
    body = wire.attempts[0]["body_shape"]
    assert body["system"]
    assert body["messages"][0]["content"][0]["type"] == "text"
    assert capture.kind == "response"
    assert capture.response["content"][0]["type"] == "text"
    assert "choices" not in capture.response


def test_structured_tool_use_streaming_usage_cache() -> None:
    _, _, kwargs, _, capture = _run("structured", _fixture("structured/STR-001.json"))
    assert kwargs["output_config"]["format"]["type"] == "json_schema"
    assert "Alice" in capture.response["content"][0]["text"]

    _, _, tkwargs, _, tcapture = _run("tools", _fixture("tools/TOOL-001.json"))
    assert tkwargs["tools"][0]["name"] == "get_weather"
    assert tcapture.response["content"][0]["type"] == "tool_use"
    assert tcapture.response["content"][0]["input"]["city"] == "Paris"

    _, _, skwargs, _, scapture = _run("stream_text", _fixture("streaming/STREAM-001.json"))
    assert skwargs.get("stream") is True
    assert scapture.kind == "stream"
    assert scapture.events

    _, _, _, _, ucapture = _run("cache", _fixture("usage/USAGE-001.json"))
    usage = ucapture.response["usage"]
    assert usage["cache_creation_input_tokens"] == 20
    assert usage["cache_read_input_tokens"] == 5


def test_returned_model_and_missing_model() -> None:
    _, _, _, _, capture = _run("generation", _fixture("generation/GEN-001.json"))
    assert capture.response["model"] == "synthetic-model"
    _, _, _, _, capture2 = _run("no_model", _fixture("generation/GEN-001.json"))
    # SDK may materialize absent model as null; do not copy requested model into it.
    assert capture2.response.get("model") in (None, "")


def test_sdk_errors_zero_retries() -> None:
    client, wire, kwargs, _, capture = _run("error", _fixture("generation/GEN-001.json"))
    assert client_retry_config(client)["anthropic_client_max_retries"] == 0
    assert capture.kind == "error"
    assert capture.attempt_count == 1
    assert len(wire.attempts) == 1


def test_manifest_preserves_anthropic_shape(tmp_path: Path) -> None:
    fixture = _fixture("tools/TOOL-001.json")
    fixture_path = tmp_path / "TOOL-001.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    _, wire, kwargs, meta, capture = _run("tools", fixture)
    manifest = write_capture(
        capture=capture,
        out_dir=tmp_path / "out",
        request_kwargs=kwargs,
        translate_meta=meta,
        wire_attempts=wire.attempts,
        fixture_path=fixture_path,
        fixture_id="TOOL-001",
        run_id="r1",
        endpoint_id="e1",
        boundary_kind="gateway",
        model="synthetic-model",
        anthropic_version="test",
        started_at="t0",
        redaction_mode="strict",
        execution_mode="offline_sdk_transport",
    )
    boundary = json.loads((tmp_path / "out" / "raw" / "endpoint_boundary.json").read_text())
    assert boundary["content_blocks"][0]["type"] == "tool_use"
    assert "choices" not in boundary
    assert manifest["identity"]["observed_returned_model_source"] == "endpoint_boundary"
    assert manifest["evidence_class"] == "custom_endpoint_compatibility"
