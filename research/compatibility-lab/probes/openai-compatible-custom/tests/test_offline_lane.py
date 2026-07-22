"""Offline OpenAI-compatible custom endpoint tests (real SDK + mock transport)."""

from __future__ import annotations

import json
from pathlib import Path


from probe.client import build_offline_client, client_retry_config
from probe.execute import execute
from probe.redact import redact, safe_headers
from probe.serialize import write_capture
from probe.translate import to_chat_completions_request
from probe.transport import build_mock_transport

# tests -> probe -> probes -> compatibility-lab -> research
RESEARCH = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = RESEARCH / "runtime-audit" / "fixtures"


def _fixture(rel: str) -> dict:
    return json.loads((FIXTURE_ROOT / rel).read_text(encoding="utf-8"))


def _run(scenario: str, fixture: dict, model: str = "synthetic-model", **controls):
    transport, wire = build_mock_transport(
        scenario=scenario,
        expected_host="compat.example.test",
        simulate_redirect_host=controls.get("simulate_redirect_host"),
    )
    client = build_offline_client(transport=transport, base_url="https://compat.example.test/v1")
    kwargs, meta = to_chat_completions_request(fixture, model)
    capture = execute(client, kwargs)
    capture.attempt_count = len(wire.attempts)
    return client, wire, kwargs, meta, capture


def test_actual_sdk_request_construction_roles() -> None:
    fixture = _fixture("roles/ROLE-001.json")
    client, wire, kwargs, meta, capture = _run("generation", fixture)
    assert client.max_retries == 0
    assert wire.attempts, "SDK must issue a real HTTP attempt"
    attempt = wire.attempts[0]
    assert attempt["method"] == "POST"
    assert attempt["path"].endswith("/chat/completions")
    body = attempt["body_shape"]
    assert body["model"] == "synthetic-model"
    roles = [m["role"] for m in body["messages"]]
    assert "system" in roles and "user" in roles
    assert capture.kind == "response"
    assert capture.response["choices"][0]["message"]["content"]


def test_structured_output_and_tools_and_usage() -> None:
    str_fixture = _fixture("structured/STR-001.json")
    _, wire, kwargs, _, capture = _run("structured", str_fixture)
    assert kwargs["response_format"]["type"] == "json_schema"
    assert "Alice" in capture.response["choices"][0]["message"]["content"]

    tool_fixture = _fixture("tools/TOOL-001.json")
    _, _, tkwargs, _, tcapture = _run("tools", tool_fixture)
    assert tkwargs["tools"][0]["function"]["name"] == "get_weather"
    tools = tcapture.response["choices"][0]["message"]["tool_calls"]
    assert tools[0]["function"]["name"] == "get_weather"

    usage_fixture = _fixture("usage/USAGE-001.json")
    _, _, _, _, ucapture = _run("generation", usage_fixture)
    assert ucapture.response["usage"]["prompt_tokens"] == 8


def test_streaming_and_returned_model() -> None:
    fixture = _fixture("streaming/STREAM-001.json")
    _, wire, kwargs, _, capture = _run("stream_text", fixture)
    assert kwargs.get("stream") is True
    assert capture.kind == "stream"
    assert capture.events
    assert any((e.get("data") or {}).get("model") == "synthetic-model" for e in capture.events)


def test_missing_fields_stay_missing() -> None:
    fixture = _fixture("generation/GEN-001.json")
    _, _, _, _, capture = _run("no_usage", fixture)
    # SDK may materialize absent usage as null; never fabricate zeros.
    assert capture.response.get("usage") in (None, {})
    if capture.response.get("usage") is None:
        assert capture.response.get("usage") != 0
    _, _, _, _, capture2 = _run("no_model", fixture)
    assert capture2.response.get("model") in (None, "")


def test_sdk_errors_zero_retries_attempt_count() -> None:
    fixture = _fixture("generation/GEN-001.json")
    client, wire, kwargs, _, capture = _run("error", fixture)
    assert client_retry_config(client)["openai_client_max_retries"] == 0
    assert capture.kind == "error"
    assert capture.sdk_exception_class
    assert capture.attempt_count == 1
    assert len(wire.attempts) == 1


def test_authorization_never_persisted() -> None:
    headers = safe_headers(
        {"Authorization": "Bearer sk-test-secret-value", "Content-Type": "application/json"}
    )
    assert headers["Authorization"] == "<redacted>"
    redacted, _ = redact({"authorization": "Bearer sk-test-secret-value"}, {"sk-test-secret-value"})
    assert "sk-test" not in json.dumps(redacted)


def test_redirect_host_blocked(tmp_path: Path) -> None:
    fixture = _fixture("generation/GEN-001.json")
    fixture_path = tmp_path / "GEN-001.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    transport, wire = build_mock_transport(
        scenario="generation",
        expected_host="compat.example.test",
        simulate_redirect_host="evil.example.test",
    )
    client = build_offline_client(transport=transport, base_url="https://compat.example.test/v1")
    kwargs, meta = to_chat_completions_request(fixture, "synthetic-model")
    capture = execute(client, kwargs)
    capture.attempt_count = len(wire.attempts)
    assert wire.redirect_blocked is True
    manifest = write_capture(
        capture=capture,
        out_dir=tmp_path / "out",
        request_kwargs=kwargs,
        translate_meta=meta,
        wire_attempts=wire.attempts,
        fixture_path=fixture_path,
        fixture_id="GEN-001",
        run_id="r1",
        endpoint_id="e1",
        boundary_kind="gateway",
        model="synthetic-model",
        openai_version="test",
        started_at="t0",
        redaction_mode="strict",
        execution_mode="offline_sdk_transport",
        redirect_behavior={
            "followed": False,
            "host_changed": True,
            "policy": "rejected",
        },
    )
    assert manifest["identity"]["observed_returned_model_source"] in {
        "endpoint_boundary",
        "unavailable",
    }
    assert manifest["execution_mode"] == "offline_sdk_transport"
    assert "provider_native" not in json.dumps(manifest)


def test_no_base_url_in_manifest_by_default(tmp_path: Path) -> None:
    fixture = _fixture("generation/GEN-001.json")
    fixture_path = tmp_path / "GEN-001.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    _, wire, kwargs, meta, capture = _run("generation", fixture)
    manifest = write_capture(
        capture=capture,
        out_dir=tmp_path / "out",
        request_kwargs=kwargs,
        translate_meta=meta,
        wire_attempts=wire.attempts,
        fixture_path=fixture_path,
        fixture_id="GEN-001",
        run_id="r1",
        endpoint_id="e1",
        boundary_kind="custom_endpoint",
        model="synthetic-model",
        openai_version="test",
        started_at="t0",
        redaction_mode="strict",
        execution_mode="offline_sdk_transport",
    )
    blob = json.dumps(manifest)
    assert "compat.example.test" not in blob or "https://" not in blob
    # host may appear in wire attempts metadata; full URL scheme+host path must not be default evidence
    boundary = json.loads((tmp_path / "out" / "raw" / "endpoint_boundary.json").read_text())
    assert "base_url" not in boundary
