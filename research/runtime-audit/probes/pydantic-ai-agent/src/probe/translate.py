"""Translate a language-neutral audit fixture into a PydanticAI Agent operation.

Pure data in, pure data out: no pydantic_ai import here, so the mapping decisions are testable
without the framework. `execute` builds the actual Agent + FunctionModel + run from this
operation. The requested model id is supplied at execution time and recorded VERBATIM as the
requested model identity (DevSpec Section 29); it is NOT the offline observed model (the offline
FunctionModel exposes its own synthetic model_name, so requested != observed offline, recorded
non-failingly per the P0.6D contract).

Instruction handling is a first-class audit subject (DevSpec Section 53): a fixture `system`
message is mapped to the Agent `instructions` channel (PydanticAI renders it as a framework
InstructionPart), a framework-owned message part that must never be relabelled provider-native.
"""

from __future__ import annotations

from typing import Any


def _text_of(message: dict) -> str:
    return " ".join(p.get("text", "") for p in message.get("parts", []) if p.get("kind") == "text")


def to_operation(
    fixture: dict, model: str, max_output_tokens: int | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (operation, translation-metadata).

    operation is a JSON-serializable description consumed by execute() and written verbatim as
    the raw request artifact, so the audit can see exactly what was asked of the PydanticAI Agent.
    """
    execution = fixture.get("execution", {})

    messages: list[dict[str, str]] = []
    instructions_parts: list[str] = []
    user_parts: list[str] = []
    for message in fixture.get("messages", []):
        role = message.get("role")
        text = _text_of(message)
        messages.append({"role": role, "content": text})
        if role == "system":
            instructions_parts.append(text)
        elif role == "user":
            user_parts.append(text)

    instructions = "\n".join(p for p in instructions_parts if p) or None
    user_prompt = "\n".join(p for p in user_parts if p)

    tools = fixture.get("tools") or None
    output_schema = fixture.get("output_schema") or None
    stream = bool(execution.get("stream"))

    # Structured output: the preferred strategy is NativeOutput (framework native structured
    # output), selected explicitly and only when an explicit synthetic model profile advertises
    # support. There is NO silent fallback to ToolOutput/PromptedOutput.
    structured_strategy = "native_output" if output_schema else None

    operation: dict[str, Any] = {
        "model": model,  # verbatim requested id; NOT the offline observed model
        "instructions": instructions,
        "user_prompt": user_prompt,
        "messages": messages,
        "tools": tools,
        "output_schema": output_schema,
        "structured_output_strategy_requested": structured_strategy,
        "stream": stream,
        "tool_choice": execution.get("tool_choice"),
    }
    if "temperature" in execution:
        operation["temperature"] = execution["temperature"]
    tokens = max_output_tokens or execution.get("max_output_tokens")
    if tokens:
        operation["max_output_tokens"] = tokens

    meta = {
        "structured_mode_requested": structured_strategy,
        # A system message becomes a framework InstructionPart (framework-owned), NOT a
        # provider-native system instruction. Recorded so instruction handling is auditable.
        "instruction_mapping": "system->agent_instructions(framework)" if instructions else "none",
        "streaming_requested": stream,
        "tools_requested": bool(tools),
        "deferred_tool_expected": bool(tools),  # tools are registered approval-required (deferred)
    }
    return operation, meta
