"""Retry safety: every owner disabled and the effective config proven, never assumed zero
merely because a fixture requested zero (DevSpec Sections 64 and 80)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.client import FakeAnthropicClient, build_client, retry_introspection
from probe.execute import execute
from probe.__main__ import run


def test_live_client_disables_retries_and_sets_no_base_url_redirect():
    client = build_client("dummy-not-used", 30000)
    assert client.max_retries == 0  # Anthropic SDK default is 2; overridden to 0
    base = str(client.base_url).lower()
    assert "openrouter" not in base and "bedrock" not in base and "vertex" not in base
    assert "api.anthropic.com" in base  # direct Anthropic only


def test_retry_introspection_records_owner():
    intro = retry_introspection(build_client("dummy", 30000))
    assert intro["anthropic_client_max_retries"] == 0
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


def test_fake_counts_single_call():
    client = FakeAnthropicClient(scenario="generation")
    execute(
        client,
        {
            "model": "m",
            "max_tokens": 32,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "hi"}]}],
            "stream": False,
            "structured_output_strategy_requested": None,
        },
    )
    assert client.calls_observed == 1
    assert retry_introspection(client)["retries_observed"] == 0


def test_no_retry_after_invalid_structured_output():
    # A schema-failing structured response must NOT trigger a second attempt; the probe records
    # the failure as evidence and stops (one call, zero retries).
    client = FakeAnthropicClient(scenario="structured_schema_fail")
    cap = execute(
        client,
        {
            "model": "m",
            "max_tokens": 64,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "x"}]}],
            "stream": False,
            "structured_output_strategy_requested": "output_config.format",
            "structured_output_format": "json_schema",
            "output_config": {
                "format": {
                    "type": "json_schema",
                    "schema": {"type": "object", "required": ["name", "age"]},
                }
            },
        },
    )
    assert cap.structured["outcome"] == "schema_validation_failed"
    assert client.calls_observed == 1  # no retry
    assert retry_introspection(client)["retries_observed"] == 0
