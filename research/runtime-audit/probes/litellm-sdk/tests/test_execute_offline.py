"""Offline raw-evidence capture: what LiteLLM exposes is preserved as-is, not flattened.

The offline path uses litellm's own mock_response seam, so real litellm machinery runs
(get_llm_provider routing, get_optional_params request translation, ModelResponse typing,
_hidden_params attachment, streaming wrapper) with zero network.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.__main__ import run


def _run(fid: str, out: Path, stream: bool = False) -> dict:
    req = write_request(
        out / "req.json",
        corpus_fixture(fid),
        out,
        controls={
            "timeout_ms": 30000,
            "max_attempts": 1,
            "max_output_tokens": 128,
            "mock_mode": True,
            "stream": stream,
        },
    )
    code, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    assert code == 0
    return manifest


def _response(manifest: dict) -> dict:
    return json.loads(Path(manifest["response_path"]).read_text(encoding="utf-8"))


def test_returned_model_prefix_stripped_and_hidden_full(tmp_path):
    m = _run("GEN-001", tmp_path)
    resp = _response(m)
    # Requested openai/mock-model -> LiteLLM returns the stripped model; the full requested string
    # survives only in _hidden_params.litellm_model_name.
    assert resp["response"]["model"] == "mock-model"
    assert resp["hidden_params"]["litellm_model_name"] == "openai/mock-model"
    assert m["package_versions"]["litellm"] == "1.92.0"


def test_usage_synthesized_and_present(tmp_path):
    resp = _response(_run("USAGE-001", tmp_path))
    usage = resp["response"]["usage"]
    # LiteLLM synthesizes token counts offline (token_counter); present, not provider-reported.
    assert usage["prompt_tokens"] is not None
    assert usage["completion_tokens"] is not None


def test_routing_observed_provider_and_component(tmp_path):
    resp = _response(_run("GEN-001", tmp_path))
    assert resp["routing"]["resolved_provider"] == "openai"
    assert resp["routing"]["resolved_model_component"] == "mock-model"
    assert resp["routing"]["error"] is None


def test_tool_call_id_name_and_raw_arguments_retained(tmp_path):
    resp = _response(_run("TOOL-001", tmp_path))
    choice = resp["response"]["choices"][0]
    assert choice["finish_reason"] == "tool_calls"
    calls = choice["message"]["tool_calls"]
    assert len(calls) == 1
    assert calls[0]["function"]["name"] == "get_weather"
    assert calls[0]["function"]["arguments"] == '{"city": "Paris"}'  # raw arg STRING preserved
    assert calls[0]["id"]  # tool-call id preserved


def test_tool_request_translation_exercised_not_via_proxy(tmp_path):
    resp = _response(_run("TOOL-001", tmp_path))
    tr = resp["tool_request_translation"]
    # The SDK request-side tool translation (get_optional_params) is exercised; tools are NOT sent
    # through litellm.completion (which would route through proxy MCP utilities / fastapi).
    assert tr["exercised"] is True
    assert tr["mechanism"] == "litellm.utils.get_optional_params"
    assert tr["tools_in_provider_params"] is True


def test_structured_strategy_parsed_and_no_tool_fallback(tmp_path):
    resp = _response(_run("STR-001", tmp_path))
    s = resp["structured"]
    assert s["strategy"] == "response_format.json_schema"  # recorded, not assumed native
    assert s["parsed"] == {"name": "Alice", "age": 30}
    assert s["parsing_error"] is None
    assert s["provider_validation"] == "unverified_until_live"  # offline: not proven native
    # NO silent tool fallback: the structured response is content, not a tool call.
    assert resp["response"]["choices"][0]["message"].get("tool_calls") in (None, [])


def test_stream_chunks_in_order_with_usage_chunk(tmp_path):
    m = _run("STREAM-001", tmp_path, stream=True)
    assert m["capture_kind"] == "stream"
    resp = _response(m)
    seqs = [c["sequence"] for c in resp["chunks"]]
    assert seqs == sorted(seqs)  # monotonic order preserved
    assert len(resp["chunks"]) >= 3
    # stream_options include_usage -> a usage chunk is captured distinctly.
    assert resp["usage_chunk"] is not None
    assert resp["usage_chunk"]["total_tokens"] is not None


def test_raw_artifacts_written_offline_mock(tmp_path):
    m = _run("GEN-001", tmp_path)
    assert Path(m["request_path"]).is_file()
    assert Path(m["response_path"]).is_file()
    assert m["execution_mode"] == "offline_mock"  # never labelled live
