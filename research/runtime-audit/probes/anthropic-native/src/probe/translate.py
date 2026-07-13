"""Translate a language-neutral audit fixture into an Anthropic Messages API request.

Anthropic-native, not OpenAI-shaped. Distinctions preserved deliberately:
  * the system instruction is a TOP-LEVEL `system` field, never an assistant/system message;
  * each message `content` is a native content-block list;
  * `max_tokens` is a REQUIRED Messages API parameter;
  * STRUCTURED OUTPUT and STRICT TOOL USE are COMPLEMENTARY, NOT interchangeable:
      - STR-001 uses direct Messages API JSON structured output via `output_config.format`
        (`{"format": {"type": "json_schema", "schema": <raw fixture schema>}}`), which shapes
        the model's RESPONSE. The raw JSON Schema is preserved verbatim.
      - TOOL-001 uses Anthropic tool use with `strict: true` (schema-constrained tool INPUT).
    A forced tool call is NOT used to implement STR-001.

Pure data in, pure data out; no Anthropic import here. The model is supplied at execution time.
"""

from __future__ import annotations

from typing import Any

# The Python SDK also offers `messages.parse(output_format=...)` as a convenience that parses
# the response for you. It is recorded here as an alternative, but the audit's primary path is
# `messages.create(output_config=...)` so the raw request transformation stays fully observable.
_STRUCTURED_CONVENIENCE_ALTERNATIVE = "messages.parse(output_format=...) SDK convenience path"


def to_operation(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (operation, translation-metadata).

    operation is a JSON-serializable Anthropic Messages request written verbatim as the raw
    request artifact, so the audit sees exactly what was asked of the native API — including
    the exact `output_config` schema actually sent.
    """
    execution = fixture.get("execution", {})

    system_parts: list[str] = []
    messages: list[dict] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = " ".join(
            p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
        )
        if role == "system":
            system_parts.append(text)
        else:
            messages.append({"role": role, "content": [{"type": "text", "text": text}]})

    max_tokens = max_output_tokens or execution.get("max_output_tokens") or 128

    operation: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "system": "\n".join(system_parts) if system_parts else None,
        "messages": messages,
        "stream": bool(execution.get("stream")),
        "tools": None,
        "tool_choice": None,
        "output_config": None,
        "structured_output_strategy_requested": None,
        "structured_output_format": None,
    }
    if "temperature" in execution:
        operation["temperature"] = execution["temperature"]

    output_schema = fixture.get("output_schema")
    if output_schema:
        # Native JSON structured output: the RESPONSE is shaped by output_config.format. The
        # raw fixture JSON Schema is preserved verbatim (no synthetic extraction tool, no
        # helper that could silently transform it). No tools are defined for STR-001.
        operation["output_config"] = {"format": {"type": "json_schema", "schema": output_schema}}
        operation["structured_output_strategy_requested"] = "output_config.format"
        operation["structured_output_format"] = "json_schema"
    elif fixture.get("tools"):
        # Tool use with strict schema-constrained INPUT (strict: true). This is a different
        # mechanism from structured output and is never merged with it.
        operation["tools"] = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {}),
                "strict": True,
            }
            for t in fixture["tools"]
        ]
        choice = execution.get("tool_choice")
        if choice == "auto":
            operation["tool_choice"] = {"type": "auto"}
        elif choice in ("required", "forced", "any"):
            operation["tool_choice"] = {"type": "any"}

    meta = {
        "system_mapping": "system->top_level_system" if system_parts else "none",
        "structured_mode_requested": operation["structured_output_strategy_requested"],
        "structured_convenience_alternative": _STRUCTURED_CONVENIENCE_ALTERNATIVE,
        "structured_vs_tool_note": (
            "output_config.format shapes the response (STR-001); strict tool use constrains "
            "tool input (TOOL-001) — complementary, not interchangeable"
        ),
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(operation["tools"]),
    }
    return operation, meta
