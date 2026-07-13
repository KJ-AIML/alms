"""Retry safety: every owner disabled and the effective config proven (DevSpec 64 and 80)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.client import FakeGeminiClient, build_client, retry_introspection
from probe.execute import execute
from probe.__main__ import run


def test_live_client_disables_retries_no_vertex_no_base_url():
    client = build_client("dummy-not-used", 30000)
    # 1 attempt == 0 retries; direct Gemini (not Vertex); default base host, no redirect.
    assert client._api_client._http_options.retry_options.attempts == 1
    assert not client._api_client.vertexai
    base = str(client._api_client._http_options.base_url).lower()
    assert "generativelanguage.googleapis.com" in base
    assert "openrouter" not in base


def test_retry_introspection_records_owner():
    intro = retry_introspection(build_client("dummy", 30000))
    assert intro["genai_client_retry_attempts"] == 1
    assert intro["probe_retry"] == "none"


def test_offline_run_observes_one_call_zero_retries(tmp_path):
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture("GEN-001"),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert manifest["retry_count_observed"] == 0  # measured from the fake's call count


def test_no_retry_after_invalid_structured_output():
    client = FakeGeminiClient(scenario="structured_schema_fail")
    cap = execute(
        client,
        {
            "model": "m",
            "input": [],
            "stream": False,
            "store": False,
            "response_format": {
                "text": {
                    "mime_type": "application/json",
                    "jsonSchema": {"type": "object", "required": ["name", "age"]},
                }
            },
            "structured_output_strategy_requested": "response_format.text.json_schema",
        },
    )
    assert cap.structured["outcome"] == "schema_validation_failed"
    assert client.calls_observed == 1  # no retry after invalid output
    assert retry_introspection(client)["retries_observed"] == 0


def test_no_retry_after_provider_error():
    client = FakeGeminiClient(scenario="error")
    execute(client, {"model": "m", "input": [], "stream": False, "store": False})
    assert client.calls_observed == 1  # single attempt, no retry after a provider error
