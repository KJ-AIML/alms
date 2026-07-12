"""Translate a language-neutral audit fixture into a LangChain operation description.

Pure data in, pure data out: no LangChain import here, so the mapping decisions are testable
without the framework. `execute` builds the actual LangChain message/tool objects from this
operation. The model id is supplied at execution time; nothing is hardcoded here.
"""

from __future__ import annotations

from typing import Any


def to_operation(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (operation, translation-metadata).

    operation is a JSON-serializable description consumed by execute() and written verbatim
    as the raw request artifact, so the audit can see exactly what was asked of LangChain.
    """
    execution = fixture.get("execution", {})

    messages: list[dict[str, str]] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = " ".join(
            p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
        )
        messages.append({"role": role, "text": text})

    tools = fixture.get("tools") or None
    tool_choice = execution.get("tool_choice")
    output_schema = fixture.get("output_schema") or None

    # with_structured_output on an injected (non-ChatOpenAI) model uses the framework's
    # function-calling strategy by default. We REQUEST that strategy explicitly and record it;
    # what a live ChatOpenAI would actually select (e.g. native json_schema) is a distinct
    # question that stays unverified_until_live.
    structured_strategy = "function_calling" if output_schema else None

    # Framework-boundary observation: LangChain's schema->function conversion REQUIRES a
    # top-level 'title' (used as the function name); a titleless JSON schema raises. The
    # openai-native lane instead passes an explicit name alongside the schema. When the
    # fixture schema has no title we inject the fixture id and record that we did, so the
    # transformation is visible evidence rather than a silent rewrite.
    schema_title_injected = False
    if output_schema and "title" not in output_schema:
        output_schema = {"title": fixture["id"].lower().replace("-", "_"), **output_schema}
        schema_title_injected = True

    operation: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": bool(execution.get("stream")),
        "tools": tools,
        "tool_choice": tool_choice,
        "output_schema": output_schema,
        "structured_output_strategy_requested": structured_strategy,
    }
    if "temperature" in execution:
        operation["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        operation["max_output_tokens"] = tokens

    system_present = any(m["role"] == "system" for m in messages)
    meta = {
        "structured_mode_requested": structured_strategy,
        "structured_schema_title_injected": schema_title_injected,
        "instruction_mapping": "system->SystemMessage" if system_present else "none",
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(tools),
    }
    return operation, meta
