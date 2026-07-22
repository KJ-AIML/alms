"""Translate fixtures to Anthropic Messages requests (native shape preserved)."""

from __future__ import annotations

from typing import Any


def to_messages_request(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
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
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
    }
    if system_parts:
        kwargs["system"] = "\n".join(system_parts)
    if "temperature" in execution:
        kwargs["temperature"] = execution["temperature"]
    if execution.get("stream"):
        kwargs["stream"] = True

    structured_mode = None
    if fixture.get("output_schema"):
        kwargs["output_config"] = {
            "format": {"type": "json_schema", "schema": fixture["output_schema"]}
        }
        structured_mode = "output_config.format"

    if fixture.get("tools") and not fixture.get("output_schema"):
        kwargs["tools"] = [
            {
                "name": t["name"],
                "description": t.get("description", ""),
                "input_schema": t.get("parameters", {}),
            }
            for t in fixture["tools"]
        ]
        choice = execution.get("tool_choice")
        if choice == "auto":
            kwargs["tool_choice"] = {"type": "auto"}
        elif choice == "forced" and fixture["tools"]:
            kwargs["tool_choice"] = {"type": "tool", "name": fixture["tools"][0]["name"]}

    meta = {
        "api_family": "anthropic_compatible",
        "structured_mode_requested": structured_mode,
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(fixture.get("tools")),
    }
    return kwargs, meta
