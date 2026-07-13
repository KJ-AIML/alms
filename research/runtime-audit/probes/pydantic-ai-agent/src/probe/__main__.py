"""Probe Process Protocol v0 entrypoint: `python -m probe <request.json>`.

Reads one JSON request, runs one fixture x lane operation through a PydanticAI Agent +
FunctionModel, writes raw artifacts and a probe-response manifest to stdout. Exit codes: 0
success, 2 invalid/unknown request, 3 blocked configuration/credential.

The live path is present but fail-closed and is NOT exercised in the P0.7B offline session. Only a
direct OPENAI_API_KEY satisfies the live credential gate; the Pydantic AI Gateway is never used and
no custom endpoint is configured. Offline runs set ALLOW_MODEL_REQUESTS=False and install a network
tripwire before any Agent executes, so no real provider model can be reached.
"""

from __future__ import annotations

import contextlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import configure_pydanticai_isolation
from .execute import execute
from .serialize import write_capture
from .translate import to_operation

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BLOCKED = 3

BLOCK_NETWORK_ENV = "ALMS_PROBE_BLOCK_NETWORK"

REQUIRED_KEYS = ("protocol_version", "run_id", "fixture_path", "lane", "output_dir", "controls")


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "0.0.0.0"})


def _is_loopback(address: object) -> bool:
    """True for the asyncio self-pipe / loopback sockets a local async run needs.

    PydanticAI's Agent is async; on Windows asyncio sets up an internal loopback self-pipe
    (127.0.0.1) that MUST be allowed or no async run can proceed. A real provider request targets
    an external host (e.g. api.openai.com) and is still hard-blocked, so the tripwire keeps its
    meaning: no OUTBOUND provider network is possible during an offline mock run.
    """
    host = address[0] if isinstance(address, (tuple, list)) and address else address
    if not isinstance(host, str):
        return False
    return host in _LOOPBACK_HOSTS or host.startswith("127.")


def _install_network_tripwire() -> None:
    """Block outbound (non-loopback) sockets when ALMS_PROBE_BLOCK_NETWORK=1 (offline mock runs)."""
    orig_connect = socket.socket.connect
    orig_connect_ex = socket.socket.connect_ex

    def _guard(orig):
        def wrapper(self, address, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
            if _is_loopback(address):
                return orig(self, address, *args, **kwargs)
            raise RuntimeError(
                "network blocked: ALMS_PROBE_BLOCK_NETWORK is set (offline mock run must not "
                f"open an outbound socket to {address!r})"
            )

        return wrapper

    socket.socket.connect = _guard(orig_connect)  # type: ignore[method-assign]
    socket.socket.connect_ex = _guard(orig_connect_ex)  # type: ignore[method-assign]


def _fail(msg: str, code: int) -> int:
    sys.stderr.write(f"[probe:pydantic-ai-agent] {msg}\n")
    return code


def _write_blocked(out_dir: Path, reason: str, detail: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "blocked.json").write_text(
        json.dumps({"status": "blocked", "reason": reason, "detail": detail}, indent=2) + "\n",
        encoding="utf-8",
    )


def _scenario_for(fixture: dict) -> str:
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
    scenario = _scenario_for(fixture)

    if mock_mode:
        # A non-empty requested model id is required by the schema; offline it is NOT the observed
        # model (the FunctionModel exposes its own synthetic model_name), so requested != observed
        # is recorded non-failingly. No provider is contacted.
        model = model or "openai:gpt-4o-mini"
        configure_pydanticai_isolation()  # ALLOW_MODEL_REQUESTS=False before any Agent runs
    else:
        # Fail-closed preflight for the live path (NOT exercised offline).
        if not model:
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "no explicit model configured")
            return _fail("blocked: BLOCKED_CONFIGURATION (no model)", EXIT_BLOCKED), None
        # Direct OpenAI credential ONLY. No Gateway key satisfies this gate; no endpoint is set.
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            _write_blocked(out_dir, "BLOCKED_CREDENTIAL", "OPENAI_API_KEY not present")
            return _fail("blocked: BLOCKED_CREDENTIAL (no credential)", EXIT_BLOCKED), None
        # A real live path would build a provider model here; out of P0.7B scope. Refuse.
        _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "live path not enabled in P0.7B")
        return _fail("blocked: live path not enabled in P0.7B", EXIT_BLOCKED), None

    operation, _meta = to_operation(fixture, model, controls.get("max_output_tokens"))
    capture = execute(operation, scenario)
    manifest = write_capture(
        capture=capture,
        out_dir=out_dir,
        operation=operation,
        fixture_path=fixture_path,
        fixture_id=fixture.get("id", "?"),
        run_id=request["run_id"],
        provider=lane.get("provider", "openai"),
        model=model,
        started_at=started_at,
        redaction_mode=request.get("redaction_mode", "strict"),
        execution_mode=execution_mode,
        secret_values={v for v in [os.environ.get("OPENAI_API_KEY")] if v},
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
    # Redirect ALL stdout to stderr during execution so the ONLY thing on real stdout is the
    # manifest line the harness parses (belt-and-suspenders against any framework banner/print).
    real_stdout = sys.stdout
    with contextlib.redirect_stdout(sys.stderr):
        code, manifest = run(request)
    if manifest is not None:
        real_stdout.write(json.dumps(manifest) + "\n")
        real_stdout.flush()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
