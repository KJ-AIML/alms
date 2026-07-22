"""Serialize Anthropic-compatible endpoint-boundary evidence."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import PROBE_ID, __version__
from .execute import RawCapture
from .redact import redact

EVIDENCE_CLASS = "custom_endpoint_compatibility"


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
    translate_meta: dict,
    wire_attempts: list[dict[str, Any]],
    fixture_path: Path,
    fixture_id: str,
    run_id: str,
    endpoint_id: str,
    boundary_kind: str,
    model: str,
    anthropic_version: str,
    started_at: str,
    redaction_mode: str,
    execution_mode: str,
    secret_values: set[str] | None = None,
    redirect_behavior: dict[str, Any] | None = None,
    provider_claim: str | None = None,
    gateway_claim: str | None = None,
) -> dict:
    raw = out_dir / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    fields_redacted: set[str] = set()

    red_request, rf = redact(request_kwargs, secret_values)
    fields_redacted.update(rf)
    request_path = raw / "anthropic_compatible_request.json"
    _write_json(request_path, red_request)

    red_wire, rf = redact(wire_attempts, secret_values)
    fields_redacted.update(rf)
    wire_path = raw / "wire_attempts.json"
    _write_json(wire_path, red_wire)

    if capture.kind == "stream":
        red_events, rf = redact(capture.events, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "anthropic_compatible_events.json"
        _write_json(response_path, red_events)
        response_body: Any = {"events": red_events}
    elif capture.kind == "error":
        red_error, rf = redact(capture.error, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "anthropic_compatible_error.json"
        _write_json(response_path, red_error)
        response_body = red_error
    else:
        red_response, rf = redact(capture.response, secret_values)
        fields_redacted.update(rf)
        response_path = raw / "anthropic_compatible_response.json"
        _write_json(response_path, red_response)
        response_body = red_response

    returned_model = None
    content_blocks = None
    stop_reason = None
    usage = None
    if isinstance(response_body, dict) and capture.kind == "response":
        returned_model = response_body.get("model") or None
        content_blocks = response_body.get("content")
        stop_reason = response_body.get("stop_reason")
        usage = response_body.get("usage") or None
    elif capture.kind == "stream" and capture.events:
        for event in capture.events:
            data = event.get("data") or {}
            if isinstance(data, dict):
                message = data.get("message") or {}
                if message.get("model"):
                    returned_model = message["model"]
                    break

    identity = {
        "endpoint_id": endpoint_id,
        "endpoint_family": "anthropic_compatible",
        "boundary_kind": boundary_kind,
        "sdk_family": "anthropic",
        "configured_provider_claim": provider_claim,
        "configured_gateway_claim": gateway_claim,
        "requested_model": model,
        "observed_returned_model": returned_model,
        "observed_returned_model_source": (
            "endpoint_boundary" if returned_model is not None else "unavailable"
        ),
        "model_identity_match": (None if returned_model is None else returned_model == model),
        "raw_model_reference": returned_model,
        "execution_mode": execution_mode,
    }

    boundary = {
        "endpoint_id": endpoint_id,
        "api_family": "anthropic_compatible",
        "boundary_kind": boundary_kind,
        "sdk_version": anthropic_version,
        "request_method": wire_attempts[0]["method"] if wire_attempts else None,
        "request_path": wire_attempts[0]["path"] if wire_attempts else None,
        "safe_request_headers": wire_attempts[0]["headers"] if wire_attempts else None,
        "request_body_shape": red_request,
        "response_body_shape": response_body
        if capture.kind != "stream"
        else {"event_count": len(capture.events)},
        "stream_event_shape": response_body if capture.kind == "stream" else None,
        "content_blocks": content_blocks,
        "stop_reason": stop_reason,
        "usage_fields": usage,
        "cache_fields": {
            k: usage.get(k)
            for k in ("cache_creation_input_tokens", "cache_read_input_tokens")
            if isinstance(usage, dict) and k in usage
        }
        if isinstance(usage, dict)
        else None,
        "requested_model": model,
        "returned_model": returned_model,
        "structured_output_request_mode": translate_meta.get("structured_mode_requested"),
        "sdk_exception_class": capture.sdk_exception_class,
        "redirect_behavior": redirect_behavior or {"followed": False, "host_changed": False},
        "attempt_count": capture.attempt_count,
        "evidence_class": EVIDENCE_CLASS,
        "disclaimer": (
            "Custom endpoint compatibility evidence is not native-provider evidence. "
            "It does not satisfy G2 or G3."
        ),
    }
    # Never convert Anthropic content blocks into OpenAI chat-completion shape.
    assert "choices" not in boundary
    boundary_path = raw / "endpoint_boundary.json"
    _write_json(boundary_path, boundary)

    manifest = {
        "spec": "alms.dev/compat-probe-response/v0",
        "run_id": run_id,
        "fixture_id": fixture_id,
        "fixture_hash": _sha256(fixture_path),
        "probe_id": PROBE_ID,
        "probe_version": __version__,
        "package_versions": {"anthropic": anthropic_version},
        "evidence_class": EVIDENCE_CLASS,
        "identity": identity,
        "started_at": started_at,
        "ended_at": _now(),
        "exit_code": 0,
        "request_path": str(request_path),
        "response_path": str(response_path),
        "wire_path": str(wire_path),
        "boundary_path": str(boundary_path),
        "retry_count_observed": max(capture.attempt_count - 1, 0) if capture.attempt_count else 0,
        "attempt_count": capture.attempt_count,
        "redaction_summary": {"mode": redaction_mode, "fields_redacted": sorted(fields_redacted)},
        "execution_mode": execution_mode,
        "disclaimer": boundary["disclaimer"],
    }
    _write_json(out_dir / "manifest.json", manifest)
    return manifest
