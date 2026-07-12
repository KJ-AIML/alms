"""Drive one translated operation through a LangChain model and capture NATIVE framework
evidence. The probe does not flatten framework semantics: the serialized AIMessage / message
chunks / tool calls / usage_metadata / response_metadata are preserved as the framework
produced them. Interpretation into ALMS audit vocabulary is the harness's job.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from .client import retry_introspection


@dataclass
class RawCapture:
    kind: str  # "response" | "stream" | "error"
    duration_ms: int
    message: dict | None = None
    structured: dict | None = None
    events: list[dict] = field(default_factory=list)
    final_message: dict | None = None
    error: dict | None = None
    retry: dict = field(default_factory=dict)


def _to_messages(operation: dict) -> list:
    out: list = []
    for m in operation.get("messages", []):
        role, text = m.get("role"), m.get("text", "")
        if role == "system":
            out.append(SystemMessage(text))
        elif role == "assistant":
            out.append(AIMessage(text))
        else:
            out.append(HumanMessage(text))
    return out


def _dump(msg: Any) -> dict:
    return msg.model_dump(mode="json") if hasattr(msg, "model_dump") else {"repr": str(msg)}


def _cause_chain(exc: BaseException) -> list[dict]:
    """Preserve the underlying cause chain rather than flattening to a single generic error."""
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
        "framework_exception_type": type(exc).__name__,
        "cause_chain": _cause_chain(exc),
        "provider_status_code": getattr(exc, "status_code", None),
        "provider_request_id": getattr(exc, "request_id", None)
        or getattr(exc, "_request_id", None),
        "message": str(exc),
    }


def execute(model: Any, operation: dict) -> RawCapture:
    """Run the operation through `model`; capture raw framework output or a framework error."""
    messages = _to_messages(operation)
    tools = operation.get("tools")
    tool_choice = operation.get("tool_choice")
    start = time.monotonic()
    try:
        if operation.get("stream"):
            runnable = model.bind_tools(tools) if tools else model
            events: list[dict] = []
            aggregate = None
            for i, chunk in enumerate(runnable.stream(messages)):
                events.append({"sequence": i, "chunk": _dump(chunk)})
                aggregate = chunk if aggregate is None else aggregate + chunk
            return RawCapture(
                kind="stream",
                duration_ms=_ms(start),
                events=events,
                final_message=_dump(aggregate) if aggregate is not None else None,
                retry=retry_introspection(model),
            )

        if operation.get("output_schema"):
            structured = model.with_structured_output(operation["output_schema"], include_raw=True)
            result = structured.invoke(messages)
            raw_msg = result.get("raw")
            err = result.get("parsing_error")
            return RawCapture(
                kind="response",
                duration_ms=_ms(start),
                message=_dump(raw_msg) if raw_msg is not None else None,
                structured={
                    "strategy": operation.get("structured_output_strategy_requested"),
                    "parsed": result.get("parsed"),
                    "parsing_error": None if err is None else str(err),
                },
                retry=retry_introspection(model),
            )

        if tools:
            bound = (
                model.bind_tools(tools, tool_choice=tool_choice)
                if tool_choice
                else (model.bind_tools(tools))
            )
            msg = bound.invoke(messages)
        else:
            msg = model.invoke(messages)
        return RawCapture(
            kind="response",
            duration_ms=_ms(start),
            message=_dump(msg),
            retry=retry_introspection(model),
        )
    except Exception as exc:  # noqa: BLE001 - framework error is evidence, captured not raised
        return RawCapture(
            kind="error",
            duration_ms=_ms(start),
            error=_error_evidence(exc),
            retry=retry_introspection(model),
        )


def _ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)
