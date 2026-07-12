"""OpenAI raw-evidence normalizer (harness side, SDK-free).

Maps serialized OpenAI Responses raw evidence into a normalized-transcript v0 document
(spec/normalized-transcript.schema.json). Unknown native event types are preserved as
provider_extension events rather than discarded. Every emitted event carries a raw_ref.
"""

from __future__ import annotations

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"

# OpenAI native event type -> candidate audit event type.
_EVENT_MAP = {
    "response.created": "response_started",
    "response.output_text.delta": "text_delta",
    "response.function_call_arguments.delta": "tool_call_arguments_delta",
    "response.function_call_arguments.done": "tool_call_completed",
    "response.completed": "response_completed",
    "error": "error",
}


def _norm_event(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    mapped = _EVENT_MAP.get(etype)
    if mapped is None:
        # output_item.added for a function_call starts a tool call; everything else is
        # preserved as provider_extension so no native semantics are silently dropped.
        if (
            etype == "response.output_item.added"
            and (data.get("item", {}) or {}).get("type") == "function_call"
        ):
            mapped = "tool_call_started"
        else:
            mapped = "provider_extension"
    return {
        "sequence": seq,
        "type": mapped,
        "timestamp_relative_ms": 0,
        "data": {"native_type": etype, **({} if not isinstance(data, dict) else data)},
        "raw_ref": raw_ref,
    }


def normalize_stream(events: list[dict], raw_manifest: str, events_ref: str) -> dict:
    """Normalize a raw stream event list. `events` items are {sequence,type,data}."""
    out_events = []
    for i, ev in enumerate(events):
        etype = ev.get("type") or "unknown"
        out_events.append(_norm_event(i, etype, ev.get("data", {}) or {}, f"{events_ref}#{i}"))
        if etype == "response.completed" and isinstance(ev.get("data"), dict):
            usage = (ev["data"].get("response", {}) or {}).get("usage")
            if usage is not None:
                out_events.append(
                    {
                        "sequence": len(out_events),
                        "type": "usage_updated",
                        "timestamp_relative_ms": 0,
                        "data": {"usage": usage},
                        "raw_ref": f"{events_ref}#{i}",
                    }
                )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": out_events}


def normalize_response(response: dict, raw_manifest: str, response_ref: str) -> dict:
    """Normalize a raw non-stream response dict."""
    events = [
        {
            "sequence": 0,
            "type": "response_started",
            "timestamp_relative_ms": 0,
            "data": {"native_type": "response", "status": response.get("status")},
            "raw_ref": response_ref,
        }
    ]
    # structured output vs plain text vs refusal are distinguished from the output items.
    for item in response.get("output", []):
        for content in item.get("content", []) if isinstance(item, dict) else []:
            if content.get("type") == "output_text":
                events.append(
                    _evt(
                        len(events),
                        "structured_output_completed"
                        if _looks_json(content.get("text"))
                        else "text_delta",
                        {"text": content.get("text")},
                        response_ref,
                    )
                )
            elif content.get("type") == "refusal":
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {"native_type": "refusal", "refusal": content.get("refusal")},
                        response_ref,
                    )
                )
        if isinstance(item, dict) and item.get("type") == "function_call":
            events.append(
                _evt(
                    len(events),
                    "tool_call_completed",
                    {
                        "call_id": item.get("call_id"),
                        "name": item.get("name"),
                        "arguments": item.get("arguments"),
                    },
                    response_ref,
                )
            )
    if response.get("usage") is not None:
        events.append(
            _evt(len(events), "usage_updated", {"usage": response["usage"]}, response_ref)
        )
    events.append(
        _evt(len(events), "response_completed", {"status": response.get("status")}, response_ref)
    )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(error: dict, raw_manifest: str, error_ref: str) -> dict:
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [
            {
                "sequence": 0,
                "type": "error",
                "timestamp_relative_ms": 0,
                "data": {"native_type": "error", **error},
                "raw_ref": error_ref,
            }
        ],
    }


def _evt(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data,
        "raw_ref": raw_ref,
    }


def _looks_json(text: str | None) -> bool:
    return bool(text) and text.strip().startswith("{")


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """Provider-reported usage, or None when the provider did not report any (never 0)."""
    if capture_kind == "response" and isinstance(raw_obj, dict):
        return raw_obj.get("usage")
    if capture_kind == "stream" and isinstance(raw_obj, list):
        for ev in raw_obj:
            data = ev.get("data") if isinstance(ev, dict) else None
            if isinstance(ev, dict) and ev.get("type") == "response.completed":
                resp = (data or {}).get("response", {}) if isinstance(data, dict) else {}
                return resp.get("usage")
    return None


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw OpenAI evidence to the right normalizer branch by capture kind."""
    if capture_kind == "stream":
        return normalize_stream(raw_obj, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(raw_obj, raw_manifest, response_ref)
    return normalize_response(raw_obj, raw_manifest, response_ref)
