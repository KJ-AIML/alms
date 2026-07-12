"""Probe Process Protocol v0 message builders.

PROVISIONAL — AUDIT INFRASTRUCTURE ONLY. NOT the ALMS runtime contract (DevSpec Section 23).
"""

from __future__ import annotations

PROTOCOL_VERSION = "alms.dev/probe-protocol/v0"


def build_probe_request(
    *,
    run_id: str,
    fixture_path: str,
    lane: dict,
    output_dir: str,
    timeout_ms: int,
    max_attempts: int,
    redaction_mode: str = "strict",
    stream: bool = False,
    mock_mode: bool = False,
) -> dict:
    """Assemble a probe-request conforming to spec/probe-request.schema.json."""
    controls: dict = {"timeout_ms": timeout_ms, "max_attempts": max_attempts, "stream": stream}
    if mock_mode:
        controls["mock_mode"] = True
    return {
        "protocol_version": PROTOCOL_VERSION,
        "run_id": run_id,
        "fixture_path": fixture_path,
        "lane": lane,
        "output_dir": output_dir,
        "controls": controls,
        "redaction_mode": redaction_mode,
    }
