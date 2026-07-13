"""Anthropic raw-evidence normalizer (harness side, provider-SDK-free).

Maps the Anthropic probe's response envelope (plain JSON, never SDK objects) into a
normalized-transcript v0 document. Anthropic-native semantics that do not fit the shared
audit vocabulary are preserved as `provider_extension` events — these are provider-native
behaviors (content-block lifecycle, ping, refusal), NOT framework transformations, so they
are never labelled `framework_extension`. The content-block lifecycle is retained rather than
collapsed. Cache usage is kept distinguishable inside the usage event data. Every event
carries a raw_ref.
"""

from __future__ import annotations

from .. import provenance

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"

# Anthropic reports its own usage block (incl. the cache split): provider-native.
USAGE_SOURCE = provenance.PROVIDER_NATIVE

# The served-model id is read from the native Message resource: provider-native under a LIVE
# call. Offline evidence is downgraded to fixture_expected by the shared result builder.
MODEL_IDENTITY_LIVE_SOURCE = provenance.PROVIDER_NATIVE


def _evt(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data,
        "raw_ref": raw_ref,
    }


def _summarize(usage: dict | None) -> dict | None:
    """Map Anthropic's native usage to the neutral usage summary (result-summary only).

    Anthropic reports a two-field cache split (creation vs read) and no total or reasoning
    tokens. The split is preserved under the shared cache_read/cache_creation names instead of
    being collapsed into a single OpenAI-shaped cached figure; absent fields stay null (not 0).
    The native object is preserved verbatim in the transcript usage_updated event.
    """
    if not usage:
        return None
    return {
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "total_tokens": usage.get("total_tokens"),  # Anthropic does not report a total: stays null
        "cache_read_input_tokens": usage.get("cache_read_input_tokens"),
        "cache_creation_input_tokens": usage.get("cache_creation_input_tokens"),
        "reasoning_tokens": None,  # not reported in the Anthropic usage block
        "source": USAGE_SOURCE,
    }


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """Provider-reported usage summary, or None if absent (absent stays absent, never 0)."""
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return _summarize((raw_obj.get("message") or {}).get("usage"))
    if capture_kind == "stream":
        # Anthropic splits usage across events: input on message_start, output on message_delta.
        merged: dict = {}
        for item in raw_obj.get("events", []):
            ev = item.get("event", {})
            if ev.get("type") == "message_start":
                u = ((ev.get("message") or {}).get("usage")) or {}
                merged.update({k: v for k, v in u.items() if v is not None})
            elif ev.get("type") == "message_delta":
                u = ev.get("usage") or {}
                merged.update({k: v for k, v in u.items() if v is not None})
        return _summarize(merged or None)
    return None


def extract_model_identity(capture_kind: str, raw_obj: object) -> str | None:
    """The served model id from the native Message, or None if absent.

    Read from the native Message `model` field, not substituted from the requested model when the
    field is missing. Exact string preserved; absence stays absence.
    """
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return (raw_obj.get("message") or {}).get("model")
    if capture_kind == "stream":
        for item in raw_obj.get("events", []):
            ev = item.get("event", {}) if isinstance(item, dict) else {}
            if ev.get("type") == "message_start":
                model = (ev.get("message") or {}).get("model")
                if model:
                    return model
    return None


