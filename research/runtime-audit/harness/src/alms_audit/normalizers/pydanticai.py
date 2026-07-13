"""PydanticAI Agent raw-evidence normalizer (harness side, SDK-free).

Maps the PydanticAI probe's response envelope (plain JSON, never pydantic_ai objects) into a
normalized-transcript v0 document. PydanticAI's Agent output is FRAMEWORK-owned: its messages,
parts, run-level usage aggregation, model identity, terminal state, deferred-tool requests, graph
nodes, and stream events are `framework_native` / `framework_extension`, NEVER `provider_native`
(a framework message part is not a provider-native message merely because it resembles one).
PydanticAI-specific and auxiliary shapes (graph nodes, Agent info, synthetic model profile,
deferred-tool requests, unknown fields) are preserved as `framework_extension` events — never
`provider_extension` and never discarded (DevSpec Section 48). Every event carries a raw_ref.
"""

from __future__ import annotations

from .. import provenance

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"

# PydanticAI's Agent RunUsage is a FRAMEWORK aggregation (offline the token figures are injected
# through FunctionModel; the aggregation itself is real framework code). Never provider_native.
USAGE_SOURCE = provenance.FRAMEWORK_NATIVE

# A model id read from PydanticAI's ModelResponse.model_name is FRAMEWORK-exposed: under a LIVE
# call it is framework_native, NEVER provider_native. Offline it is downgraded to fixture_expected
# by the shared result builder (the offline FunctionModel exposes a synthetic model_name).
MODEL_IDENTITY_LIVE_SOURCE = provenance.FRAMEWORK_NATIVE


def _evt(seq: int, etype: str, data: dict, raw_ref: str) -> dict:
    return {
        "sequence": seq,
        "type": etype,
        "timestamp_relative_ms": 0,
        "data": data,
        "raw_ref": raw_ref,
    }


def _summarize(usage: dict | None) -> dict | None:
    """Map PydanticAI's RunUsage aggregation to the neutral usage summary, framework_native.

    input/output map straight through; cache_read/cache_write map to the cache split; reasoning
    tokens come from `details` when present. The figure is the Agent's FRAMEWORK aggregation, not a
    provider-reported block. Missing usage stays None (never coerced to 0).
    """
    if not usage:
        return None
    input_tok = usage.get("input_tokens")
    output_tok = usage.get("output_tokens")
    total = (
        input_tok + output_tok
        if isinstance(input_tok, int) and isinstance(output_tok, int)
        else None
    )
    details = usage.get("details") or {}
    return {
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "total_tokens": total,
        "cache_read_input_tokens": usage.get("cache_read_tokens"),
        "cache_creation_input_tokens": usage.get("cache_write_tokens"),
        "reasoning_tokens": details.get("reasoning_tokens"),
        "source": USAGE_SOURCE,
    }


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """PydanticAI Agent run-level usage summary, or None when absent (absent stays absent)."""
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind in ("response", "stream"):
        return _summarize(raw_obj.get("agent_run_usage"))
    return None


def extract_model_identity(capture_kind: str, raw_obj: object) -> str | None:
    """The model id PydanticAI exposes on its ModelResponse (model_name), or None if absent.

    Framework-exposed (ModelResponse.model_name); the shared builder tags it framework_native under
    a live call, fixture_expected offline. The requested model is never copied in: absence stays
    None. Exact string preserved.
    """
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind in ("response", "stream"):
        return raw_obj.get("model_name")
    return None


def _framework_metadata(envelope: dict) -> dict:
    """PydanticAI-owned, non-provider Agent metadata worth preserving distinctly.

    Graph nodes, Agent info (output mode/object, tools, instructions), the synthetic model profile,
    tool definitions, and the deferred/graph-iteration notes are FRAMEWORK abstraction artifacts,
    not provider-native metadata. Kept as framework evidence, never dropped nor relabelled.
    """
    extra: dict = {"native_type": "pydanticai_agent"}
    for key in (
        "graph_nodes",
        "agent_info",
        "output_type",
        "synthetic_profile",
        "tools_evidence",
        "graph_iteration_note",
        "graph_iteration_requests",
    ):
        if envelope.get(key) is not None:
            extra[key] = envelope[key]
    return extra


