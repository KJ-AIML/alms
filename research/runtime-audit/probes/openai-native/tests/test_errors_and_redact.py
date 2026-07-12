"""Native error capture and secret redaction."""

from __future__ import annotations

from probe.client import MockResponsesClient
from probe.execute import execute
from probe.redact import MASK, redact


def test_error_capture_preserves_native_evidence():
    cap = execute(MockResponsesClient("error"), {"model": "m"})
    assert cap.kind == "error"
    assert cap.error["exception_type"] == "FakeOpenAIError"
    assert cap.error["provider_error_type"] == "NotFoundError"
    assert cap.error["status_code"] == 404
    assert cap.error["request_id"] == "req_mock_error"


def test_error_is_distinct_from_response():
    err = execute(MockResponsesClient("error"), {"model": "m"})
    ok = execute(MockResponsesClient("generation"), {"model": "m"})
    assert err.kind == "error" and ok.kind == "response"


def test_redact_masks_api_key_field():
    out, fields = redact({"api_key": "sk-live-abcdefgh12345", "model": "gpt-x"})
    assert out["api_key"] == MASK
    assert out["model"] == "gpt-x"
    assert "api_key" in fields


def test_redact_masks_bearer_in_text():
    out, _ = redact({"log": "Authorization: Bearer sk-SECRETVALUE0000"})
    assert "sk-SECRETVALUE0000" not in out["log"]
    assert MASK in out["log"]
