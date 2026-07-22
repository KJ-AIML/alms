"""Probe entrypoint for anthropic-compatible-custom."""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

from .client import (
    build_live_client,
    build_offline_client,
    client_retry_config,
    supports_custom_base_url,
)
from .execute import execute
from .serialize import write_capture
from .translate import to_messages_request
from .transport import build_mock_transport

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BLOCKED = 3
EXIT_UNSUPPORTED = 4

BLOCK_NETWORK_ENV = "ALMS_PROBE_BLOCK_NETWORK"
REQUIRED_KEYS = ("protocol_version", "run_id", "fixture_path", "lane", "output_dir", "controls")
OFFLINE_BASE_URL = "https://compat.example.test"


def _install_network_tripwire() -> None:
    def _blocked(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise RuntimeError(
            "network blocked: ALMS_PROBE_BLOCK_NETWORK is set (offline run must not open a socket)"
        )

    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked  # type: ignore[method-assign]


def _fail(msg: str, code: int) -> int:
    sys.stderr.write(f"[probe:anthropic-compatible-custom] {msg}\n")
    return code


def _write_blocked(out_dir: Path, reason: str, detail: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocked.json").write_text(
        json.dumps({"status": "blocked", "reason": reason, "detail": detail}, indent=2) + "\n",
        encoding="utf-8",
    )


def _scenario_for(fixture: dict) -> str:
    feature = fixture.get("feature")
    execution = fixture.get("execution", {})
    stream = bool(execution.get("stream"))
    has_tools = bool(fixture.get("tools"))
    if feature == "errors":
        return "error"
    if stream and has_tools:
        return "stream_tools"
    if stream:
        return "stream_text"
    if has_tools:
        return "tools"
    if fixture.get("output_schema"):
        return "structured"
    if feature == "usage":
        return "cache"
    return "generation"


def run(request: dict) -> tuple[int, dict | None]:
    missing = [k for k in REQUIRED_KEYS if k not in request]
    if missing:
        return _fail(f"invalid request: missing {missing}", EXIT_INVALID), None

    support = supports_custom_base_url()
    if support["status"] != "SUPPORTED":
        out_dir = Path(request["output_dir"])
        _write_blocked(out_dir, "UNSUPPORTED", support["reason"] or "unsupported")
        return _fail(f"unsupported: {support['reason']}", EXIT_UNSUPPORTED), None

    fixture_path = Path(request["fixture_path"])
    if not fixture_path.is_file():
        return _fail(f"unknown fixture: {fixture_path}", EXIT_INVALID), None
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    out_dir = Path(request["output_dir"])
    lane = request["lane"]
    controls = request["controls"]
    model = lane.get("model") or "synthetic-compat-model"
    endpoint_id = lane.get("endpoint_id") or "compat-anthropic-offline"
    boundary_kind = lane.get("boundary_kind") or "unknown"
    provider_claim = lane.get("provider_claim")
    gateway_claim = lane.get("gateway_claim")
    mock_mode = bool(controls.get("mock_mode"))
    execution_mode = "offline_sdk_transport" if mock_mode else "live_custom_endpoint"
    started_at = datetime.now(timezone.utc).isoformat()
    secret_values: set[str] = set()
    wire_attempts: list[dict] = []
    redirect_behavior = {"followed": False, "host_changed": False}

    if mock_mode:
        scenario = controls.get("scenario") or _scenario_for(fixture)
        transport, wire = build_mock_transport(
            scenario=scenario,
            expected_host="compat.example.test",
            simulate_redirect_host=controls.get("simulate_redirect_host"),
        )
        client = build_offline_client(
            transport=transport,
            base_url=OFFLINE_BASE_URL,
            timeout_ms=controls.get("timeout_ms", 30000),
        )
    else:
        if os.environ.get("ALMS_COMPAT_CONFIRM_LIVE") != "1":
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "ALMS_COMPAT_CONFIRM_LIVE not set")
            return _fail("blocked: BLOCKED_CONFIGURATION", EXIT_BLOCKED), None
        api_key = os.environ.get("ALMS_COMPAT_ANTHROPIC_API_KEY")
        base_url = os.environ.get("ALMS_COMPAT_ANTHROPIC_BASE_URL")
        if not api_key or not base_url:
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "missing live credential or base URL")
            return _fail("blocked: BLOCKED_CONFIGURATION", EXIT_BLOCKED), None
        secret_values.add(api_key)
        host = urlparse(base_url).hostname or ""
        allowed = {
            h.strip().lower()
            for h in (os.environ.get("ALMS_COMPAT_ALLOWED_HOSTS") or "").split(",")
            if h.strip()
        }
        if host.lower() not in allowed:
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "host not allowlisted")
            return _fail("blocked: BLOCKED_CONFIGURATION (host)", EXIT_BLOCKED), None
        client = build_live_client(
            api_key=api_key,
            base_url=base_url,
            timeout_ms=controls.get("timeout_ms", 30000),
        )
        wire = None

    kwargs, meta = to_messages_request(fixture, model, controls.get("max_output_tokens"))
    meta["sdk_support"] = support
    meta["retry_config"] = client_retry_config(client)
    capture = execute(client, kwargs)
    if wire is not None:
        wire_attempts = wire.attempts
        capture.attempt_count = len(wire.attempts)
        if wire.redirect_blocked:
            redirect_behavior = {
                "followed": False,
                "host_changed": True,
                "location_host": wire.redirect_location_host,
                "policy": "rejected",
            }
    else:
        capture.attempt_count = 1

    manifest = write_capture(
        capture=capture,
        out_dir=out_dir,
        request_kwargs=kwargs,
        translate_meta=meta,
        wire_attempts=wire_attempts,
        fixture_path=fixture_path,
        fixture_id=fixture.get("id", "?"),
        run_id=request["run_id"],
        endpoint_id=endpoint_id,
        boundary_kind=boundary_kind,
        model=model,
        anthropic_version=version("anthropic"),
        started_at=started_at,
        redaction_mode=request.get("redaction_mode", "strict"),
        execution_mode=execution_mode,
        secret_values=secret_values,
        redirect_behavior=redirect_behavior,
        provider_claim=provider_claim,
        gateway_claim=gateway_claim,
    )
    return EXIT_OK, manifest


def main(argv: list[str] | None = None) -> int:
    if os.environ.get(BLOCK_NETWORK_ENV) == "1":
        _install_network_tripwire()
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        return _fail("usage: python -m probe <request.json>", EXIT_INVALID)
    request_path = Path(argv[0])
    if not request_path.is_file():
        return _fail(f"request file not found: {request_path}", EXIT_INVALID)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    code, manifest = run(request)
    if manifest is not None:
        sys.stdout.write(json.dumps(manifest) + "\n")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
