"""Injectable client boundary for the Gemini Interactions API.

`build_client` returns a real `google.genai.Client` bound to DIRECT Gemini (not Vertex) with
all automatic retries disabled (used only on the live path, which is NOT exercised offline).
`FakeGeminiClient.interactions.create(...)` returns NATIVE Interaction / stream-event
dictionaries modelled on the SDK's real field names. The Interactions API is GA; the SDK's
generated Python types/resources (re-exported from internal `_gaos`) may evolve on upgrade, so
validated native dicts are used offline per the P0.6B brief. It models only the shapes P0.6B
needs and is not a universal provider framework, and never touches the network.
"""

from __future__ import annotations

from typing import Any

_CREATED = 1_700_000_000  # fixed timestamp (no wall-clock in offline evidence)


def build_client(api_key: str, timeout_ms: int):
    """Construct a real direct-Gemini client with retries disabled. Import is local so the
    module loads without a key. NOT Vertex (vertexai defaults off), NO base_url override (no
    OpenRouter/gateway/compat redirect). retry_options.attempts=1 means a single attempt / zero
    retries; the audit must observe true single-attempt behavior (DevSpec Sections 64 and 80).
    """
    from google import genai
    from google.genai import types as gt

    return genai.Client(
        api_key=api_key,
        http_options=gt.HttpOptions(
            timeout=max(timeout_ms, 1),
            retry_options=gt.HttpRetryOptions(attempts=1),
        ),
    )


def retry_introspection(client: Any) -> dict:
    """Record each retry owner independently; read effective config where available."""
    calls = getattr(client, "calls_observed", None)
    attempts = None
    try:
        attempts = client._api_client._http_options.retry_options.attempts  # live client
    except Exception:  # noqa: BLE001 - the offline fake has no _api_client
        attempts = getattr(client, "retry_attempts", None)
    return {
        "genai_client_retry_attempts": attempts,  # 1 attempt == 0 retries
        "http_transport_retry": "owned by google-genai HttpOptions.retry_options",
        "probe_retry": "none",
        "calls_observed": calls,
        "retries_observed": (calls - 1) if isinstance(calls, int) else None,
    }


class FakeGeminiError(Exception):
    """Mimics the attributes the probe reads off a real google.genai APIError."""

    def __init__(self, message: str = "mock provider error", code: int = 404) -> None:
        super().__init__(message)
        self.code = code
        self.status = "NOT_FOUND"


def _usage(cache: bool = False, thought: int = 0) -> dict:
    return {
        "total_input_tokens": 9,
        "total_output_tokens": 5,
        "total_tokens": 14,
        "total_thought_tokens": thought,
        "total_cached_tokens": 20 if cache else 0,
    }


def _interaction(scenario: str, model: str) -> dict:
    status = "completed"
    steps: list[dict] = []
    output_text: str | None = None
    thought_tokens = 0

    if scenario in ("structured", "structured_schema_fail", "structured_notjson"):
        text = {
            "structured": '{"name": "Alice", "age": 30}',
            "structured_schema_fail": '{"name": "Alice"}',
            "structured_notjson": "Sorry, only prose here.",
        }[scenario]
        steps = [{"type": "model_output", "content": [{"type": "text", "text": text}]}]
        output_text = text
    elif scenario == "structured_incomplete":
        status = "incomplete"
        steps = [{"type": "model_output", "content": [{"type": "text", "text": '{"name": "Ali'}]}]
        output_text = '{"name": "Ali'
    elif scenario == "tools":
        status = "requires_action"  # a function call awaits a result; no second turn in P0.6B
        steps = [
            {
                "type": "function_call",
                "id": "fc_mock_1",
                "name": "get_weather",
                "arguments": {"city": "Paris"},
            }
        ]
    elif scenario == "thought":
        thought_tokens = 4
        steps = [
            {"type": "thought", "thought_signature": "sig_mock_opaque_1"},  # structural only
            {"type": "model_output", "content": [{"type": "text", "text": "Hello there, friend."}]},
        ]
        output_text = "Hello there, friend."
    elif scenario == "multi":
        steps = [
            {
                "type": "model_output",
                "content": [
                    {"type": "text", "text": "First part."},
                    {"type": "text", "text": "Second part."},
                ],
            }
        ]
        output_text = "First part.Second part."
    else:  # generation / roles / usage / cache
        steps = [
            {"type": "model_output", "content": [{"type": "text", "text": "Hello there, friend."}]}
        ]
        output_text = "Hello there, friend."

    return {
        "id": "interaction_mock_" + scenario,
        "object": "interaction",
        "status": status,
        "model": model,  # provider-returned model
        "created": _CREATED,
        "store": False,  # echoes the request; no server-side retention
        "previous_interaction_id": None,
        "steps": steps,
        "usage": _usage(cache=(scenario == "cache"), thought=thought_tokens),
        "output_text": output_text,  # SDK convenience projection, distinct from `steps`
    }


def _stream_events(scenario: str, model: str) -> list[dict]:
    iid = "interaction_mock_stream"
    if scenario == "stream_tools":
        step = {"event_type": "step.start", "step_index": 0, "step_type": "function_call"}
        deltas = [
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {"type": "arguments_delta", "arguments": '{"city":'},
            },
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {"type": "arguments_delta", "arguments": ' "Paris"}'},
            },
        ]
        final_status = "requires_action"
    elif scenario == "stream_thought":
        step = {"event_type": "step.start", "step_index": 0, "step_type": "thought"}
        deltas = [
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {
                    "type": "thought_signature_delta",
                    "thought_signature": "sig_mock_stream_1",
                },
            },
        ]
        final_status = "completed"
    else:  # stream (text)
        step = {"event_type": "step.start", "step_index": 0, "step_type": "model_output"}
        deltas = [
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {"type": "text_delta", "text": "one\n"},
            },
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {"type": "text_delta", "text": "two\n"},
            },
            {
                "event_type": "step.delta",
                "step_index": 0,
                "delta": {"type": "text_delta", "text": "three\n"},
            },
        ]
        final_status = "completed"

    events: list[dict] = [
        {
            "event_type": "interaction.created",
            "interaction": {"id": iid, "status": "in_progress", "model": model},
        },
        step,
        *deltas,
        {"event_type": "step.stop", "step_index": 0},
        {
            "event_type": "gemini.unknown_native_event",
            "payload": {"note": "not yet in the audit vocabulary"},
        },
        {
            "event_type": "interaction.completed",
            "interaction": {"id": iid, "status": final_status, "model": model, "usage": _usage()},
        },
    ]
    return events


class _FakeInteractions:
    def __init__(self, outer: FakeGeminiClient) -> None:
        self._outer = outer

    def create(self, request: dict | None = None, **kwargs: Any):
        return self._outer._respond(request or kwargs.get("body") or {}, **kwargs)


class FakeGeminiClient:
    """Deterministic offline fake returning native Interaction / event dicts. `scenario` forces
    a shape; the model is read from the request so evidence echoes the request."""

    def __init__(self, scenario: str | None = None) -> None:
        self.scenario = scenario or "generation"
        self.interactions = _FakeInteractions(self)
        self.retry_attempts = 1
        self.calls_observed = 0

    def _respond(self, request: dict, **kwargs: Any):
        self.calls_observed += 1
        model = request.get("model", "gemini-mock")
        if self.scenario == "error":
            raise FakeGeminiError()
        if request.get("stream") or kwargs.get("stream"):
            return iter(_stream_events(self.scenario, model))
        return _interaction(self.scenario, model)
