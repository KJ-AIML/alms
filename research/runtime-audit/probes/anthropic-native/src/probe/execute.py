"""Drive one translated operation through the Anthropic client and capture NATIVE evidence.

The probe does not reshape Anthropic semantics into OpenAI forms: the serialized Message,
content blocks, tool_use blocks, stop_reason, usage (including cache fields), and native
stream events are preserved as the SDK produced them. Interpretation into shared ALMS audit
vocabulary is the harness's job.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from .client import retry_introspection


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    duration_ms: int
    message: dict | None = None
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


def _kwargs(operation: dict) -> dict:
    kwargs: dict[str, Any] = {
        "model": operation["model"],
        "max_tokens": operation["max_tokens"],
        "messages": operation["messages"],
    }
    if operation.get("system") is not None:
        kwargs["system"] = operation["system"]
    if operation.get("tools") is not None:
        kwargs["tools"] = operation["tools"]
    if operation.get("tool_choice") is not None:
        kwargs["tool_choice"] = operation["tool_choice"]
    if operation.get("output_config") is not None:
        kwargs["output_config"] = operation["output_config"]
    if "temperature" in operation:
        kwargs["temperature"] = operation["temperature"]
    return kwargs


def _first_text(message: dict) -> str | None:
    for block in message.get("content", []):
        if isinstance(block, dict) and block.get("type") == "text":
            return block.get("text")
    return None


def _minimal_schema_check(parsed: object, schema: dict) -> bool:
    """Dependency-free structural check (required keys present on an object). This is NOT full
    JSON Schema validation — that stays a harness concern — but it is enough to distinguish a
    schema-conformant parse from a missing-field one in the audit evidence."""
    if schema.get("type") == "object" and not isinstance(parsed, dict):
        return False
    if isinstance(parsed, dict):
        return all(key in parsed for key in schema.get("required", []))
    return True


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
        "status_code": getattr(exc, "status_code", None),
        "request_id": getattr(exc, "request_id", None) or getattr(exc, "_request_id", None),
        "message": str(exc),
    }


def _structured_from_message(message: dict, operation: dict) -> dict | None:
    """Native JSON structured output (output_config.format) evidence, kept DISTINCT from the
    parsed value. The response is a text block; the probe performs the parse here so raw text
    and parsed JSON stay separately auditable, and classifies the terminal outcome so a
    refusal or a max_tokens truncation is never confused with a schema-validation failure."""
    if operation.get("structured_output_strategy_requested") is None:
        return None

    schema = ((operation.get("output_config") or {}).get("format") or {}).get("schema") or {}
    raw_text = _first_text(message)
    stop_reason = message.get("stop_reason")

    parsed = None
    parse_error = None
    if raw_text is not None:
        try:
            parsed = json.loads(raw_text)
        except (ValueError, TypeError) as exc:
            parse_error = str(exc)

    if stop_reason == "refusal":
        outcome, validation = "provider_refusal", "not_performed"
    elif stop_reason == "max_tokens":
        outcome, validation = "max_tokens_truncation", "not_performed"
    elif parse_error is not None:
        outcome, validation = "parse_failed", "not_performed"
    elif _minimal_schema_check(parsed, schema):
        outcome, validation = "schema_validation_passed", "passed"
    else:
        outcome, validation = "schema_validation_failed", "failed"

    return {
        "strategy": operation["structured_output_strategy_requested"],  # output_config.format
        "format": operation.get("structured_output_format"),  # json_schema
        "requested_schema": schema,  # raw fixture schema, preserved
        "schema_sent": schema,  # observable: exactly what was placed in output_config
        "raw_text": raw_text,  # raw response text block, distinct from the parse
        "parsed": parsed,  # parsed JSON, when parsing succeeded
        "parse_error": parse_error,
        "schema_validation": validation,  # passed | failed | not_performed
        "schema_validation_method": "minimal_structural (required-keys); full validation is a harness concern",
        "outcome": outcome,
        "stop_reason": stop_reason,
    }


def _reconstruct_stream(events: list[dict]) -> dict:
    """A minimal terminal summary derived from native events (NOT a replacement for them)."""
    text_parts: list[str] = []
    stop_reason = None
    usage = None
    for item in events:
        ev = item.get("event", {})
        etype = ev.get("type")
        if etype == "content_block_delta" and (ev.get("delta") or {}).get("type") == "text_delta":
            text_parts.append(ev["delta"].get("text", ""))
        elif etype == "message_delta":
            stop_reason = (ev.get("delta") or {}).get("stop_reason", stop_reason)
            usage = ev.get("usage", usage)
    return {"text": "".join(text_parts), "stop_reason": stop_reason, "usage": usage}


def execute(client: Any, operation: dict) -> RawCapture:
    """Run the operation through `client.messages.create`; capture native output or error."""
    kwargs = _kwargs(operation)
    start = time.monotonic()
    try:
        if operation.get("stream"):
            stream = client.messages.create(stream=True, **kwargs)
            events = [{"sequence": i, "event": _dump(ev)} for i, ev in enumerate(stream)]
            return RawCapture(
                kind="stream",
                duration_ms=_ms(start),
                events=events,
                reconstructed=_reconstruct_stream(events),
                retry=retry_introspection(client),
            )
        message = _dump(client.messages.create(**kwargs))
        return RawCapture(
            kind="response",
            duration_ms=_ms(start),
            message=message,
            structured=_structured_from_message(message, operation),
            retry=retry_introspection(client),
        )
    except Exception as exc:  # noqa: BLE001 - native error is evidence, captured not raised
        return RawCapture(
            kind="error",
            duration_ms=_ms(start),
            error=_error_evidence(exc),
            retry=retry_introspection(client),
        )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
