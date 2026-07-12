"""Offline raw-evidence capture: what LangChain exposes is preserved as-is, not flattened."""

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


def test_message_and_usage_retained(tmp_path):
    m = _run("GEN-001", tmp_path)
    resp = _response(m)
    msg = resp["message"]
    assert msg["content"] == "Hello there, friend."
    assert msg["usage_metadata"]["input_tokens"] == 9  # framework usage_metadata retained
    assert msg["response_metadata"]["finish_reason"] == "stop"  # response metadata retained
    assert m["package_versions"]["langchain-core"] == "1.4.9"
    assert m["package_versions"]["langchain-openai"] == "1.3.5"


def test_tool_call_ids_and_args_retained(tmp_path):
    resp = _response(_run("TOOL-001", tmp_path))
    calls = resp["message"]["tool_calls"]
    assert len(calls) == 1
    assert calls[0]["name"] == "get_weather"
    assert calls[0]["args"] == {"city": "Paris"}
    assert calls[0]["id"]  # framework tool-call id preserved
    assert resp["message"]["invalid_tool_calls"] == []


def test_structured_strategy_and_parsed_and_raw_retained(tmp_path):
    resp = _response(_run("STR-001", tmp_path))
    assert resp["structured"]["strategy"] == "function_calling"  # strategy recorded, not assumed
    assert resp["structured"]["parsed"] == {"name": "Alice", "age": 30}
    assert resp["structured"]["parsing_error"] is None
    # The raw framework message that produced the parse is preserved alongside the parse.
    assert resp["message"]["tool_calls"][0]["args"] == {"name": "Alice", "age": 30}


def test_stream_chunks_retained_in_order(tmp_path):
    m = _run("STREAM-001", tmp_path, stream=True)
    assert m["capture_kind"] == "stream"
    resp = _response(m)
    seqs = [c["sequence"] for c in resp["chunks"]]
    assert seqs == sorted(seqs)  # monotonic order preserved
    assert len(resp["chunks"]) >= 3
    # Framework aggregation is captured distinctly from the individual chunks.
    assert resp["final_message"]["content"] == "one\ntwo\nthree\n"
    assert resp["final_message"]["usage_metadata"]["total_tokens"] == 14


def test_usage_absent_is_not_fabricated(tmp_path):
    # USAGE-001 mock reports usage; the point tested elsewhere is that ABSENT stays absent.
    resp = _response(_run("USAGE-001", tmp_path))
    assert resp["message"]["usage_metadata"] is not None


def test_raw_artifacts_written(tmp_path):
    m = _run("GEN-001", tmp_path)
    assert Path(m["request_path"]).is_file()  # request artifact
    assert Path(m["response_path"]).is_file()  # response artifact
    assert m["execution_mode"] == "offline_mock"  # never labelled live
