"""PydanticAI Agent probe test fixtures: isolation + a loopback-allowing network tripwire.

PydanticAI's Agent is async; on Windows asyncio needs an internal loopback self-pipe, so the
tripwire allows 127.0.0.1 and blocks every other (outbound) host. Isolation
(ALLOW_MODEL_REQUESTS=False) is applied before every test.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

import pytest

RUNTIME_AUDIT_ROOT = Path(__file__).resolve().parents[3]

_LANE = {
    "lane_id": "pydantic-ai-agent",
    "runtime_layer": "pydantic-ai-agent",
    "provider": "openai",
    "model": "openai:gpt-4o-mini",
    "transport": "direct",
}

_LOOPBACK = ("127.0.0.1", "::1", "localhost", "0.0.0.0")


def _is_loopback(address: object) -> bool:
    host = address[0] if isinstance(address, (tuple, list)) and address else address
    return isinstance(host, str) and (host in _LOOPBACK or host.startswith("127."))


@pytest.fixture(autouse=True)
def _isolation(monkeypatch):
    """Force ALLOW_MODEL_REQUESTS=False and block any OUTBOUND (non-loopback) socket."""
    from probe.client import configure_pydanticai_isolation

    configure_pydanticai_isolation()

    orig = socket.socket.connect

    def guard(self, address, *args, **kwargs):
        if _is_loopback(address):
            return orig(self, address, *args, **kwargs)
        raise RuntimeError(f"outbound network forbidden in probe tests: {address!r}")

    monkeypatch.setattr(socket.socket, "connect", guard)


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


def load_fixture(fixture_id: str) -> dict:
    return json.loads(corpus_fixture(fixture_id).read_text(encoding="utf-8"))


def run_fixture(fixture_id: str, model: str = "openai:gpt-4o-mini"):
    """Translate + execute one corpus fixture offline; return (capture, operation, scenario)."""
    from probe.__main__ import _scenario_for
    from probe.execute import execute
    from probe.translate import to_operation

    fx = load_fixture(fixture_id)
    operation, _meta = to_operation(fx, model)
    scenario = _scenario_for(fx)
    return execute(operation, scenario), operation, scenario


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
