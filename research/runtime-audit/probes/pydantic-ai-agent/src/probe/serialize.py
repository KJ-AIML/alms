"""Serialize raw PydanticAI evidence to disk and build a schema-valid probe-response manifest.

Conforms to spec/probe-response.schema.json. Raw artifacts are redacted before writing. The
manifest references artifacts by path and never contains secret values. The response artifact is
a small envelope the harness's PydanticAI normalizer understands; it carries PydanticAI's native
Agent messages / parts / ModelResponse / stream events / graph nodes / usage / deferred-tool
requests / terminal output, plus isolation and retry evidence, never a normalized interpretation.
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


def _retry_block(capture: RawCapture) -> dict:
    calls = capture.invocations
    return {
        "model_invocations_observed": calls,
        "retries_observed": (calls - 1) if isinstance(calls, int) else None,
        "tool_executions_observed": capture.tool_executions,
        "retry_budgets": capture.retry_budgets,
        "graph_iteration_requests": capture.graph_iteration_requests,
    }


def _response_envelope(capture: RawCapture) -> dict:
    common = {
        "scenario": capture.scenario,
        "agent_info": capture.agent_info,
        "isolation": capture.isolation,
        "retry": _retry_block(capture),
    }
    if capture.kind == "error":
        return {"capture_kind": "error", **(capture.error or {}), **common}

    body = {
        "capture_kind": capture.kind,
        "messages": capture.messages_json,
        "model_response": capture.model_response,
        "model_response_usage": capture.model_response_usage,
        "agent_run_usage": capture.agent_run_usage,
        "output": capture.output,
        "output_type": capture.output_type,
        "deferred": capture.deferred,
        "finish_reason": capture.finish_reason,
        "model_name": capture.model_name,
        "graph_nodes": capture.graph_nodes,
        "structured": capture.structured,
        "synthetic_profile": capture.synthetic_profile,
        "tools_evidence": capture.tools_evidence,
        **common,
    }
    if capture.kind == "stream":
        body["stream_events"] = capture.stream_events
        body["graph_iteration_note"] = capture.graph_iteration_note
    return body


def _package_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for dist, key in (
        ("pydantic-ai-slim", "pydantic_ai"),
        ("pydantic", "pydantic"),
        ("pydantic-graph", "pydantic_graph"),
    ):
        try:
            out[key] = version(dist)
        except Exception:  # noqa: BLE001 - a missing version is not a run failure
            out[key] = "unknown"
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
    request_path = raw / "pydanticai_request.json"
    _write_json(request_path, red_request)

    envelope = _response_envelope(capture)
    red_response, rf = redact(envelope, secret_values)
    fields_redacted.update(rf)
    fname = {"stream": "pydanticai_events.json", "error": "pydanticai_error.json"}.get(
        capture.kind, "pydanticai_response.json"
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
        # Measured from RunUsage.requests (one primary run per fixture). NOT coerced to 0 by
        # assumption: retries are zero AND exactly one model request was made per primary run.
        "retry_count_observed": capture.invocations - 1 if capture.invocations else None,
        "timeout_or_cancellation_action": None,
        "redaction_summary": {"mode": redaction_mode, "fields_redacted": sorted(fields_redacted)},
        "capture_kind": capture.kind,
        "duration_ms": capture.duration_ms,
        "execution_mode": execution_mode,
    }
    return manifest
