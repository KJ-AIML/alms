"""Probe test fixtures, including an in-process network tripwire."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail immediately on any accidental outbound socket connection."""

    def _blocked(*args, **kwargs):
        raise RuntimeError("network access is forbidden in probe tests")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


def write_fixture(path: Path, **overrides) -> Path:
    fixture = {
        "spec": "alms.dev/runtime-audit-fixture/v0",
        "id": overrides.get("id", "GEN-001"),
        "feature": overrides.get("feature", "generation"),
        "tier": "BASE",
        "cost_class": "live_core",
        "summary": "test fixture",
        "messages": overrides.get(
            "messages",
            [{"role": "user", "parts": [{"kind": "text", "text": "Say hi."}]}],
        ),
        "requirements": {"live_required": True, "capabilities": ["generation"]},
        "execution": overrides.get("execution", {"temperature": 0, "max_output_tokens": 32}),
        "expected_invariants": {"non_empty_assistant_content": True},
        "allowed_outcomes": ["PASS"],
        "evidence_requirements": {"raw": ["raw_response"], "normalized": ["response_completed"]},
    }
    for key in ("output_schema", "tools"):
        if key in overrides:
            fixture[key] = overrides[key]
    path.write_text(json.dumps(fixture), encoding="utf-8")
    return path


def write_request(path: Path, fixture_path: Path, out_dir: Path, **overrides) -> Path:
    request = {
        "protocol_version": "alms.dev/probe-protocol/v0",
        "run_id": overrides.get("run_id", "testrun"),
        "fixture_path": str(fixture_path),
        "lane": overrides.get(
            "lane",
            {
                "lane_id": "openai-native",
                "runtime_layer": "openai",
                "provider": "openai",
                "model": "mock-model",
            },
        ),
        "output_dir": str(out_dir),
        "controls": overrides.get(
            "controls", {"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True}
        ),
        "redaction_mode": "strict",
    }
    for key in ("drop_key",):
        overrides.pop(key, None)
    path.write_text(json.dumps(request), encoding="utf-8")
    return path
