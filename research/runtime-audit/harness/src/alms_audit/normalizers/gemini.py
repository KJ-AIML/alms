"""Gemini raw-evidence normalizer (harness side, provider-SDK-free).

Maps the Gemini probe's Interactions envelope (plain JSON, never SDK objects) into a
normalized-transcript v0 document. Interactions-native behavior that does not fit the shared
audit vocabulary is preserved as `provider_extension` events — these are provider-native
concepts (step lifecycle, thought steps/signatures, requires_action, unknown native events),
NOT framework transformations, so they are never labelled `framework_extension`. Thought
evidence is retained ONLY structurally (step presence, opaque signature); no reasoning text is
produced. The content-part / step lifecycle is retained rather than collapsed. Usage token
names may be mapped here (normalization) while the native usage object is preserved in the
usage event data. Every event carries a raw_ref.
"""

from __future__ import annotations

from .. import provenance

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"

# Gemini reports its own Interaction usage totals: provider-native.
USAGE_SOURCE = provenance.PROVIDER_NATIVE


def _evt(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data,
        "raw_ref": raw_ref,
    }


def _map_usage(native: dict | None) -> dict | None:
    """Map Gemini's native Interaction usage totals to the neutral usage summary (result-summary
    only). thought tokens are surfaced as reasoning_tokens (a documented normalization); cache
    reads map to cache_read (Gemini exposes no cache-creation split here). The native object is
    preserved verbatim in the transcript usage_updated event and the raw artifact; mapping here
    is normalization, not raw reshaping (DevSpec Section 43: normalization may map usage)."""
    if not native:
        return None
    return {
        "input_tokens": native.get("total_input_tokens"),
        "output_tokens": native.get("total_output_tokens"),
        "total_tokens": native.get("total_tokens"),
        "cache_read_input_tokens": native.get("total_cached_tokens"),
        "cache_creation_input_tokens": None,
        "reasoning_tokens": native.get("total_thought_tokens"),
        "source": USAGE_SOURCE,
    }


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return _map_usage((raw_obj.get("interaction") or {}).get("usage"))
    if capture_kind == "stream":
        native = (raw_obj.get("reconstructed") or {}).get("usage")
        if native is None:
            for item in raw_obj.get("events", []):
                ev = item.get("event", {})
                if ev.get("event_type") == "interaction.completed":
                    native = (ev.get("interaction") or {}).get("usage")
        return _map_usage(native)
    return None


def _step_events(step: dict, events: list[dict], ref: str) -> None:
    stype = step.get("type") if isinstance(step, dict) else None
    if stype == "model_output":
        for part in step.get("content", []):
            if isinstance(part, dict) and part.get("type") == "text":
                events.append(_evt(len(events), "text_delta", {"text": part.get("text")}, ref))
    elif stype == "function_call":
        events.append(_evt(len(events), "tool_call_started", {"name": step.get("name")}, ref))
        events.append(
            _evt(
                len(events),
                "tool_call_completed",
                {
                    "call_id": step.get("id"),
                    "name": step.get("name"),
                    "arguments": step.get("arguments"),
                },
                ref,
            )
        )
    elif stype == "thought":
        # Structural only: signature PRESENCE and opaque value; never reasoning text.
        events.append(
            _evt(
                len(events),
                "provider_extension",
                {
                    "native_type": "thought_step",
                    "thought_signature_present": bool(step.get("thought_signature")),
                },
                ref,
            )
        )
    else:
        events.append(
            _evt(
                len(events),
                "provider_extension",
                {"native_type": "unknown_step", "step_type": stype},
                ref,
            )
        )