def _append_deferred(events: list, envelope: dict, ref: str) -> None:
    deferred = envelope.get("deferred") or {}
    for approval in deferred.get("approvals") or []:
        events.append(
            _evt(len(events), "tool_call_started", {"name": approval.get("tool_name")}, ref)
        )
        events.append(
            _evt(
                len(events),
                "tool_call_completed",
                {
                    "call_id": approval.get("tool_call_id"),
                    "name": approval.get("tool_name"),
                    "arguments": approval.get("args"),
                    # A deferred/approval-required request: the tool body did NOT execute.
                    "deferred": True,
                    "requires_approval": True,
                },
                ref,
            )
        )
    events.append(
        _evt(
            len(events),
            "framework_extension",
            {
                "native_type": "pydanticai_deferred_tool_requests",
                "approvals": deferred.get("approvals"),
                "calls": deferred.get("calls"),
                "metadata": deferred.get("metadata"),
            },
            ref,
        )
    )


def normalize_response(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "pydanticai_model_response"}, ref)
    ]

    structured = envelope.get("structured")
    if structured is not None:
        events.append(
            _evt(
                len(events),
                "structured_output_completed",
                {
                    "strategy": structured.get("strategy_requested"),
                    "output_mode_observed": structured.get("output_mode_observed"),
                    "is_native": structured.get("is_native"),
                    "parsed": structured.get("parsed_output"),
                    "generated_json_schema": structured.get("generated_json_schema"),
                    "parse_error": structured.get("parse_error"),
                    "synthetic_model_profile": structured.get("synthetic_model_profile"),
                    "provider_validation": structured.get("provider_validation"),
                },
                ref,
            )
        )
    elif envelope.get("deferred") is not None:
        _append_deferred(events, envelope, ref)
    else:
        output = envelope.get("output")
        if isinstance(output, str) and output:
            events.append(_evt(len(events), "text_delta", {"text": output}, ref))

    events.append(_evt(len(events), "framework_extension", _framework_metadata(envelope), ref))

    if envelope.get("agent_run_usage") is not None:
        events.append(
            _evt(len(events), "usage_updated", {"usage": envelope["agent_run_usage"]}, ref)
        )

    events.append(
        _evt(
            len(events), "response_completed", {"finish_reason": envelope.get("finish_reason")}, ref
        )
    )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def _stream_text(event_obj: dict) -> str | None:
    """Extract a text delta from a PartStartEvent (part.content) or PartDeltaEvent (content_delta)."""
    payload = event_obj.get("event") or {}
    kind = event_obj.get("event_type")
    if kind == "PartDeltaEvent":
        delta = payload.get("delta") or {}
        text = delta.get("content_delta")
        return text if isinstance(text, str) and text else None
    if kind == "PartStartEvent":
        part = payload.get("part") or {}
        if part.get("part_kind") == "text":
            text = part.get("content")
            return text if isinstance(text, str) and text else None
    return None


def normalize_stream(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "pydanticai_model_response_stream"}, ref)
    ]
    for i, item in enumerate(envelope.get("stream_events") or []):
        text = _stream_text(item)
        if text is not None:
            events.append(_evt(len(events), "text_delta", {"text": text}, f"{ref}#{i}"))

    # Preserve the FULL framework event stream + graph nodes distinctly (framework-owned; the two
    # streaming dimensions - run_stream_events events vs agent.iter graph nodes - are kept separate).
    fw = _framework_metadata(envelope)
    fw["stream_events"] = [e.get("event_type") for e in envelope.get("stream_events") or []]
    events.append(_evt(len(events), "framework_extension", fw, ref))

    if envelope.get("agent_run_usage") is not None:
        events.append(
            _evt(len(events), "usage_updated", {"usage": envelope["agent_run_usage"]}, ref)
        )
    events.append(
        _evt(
            len(events), "response_completed", {"finish_reason": envelope.get("finish_reason")}, ref
        )
    )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(envelope: dict, raw_manifest: str, ref: str) -> dict:
    data = {
        "native_type": "framework_error",
        "exception_type": envelope.get("exception_type"),
        "exception_module": envelope.get("exception_module"),
        "cause_chain": envelope.get("cause_chain"),
        "message": envelope.get("message"),
    }
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [_evt(0, "error", data, ref)],
    }


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw PydanticAI evidence to the right normalizer branch by capture kind."""
    envelope = raw_obj if isinstance(raw_obj, dict) else {}
    if capture_kind == "stream":
        return normalize_stream(envelope, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(envelope, raw_manifest, response_ref)
    return normalize_response(envelope, raw_manifest, response_ref)
