"""Serialize raw evidence to disk and build a schema-valid probe-response manifest.

Conforms to spec/probe-response.schema.json. Raw artifacts are redacted before writing.
The manifest references artifacts by path and never contains secret values.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from . import PROBE_ID, __version__
from .execute import RawCapture
from .redact import redact

PROBE_RESPONSE_SPEC = "alms.dev/probe-response/v0"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_capture(
    *,
    capture: RawCapture,
    out_dir: Path,
    request_kwargs: dict,
    fixture_path: Path,
    fixture_id: str,
    run_id: str,
    provider: str,
    model: str,
    openai_version: str,
    started_at: str,
    redaction_mode: str,
    execution_mode: str = "live",
    secret_values: set[str] | None = None,
) -> dict:
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    fields_redacted: set[str] = set()

    red_request, rf = redact(request_kwargs, secret_values)
    fields_redacted.update(rf)
    request_path = raw / "openai_request.json"
    _write_json(request_path, red_request)

    if capture.kind == "stream":
        red_events, rf = redact(capture.events, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "openai_events.json"
        _write_json(response_path, red_events)
    elif capture.kind == "error":
        red_error, rf = redact(capture.error, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "openai_error.json"
        _write_json(response_path, red_error)
    else:
        red_response, rf = redact(capture.response, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "openai_response.json"
        _write_json(response_path, red_response)

    stdout_path = raw / "probe.stdout.txt"
    stderr_path = raw / "probe.stderr.txt"
    stdout_path.write_text(f"probe {PROBE_ID} kind={capture.kind}\n", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")

    manifest = {
        "spec": PROBE_RESPONSE_SPEC,
        "run_id": run_id,
        "fixture_id": fixture_id,
        "fixture_hash": _sha256(fixture_path),
        "probe_id": PROBE_ID,
        "probe_version": __version__,
        "package_versions": {"openai": openai_version},
        "provider": provider,
        "model": model,
        "started_at": started_at,
        "ended_at": _now(),
        "exit_code": 0,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "request_path": str(request_path),
        "response_path": str(response_path),
        "retry_count_observed": None,
        "timeout_or_cancellation_action": None,
        "redaction_summary": {"mode": redaction_mode, "fields_redacted": sorted(fields_redacted)},
        "capture_kind": capture.kind,
        "duration_ms": capture.duration_ms,
        "execution_mode": execution_mode,
    }
    return manifest
