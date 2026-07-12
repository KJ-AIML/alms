"""OpenAI normalizer tests (harness side; SDK-free, schema-validated output)."""

from __future__ import annotations

import importlib.util

from alms_audit.normalizers import openai as nz
from alms_audit.schemas import is_valid, validation_errors


def test_normalize_stream_valid_and_preserves_unknown():
    events = [
        {"sequence": 0, "type": "response.created", "data": {}},
        {"sequence": 1, "type": "response.output_text.delta", "data": {"delta": "hi"}},
        {"sequence": 2, "type": "response.some_future_event", "data": {"x": 1}},
        {
            "sequence": 3,
            "type": "response.completed",
            "data": {"response": {"usage": {"input_tokens": 1}}},
        },
    ]
    doc = nz.normalize_stream(events, "raw-manifest.json", "raw/openai_events.json")
    assert is_valid("normalized-transcript", doc), validation_errors("normalized-transcript", doc)
    types = [e["type"] for e in doc["events"]]
    assert "response_started" in types
    assert "text_delta" in types
    assert "provider_extension" in types  # unknown native event preserved, not dropped
    assert "usage_updated" in types
    assert all(e["raw_ref"] for e in doc["events"])


def test_normalize_response_structured_output():
    resp = {
        "status": "completed",
        "output": [{"type": "message", "content": [{"type": "output_text", "text": '{"a": 1}'}]}],
        "usage": {"input_tokens": 1},
    }
    doc = nz.normalize_response(resp, "m", "raw/openai_response.json")
    assert is_valid("normalized-transcript", doc), validation_errors("normalized-transcript", doc)
    assert any(e["type"] == "structured_output_completed" for e in doc["events"])
    assert any(e["type"] == "usage_updated" for e in doc["events"])


def test_normalize_error_valid():
    doc = nz.normalize_error(
        {"exception_type": "NotFoundError", "status_code": 404}, "m", "raw/openai_error.json"
    )
    assert is_valid("normalized-transcript", doc), validation_errors("normalized-transcript", doc)
    assert doc["events"][0]["type"] == "error"


def test_harness_normalizer_has_no_openai_dependency():
    # The harness env must not have the OpenAI SDK installed.
    assert importlib.util.find_spec("openai") is None
