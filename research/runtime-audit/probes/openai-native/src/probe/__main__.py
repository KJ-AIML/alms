"""Probe Process Protocol v0 entrypoint: `python -m probe <request.json>`.

Reads one JSON request, executes one fixture x lane operation, writes raw artifacts and a
probe-response manifest to stdout. Exit codes: 0 success (including a captured provider
error result), 2 invalid/unknown request, 3 blocked configuration/credential.

The live path is present but fail-closed and is NOT exercised in the P0.4 offline session.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from .client import MockResponsesClient, build_live_client
from .execute import execute
from .serialize import write_capture
from .translate import to_responses_request

EXIT_OK = 0
EXIT_INVALID = 2
EXIT_BLOCKED = 3

REQUIRED_KEYS = ("protocol_version", "run_id", "fixture_path", "lane", "output_dir", "controls")


def _fail(msg: str, code: int) -> int:
    sys.stderr.write(f"[probe:openai-native] {msg}\n")
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
    started_at = datetime.now(timezone.utc).isoformat()

    if mock_mode:
        model = model or "mock-model"
        client = MockResponsesClient(scenario=_scenario_for(fixture))
    else:
        # Fail-closed preflight for the live path.
        if not model:
            _write_blocked(out_dir, "BLOCKED_CONFIGURATION", "no explicit model configured")
            return _fail("blocked: BLOCKED_CONFIGURATION (no model)", EXIT_BLOCKED), None
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            _write_blocked(out_dir, "BLOCKED_CREDENTIAL", "OPENAI_API_KEY not present")
            return _fail("blocked: BLOCKED_CREDENTIAL (no credential)", EXIT_BLOCKED), None
        client = build_live_client(api_key, controls.get("timeout_ms", 30000))

    kwargs, _meta = to_responses_request(fixture, model, controls.get("max_output_tokens"))
    capture = execute(client, kwargs)
    manifest = write_capture(
        capture=capture,
        out_dir=out_dir,
        request_kwargs=kwargs,
        fixture_path=fixture_path,
        fixture_id=fixture.get("id", "?"),
        run_id=request["run_id"],
        provider=lane.get("provider", "openai"),
        model=model,
        openai_version=version("openai"),
        started_at=started_at,
        redaction_mode=request.get("redaction_mode", "strict"),
        secret_values={v for v in [os.environ.get("OPENAI_API_KEY")] if v},
    )
    return EXIT_OK, manifest


def main(argv: list[str] | None = None) -> int:
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
