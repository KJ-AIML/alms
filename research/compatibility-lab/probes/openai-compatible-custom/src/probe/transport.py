"""Offline HTTP seam: real OpenAI SDK over httpx.MockTransport.

The SDK performs request construction and response parsing. Wire-shaped JSON is returned by
the transport; pre-normalized objects are never injected as the transport result.
"""

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


def _usage() -> dict[str, int]:
    return {"prompt_tokens": 8, "completion_tokens": 3, "total_tokens": 11}


def _chat_body(scenario: str, model: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": f"chatcmpl_mock_{scenario}",
        "object": "chat.completion",
        "model": model,
        "choices": [],
        "usage": _usage(),
    }
    if scenario == "structured":
        base["choices"] = [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"name": "Alice", "age": 30}',
                },
                "finish_reason": "stop",
            }
        ]
    elif scenario == "tools":
        base["choices"] = [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_mock_1",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Paris"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ]
    elif scenario == "no_usage":
        base["choices"] = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there, friend."},
                "finish_reason": "stop",
            }
        ]
        del base["usage"]
    elif scenario == "no_model":
        base["choices"] = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there, friend."},
                "finish_reason": "stop",
            }
        ]
        del base["model"]
    elif scenario == "error":
        return {
            "error": {
                "message": "mock endpoint error",
                "type": "invalid_request_error",
                "code": "not_found",
            }
        }
    else:
        base["choices"] = [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Hello there, friend."},
                "finish_reason": "stop",
            }
        ]
    return base


def _stream_bytes(scenario: str, model: str) -> bytes:
    chunks: list[dict[str, Any]]
    if scenario == "stream_tools":
        chunks = [
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "call_mock_1",
                                    "type": "function",
                                    "function": {"name": "get_weather", "arguments": ""},
                                }
                            ],
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {
                            "tool_calls": [
                                {"index": 0, "function": {"arguments": '{"city": "Paris"}'}}
                            ]
                        },
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "tool_calls"}],
            },
        ]
    else:
        chunks = [
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": "one\n"},
                        "finish_reason": None,
                    }
                ],
            },
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": "two\n"}, "finish_reason": None}],
            },
            {
                "id": "chatcmpl_stream",
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                "usage": _usage(),
            },
        ]
    lines = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks]
    lines.append(b"data: [DONE]\n\n")
    return b"".join(lines)


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
        body_json: Any
        try:
            body_json = json.loads(body_text) if body_text else None
        except json.JSONDecodeError:
            body_json = body_text

        attempt = {
            "method": request.method,
            "path": request.url.path,
            "host": host,
            "headers": safe_headers({k: v for k, v in request.headers.items()}),
            "body_shape": body_json,
        }
        capture.attempts.append(attempt)

        if simulate_redirect_host and simulate_redirect_host.lower() != expected_host.lower():
            capture.redirect_blocked = True
            capture.redirect_location_host = simulate_redirect_host
            # Do not follow: return error-shaped response the probe treats as redirect policy fail.
            return httpx.Response(
                302,
                headers={"location": f"https://{simulate_redirect_host}/v1/chat/completions"},
                json={"error": {"message": "redirect host change rejected"}},
            )

        model = "mock-model"
        if isinstance(body_json, dict):
            model = body_json.get("model", model)

        if scenario == "error":
            return httpx.Response(404, json=_chat_body("error", model))

        if request.url.path.endswith("/chat/completions") and (
            "text/event-stream" in request.headers.get("accept", "")
            or (isinstance(body_json, dict) and body_json.get("stream"))
        ):
            stream_scenario = "stream_tools" if scenario == "stream_tools" else "stream_text"
            return httpx.Response(
                200,
                headers={"content-type": "text/event-stream"},
                content=_stream_bytes(stream_scenario, model),
            )

        status = 200
        return httpx.Response(status, json=_chat_body(scenario, model))

    return httpx.MockTransport(handler), capture
