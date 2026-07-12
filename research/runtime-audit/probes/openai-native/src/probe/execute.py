"""Execute a translated request through the injected client and capture NATIVE evidence.

The probe does not flatten native semantics: raw responses and raw stream events are
preserved as-returned. Interpretation into ALMS audit vocabulary is the harness's job.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


def _dump(obj: Any) -> Any:
    if isinstance(obj, (dict, list, str, int, float, bool)) or obj is None:
        return obj
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return {k: _dump(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return str(obj)


def _event_type(event: Any) -> str | None:
    if isinstance(event, dict):
        return event.get("type")
    return getattr(event, "type", None)


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    duration_ms: int
    response: dict | None = None
    events: list[dict] = field(default_factory=list)
    error: dict | None = None


def _error_evidence(exc: Exception) -> dict:
    return {
        "exception_type": type(exc).__name__,
        "provider_error_type": getattr(exc, "provider_error_type", None),
        "status_code": getattr(exc, "status_code", None),
        "request_id": getattr(exc, "request_id", None) or getattr(exc, "_request_id", None),
        "message": str(exc),
    }


def execute(client: Any, request_kwargs: dict) -> RawCapture:
    """Run responses.create through `client`; capture raw native output or native error."""
    streaming = bool(request_kwargs.get("stream"))
    start = time.monotonic()
    try:
        result = client.responses.create(**request_kwargs)
    except Exception as exc:  # noqa: BLE001 - native error is evidence, captured not raised
        return RawCapture(kind="error", duration_ms=_ms(start), error=_error_evidence(exc))

    if streaming:
        events: list[dict] = []
        for i, event in enumerate(result):
            events.append({"sequence": i, "type": _event_type(event), "data": _dump(event)})
        return RawCapture(kind="stream", duration_ms=_ms(start), events=events)

    return RawCapture(kind="response", duration_ms=_ms(start), response=_dump(result))


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
