"""LangChain raw-evidence normalizer (harness side, framework-SDK-free).

Maps the LangChain probe's response envelope (plain JSON, never framework objects) into a
normalized-transcript v0 document. Framework-specific behavior that does not fit the shared
audit vocabulary is preserved as `framework_extension` events — never as `provider_extension`
(a framework transformation is not a provider-native behavior) and never discarded
(DevSpec Section 48). Every emitted event carries a raw_ref. No LangChain type name is emitted
as an audit event type; concrete framework types stay inside event `data`.
"""

from __future__ import annotations

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"


def _evt(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data,
        "raw_ref": raw_ref,
    }


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """LangChain usage_metadata, or None when absent (absent stays absent, never 0).

    Note: this is the framework's usage_metadata shape, not the provider's raw usage block;
    the two are recorded as distinct facts and are not assumed byte-identical.
    """
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return (raw_obj.get("message") or {}).get("usage_metadata")
    if capture_kind == "stream":
        return (raw_obj.get("final_message") or {}).get("usage_metadata")
    return None


def _framework_metadata(message: dict) -> dict | None:
    """Framework-added, non-provider metadata worth preserving distinctly (not silently kept
    nor mislabelled as provider-native)."""
    extra = {}
    if message.get("additional_kwargs"):
        extra["additional_kwargs"] = message["additional_kwargs"]
    if message.get("invalid_tool_calls"):
        extra["invalid_tool_calls"] = message["invalid_tool_calls"]
    return extra or None


def normalize_response(envelope: dict, raw_manifest: str, ref: str) -> dict:
    message = envelope.get("message") or {}
    structured = envelope.get("structured")
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "ai_message"}, ref),
    ]

    if structured is not None and structured.get("parsed") is not None:
        events.append(
            _evt(
                len(events),
                "structured_output_completed",
                {
                    "strategy": structured.get("strategy"),
                    "parsed": structured.get("parsed"),
                    "parsing_error": structured.get("parsing_error"),
                },
                ref,
            )
        )
    elif isinstance(message.get("content"), str) and message["content"]:
        events.append(_evt(len(events), "text_delta", {"text": message["content"]}, ref))

    for call in message.get("tool_calls") or []:
        events.append(_evt(len(events), "tool_call_started", {"name": call.get("name")}, ref))
        events.append(
            _evt(
                len(events),
                "tool_call_completed",
                {
                    "call_id": call.get("id"),
                    "name": call.get("name"),
                    "arguments": call.get("args"),
                },
                ref,
            )
        )

    fw = _framework_metadata(message)
    if fw is not None:
        events.append(
            _evt(
                len(events),
                "framework_extension",
                {"native_type": "langchain_message_metadata", **fw},
                ref,
            )
        )

    if message.get("usage_metadata") is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": message["usage_metadata"]}, ref))

    finish = (message.get("response_metadata") or {}).get("finish_reason")
    events.append(_evt(len(events), "response_completed", {"finish_reason": finish}, ref))
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_stream(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = [_evt(0, "response_started", {"native_type": "ai_message_chunk"}, ref)]
    for item in envelope.get("chunks") or []:
        i = item.get("sequence")
        chunk = item.get("chunk") or {}
        content = chunk.get("content")
        chunk_ref = f"{ref}#{i}"
        if isinstance(content, str) and content:
            events.append(_evt(len(events), "text_delta", {"text": content}, chunk_ref))
        else:
            # A framework-synthesized chunk (e.g. an extra terminal chunk LangChain appends)
            # is preserved and labelled as a framework behavior, not dropped.
            events.append(
                _evt(
                    len(events),
                    "framework_extension",
                    {"native_type": "framework_stream_chunk", "chunk": chunk},
                    chunk_ref,
                )
            )
    usage = (envelope.get("final_message") or {}).get("usage_metadata")
    if usage is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": usage}, ref))
    finish = ((envelope.get("final_message") or {}).get("response_metadata") or {}).get(
        "finish_reason"
    )
    events.append(_evt(len(events), "response_completed", {"finish_reason": finish}, ref))
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(envelope: dict, raw_manifest: str, ref: str) -> dict:
    data = {
        "native_type": "framework_error",
        "framework_exception_type": envelope.get("framework_exception_type"),
        "cause_chain": envelope.get("cause_chain"),
        "provider_status_code": envelope.get("provider_status_code"),
        "provider_request_id": envelope.get("provider_request_id"),
        "message": envelope.get("message"),
    }
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [_evt(0, "error", data, ref)],
    }


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw LangChain evidence to the right normalizer branch by capture kind."""
    envelope = raw_obj if isinstance(raw_obj, dict) else {}
    if capture_kind == "stream":
        return normalize_stream(envelope, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(envelope, raw_manifest, response_ref)
    return normalize_response(envelope, raw_manifest, response_ref)
