"""Injectable client boundary for the Anthropic Messages API.

`build_client` returns a real `anthropic.Anthropic` bound to DIRECT Anthropic with all
automatic retries disabled (used only on the live path, which is NOT exercised offline).
`FakeAnthropicClient` is a NARROW deterministic fake whose `.messages.create(...)` returns
REAL Anthropic SDK objects (`Message`, `TextBlock`, `ToolUseBlock`, native `Raw*Event`
stream events) so raw evidence is genuinely Anthropic-native, never the network. It models
only the native shapes P0.6A needs and is not a universal provider framework.
"""

from __future__ import annotations

from typing import Any

from anthropic.types import (
    InputJSONDelta,
    Message,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    TextBlock,
    TextDelta,
    ToolUseBlock,
    Usage,
)
from anthropic.types.raw_message_delta_event import Delta, MessageDeltaUsage


def build_client(api_key: str, timeout_ms: int):
    """Construct a real Anthropic client against DIRECT Anthropic. Import is local so the
    module loads without a key. NO base_url is set (no OpenRouter/Bedrock/Vertex/gateway
    redirect). max_retries=0 disables the SDK's default auto-retries (2); the audit must
    observe true single-attempt behavior (DevSpec Sections 64 and 80).
    """
    import anthropic

    return anthropic.Anthropic(api_key=api_key, max_retries=0, timeout=max(timeout_ms, 1) / 1000.0)


def retry_introspection(client: Any) -> dict:
    """Record each retry owner independently; read effective config off the object, and record
    calls actually observed. Never claims zero merely because a fixture requested zero."""
    calls = getattr(client, "calls_observed", None)
    return {
        "anthropic_client_max_retries": getattr(client, "max_retries", None),
        "http_transport_retry": "owned by anthropic client (max_retries above)",
        "probe_retry": "none",
        "calls_observed": calls,
        "retries_observed": (calls - 1) if isinstance(calls, int) else None,
    }


class FakeAnthropicError(Exception):
    """Mimics the attributes the probe reads off a real anthropic.APIStatusError."""

    def __init__(
        self,
        message: str = "mock provider error",
        status_code: int = 404,
        request_id: str = "req_mock_error",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id


def _usage(cache: bool = False) -> Usage:
    if cache:
        return Usage(
            input_tokens=10,
            output_tokens=3,
            cache_creation_input_tokens=20,
            cache_read_input_tokens=5,
        )
    return Usage(input_tokens=9, output_tokens=5)


def _text(s: str) -> TextBlock:
    return TextBlock(type="text", text=s, citations=None)


def _content_and_stop(scenario: str, model: str, tool_name: str | None):
    # STR-001 native structured output returns a TEXT block carrying the JSON (output_config.
    # format shapes the RESPONSE); it is NOT a tool_use block.
    if scenario == "structured":
        return [_text('{"name": "Alice", "age": 30}')], "end_turn"
    if scenario == "structured_schema_fail":
        return [_text('{"name": "Alice"}')], "end_turn"  # valid JSON, missing required "age"
    if scenario == "structured_notjson":
        return [_text("Sorry, I can only chat in prose.")], "end_turn"  # not JSON at all
    if scenario == "structured_refusal":
        return [_text("")], "refusal"  # provider refusal, distinct from a schema failure
    if scenario == "structured_max_tokens":
        return [_text('{"name": "Ali')], "max_tokens"  # truncated, distinct from schema failure
    if scenario == "tools" and tool_name:
        return [
            ToolUseBlock(
                type="tool_use", id="toolu_tools_1", name=tool_name, input={"city": "Paris"}
            )
        ], "tool_use"
    if scenario == "multi":
        return [_text("First block."), _text("Second block.")], "end_turn"
    return [_text("Hello there, friend.")], "end_turn"


def _message(scenario: str, model: str, tool_name: str | None) -> Message:
    content, stop_reason = _content_and_stop(scenario, model, tool_name)
    return Message(
        id="msg_mock_" + scenario,
        type="message",
        role="assistant",
        model=model,
        content=content,
        stop_reason=stop_reason,
        stop_sequence=None,
        usage=_usage(cache=(scenario == "cache")),
    )


def _text_stream(model: str) -> list:
    msg = Message(
        id="msg_mock_stream",
        type="message",
        role="assistant",
        model=model,
        content=[],
        stop_reason=None,
        stop_sequence=None,
        usage=_usage(),
    )
    return [
        RawMessageStartEvent(type="message_start", message=msg),
        RawContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=TextBlock(type="text", text="", citations=None),
        ),
        RawContentBlockDeltaEvent(
            type="content_block_delta", index=0, delta=TextDelta(type="text_delta", text="one\n")
        ),
        RawContentBlockDeltaEvent(
            type="content_block_delta", index=0, delta=TextDelta(type="text_delta", text="two\n")
        ),
        RawContentBlockDeltaEvent(
            type="content_block_delta", index=0, delta=TextDelta(type="text_delta", text="three\n")
        ),
        RawContentBlockStopEvent(type="content_block_stop", index=0),
        {"type": "ping"},  # a genuine but vocabulary-less Anthropic native event
        RawMessageDeltaEvent(
            type="message_delta",
            delta=Delta(stop_reason="end_turn", stop_sequence=None),
            usage=MessageDeltaUsage(output_tokens=5),
        ),
        RawMessageStopEvent(type="message_stop"),
    ]


def _tool_stream(model: str, tool_name: str) -> list:
    msg = Message(
        id="msg_mock_toolstream",
        type="message",
        role="assistant",
        model=model,
        content=[],
        stop_reason=None,
        stop_sequence=None,
        usage=_usage(),
    )
    return [
        RawMessageStartEvent(type="message_start", message=msg),
        RawContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=ToolUseBlock(
                type="tool_use", id="toolu_stream_1", name=tool_name, input={}
            ),
        ),
        RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=InputJSONDelta(type="input_json_delta", partial_json='{"city":'),
        ),
        RawContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=InputJSONDelta(type="input_json_delta", partial_json=' "Paris"}'),
        ),
        RawContentBlockStopEvent(type="content_block_stop", index=0),
        RawMessageDeltaEvent(
            type="message_delta",
            delta=Delta(stop_reason="tool_use", stop_sequence=None),
            usage=MessageDeltaUsage(output_tokens=7),
        ),
        RawMessageStopEvent(type="message_stop"),
    ]


class _FakeMessages:
    def __init__(self, outer: FakeAnthropicClient) -> None:
        self._outer = outer

    def create(self, **kwargs: Any):
        return self._outer._respond(**kwargs)


class FakeAnthropicClient:
    """Deterministic offline fake returning REAL Anthropic SDK objects. `scenario` forces a
    shape; the model and tool name are read from the request so evidence echoes the request."""

    def __init__(self, scenario: str | None = None) -> None:
        self.scenario = scenario or "generation"
        self.messages = _FakeMessages(self)
        self.max_retries = 0
        self.calls_observed = 0

    def _tool_name(self, kwargs: dict) -> str | None:
        tools = kwargs.get("tools") or []
        return tools[0].get("name") if tools else None

    def _respond(self, **kwargs: Any):
        self.calls_observed += 1
        scenario = self.scenario
        model = kwargs.get("model", "claude-mock")
        if scenario == "error":
            raise FakeAnthropicError()
        if kwargs.get("stream"):
            if scenario in ("stream_tools",) or (scenario == "tools" and kwargs.get("stream")):
                return iter(_tool_stream(model, self._tool_name(kwargs) or "get_weather"))
            return iter(_text_stream(model))
        return _message(scenario, model, self._tool_name(kwargs))
