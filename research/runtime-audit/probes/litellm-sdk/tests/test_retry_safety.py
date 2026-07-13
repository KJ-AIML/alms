"""Isolation + retry/fallback/callback/telemetry safety, and LiteLLM exception mapping.

Every automatic behavior is proven off from the effective module state, never assumed zero
merely because a fixture requested zero (DevSpec Sections 64 and 80). No Router is constructed,
so no fallbacks / load balancing exist. LiteLLM's own mock exception seam exercises its exception
taxonomy without contacting a provider.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.__main__ import run
from probe.client import (
    configure_litellm_isolation,
    isolation_introspection,
    mock_argument,
    observe_routing,
)
from probe.execute import execute
from probe.translate import to_operation


def test_isolation_disables_every_automatic_behavior():
    state = configure_litellm_isolation()
    assert state["telemetry"] is False
    assert state["num_retries"] == 0
    assert state["success_callback"] == []
    assert state["failure_callback"] == []
    assert state["input_callback"] == []
    assert state["callbacks"] == []
    assert state["cache"] is None
    assert state["router_used"] is False
    assert state["fallbacks"] is None
    assert state["base_url_override"] is None


def test_offline_run_makes_exactly_one_call_zero_retries(tmp_path):
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture("GEN-001"),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert manifest["retry_count_observed"] == 0  # measured: calls_observed - 1
    resp = json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))
    assert resp["retry"]["calls_observed"] == 1
    assert resp["retry"]["retries_observed"] == 0
    assert resp["retry"]["router_used"] is False
    assert resp["retry"]["fallbacks"] is None


def test_structured_parse_does_not_retry(tmp_path):
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture("STR-001"),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert manifest["retry_count_observed"] == 0


def test_unqualified_model_has_no_hidden_default():
    # A bare (provider-unqualified) model string must NOT silently default to a provider: litellm
    # routing records an error rather than picking one.
    configure_litellm_isolation()
    routing = observe_routing("gpt-x")
    assert routing["resolved_provider"] is None
    assert routing["error"] is not None


def test_provider_qualified_model_routes_and_preserves_prefix():
    configure_litellm_isolation()
    routing = observe_routing("openai/gpt-x")
    assert routing["resolved_provider"] == "openai"
    assert routing["resolved_model_component"] == "gpt-x"  # prefix parsed, provider preserved


def test_error_scenario_maps_to_litellm_exception_taxonomy():
    # LiteLLM's mock exception seam raises through its OWN exception taxonomy (OpenAI-shaped),
    # captured as an error, not re-raised, and never flattened to a generic provider error.
    configure_litellm_isolation()
    op, _ = to_operation(
        {"id": "E", "messages": [{"role": "user", "parts": [{"kind": "text", "text": "hi"}]}]},
        "openai/gpt-x",
    )
    capture = execute(op, mock_argument("error", "openai/gpt-x"))
    assert capture.kind == "error"
    assert capture.error["litellm_exception_type"]  # a concrete litellm exception class name
    assert capture.error["llm_provider"] == "openai"  # provider name preserved
    assert capture.error["cause_chain"]  # underlying cause preserved, not flattened
    assert capture.calls_observed == 1  # a failure does not trigger a retry


def test_introspection_reads_live_state_not_assumptions():
    configure_litellm_isolation()
    intro = isolation_introspection()
    assert intro["num_retries"] == 0
    assert intro["telemetry"] is False