def normalize_response(envelope: dict, raw_manifest: str, ref: str) -> dict:
    message = envelope.get("message") or {}
    structured = envelope.get("structured")
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "message", "role": message.get("role")}, ref)
    ]

    if structured is not None:
        # Native JSON structured output (output_config.format). The carrier text block is the
        # structured payload, so it is represented as a structured-output event, not text_delta.
        # The parsed value is kept distinct from the raw text and the validation outcome.
        events.append(
            _evt(
                len(events),
                "structured_output_completed",
                {
                    "strategy": structured.get("strategy"),
                    "format": structured.get("format"),
                    "parsed": structured.get("parsed"),
                    "schema_validation": structured.get("schema_validation"),
                    "outcome": structured.get("outcome"),
                },
                ref,
            )
        )

    for block in [] if structured is not None else message.get("content", []):
        btype = block.get("type") if isinstance(block, dict) else None
        if btype == "text":
            events.append(_evt(len(events), "text_delta", {"text": block.get("text")}, ref))
        elif btype == "tool_use":
            events.append(_evt(len(events), "tool_call_started", {"name": block.get("name")}, ref))
            events.append(
                _evt(
                    len(events),
                    "tool_call_completed",
                    {
                        "call_id": block.get("id"),
                        "name": block.get("name"),
                        "arguments": block.get("input"),
                    },
                    ref,
                )
            )
        else:
            # An unknown native content block is preserved, not discarded.
            events.append(
                _evt(len(events), "provider_extension", {"native_type": btype, "block": block}, ref)
            )

    stop_reason = message.get("stop_reason")
    if stop_reason == "refusal":
        events.append(
            _evt(
                len(events),
                "provider_extension",
                {"native_type": "refusal", "stop_reason": stop_reason},
                ref,
            )
        )

    if message.get("usage") is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": message["usage"]}, ref))

    events.append(
        _evt(
            len(events),
            "response_completed",
            {"stop_reason": stop_reason, "stop_sequence": message.get("stop_sequence")},
            ref,
        )
    )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_stream(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = []
    stop_reason = None
    for item in envelope.get("events", []):
        i = item.get("sequence")
        ev = item.get("event", {}) if isinstance(item.get("event"), dict) else {}
        etype = ev.get("type")
        r = f"{ref}#{i}"
        if etype == "message_start":
            events.append(
                _evt(len(events), "response_started", {"native_type": "message_start"}, r)
            )
        elif etype == "content_block_start":
            block = ev.get("content_block") or {}
            if block.get("type") == "tool_use":
                events.append(
                    _evt(len(events), "tool_call_started", {"name": block.get("name")}, r)
                )
            else:
                # Native block lifecycle has no shared-vocab equivalent; retain it.
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {"native_type": "content_block_start", "block_type": block.get("type")},
                        r,
                    )
                )
        elif etype == "content_block_delta":
            delta = ev.get("delta") or {}
            if delta.get("type") == "text_delta":
                events.append(_evt(len(events), "text_delta", {"text": delta.get("text")}, r))
            elif delta.get("type") == "input_json_delta":
                events.append(
                    _evt(
                        len(events),
                        "tool_call_arguments_delta",
                        {"partial_json": delta.get("partial_json")},
                        r,
                    )
                )
            else:
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {"native_type": "content_block_delta", "delta": delta},
                        r,
                    )
                )
        elif etype == "content_block_stop":
            events.append(
                _evt(len(events), "provider_extension", {"native_type": "content_block_stop"}, r)
            )
        elif etype == "message_delta":
            stop_reason = (ev.get("delta") or {}).get("stop_reason", stop_reason)
            if ev.get("usage") is not None:
                events.append(_evt(len(events), "usage_updated", {"usage": ev["usage"]}, r))
        elif etype == "message_stop":
            events.append(_evt(len(events), "response_completed", {"stop_reason": stop_reason}, r))
        else:
            # ping and any other vocabulary-less native event stay available as provider extensions.
            events.append(
                _evt(len(events), "provider_extension", {"native_type": etype, "event": ev}, r)
            )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(envelope: dict, raw_manifest: str, ref: str) -> dict:
    data = {
        "native_type": "provider_error",
        "exception_type": envelope.get("exception_type"),
        "cause_chain": envelope.get("cause_chain"),
        "status_code": envelope.get("status_code"),
        "request_id": envelope.get("request_id"),
        "message": envelope.get("message"),
    }
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [_evt(0, "error", data, ref)],
    }


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw Anthropic evidence to the right normalizer branch by capture kind."""
    envelope = raw_obj if isinstance(raw_obj, dict) else {}
    if capture_kind == "stream":
        return normalize_stream(envelope, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(envelope, raw_manifest, response_ref)
    return normalize_response(envelope, raw_manifest, response_ref)
