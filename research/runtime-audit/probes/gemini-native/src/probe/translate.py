"""Translate a language-neutral audit fixture into a Gemini Interactions API request.

Gemini Interactions-native, not OpenAI-shaped. Distinctions preserved deliberately:
  * the system instruction is a TOP-LEVEL `system_instruction`, never a user-input message;
  * input is a list of chronological STEPS (a `user_input` step with ordered content parts);
  * `store` is ALWAYS false (no server-side retention) and `previous_interaction_id` is never
    set (each base fixture is stateless single-turn);
  * structured output uses the native `response_format` (text / application/json / jsonSchema),
    NOT a synthetic function tool;
  * function calling uses a native Interactions function tool.

Pure data in, pure data out; no google-genai import here. The model is supplied at execution
time (no hidden default). The shapes use the SDK's real field names; the Interactions API is GA,
but its generated Python types may evolve on SDK upgrade, so the exact typed wire objects are
unverified_until_live.
"""

from __future__ import annotations

from typing import Any

# Recorded but NOT the primary path: models.generate_content (the classic surface) and the SDK
# response.text convenience projection. The audit's authoritative evidence is the full
# Interaction resource returned by interactions.create.
_ALTERNATIVE_SURFACE = "models.generate_content (classic; NOT used as the P0.6B audit surface)"


def to_operation(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (operation, translation-metadata).

    operation is a JSON-serializable CreateModelInteraction request written verbatim as the raw
    request artifact, so the audit sees exactly what was asked of the native API — including
    `store=false` and the exact `response_format` schema sent.
    """
    execution = fixture.get("execution", {})

    system_parts: list[str] = []
    input_steps: list[dict] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        parts = [
            {"type": "text", "text": p.get("text", "")}
            for p in message.get("parts", [])
            if p.get("kind") == "text"
        ]
        if role == "system":
            system_parts.extend(p["text"] for p in parts)
        else:
            input_steps.append({"type": "user_input", "content": parts})

    operation: dict[str, Any] = {
        "model": model,
        "system_instruction": "\n".join(system_parts) if system_parts else None,
        "input": input_steps,
        "stream": bool(execution.get("stream")),
        "store": False,  # ALWAYS false: no server-side retention in P0.6B
        "tools": None,
        "response_format": None,
        # previous_interaction_id is deliberately never set (stateless single-turn).
    }
    gen_config: dict[str, Any] = {}
    if "temperature" in execution:
        gen_config["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        gen_config["max_output_tokens"] = tokens
    if gen_config:
        operation["generation_config"] = gen_config

    output_schema = fixture.get("output_schema")
    if output_schema:
        # Native structured output via response_format (NOT a synthetic extraction tool). The
        # raw fixture JSON Schema is preserved verbatim under the SDK's `jsonSchema` field.
        operation["response_format"] = {
            "text": {"mime_type": "application/json", "jsonSchema": output_schema}
        }
        operation["structured_output_strategy_requested"] = "response_format.text.json_schema"
    elif fixture.get("tools"):
        operation["tools"] = [
            {
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("parameters", {}),
                }
            }
            for t in fixture["tools"]
        ]

    meta = {
        "system_mapping": "system->top_level_system_instruction" if system_parts else "none",
        "structured_mode_requested": operation.get("structured_output_strategy_requested"),
        "store": False,
        "previous_interaction_id_used": False,
        "alternative_surface_recorded": _ALTERNATIVE_SURFACE,
        "streaming_requested": bool(execution.get("stream")),
        "tools_requested": bool(operation["tools"]),
    }
    return operation, meta
