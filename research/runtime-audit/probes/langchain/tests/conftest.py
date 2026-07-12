"""LangChain probe test fixtures, including an in-process network tripwire."""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

RUNTIME_AUDIT_ROOT = Path(__file__).resolve().parents[3]

_LANE = {
    "lane_id": "langchain-openai",
    "runtime_layer": "langchain",
    "provider": "openai",
    "model": "mock-model",
    "transport": "direct",
}


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    """Fail immediately on any accidental outbound socket connection."""

    def _blocked(*args, **kwargs):
        raise RuntimeError("network access is forbidden in probe tests")

    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)


@pytest.fixture
def corpus_root() -> Path:
    return RUNTIME_AUDIT_ROOT


def corpus_fixture(fixture_id: str) -> Path:
    for p in (RUNTIME_AUDIT_ROOT / "fixtures").rglob("*.json"):
        try:
            if json.loads(p.read_text(encoding="utf-8")).get("id") == fixture_id:
                return p
        except (ValueError, OSError):
            continue
    raise AssertionError(f"corpus fixture {fixture_id} not found")


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
        "lane": overrides.get("lane", dict(_LANE)),
        "output_dir": str(out_dir),
        "controls": overrides.get(
            "controls", {"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True}
        ),
        "redaction_mode": "strict",
    }
    path.write_text(json.dumps(request), encoding="utf-8")
    return path
