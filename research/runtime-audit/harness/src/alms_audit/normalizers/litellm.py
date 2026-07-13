"""LiteLLM SDK raw-evidence normalizer (harness side, SDK-free).

Maps the LiteLLM probe's response envelope (plain JSON, never litellm objects) into a
normalized-transcript v0 document. LiteLLM presents unlike providers through an OpenAI-Chat-
Completions-SHAPED abstraction (ModelResponse / ModelResponseStream / usage / tool_calls /
exception taxonomy). That output is FRAMEWORK-owned: its usage, model id, terminal signal, and
extensions are `framework_native`, NEVER `provider_native` merely because the field names
resemble OpenAI's. LiteLLM-specific and auxiliary shapes (hidden params, routing, tool request
translation, unknown fields) are preserved as `framework_extension` events — never
`provider_extension` and never discarded (DevSpec Section 48). Every event carries a raw_ref.
"""

from __future__ import annotations

from .. import provenance

NORMALIZED_SPEC = "alms.dev/normalized-transcript/v0"

# LiteLLM's normalized usage is a FRAMEWORK figure (offline it is token-counter-synthesized; live
# it is LiteLLM's ModelResponse.usage), not the provider's own raw block. Never provider_native.
USAGE_SOURCE = provenance.FRAMEWORK_NATIVE

# A model id read from LiteLLM's ModelResponse is FRAMEWORK-mediated: under a LIVE call it is
# framework_native, NEVER provider_native (even when the string resembles an OpenAI id, and even
# though LiteLLM strips the provider prefix). Offline evidence is downgraded to fixture_expected
# by the shared result builder.
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
    """Map LiteLLM's OpenAI-shaped usage to the neutral usage summary, tagged framework_native.

    prompt/completion/total map to input/output/total; cache reads come from prompt_tokens_details
    and reasoning from completion_tokens_details (LiteLLM mirrors the OpenAI shape). The figure is
    LiteLLM-owned, so it is framework_native and must not be mistaken for a provider-reported block.
    Missing usage stays None (never 0).
    """
    if not usage:
        return None
    in_details = usage.get("prompt_tokens_details") or {}
    out_details = usage.get("completion_tokens_details") or {}
    return {
        "input_tokens": usage.get("prompt_tokens"),
        "output_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cache_read_input_tokens": in_details.get("cached_tokens"),
        "cache_creation_input_tokens": None,  # no LiteLLM equivalent; not invented
        "reasoning_tokens": out_details.get("reasoning_tokens"),
        "source": USAGE_SOURCE,
    }


def extract_usage(capture_kind: str, raw_obj: object) -> dict | None:
    """LiteLLM usage summary, or None when absent (absent stays absent, never 0)."""
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return _summarize((raw_obj.get("response") or {}).get("usage"))
    if capture_kind == "stream":
        # The include_usage terminal chunk, captured distinctly by the probe.
        return _summarize(raw_obj.get("usage_chunk"))
    return None


def extract_model_identity(capture_kind: str, raw_obj: object) -> str | None:
    """The model id LiteLLM exposes on its ModelResponse, or None if absent.

    This is a FRAMEWORK-exposed value (ModelResponse.model), not the provider's own field; the
    shared builder tags it framework_native under a live call, never provider_native. LiteLLM
    strips the provider prefix here (the full requested string survives only in _hidden_params),
    so requested != observed is expected and recorded, not corrected. The requested model is never
    copied in: absence stays None. Exact string preserved.
    """
    if not isinstance(raw_obj, dict):
        return None
    if capture_kind == "response":
        return (raw_obj.get("response") or {}).get("model")
    if capture_kind == "stream":
        agg = raw_obj.get("aggregate") or {}
        if agg.get("model"):
            return agg["model"]
        model = None
        for item in raw_obj.get("chunks") or []:
            chunk = item.get("chunk") or {}
            if chunk.get("model"):
                model = chunk["model"]  # last wins
        return model
    return None


def _framework_metadata(envelope: dict) -> dict | None:
    """LiteLLM-added, non-provider auxiliary metadata worth preserving distinctly.

    _hidden_params (api_base, litellm_model_name, response_cost, litellm_call_id, ...) and the
    request-side routing / tool-translation evidence are LiteLLM abstraction artifacts, not
    provider-native metadata. Kept as framework evidence, never silently dropped nor relabelled.
    """
    extra = {}
    if envelope.get("hidden_params"):
        extra["hidden_params"] = envelope["hidden_params"]
    if envelope.get("routing"):
        extra["routing"] = envelope["routing"]
    if envelope.get("tool_request_translation"):
        extra["tool_request_translation"] = envelope["tool_request_translation"]
    # The per-fixture execution-path classification: which offline path was actually exercised
    # (evidence accuracy - a tool fixture is request-transform + response-object-injection, NOT the
    # full completion(tools=...) path). Surfaced so the transcript records it, never inferred.
    if envelope.get("execution_path"):
        extra["execution_path"] = envelope["execution_path"]
    return extra or None


