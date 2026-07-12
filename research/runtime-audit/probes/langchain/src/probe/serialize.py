"""Serialize raw LangChain evidence to disk and build a schema-valid probe-response manifest.

Conforms to spec/probe-response.schema.json. Raw artifacts are redacted before writing. The
manifest references artifacts by path and never contains secret values. The response artifact
is a small envelope the harness's LangChain normalizer understands; it carries the framework's
native message/chunks/error plus the retry introspection, never a normalized interpretation.
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
            "chunks": capture.events,
            "final_message": capture.final_message,
            "retry": capture.retry,
        }
    if capture.kind == "error":
        return {"capture_kind": "error", **(capture.error or {}), "retry": capture.retry}
    return {
        "capture_kind": "response",
        "message": capture.message,
        "structured": capture.structured,
        "retry": capture.retry,
    }


def _package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for pkg in ("langchain-core", "langchain-openai"):
        try:
            out[pkg] = version(pkg)
        except Exception:  # noqa: BLE001 - a missing version is not a run failure
            out[pkg] = "unknown"
    return out


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

    red_request, rf = redact(operation, secret_values)
    fields_redacted.update(rf)
    request_path = raw / "langchain_request.json"
    _write_json(request_path, red_request)

    envelope = _response_envelope(capture)
    red_response, rf = redact(envelope, secret_values)
    fields_redacted.update(rf)
    fname = {"stream": "langchain_events.json", "error": "langchain_error.json"}.get(
        capture.kind, "langchain_response.json"
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
        "model": model,
        "started_at": started_at,
        "ended_at": _now(),
        "exit_code": 0,
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
        "request_path": str(request_path),
        "response_path": str(response_path),
        # Measured from the injected fake's call count (offline) or null when unmeasurable
        # (live). NOT coerced to 0 just because a fixture requested zero retries.
        "retry_count_observed": capture.retry.get("retries_observed"),
        "timeout_or_cancellation_action": None,
        "redaction_summary": {"mode": redaction_mode, "fields_redacted": sorted(fields_redacted)},
        "capture_kind": capture.kind,
        "duration_ms": capture.duration_ms,
        "execution_mode": execution_mode,
    }
    return manifest
