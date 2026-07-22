"""Execute Messages API through the real Anthropic SDK."""

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


@dataclass
class RawCapture:
    kind: str
    duration_ms: int
    response: dict | None = None
    events: list[dict] = field(default_factory=list)
    error: dict | None = None
    attempt_count: int = 0
    sdk_exception_class: str | None = None


def execute(client: Any, request_kwargs: dict) -> RawCapture:
    streaming = bool(request_kwargs.get("stream"))
    start = time.monotonic()
    try:
        result = client.messages.create(**request_kwargs)
    except Exception as exc:  # noqa: BLE001
        return RawCapture(
            kind="error",
            duration_ms=int((time.monotonic() - start) * 1000),
            error={
                "exception_type": type(exc).__name__,
                "status_code": getattr(exc, "status_code", None),
                "request_id": getattr(exc, "request_id", None),
                "message": str(exc),
            },
            sdk_exception_class=type(exc).__name__,
        )

    if streaming:
        events: list[dict] = []
        for i, event in enumerate(result):
            events.append(
                {
                    "sequence": i,
                    "type": getattr(event, "type", None)
                    if not isinstance(event, dict)
                    else event.get("type"),
                    "data": _dump(event),
                }
            )
        return RawCapture(
            kind="stream",
            duration_ms=int((time.monotonic() - start) * 1000),
            events=events,
        )

    return RawCapture(
        kind="response",
        duration_ms=int((time.monotonic() - start) * 1000),
        response=_dump(result),
    )