def normalize_response(envelope: dict, raw_manifest: str, ref: str) -> dict:
    response = envelope.get("response") or {}
    choice = (response.get("choices") or [{}])[0]
    message = choice.get("message") or {}
    structured = envelope.get("structured")
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "litellm_model_response"}, ref),
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
                    "provider_validation": structured.get("provider_validation"),
                },
                ref,
            )
        )
    elif isinstance(message.get("content"), str) and message["content"]:
        events.append(_evt(len(events), "text_delta", {"text": message["content"]}, ref))

    for call in message.get("tool_calls") or []:
        fn = call.get("function") or {}
        events.append(_evt(len(events), "tool_call_started", {"name": fn.get("name")}, ref))
        events.append(
            _evt(
                len(events),
                "tool_call_completed",
                {
                    "call_id": call.get("id"),
                    "name": fn.get("name"),
                    # Raw arguments string preserved distinctly (LiteLLM leaves it a JSON string);
                    # parsing is a separate concern, not done here.
                    "arguments": fn.get("arguments"),
                },
                ref,
            )
        )

    fw = _framework_metadata(envelope)
    if fw is not None:
        events.append(
            _evt(len(events), "framework_extension", {"native_type": "litellm_metadata", **fw}, ref)
        )

    if response.get("usage") is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": response["usage"]}, ref))

    events.append(
        _evt(len(events), "response_completed", {"finish_reason": choice.get("finish_reason")}, ref)
    )
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_stream(envelope: dict, raw_manifest: str, ref: str) -> dict:
    events: list[dict] = [
        _evt(0, "response_started", {"native_type": "litellm_model_response_stream"}, ref)
    ]
    finish = None
    for item in envelope.get("chunks") or []:
        i = item.get("sequence")
        chunk = item.get("chunk") or {}
        chunk_ref = f"{ref}#{i}"
        choice = (chunk.get("choices") or [{}])[0]
        delta = choice.get("delta") or {}
        if choice.get("finish_reason"):
            finish = choice["finish_reason"]
        content = delta.get("content")
        if isinstance(content, str) and content:
            events.append(_evt(len(events), "text_delta", {"text": content}, chunk_ref))
        for call in delta.get("tool_calls") or []:
            fn = call.get("function") or {}
            events.append(
                _evt(
                    len(events),
                    "tool_call_arguments_delta",
                    {"name": fn.get("name"), "arguments": fn.get("arguments")},
                    chunk_ref,
                )
            )

    fw = _framework_metadata(envelope)
    if fw is not None:
        events.append(
            _evt(len(events), "framework_extension", {"native_type": "litellm_metadata", **fw}, ref)
        )

    if envelope.get("usage_chunk") is not None:
        events.append(_evt(len(events), "usage_updated", {"usage": envelope["usage_chunk"]}, ref))
    events.append(_evt(len(events), "response_completed", {"finish_reason": finish}, ref))
    return {"spec": NORMALIZED_SPEC, "raw_manifest": raw_manifest, "events": events}


def normalize_error(envelope: dict, raw_manifest: str, ref: str) -> dict:
    data = {
        "native_type": "framework_error",
        "litellm_exception_type": envelope.get("litellm_exception_type"),
        "cause_chain": envelope.get("cause_chain"),
        "llm_provider": envelope.get("llm_provider"),
        "provider_status_code": envelope.get("provider_status_code"),
        "provider_request_id": envelope.get("provider_request_id"),
        "model": envelope.get("model"),
        "message": envelope.get("message"),
    }
    return {
        "spec": NORMALIZED_SPEC,
        "raw_manifest": raw_manifest,
        "events": [_evt(0, "error", data, ref)],
    }


def normalize(capture_kind: str, raw_obj: object, raw_manifest: str, response_ref: str) -> dict:
    """Dispatch raw LiteLLM evidence to the right normalizer branch by capture kind."""
    envelope = raw_obj if isinstance(raw_obj, dict) else {}
    if capture_kind == "stream":
        return normalize_stream(envelope, raw_manifest, response_ref)
    if capture_kind == "error":
        return normalize_error(envelope, raw_manifest, response_ref)
    return normalize_response(envelope, raw_manifest, response_ref)
