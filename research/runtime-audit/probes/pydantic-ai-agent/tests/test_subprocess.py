"""Subprocess protocol behavior (python -m probe <request.json>).

Includes the guarantee that no framework banner corrupts the manifest: real stdout must carry
ONLY the one-line JSON manifest the harness parses. The offline run must complete with the
network tripwire armed (loopback allowed, outbound blocked).
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import write_fixture, write_request

_LIVE_LANE = {
    "lane_id": "pydantic-ai-agent",
    "runtime_layer": "pydantic-ai-agent",
    "provider": "openai",
    "model": "openai:gpt-real",
    "transport": "direct",
}
_LIVE_CONTROLS = {"timeout_ms": 30000, "max_attempts": 1, "mock_mode": False}


def _run(request_path: Path, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "probe", str(request_path)],
        capture_output=True,
        text=True,
        env=env,
    )


def test_mock_subprocess_stdout_is_clean_single_line_manifest(tmp_path):
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out)
    env = {**os.environ, "OPENAI_API_KEY": "sk-DONOTLEAK000000", "ALMS_PROBE_BLOCK_NETWORK": "1"}
    result = _run(req, env=env)
    assert result.returncode == 0, result.stderr
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    assert len(lines) == 1, f"stdout not clean: {result.stdout!r}"
    manifest = json.loads(lines[0])
    assert manifest["probe_id"] == "pydantic-ai-agent"
    assert manifest["execution_mode"] == "offline_mock"
    assert Path(manifest["response_path"]).is_file()
    assert Path(manifest["request_path"]).is_file()
    blob = "".join(p.read_text(encoding="utf-8") for p in (out / "raw").glob("*"))
    assert "sk-DONOTLEAK000000" not in blob


def test_offline_subprocess_runs_with_network_blocked(tmp_path):
    # The async Agent run must complete offline even with outbound sockets blocked (loopback ok).
    fx = write_fixture(tmp_path / "fx.json", id="TOOL-001", feature="tools")
    fx_data = json.loads(fx.read_text())
    fx_data["tools"] = [
        {
            "name": "get_weather",
            "description": "weather",
            "parameters": {
                "type": "object",
                "required": ["city"],
                "properties": {"city": {"type": "string"}},
            },
        }
    ]
    fx.write_text(json.dumps(fx_data), encoding="utf-8")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out)
    env = {**os.environ, "ALMS_PROBE_BLOCK_NETWORK": "1"}
    result = _run(req, env=env)
    assert result.returncode == 0, result.stderr
    manifest = json.loads([ln for ln in result.stdout.splitlines() if ln.strip()][0])
    response = json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))
    assert response["output_type"] == "DeferredToolRequests"
    assert response["retry"]["tool_executions_observed"] == 0


def test_invalid_request_exit_2(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"protocol_version": "x"}), encoding="utf-8")
    assert _run(bad).returncode == 2


def test_unknown_fixture_exit_2(tmp_path):
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", tmp_path / "nope.json", out)
    assert _run(req).returncode == 2


def test_blocked_no_model_exit_3(tmp_path):
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(
        tmp_path / "req.json", fx, out, lane={**_LIVE_LANE, "model": None}, controls=_LIVE_CONTROLS
    )
    result = _run(req)
    assert result.returncode == 3
    assert json.loads((out / "blocked.json").read_text())["reason"] == "BLOCKED_CONFIGURATION"


def test_blocked_no_credential_exit_3(tmp_path):
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    result = _run(req, env=env)
    assert result.returncode == 3
    assert json.loads((out / "blocked.json").read_text())["reason"] == "BLOCKED_CREDENTIAL"


def test_live_path_refused_even_with_credential(tmp_path):
    # The live path is NOT enabled in P0.7B: even with a credential present it is refused, so no
    # provider request can occur from this session.
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {**os.environ, "OPENAI_API_KEY": "sk-present-but-refused-000000"}
    result = _run(req, env=env)
    assert result.returncode == 3
    assert json.loads((out / "blocked.json").read_text())["reason"] == "BLOCKED_CONFIGURATION"


def test_gateway_key_does_not_satisfy_credential_gate(tmp_path):
    # A gateway / OpenRouter key must NOT unlock the live path: only a direct OPENAI_API_KEY does.
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    env["OPENROUTER_API_KEY"] = "sk-or-should-be-ignored-000000"
    result = _run(req, env=env)
    assert result.returncode == 3
    assert json.loads((out / "blocked.json").read_text())["reason"] == "BLOCKED_CREDENTIAL"


def test_pydantic_ai_importable_in_probe_env():
    assert importlib.util.find_spec("pydantic_ai") is not None


def test_provider_sdk_absent_confirms_slim_isolation():
    # This lane audits the PydanticAI Agent with FunctionModel only. Vendor provider SDKs are
    # deliberately absent in the slim install; their absence blocks any real provider model.
    assert importlib.util.find_spec("openai") is None
    assert importlib.util.find_spec("logfire") is None
