"""Offline HTTP seam for Anthropic Messages-compatible endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import httpx

from .redact import safe_headers


@dataclass
class WireCapture:
    attempts: list[dict[str, Any]] = field(default_factory=list)
    redirect_blocked: bool = False
    redirect_location_host: str | None = None


def _usage(cache: bool = False) -> dict[str, int]:
    if cache:
        return {
            "input_tokens": 10,
            "output_tokens": 3,
            "cache_creation_input_tokens": 20,
            "cache_read_input_tokens": 5,
        }
    return {"input_tokens": 9, "output_tokens": 5}


def _message_body(scenario: str, model: str, tool_name: str | None) -> dict[str, Any]:
    if scenario == "error":
        return {"type": "error", "error": {"type": "not_found_error", "message": "mock error"}}
    if scenario == "structured":
        content = [{"type": "text", "text": '{"name": "Alice", "age": 30}'}]
        stop = "end_turn"
    elif scenario == "tools":
        content = [
            {
                "type": "tool_use",
                "id": "toolu_mock_1",
                "name": tool_name or "get_weather",
                "input": {"city": "Paris"},
            }
        ]
        stop = "tool_use"
    elif scenario == "cache":
        content = [{"type": "text", "text": "Hello there, friend."}]
        stop = "end_turn"
    elif scenario == "no_model":
        return {
            "id": "msg_mock_no_model",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello there, friend."}],
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": _usage(),
        }
    else:
        content = [{"type": "text", "text": "Hello there, friend."}]
        stop = "end_turn"
    body: dict[str, Any] = {
        "id": f"msg_mock_{scenario}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": stop,
        "stop_sequence": None,
        "usage": _usage(cache=(scenario == "cache")),
    }
    return body


def _stream_bytes(scenario: str, model: str, tool_name: str | None) -> bytes:
    events: list[dict[str, Any]] = [
        {
            "type": "message_start",
            "message": {
                "id": "msg_mock_stream",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [],
                "stop_reason": None,
                "stop_sequence": None,
                "usage": {"input_tokens": 9, "output_tokens": 0},
            },
        }
    ]
    if scenario == "stream_tools":
        events += [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {
                    "type": "tool_use",
                    "id": "toolu_stream_1",
                    "name": tool_name or "get_weather",
                    "input": {},
                },
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "input_json_delta", "partial_json": '{"city": "Paris"}'},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "tool_use", "stop_sequence": None},
                "usage": {"output_tokens": 7},
            },
            {"type": "message_stop"},
        ]
    else:
        events += [
            {
                "type": "content_block_start",
                "index": 0,
                "content_block": {"type": "text", "text": ""},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "one\n"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "text_delta", "text": "two\n"},
            },
            {"type": "content_block_stop", "index": 0},
            {
                "type": "message_delta",
                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                "usage": {"output_tokens": 5},
            },
            {"type": "message_stop"},
        ]
    return b"".join(f"event: {e['type']}\ndata: {json.dumps(e)}\n\n".encode() for e in events)


def build_mock_transport(
    *,
    scenario: str,
    expected_host: str,
    simulate_redirect_host: str | None = None,
) -> tuple[httpx.MockTransport, WireCapture]:
    capture = WireCapture()

    def handler(request: httpx.Request) -> httpx.Response:
        host = urlparse(str(request.url)).hostname or ""
        body_text = request.content.decode("utf-8") if request.content else ""
        try:
            body_json: Any = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            body_json = body_text
        capture.attempts.append(
            {
                "method": request.method,
                "path": request.url.path,
                "host": host,
                "headers": safe_headers({k: v for k, v in request.headers.items()}),
                "body_shape": body_json,
            }
        )
        if simulate_redirect_host and simulate_redirect_host.lower() != expected_host.lower():
            capture.redirect_blocked = True
            capture.redirect_location_host = simulate_redirect_host
            return httpx.Response(
                302,
                headers={"location": f"https://{simulate_redirect_host}/v1/messages"},
                json={"error": {"message": "redirect host change rejected"}},
            )

        model = "claude-mock"
        tool_name = None
        if isinstance(body_json, dict):
            model = body_json.get("model", model)
            tools = body_json.get("tools") or []
            if tools:
                tool_name = tools[0].get("name")

        if scenario == "error":
            return httpx.Response(404, json=_message_body("error", model, tool_name))

        streaming = isinstance(body_json, dict) and body_json.get("stream")
        if streaming:
            stream_scenario = (
                "stream_tools" if scenario in {"stream_tools", "tools"} else "stream_text"
            )
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=_stream_bytes(stream_scenario, model, tool_name),
            )
        return httpx.Response(200, json=_message_body(scenario, model, tool_name))

    return httpx.MockTransport(handler), capture