def normalize_response(envelope: dict, raw_manifest: str, ref: str) -> dict:
    interaction = envelope.get("interaction") or {}
    structured = envelope.get("structured")
    status = interaction.get("status")
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "interaction", "status": status}, ref)
    ]

    if structured is not None:
        events.append(
            _evt(
                len(events),
                "structured_output_completed",
                {
                    "strategy": structured.get("strategy"),
                    "parsed": structured.get("parsed"),
                    "schema_validation": structured.get("schema_validation"),
                    "outcome": structured.get("outcome"),
                },
                ref,
            )
        )
        # Still surface non-model_output steps (e.g. thought) even in a structured response.
        for step in interaction.get("steps", []):
            if isinstance(step, dict) and step.get("type") != "model_output":
                _step_events(step, events, ref)
    else:
        for step in interaction.get("steps", []):
            _step_events(step, events, ref)

    if interaction.get("usage") is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": interaction["usage"]}, ref))

    if status == "requires_action":
        # A native non-terminal state (a function call awaits a result); no OpenAI equivalent.
        events.append(
            _evt(len(events), "provider_extension", {"native_type": "requires_action"}, ref)
        )

    events.append(_evt(len(events), "response_completed", {"status": status}, ref))
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_stream(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = []
    status = None
    for item in envelope.get("events", []):
        i = item.get("sequence")
        ev = item.get("event", {}) if isinstance(item.get("event"), dict) else {}
        etype = ev.get("event_type")
        r = f"{ref}#{i}"
        if etype == "interaction.created":
            events.append(
                _evt(len(events), "response_started", {"native_type": "interaction.created"}, r)
            )
        elif etype == "step.start":
            if ev.get("step_type") == "function_call":
                events.append(
                    _evt(len(events), "tool_call_started", {"step_type": "function_call"}, r)
                )
            else:
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {"native_type": "step_start", "step_type": ev.get("step_type")},
                        r,
                    )
                )
        elif etype == "step.delta":
            delta = ev.get("delta") or {}
            dtype = delta.get("type")
            if dtype == "text_delta":
                events.append(_evt(len(events), "text_delta", {"text": delta.get("text")}, r))
            elif dtype == "arguments_delta":
                events.append(
                    _evt(
                        len(events),
                        "tool_call_arguments_delta",
                        {"arguments": delta.get("arguments")},
                        r,
                    )
                )
            elif dtype == "thought_signature_delta":
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {
                            "native_type": "thought_signature",
                            "present": bool(delta.get("thought_signature")),
                        },
                        r,
                    )
                )
            else:
                events.append(
                    _evt(
                        len(events),
                        "provider_extension",
                        {"native_type": "step_delta", "delta_type": dtype},
                        r,
                    )
                )
        elif etype == "step.stop":
            events.append(_evt(len(events), "provider_extension", {"native_type": "step_stop"}, r))
        elif etype == "interaction.completed":
            inter = ev.get("interaction", {})
            status = inter.get("status", status)
            if inter.get("usage") is not None:
                events.append(_evt(len(events), "usage_updated", {"usage": inter["usage"]}, r))
        elif etype in ("error", "errorevent"):
            events.append(
                _evt(
                    len(events), "error", {"native_type": "errorevent", "error": ev.get("error")}, r
                )
            )
        else:
            events.append(
                _evt(len(events), "provider_extension", {"native_type": etype, "event": ev}, r)
            )
    events.append(_evt(len(events), "response_completed", {"status": status}, ref))
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(envelope: dict, raw_manifest: str, ref: str) -> dict:
    data = {
        "native_type": "provider_error",
        "exception_type": envelope.get("exception_type"),
        "cause_chain": envelope.get("cause_chain"),
        "code": envelope.get("code"),
        "status": envelope.get("status"),
        "request_id": envelope.get("request_id"),
        "message": envelope.get("message"),
    }
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [_evt(0, "error", data, ref)],
    }


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw Gemini evidence to the right normalizer branch by capture kind."""
    envelope = raw_obj if isinstance(raw_obj, dict) else {}
    if capture_kind == "stream":
        return normalize_stream(envelope, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(envelope, raw_manifest, response_ref)
    return normalize_response(envelope, raw_manifest, response_ref)
