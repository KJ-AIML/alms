"""Per-fixture execution-path classification (P0.7A evidence-accuracy amendment).

The six fixtures do NOT all use an identical path. TOOL-001 in particular is a PARTIAL path
(request transformation + framework response-object injection), NOT the full
litellm.completion(tools=...) path, which imports proxy MCP utilities requiring fastapi. A path
is recorded as exercised only when it was actually run, never because an output type was
instantiated.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.__main__ import run
from probe.client import execution_path


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
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    return json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))


# --- pure classifier (fixture-shape independent) --------------------------------------
def test_classifier_paths_per_scenario():
    assert execution_path("generation")["components"] == ["completion_mock_response"]
    assert execution_path("roles")["components"] == ["completion_mock_response"]
    assert execution_path("stream")["components"] == ["completion_mock_response"]
    assert execution_path("usage")["components"] == ["completion_mock_response"]
    assert execution_path("structured")["components"] == [
        "completion_mock_response",
        "framework_request_transformation",
    ]
    assert execution_path("tools")["components"] == [
        "framework_request_transformation",
        "framework_response_object_injection",
    ]


def test_full_provider_adapter_never_exercised_any_scenario():
    for scenario in ("generation", "roles", "structured", "tools", "stream", "usage"):
        ep = execution_path(scenario)
        assert ep["full_provider_adapter_exercised"] is False
        assert "full_provider_adapter" in ep["unverified_until_live"]


# --- TOOL-001: partial path, explicitly classified ------------------------------------
def test_tool_fixture_is_partial_not_full_completion_path(tmp_path):
    resp = _run("TOOL-001", tmp_path)
    ep = resp["execution_path"]
    assert ep["components"] == [
        "framework_request_transformation",
        "framework_response_object_injection",
    ]
    assert ep["full_completion_tools_path_exercised"] is False
    assert ep["coverage"] == "offline_partial_request_transform_plus_response_injection"
    assert "full_completion_tools_path" in ep["unverified_until_live"]
    assert "fastapi" in ep["package_boundary_dependency"]


def test_tool_request_transformation_evidence_exists(tmp_path):
    resp = _run("TOOL-001", tmp_path)
    tr = resp["tool_request_translation"]
    assert tr["exercised"] is True
    assert tr["mechanism"] == "litellm.utils.get_optional_params"
    assert tr["tools_in_provider_params"] is True


def test_tool_response_object_injection_evidence_exists(tmp_path):
    resp = _run("TOOL-001", tmp_path)
    # A real litellm ModelResponse tool-call representation exists (id/name/raw args).
    calls = resp["response"]["choices"][0]["message"]["tool_calls"]
    assert calls[0]["id"]
    assert calls[0]["function"]["name"] == "get_weather"
    assert calls[0]["function"]["arguments"] == '{"city": "Paris"}'


def test_no_tool_is_executed(tmp_path):
    resp = _run("TOOL-001", tmp_path)
    # The probe captures the tool CALL; it never executes a tool. No tool result appears in the
    # message content, and the message role stays assistant (no tool/function result turn).
    msg = resp["response"]["choices"][0]["message"]
    assert msg["role"] == "assistant"
    assert msg.get("content") in (None, "")
    # No follow-up message / tool-result evidence exists in the single captured response.
    assert len(resp["response"]["choices"]) == 1


# --- other five fixtures: completion mock path ----------------------------------------
def test_generation_roles_usage_use_completion_mock_response(tmp_path):
    for fid in ("GEN-001", "ROLE-001", "USAGE-001"):
        out = tmp_path / fid
        out.mkdir()
        ep = _run(fid, out)["execution_path"]
        assert ep["components"] == ["completion_mock_response"]
        assert ep.get("full_completion_tools_path_exercised") is None  # not a tool fixture


def test_structured_is_completion_mock_plus_request_transformation(tmp_path):
    ep = _run("STR-001", tmp_path)["execution_path"]
    assert ep["components"] == ["completion_mock_response", "framework_request_transformation"]
    assert ep["coverage"] == "offline_completion_mock_path"


def test_stream_uses_completion_mock_response(tmp_path):
    ep = _run("STREAM-001", tmp_path, stream=True)["execution_path"]
    assert ep["components"] == ["completion_mock_response"]


# --- boundary: fastapi absent, proxy never started ------------------------------------
def test_fastapi_absent_and_proxy_dependency_boundary():
    # The full tool path's dependency (fastapi) is absent by design; do NOT install it to make the
    # full path pass - that would blur the SDK/Proxy boundary. No Proxy process is started.
    assert importlib.util.find_spec("fastapi") is None
