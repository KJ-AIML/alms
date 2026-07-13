"""Credential isolation: ONLY a direct GEMINI_API_KEY satisfies the lane; no SDK
auto-discovery of GOOGLE_API_KEY, and no credential value ever crosses the boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from conftest import write_fixture, write_request
from probe.__main__ import gemini_api_key
from probe.client import build_client

_LIVE_LANE = {
    "lane_id": "gemini-native",
    "runtime_layer": "google-genai",
    "provider": "google",
    "model": "gemini-real",
    "transport": "direct",
}
_LIVE_CONTROLS = {"timeout_ms": 30000, "max_attempts": 1, "mock_mode": False}


def _run(request_path: Path, env: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "probe", str(request_path)], capture_output=True, text=True, env=env
    )


def test_gemini_api_key_reads_only_gemini():
    assert gemini_api_key({"GEMINI_API_KEY": "g"}) == "g"
    # None of these are accepted (no auto-discovery of GOOGLE_API_KEY, no OpenAI/OpenRouter/ADC).
    assert gemini_api_key({"GOOGLE_API_KEY": "x"}) is None
    assert gemini_api_key({"OPENAI_API_KEY": "x"}) is None
    assert gemini_api_key({"OPENROUTER_API_KEY": "x"}) is None
    assert gemini_api_key({"GOOGLE_APPLICATION_CREDENTIALS": "/tmp/adc.json"}) is None
    assert gemini_api_key({"GOOGLE_GENAI_USE_VERTEXAI": "true"}) is None


def test_explicit_construction_beats_google_api_key_auto_discovery(monkeypatch):
    # With GOOGLE_API_KEY set to a different value, the explicitly constructed client uses the
    # passed Gemini key — proving arg-less auto-discovery is not the path this probe takes.
    monkeypatch.setenv("GOOGLE_API_KEY", "google-auto-should-not-be-used")
    client = build_client("explicit-gemini-key", 30000)
    assert client._api_client.api_key == "explicit-gemini-key"
    assert not client._api_client.vertexai  # never Vertex


def _blocked_env_case(tmp_path, env_overrides) -> str:
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out, lane=_LIVE_LANE, controls=_LIVE_CONTROLS)
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    env.update(env_overrides)
    result = _run(req, env)
    assert result.returncode == 3
    info = json.loads((out / "blocked.json").read_text())
    # blocked.json means the gate fired BEFORE any client was constructed (no network attempt).
    assert info["reason"] == "BLOCKED_CREDENTIAL"
    return info["reason"]


def test_google_api_key_alone_does_not_satisfy_and_builds_no_client(tmp_path):
    _blocked_env_case(tmp_path, {"GOOGLE_API_KEY": "AIza-google-only-000000000000000000"})


def test_vertex_and_adc_and_openai_family_do_not_satisfy(tmp_path):
    _blocked_env_case(
        tmp_path,
        {
            "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/adc-ignored.json",
            "GOOGLE_GENAI_USE_VERTEXAI": "true",
            "OPENAI_API_KEY": "sk-openai-ignored",
            "OPENROUTER_API_KEY": "sk-or-ignored",
        },
    )


def test_no_credential_value_crosses_boundary(tmp_path):
    # A present GEMINI key in a mock run must never appear in the manifest (stdout) or artifacts.
    fx = write_fixture(tmp_path / "fx.json")
    out = tmp_path / "out"
    req = write_request(tmp_path / "req.json", fx, out)
    secret = "AIzaSyGEMINI_DONOTLEAK_00000000000000000"
    env = {**os.environ, "GEMINI_API_KEY": secret, "ALMS_PROBE_BLOCK_NETWORK": "1"}
    result = _run(req, env)
    assert result.returncode == 0, result.stderr
    assert secret not in result.stdout  # never returned across the process boundary
    blob = "".join(p.read_text(encoding="utf-8") for p in (out / "raw").glob("*"))
    assert secret not in blob
