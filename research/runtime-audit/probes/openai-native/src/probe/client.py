"""Injectable client boundary for the OpenAI Responses API.

`build_live_client` returns a real `openai.OpenAI` (used only on the live path, which is
NOT exercised in the P0.4 offline session). `MockResponsesClient` is a NARROW deterministic
fake modeling only the OpenAI response/stream shapes P0.4 needs. It is not a universal
provider framework, and it never touches the network.
"""

from __future__ import annotations

from typing import Any


def build_live_client(api_key: str, timeout_ms: int):
    """Construct a real OpenAI client. Import is local so the module loads without a key.

    max_retries=0 disables the SDK's default auto-retries (which is 2). The audit must
    observe true single-attempt behavior; hidden SDK retries would corrupt retry/attempt
    evidence and could add unplanned cost (DevSpec Sections 64 and 80).
    """
    import openai

    return openai.OpenAI(api_key=api_key, timeout=max(timeout_ms, 1) / 1000.0, max_retries=0)


class FakeOpenAIError(Exception):
    """Mimics the attributes the probe reads off a real openai.APIStatusError."""

    def __init__(
        self,
        message: str = "mock provider error",
        status_code: int = 404,
        request_id: str = "req_mock_error",
        provider_error_type: str = "NotFoundError",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_id = request_id
        self.provider_error_type = provider_error_type


def _usage() -> dict:
    return {
        "input_tokens": 8,
        "output_tokens": 3,
        "total_tokens": 11,
        "input_tokens_details": {"cached_tokens": 0},
        "output_tokens_details": {"reasoning_tokens": 0},
    }


def _nonstream(scenario: str, model: str) -> dict:
    base = {"id": "resp_mock_" + scenario, "status": "completed", "model": model, "usage": _usage()}
    if scenario == "structured":
        base["output"] = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": '{"name": "Alice", "age": 30}'}],
            }
        ]
    elif scenario == "tools":
        base["output"] = [
            {
                "type": "function_call",
                "call_id": "call_mock_1",
                "name": "get_weather",
                "arguments": '{"city": "Paris"}',
            }
        ]
    elif scenario == "refusal":
        base["output"] = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "refusal", "refusal": "I cannot help with that."}],
            }
        ]
    else:  # generation / roles / usage
        base["output"] = [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Hello there, friend."}],
            }
        ]
    return base


def _stream_events(scenario: str, model: str) -> list[dict]:
    rid = "resp_mock_stream"
    events: list[dict] = [
        {
            "type": "response.created",
            "response": {"id": rid, "status": "in_progress", "model": model},
        },
    ]
    if scenario == "stream_tools":
        events += [
            {
                "type": "response.output_item.added",
                "item": {"type": "function_call", "call_id": "call_mock_1", "name": "get_weather"},
            },
            {"type": "response.function_call_arguments.delta", "delta": '{"city":'},
            {"type": "response.function_call_arguments.delta", "delta": ' "Paris"}'},
            {"type": "response.function_call_arguments.done", "arguments": '{"city": "Paris"}'},
        ]
    else:  # stream_text / stream_unknown
        events += [
            {"type": "response.output_item.added", "item": {"type": "message"}},
            {"type": "response.output_text.delta", "delta": "one\n"},
            {"type": "response.output_text.delta", "delta": "two\n"},
            {"type": "response.output_text.done", "text": "one\ntwo\n"},
        ]
        if scenario == "stream_unknown":
            events.append(
                {"type": "response.some_future_event", "payload": {"note": "not yet understood"}}
            )
    events.append(
        {
            "type": "response.completed",
            "response": {"id": rid, "status": "completed", "model": model, "usage": _usage()},
        }
    )
    return events


class _MockResponses:
    def __init__(self, outer: MockResponsesClient) -> None:
        self._outer = outer

    def create(self, **kwargs: Any):
        return self._outer._respond(**kwargs)


class MockResponsesClient:
    """Deterministic offline fake. `scenario` forces a shape; otherwise it is inferred."""

    def __init__(self, scenario: str | None = None) -> None:
        self.scenario = scenario
        self.responses = _MockResponses(self)
        self.calls: list[dict] = []

    def _pick(self, kwargs: dict) -> str:
        if self.scenario:
            return self.scenario
        stream = bool(kwargs.get("stream"))
        tools = bool(kwargs.get("tools"))
        if stream and tools:
            return "stream_tools"
        if stream:
            return "stream_text"
        if tools:
            return "tools"
        if kwargs.get("text"):
            return "structured"
        return "generation"

    def _respond(self, **kwargs: Any):
        self.calls.append(kwargs)
        scenario = self._pick(kwargs)
        model = kwargs.get("model", "mock-model")
        if scenario == "error":
            raise FakeOpenAIError()
        if scenario.startswith("stream"):
            return iter(_stream_events(scenario, model))
        if scenario == "no_usage":
            response = _nonstream("generation", model)
            del response["usage"]  # provider omitted usage; must stay absent, never 0
            return response
        return _nonstream(scenario, model)
