"""Retry safety: every retry owner is disabled and the effective config is proven, never
assumed zero merely because the fixture requested zero (DevSpec Sections 64 and 80)."""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.client import OfflineChatModel, build_chat_model, retry_introspection
from probe.__main__ import run


def test_live_chat_model_disables_wrapper_and_client_retries():
    # Constructed offline with a dummy key; no network call is made by construction.
    model = build_chat_model("dummy-not-used", 30000, "gpt-x")
    assert model.max_retries == 0  # LangChain wrapper retry
    assert model.root_client.max_retries == 0  # underlying openai client retry


def test_live_chat_model_sets_no_base_url_redirect():
    model = build_chat_model("dummy-not-used", 30000, "gpt-x")
    # Direct OpenAI only: the openai client base_url must remain the default api.openai.com,
    # never an OpenRouter or gateway host.
    assert "openrouter" not in str(model.root_client.base_url).lower()
    assert "api.openai.com" in str(model.root_client.base_url)


def test_retry_introspection_records_each_owner():
    intro = retry_introspection(build_chat_model("dummy", 30000, "gpt-x"))
    assert intro["chat_model_max_retries"] == 0
    assert intro["openai_client_max_retries"] == 0
    assert intro["langchain_runnable_retry"].startswith("none")


def test_offline_run_observes_exactly_one_call_zero_retries(tmp_path):
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture("GEN-001"),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    # Measured from the fake's call counter, not inferred from the request.
    assert manifest["retry_count_observed"] == 0
    resp = json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))
    assert resp["retry"]["calls_observed"] == 1


def test_structured_parse_does_not_retry(tmp_path):
    # A structured request that parses on the first attempt must not trigger a second call.
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture("STR-001"),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert manifest["retry_count_observed"] == 0


def test_offline_fake_applies_no_runnable_retry():
    intro = retry_introspection(OfflineChatModel(scenario="generation"))
    assert intro["langchain_runnable_retry"].startswith("none")
