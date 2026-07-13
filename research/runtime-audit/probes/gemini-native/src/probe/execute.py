"""Drive one translated operation through the Gemini Interactions client and capture NATIVE
evidence. The probe does not reshape Interactions semantics into OpenAI forms: the full
Interaction resource (id, status, steps, usage, output_text) and native stream events are
preserved as returned. The authoritative evidence is the full Interaction; `output_text` is
kept separately as an SDK convenience projection. Interpretation into shared ALMS audit
vocabulary is the harness's job.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .client import retry_introspection

# CreateModelInteraction fields we forward as the request (audit-relevant subset). Extra
# audit-only keys on the operation (e.g. strategy labels) are NOT sent to the API.
_REQUEST_FIELDS = (
    "model",
    "system_instruction",
    "input",
    "stream",
    "store",
    "tools",
    "response_format",
    "generation_config",
)


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    duration_ms: int
    request: dict | None = None  # exactly what was sent to interactions.create (schema sent)
    interaction: dict | None = None
    structured: dict | None = None
    events: list[dict] = field(default_factory=list)
    reconstructed: dict | None = None
    error: dict | None = None
    retry: dict = field(default_factory=dict)


def _dump(obj: Any) -> Any:
    if isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return {k: _dump(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _request(operation: dict) -> dict:
    return {k: operation[k] for k in _REQUEST_FIELDS if operation.get(k) is not None}


def _model_output_text(interaction: dict) -> str | None:
    for step in interaction.get("steps", []):
        if isinstance(step, dict) and step.get("type") == "model_output":
            parts = [
                c.get("text", "")
                for c in step.get("content", [])
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            if parts:
                return "".join(parts)
    return None


def _minimal_schema_check(parsed: object, schema: dict) -> bool:
    if schema.get("type") == "object" and not isinstance(parsed, dict):
        return False
    if isinstance(parsed, dict):
        return all(key in parsed for key in schema.get("required", []))
    return True


def _structured(interaction: dict, operation: dict) -> dict | None:
    if operation.get("structured_output_strategy_requested") is None:
        return None
    schema = ((operation.get("response_format") or {}).get("text") or {}).get("jsonSchema") or {}
    status = interaction.get("status")
    raw_text = _model_output_text(interaction)  # from the authoritative step, not output_text

    parsed = None
    parse_error = None
    if raw_text is not None:
        try:
            parsed = json.loads(raw_text)
        except (ValueError, TypeError) as exc:
            parse_error = str(exc)

    if status != "completed":
        outcome, validation = "interaction_incomplete", "not_performed"
    elif parse_error is not None:
        outcome, validation = "parse_failed", "not_performed"
    elif _minimal_schema_check(parsed, schema):
        outcome, validation = "schema_validation_passed", "passed"
    else:
        outcome, validation = "schema_validation_failed", "failed"

    return {
        "strategy": operation[
            "structured_output_strategy_requested"
        ],  # response_format.text.json_schema
        "mime_type": ((operation.get("response_format") or {}).get("text") or {}).get("mime_type"),
        "requested_schema": schema,
        "schema_sent": schema,  # observable in the raw request artifact too
        "raw_text": raw_text,  # from the model_output step, distinct from the parse
        "parsed": parsed,
        "parse_error": parse_error,
        "schema_validation": validation,
        "schema_validation_method": "minimal_structural (required-keys); full validation is a harness concern",
        "outcome": outcome,
        "interaction_status": status,
    }


def _cause_chain(exc: BaseException) -> list[dict]:
    chain: list[dict] = []
    seen: set[int] = set()
    cur: BaseException | None = exc
    while cur is not None and id(cur) not in seen:
        seen.add(id(cur))
        chain.append({"type": type(cur).__name__, "message": str(cur)})
        cur = cur.__cause__ or cur.__context__
    return chain


def _error_evidence(exc: BaseException) -> dict:
    return {
        "exception_type": type(exc).__name__,
        "cause_chain": _cause_chain(exc),
        "code": getattr(exc, "code", None),
        "status": getattr(exc, "status", None),
        "request_id": getattr(exc, "request_id", None) or getattr(exc, "_request_id", None),
        "message": str(exc),
    }


def _reconstruct_stream(events: list[dict]) -> dict:
    text_parts: list[str] = []
    status = None
    usage = None
    for item in events:
        ev = item.get("event", {})
        etype = ev.get("event_type")
        if etype == "step.delta" and (ev.get("delta") or {}).get("type") == "text_delta":
            text_parts.append(ev["delta"].get("text", ""))
        elif etype == "interaction.completed":
            inter = ev.get("interaction", {})
            status = inter.get("status", status)
            usage = inter.get("usage", usage)
    return {"text": "".join(text_parts), "status": status, "usage": usage}


def execute(client: Any, operation: dict) -> RawCapture:
    """Run interactions.create; capture the native Interaction / event stream or a native error."""
    request = _request(operation)
    start = time.monotonic()
    try:
        if operation.get("stream"):
            stream = client.interactions.create(request=request, stream=True)
            events = [{"sequence": i, "event": _dump(ev)} for i, ev in enumerate(stream)]
            return RawCapture(
                kind="stream",
                duration_ms=_ms(start),
                request=request,
                events=events,
                reconstructed=_reconstruct_stream(events),
                retry=retry_introspection(client),
            )
        interaction = _dump(client.interactions.create(request=request))
        return RawCapture(
            kind="response",
            duration_ms=_ms(start),
            request=request,
            interaction=interaction,
            structured=_structured(interaction, operation),
            retry=retry_introspection(client),
        )
    except Exception as exc:  # noqa: BLE001 - native error is evidence, captured not raised
        return RawCapture(
            kind="error",
            duration_ms=_ms(start),
            request=request,
            error=_error_evidence(exc),
            retry=retry_introspection(client),
        )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
