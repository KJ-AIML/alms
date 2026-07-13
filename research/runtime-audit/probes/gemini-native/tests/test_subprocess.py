"""Subprocess protocol behavior (python -m probe <request.json>)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import write_fixture, write_request

_LIVE_LANE = {
    "lane_id": "gemini-native",
    "runtime_layer": "google-genai",
    "provider": "google",
    "model": "gemini-real",
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


def _blocked_reason(out: Path) -> str:
    return json.loads((out / "blocked.json").read_text())["reason"]


def test_mock_subprocess_success_no_secret(tmp_path):
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out)
    env = {
        **os.environ,
        "GEMINI_API_KEY": "AIzaSyDONOTLEAK000000000000000000000000",
        "ALMS_PROBE_BLOCK_NETWORK": "1",
    }
    result = _run(req, env=env)
    assert result.returncode == 0, result.stderr
    manifest = json.loads(result.stdout)
    assert manifest["probe_id"] == "gemini-native"
    assert manifest["provider"] == "google"
    blob = "".join(p.read_text(encoding="utf-8") for p in (out / "raw").glob("*"))
    assert "DONOTLEAK" not in blob


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
    assert _blocked_reason(out) == "BLOCKED_CONFIGURATION"


def test_blocked_no_credential_exit_3(tmp_path):
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    result = _run(req, env=env)
    assert result.returncode == 3
    assert _blocked_reason(out) == "BLOCKED_CREDENTIAL"


def test_only_gemini_key_satisfies_gate(tmp_path):
    # OpenRouter / OpenAI / Vertex-ADC credentials must NOT unlock the Gemini live path.
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    env["OPENROUTER_API_KEY"] = "sk-or-ignored"
    env["OPENAI_API_KEY"] = "sk-openai-ignored"
    env["GOOGLE_APPLICATION_CREDENTIALS"] = "/tmp/adc-ignored.json"
    result = _run(req, env=env)
    assert result.returncode == 3
    assert _blocked_reason(out) == "BLOCKED_CREDENTIAL"


def test_google_genai_importable_in_probe_env():
    assert importlib.util.find_spec("google.genai") is not None
