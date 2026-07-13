"""Serialize raw Gemini evidence to disk and build a schema-valid probe-response manifest.

Conforms to spec/probe-response.schema.json. Raw artifacts are redacted before writing. The
manifest references artifacts by path and never contains secret values. The response artifact
is an envelope the harness's Gemini normalizer understands; it carries the full native
Interaction / stream events / error plus retry introspection, never a normalized interpretation.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version
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


def _response_envelope(capture: RawCapture) -> dict:
    if capture.kind == "stream":
        return {
            "capture_kind": "stream",
            "events": capture.events,
            "reconstructed": capture.reconstructed,
            "retry": capture.retry,
        }
    if capture.kind == "error":
        return {"capture_kind": "error", **(capture.error or {}), "retry": capture.retry}
    return {
        "capture_kind": "response",
        "interaction": capture.interaction,
        "structured": capture.structured,
        "retry": capture.retry,
    }


def _package_versions() -> dict[str, str]:
    try:
        return {"google-genai": version("google-genai")}
    except Exception:  # noqa: BLE001 - a missing version is not a run failure
        return {"google-genai": "unknown"}


def write_capture(
    *,
    capture: RawCapture,
    out_dir: Path,
    operation: dict,
    fixture_path: Path,
    fixture_id: str,
    run_id: str,
    provider: str,
    model: str,
    started_at: str,
    redaction_mode: str,
    execution_mode: str = "live",
    secret_values: set[str] | None = None,
) -> dict:
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)

    fields_redacted: set[str] = set()

    # The raw request artifact records exactly what was sent to interactions.create (the
    # CreateModelInteraction payload), not the wider translated operation — so "schema actually
    # sent" is faithful and audit-only keys never leak into it.
    red_request, rf = redact(
        capture.request if capture.request is not None else operation, secret_values
    )
    fields_redacted.update(rf)
    request_path = raw / "gemini_request.json"
    _write_json(request_path, red_request)

    envelope = _response_envelope(capture)
    red_response, rf = redact(envelope, secret_values)
    fields_redacted.update(rf)
    fname = {"stream": "gemini_events.json", "error": "gemini_error.json"}.get(
        capture.kind, "gemini_response.json"
    )
    response_path = raw / fname
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
        "package_versions": _package_versions(),
        "provider": provider,
        "model": model,  # REQUESTED model; the provider-returned model lives in the Interaction
        "started_at": started_at,
        "ended_at": _now(),
        "exit_code": 0,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "request_path": str(request_path),
        "response_path": str(response_path),
        "retry_count_observed": capture.retry.get("retries_observed"),
        "timeout_or_cancellation_action": None,
        "redaction_summary": {"mode": redaction_mode, "fields_redacted": sorted(fields_redacted)},
        "capture_kind": capture.kind,
        "duration_ms": capture.duration_ms,
        "execution_mode": execution_mode,
    }
    return manifest
