"""Translate fixtures to OpenAI Chat Completions requests (custom-endpoint family)."""

from __future__ import annotations

from typing import Any


def to_chat_completions_request(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (chat.completions.create kwargs, translation metadata)."""
    execution = fixture.get("execution", {})
    messages: list[dict[str, str]] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = " ".join(
            p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text"
        )
        messages.append({"role": role, "content": text})

    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if "temperature" in execution:
        kwargs["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        kwargs["max_tokens"] = tokens
    if execution.get("stream"):
        kwargs["stream"] = True

    structured_mode = None
    if fixture.get("output_schema"):
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": fixture["id"].lower().replace("-", "_"),
                "schema": fixture["output_schema"],
                "strict": True,
            },
        }
        structured_mode = "response_format.json_schema"

    if fixture.get("tools"):
        kwargs["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                },
            }
            for t in fixture["tools"]
        ]
        choice = execution.get("tool_choice")
        if choice == "forced":
            choice = "required"
        if choice in ("auto", "required", "none"):
            kwargs["tool_choice"] = choice

    meta = {
        "api_family": "openai_compatible",
        "structured_mode_requested": structured_mode,
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(fixture.get("tools")),
    }
    return kwargs, meta
