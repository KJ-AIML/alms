"""Redaction tests (DevSpec Section 85): strip secrets, preserve benign evidence."""

from __future__ import annotations

from alms_audit.redaction import MASK, redact


def test_authorization_header_value_is_masked() -> None:
    out, fields = redact({"headers": {"Authorization": "Bearer sk-abc123456789"}})
    assert out["headers"]["Authorization"] == MASK
    assert "headers/Authorization" in fields


def test_api_key_field_is_masked() -> None:
    out, fields = redact({"api_key": "sk-livesecret000", "model": "gpt-4o-mini"})
    assert out["api_key"] == MASK
    assert out["model"] == "gpt-4o-mini"  # benign preserved


def test_bearer_and_sk_tokens_in_free_text_are_masked() -> None:
    out, _ = redact({"log": "sent Authorization: Bearer sk-TOPSECRET12345 to api"})
    assert "sk-TOPSECRET12345" not in out["log"]
    assert MASK in out["log"]


def test_signed_url_signature_is_masked() -> None:
    url = "https://blob.example.com/x?X-Amz-Signature=deadbeefcafe&expires=1"
    out, _ = redact({"url": url})
    assert "deadbeefcafe" not in out["url"]
    assert "expires=1" in out["url"]  # non-secret query param preserved


def test_configured_secret_value_is_masked_anywhere() -> None:
    out, fields = redact({"note": "key is HUNTER2SECRET here"}, secret_values={"HUNTER2SECRET"})
    assert "HUNTER2SECRET" not in out["note"]
    assert fields  # a field was recorded


def test_synthetic_content_preserved() -> None:
    payload = {"prompt": "Alice is 30 years old.", "request_id": "req_123", "status": 200}
    out, fields = redact(payload)
    assert out == payload
    assert fields == []
