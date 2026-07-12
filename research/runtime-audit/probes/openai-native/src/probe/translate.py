"""Translate a language-neutral audit fixture into an OpenAI Responses API request.

Uses the current native surface: client.responses.create(model, input, instructions,
max_output_tokens, temperature, text, tools, tool_choice, stream). No model id is
hardcoded here; the model is supplied at execution time.
"""

from __future__ import annotations

from typing import Any


def to_responses_request(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (responses.create kwargs, translation metadata)."""
    execution = fixture.get("execution", {})
    kwargs: dict[str, Any] = {"model": model}

    instructions: list[str] = []
    input_items: list[dict] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = " ".join(
            p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
        )
        if role == "system":
            instructions.append(text)
        else:
            input_items.append({"role": role, "content": [{"type": "input_text", "text": text}]})
    if instructions:
        kwargs["instructions"] = "\n".join(instructions)
    if input_items:
        kwargs["input"] = input_items

    if "temperature" in execution:
        kwargs["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        kwargs["max_output_tokens"] = tokens
    if execution.get("stream"):
        kwargs["stream"] = True

    structured_mode = None
    if fixture.get("output_schema"):
        kwargs["text"] = {
            "format": {
                "type": "json_schema",
                "name": fixture["id"].lower().replace("-", "_"),
                "schema": fixture["output_schema"],
                "strict": True,
            }
        }
        structured_mode = "native_schema"

    if fixture.get("tools"):
        kwargs["tools"] = [
            {
                "type": "function",
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("parameters", {}),
            }
            for t in fixture["tools"]
        ]
        choice = execution.get("tool_choice")
        if choice == "forced":
            choice = "required"
        if choice in ("auto", "required", "none"):
            kwargs["tool_choice"] = choice

    meta = {
        "structured_mode_requested": structured_mode,
        "instruction_mapping": "system->instructions" if instructions else "none",
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(fixture.get("tools")),
    }
    return kwargs, meta
