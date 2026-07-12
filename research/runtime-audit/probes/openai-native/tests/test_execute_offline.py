"""Offline execute() against the narrow fake client."""

from __future__ import annotations

import json

from probe.client import MockResponsesClient
from probe.execute import execute


def _first_content(response):
    return response["output"][0]["content"][0]


def test_generation_capture():
    cap = execute(MockResponsesClient("generation"), {"model": "m"})
    assert cap.kind == "response"
    assert _first_content(cap.response)["type"] == "output_text"
    assert cap.response["output"][0]["content"][0]["text"]


def test_structured_raw_json_preserved_not_flattened():
    cap = execute(
        MockResponsesClient("structured"),
        {"model": "m", "text": {"format": {"type": "json_schema"}}},
    )
    text = _first_content(cap.response)["text"]
    assert json.loads(text) == {"name": "Alice", "age": 30}  # raw text preserved verbatim


def test_tools_capture_preserves_call_id_name_args():
    cap = execute(
        MockResponsesClient("tools"),
        {"model": "m", "tools": [{"type": "function", "name": "get_weather"}]},
    )
    item = cap.response["output"][0]
    assert item["type"] == "function_call"
    assert item["call_id"] == "call_mock_1"
    assert item["name"] == "get_weather"
    assert json.loads(item["arguments"]) == {"city": "Paris"}


def test_usage_present_not_fabricated():
    cap = execute(MockResponsesClient("generation"), {"model": "m"})
    assert cap.response["usage"]["input_tokens"] == 8


def test_missing_usage_stays_absent_not_zero():
    cap = execute(MockResponsesClient("no_usage"), {"model": "m"})
    assert "usage" not in cap.response  # absent, never coerced to 0


def test_refusal_preserved_distinctly_from_error():
    cap = execute(MockResponsesClient("refusal"), {"model": "m"})
    assert cap.kind == "response"  # a refusal is a response, not an error
    assert _first_content(cap.response)["type"] == "refusal"
