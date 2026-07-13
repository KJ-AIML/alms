"""Drive one translated operation through litellm.completion and capture NATIVE LiteLLM
evidence. The probe does not flatten LiteLLM semantics: the serialized ModelResponse /
ModelResponseStream chunks / tool calls / usage / _hidden_params are preserved as LiteLLM
produced them. Interpretation into ALMS audit vocabulary is the harness's job.

Every automatic retry/fallback owner is off (client.configure_litellm_isolation + per-call
num_retries=0). A structured or streaming failure never triggers a second call.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import litellm

from .client import isolation_introspection, observe_routing


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    duration_ms: int
    response: dict | None = None
    hidden_params: dict | None = None
    routing: dict = field(default_factory=dict)
    structured: dict | None = None
    tool_request_translation: dict | None = None
    chunks: list[dict] = field(default_factory=list)
    aggregate: dict | None = None
    usage_chunk: dict | None = None
    error: dict | None = None
    isolation: dict = field(default_factory=dict)
    calls_observed: int = 0


def _dump(obj: Any) -> dict:
    return obj.model_dump() if hasattr(obj, "model_dump") else {"repr": str(obj)}


def _hidden(obj: Any) -> dict | None:
    hp = getattr(obj, "_hidden_params", None)
    if hp is None:
        return None
    try:
        return json.loads(json.dumps(dict(hp), default=str))
    except Exception:  # noqa: BLE001 - hidden params are best-effort evidence
        return {"repr": str(hp)}


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
        "litellm_exception_type": type(exc).__name__,
        "litellm_exception_module": type(exc).__module__,
        "cause_chain": _cause_chain(exc),
        "llm_provider": getattr(exc, "llm_provider", None),
        "provider_status_code": getattr(exc, "status_code", None),
        "provider_request_id": getattr(exc, "request_id", None)
        or getattr(exc, "_request_id", None),
        "model": getattr(exc, "model", None),
        "message": str(exc),
    }


def _tool_request_translation(operation: dict, routing: dict) -> dict:
    """Exercise LiteLLM's request-side tool translation (get_optional_params) as evidence.

    Passing `tools` directly to litellm.completion in this SDK version routes through LiteLLM's
    proxy MCP utilities (which import fastapi, a proxy-server dependency out of this SDK lane's
    scope), so the tools are NOT sent through completion here. The pure SDK request translation is
    still exercised via get_optional_params; the tool-call RESPONSE is injected via LiteLLM's own
    ModelResponse types. Provider -> LiteLLM tool translation stays unverified_until_live.
    """
    provider = routing.get("resolved_provider")
    model_component = routing.get("resolved_model_component") or operation["model"]
    try:
        from litellm.utils import get_optional_params

        params = get_optional_params(
            model=model_component,
            custom_llm_provider=provider,
            tools=operation.get("tools"),
            tool_choice=operation.get("tool_choice"),
        )
        return {
            "exercised": True,
            "mechanism": "litellm.utils.get_optional_params",
            "translated_param_keys": sorted(params.keys()),
            "tools_in_provider_params": "tools" in params,
            "tool_choice_in_provider_params": "tool_choice" in params,
            "note": (
                "SDK request-side tool translation. Passing tools directly to litellm.completion "
                "in this version routes through proxy MCP utilities (fastapi), out of SDK scope; "
                "the tool-call response was injected via litellm ModelResponse types."
            ),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - a translation failure is recorded evidence
        return {"exercised": False, "error": f"{type(exc).__name__}: {exc}"}


def _completion_kwargs(operation: dict, mock_response: Any) -> dict:
    kwargs: dict[str, Any] = {
        "model": operation["model"],
        "messages": operation["messages"],
        "num_retries": 0,  # per-call belt-and-suspenders; no retry loop
    }
    # NOTE: `tools` is deliberately NOT forwarded to completion (see _tool_request_translation).
    if operation.get("response_format"):
        kwargs["response_format"] = operation["response_format"]
    if "temperature" in operation:
        kwargs["temperature"] = operation["temperature"]
    if operation.get("max_output_tokens"):
        kwargs["max_tokens"] = operation["max_output_tokens"]
    if mock_response is not None:
        kwargs["mock_response"] = mock_response
    return kwargs


def _parse_structured(operation: dict, content: str | None) -> dict:
    """Local JSON parse + local schema-presence check, kept distinct from the raw text.

    Valid JSON alone is NOT treated as native structured-output proof (offline, provider
    validation is unverified_until_live). Parse failure and schema failure stay distinct, and
    there is NO fallback to tool calling.
    """
    strategy = operation.get("structured_output_strategy_requested")
    parsed = None
    parsing_error = None
    if content is None:
        parsing_error = "no content"
    else:
        try:
            parsed = json.loads(content)
        except (json.JSONDecodeError, TypeError) as exc:
            parsing_error = f"json_parse_error: {exc}"
    schema = (operation.get("response_format") or {}).get("json_schema", {}).get("schema")
    required = (schema or {}).get("required", [])
    schema_valid = None
    if parsed is not None and isinstance(parsed, dict):
        schema_valid = all(k in parsed for k in required)
    return {
        "strategy": strategy,
        "parsed": parsed,
        "parsing_error": parsing_error,
        "local_schema_required_fields_present": schema_valid,
        "provider_validation": "unverified_until_live",
    }


def execute(operation: dict, mock_response: Any) -> RawCapture:
    """Run the operation through litellm.completion; capture raw output or a litellm exception.

    mock_response is required for the offline path (live is gated in __main__ and out of P0.7A
    scope). A single call is made; retries/fallbacks are disabled so no second call can occur.
    """
    routing = observe_routing(operation["model"])
    isolation = isolation_introspection()
    tool_translation = (
        _tool_request_translation(operation, routing) if operation.get("tools") else None
    )
    kwargs = _completion_kwargs(operation, mock_response)
    start = time.monotonic()
    try:
        if operation.get("stream"):
            kwargs["stream"] = True
            kwargs["stream_options"] = {"include_usage": True}
            stream = litellm.completion(**kwargs)
            chunks: list[dict] = []
            raw_chunks = []
            usage_chunk = None
            for i, chunk in enumerate(stream):
                d = _dump(chunk)
                chunks.append({"sequence": i, "chunk": d})
                raw_chunks.append(chunk)
                if d.get("usage"):
                    usage_chunk = d["usage"]
            aggregate = None
            try:
                rebuilt = litellm.stream_chunk_builder(raw_chunks, messages=operation["messages"])
                aggregate = _dump(rebuilt) if rebuilt is not None else None
            except Exception:  # noqa: BLE001 - reconstruction is best-effort, never fatal
                aggregate = None
            return RawCapture(
                kind="stream",
                duration_ms=_ms(start),
                chunks=chunks,
                aggregate=aggregate,
                usage_chunk=usage_chunk,
                tool_request_translation=tool_translation,
                routing=routing,
                isolation=isolation,
                calls_observed=1,
            )

        response = litellm.completion(**kwargs)
        dumped = _dump(response)
        structured = None
        if operation.get("response_format"):
            content = None
            choices = dumped.get("choices") or []
            if choices:
                content = (choices[0].get("message") or {}).get("content")
            structured = _parse_structured(operation, content)
        return RawCapture(
            kind="response",
            duration_ms=_ms(start),
            response=dumped,
            hidden_params=_hidden(response),
            structured=structured,
            tool_request_translation=tool_translation,
            routing=routing,
            isolation=isolation,
            calls_observed=1,
        )
    except Exception as exc:  # noqa: BLE001 - a litellm error is evidence, captured not raised
        return RawCapture(
            kind="error",
            duration_ms=_ms(start),
            error=_error_evidence(exc),
            tool_request_translation=tool_translation,
            routing=routing,
            isolation=isolation,
            calls_observed=1,
        )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
