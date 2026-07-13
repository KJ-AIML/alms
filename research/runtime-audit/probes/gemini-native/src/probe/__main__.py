"""Probe Process Protocol v0 entrypoint: `python -m probe <request.json>`.

Reads one JSON request, runs one fixture x lane operation through the Gemini Interactions API,
writes raw native artifacts and a probe-response manifest to stdout. Exit codes: 0 success,
2 invalid/unknown request, 3 blocked configuration/credential.

The live path is present but fail-closed and is NOT exercised in the P0.6B offline session.
Only a direct GEMINI_API_KEY satisfies the live credential gate; OPENROUTER_API_KEY,
OPENAI_API_KEY, and GOOGLE_APPLICATION_CREDENTIALS (Vertex/ADC) do NOT, and no base_url /
Vertex mode is ever configured.
"""

from __future__ import annotations

import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import FakeGeminiClient, build_client
from .execute import execute
from .serialize import write_capture
from .translate import to_operation

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BLOCKED = 3

BLOCK_NETWORK_ENV = "ALMS_PROBE_BLOCK_NETWORK"

REQUIRED_KEYS = ("protocol_version", "run_id", "fixture_path", "lane", "output_dir", "controls")


def _install_network_tripwire() -> None:
    """Hard-block outbound sockets when ALMS_PROBE_BLOCK_NETWORK=1 (offline mock runs)."""

    def _blocked(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        raise RuntimeError(
            "network blocked: ALMS_PROBE_BLOCK_NETWORK is set (offline mock run must not "
            "open a socket)"
        )

    socket.socket.connect = _blocked  # type: ignore[method-assign]
    socket.socket.connect_ex = _blocked  # type: ignore[method-assign]


def _fail(msg: str, code: int) -> int:
    sys.stderr.write(f"[probe:gemini-native] {msg}\n")
    return code


def _write_blocked(out_dir: Path, reason: str, detail: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocked.json").write_text(
        json.dumps({"status": "blocked", "reason": reason, "detail": detail}, indent=2) + "\n",
        encoding="utf-8",
    )


def gemini_api_key(env: dict | None = None) -> str | None:
    """Read ONLY the direct Gemini key for the credential gate.

    GOOGLE_API_KEY (the SDK's other auto-discovery key), OPENROUTER_API_KEY, OPENAI_API_KEY,
    GOOGLE_APPLICATION_CREDENTIALS, and Vertex env vars are intentionally NOT accepted. The
    value is only tested for presence and passed to an EXPLICIT genai.Client(api_key=...); the
    SDK's arg-less auto-discovery path (which would read GEMINI_API_KEY or GOOGLE_API_KEY) is
    never used.
    """
    return (os.environ if env is None else env).get("GEMINI_API_KEY")


def _scenario_for(fixture: dict) -> str:
    if fixture.get("feature") == "errors":
        return "error"
    if fixture.get("output_schema"):
        return "structured"
    if fixture.get("tools"):
        return "tools"
    if fixture.get("execution", {}).get("stream"):
        return "stream"
    return "generation"


def run(request: dict) -> tuple[int, dict | None]:
    missing = [k for k in REQUIRED_KEYS if k not in request]
    if missing:
        return _fail(f"invalid request: missing {missing}", EXIT_INVALID), None

    fixture_path = Path(request["fixture_path"])
    if not fixture_path.is_file():
        return _fail(f"unknown fixture: {fixture_path}", EXIT_INVALID), None
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    out_dir = Path(request["output_dir"])
    lane = request["lane"]
    controls = request["controls"]
    model = lane.get("model")
    mock_mode = bool(controls.get("mock_mode"))
    execution_mode = "offline_mock" if mock_mode else "live"
    started_at = datetime.now(timezone.utc).isoformat()

    if mock_mode:
        model = model or "gemini-mock-model"
        client = FakeGeminiClient(scenario=_scenario_for(fixture))
    else:
        # Fail-closed preflight for the live path (NOT exercised offline).
        if not model:
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "no explicit model configured")
            return _fail("blocked: BLOCKED_CONFIGURATION (no model)", EXIT_BLOCKED), None
        # Direct Gemini API key ONLY (read explicitly, never via SDK auto-discovery). A
        # GOOGLE_API_KEY / OpenRouter / OpenAI / Vertex-ADC credential must NOT satisfy this
        # gate, and no base_url / Vertex mode is ever set. The gate fails closed BEFORE any
        # client is constructed.
        api_key = gemini_api_key()
        if not api_key:
            _write_blocked(out_dir, "BLOCKED_CREDENTIAL", "GEMINI_API_KEY not present")
            return _fail("blocked: BLOCKED_CREDENTIAL (no credential)", EXIT_BLOCKED), None
        client = build_client(api_key, controls.get("timeout_ms", 30000))

    operation, _meta = to_operation(fixture, model, controls.get("max_output_tokens"))
    capture = execute(client, operation)
    manifest = write_capture(
        capture=capture,
        out_dir=out_dir,
        operation=operation,
        fixture_path=fixture_path,
        fixture_id=fixture.get("id", "?"),
        run_id=request["run_id"],
        provider=lane.get("provider", "google"),
        model=model,
        started_at=started_at,
        redaction_mode=request.get("redaction_mode", "strict"),
        execution_mode=execution_mode,
        secret_values={v for v in [os.environ.get("GEMINI_API_KEY")] if v},
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
