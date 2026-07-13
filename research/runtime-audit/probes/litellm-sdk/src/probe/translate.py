"""Translate a language-neutral audit fixture into a LiteLLM completion operation.

Pure data in, pure data out: no litellm import here, so the mapping decisions are testable
without the SDK. `execute` builds the actual litellm.completion(...) call from this operation.
The model id is supplied at execution time and used VERBATIM: it must be provider-qualified
(e.g. `openai/<model>`), and nothing is defaulted here (DevSpec: no hidden default model).
"""

from __future__ import annotations

from typing import Any


def _openai_tool(tool: dict) -> dict:
    """ALMS-neutral tool -> OpenAI/LiteLLM function-tool shape (what litellm.completion expects)."""
    return {
        "type": "function",
        "function": {
            "name": tool.get("name"),
            "description": tool.get("description"),
            "parameters": tool.get("parameters", {}),
        },
    }


def to_operation(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (operation, translation-metadata).

    operation is a JSON-serializable description consumed by execute() and written verbatim as
    the raw request artifact, so the audit can see exactly what was asked of litellm.completion.
    """
    execution = fixture.get("execution", {})

    messages: list[dict[str, str]] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = " ".join(
            p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
        )
        messages.append({"role": role, "content": text})

    tools = [_openai_tool(t) for t in fixture.get("tools") or []] or None
    tool_choice = execution.get("tool_choice")
    output_schema = fixture.get("output_schema") or None

    # LiteLLM accepts an OpenAI-style response_format for structured output; the SDK translates it
    # into provider params via get_optional_params (a request-side transformation exercised offline).
    # We REQUEST json_schema and record the strategy; whether a live provider would honor strict
    # json_schema vs fall back to prompting stays unverified_until_live. No silent tool fallback.
    response_format = None
    structured_strategy = None
    if output_schema:
        structured_strategy = "response_format.json_schema"
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": fixture["id"].lower().replace("-", "_"),
                "schema": output_schema,
            },
        }

    operation: dict[str, Any] = {
        "model": model,  # verbatim, provider-qualified; no default injected
        "messages": messages,
        "stream": bool(execution.get("stream")),
        "tools": tools,
        "tool_choice": tool_choice,
        "response_format": response_format,
        "structured_output_strategy_requested": structured_strategy,
    }
    if "temperature" in execution:
        operation["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        operation["max_output_tokens"] = tokens

    system_present = any(m["role"] == "system" for m in messages)
    provider_prefix = model.split("/", 1)[0] if "/" in model else None
    provider_model = model.split("/", 1)[1] if "/" in model else model
    meta = {
        "structured_mode_requested": structured_strategy,
        "instruction_mapping": "system->system_message" if system_present else "none",
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(tools),
        # Request-side routing view derived from the model STRING only. The actual routing decision
        # litellm makes is captured at execution time via get_llm_provider; the true provider
        # request/route stays unverified_until_live.
        "model_provider_prefix": provider_prefix,
        "model_provider_component": provider_model,
    }
    return operation, meta
