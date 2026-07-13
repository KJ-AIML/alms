"""Storage and privacy: store=false always, stateless, no credential serialized."""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import corpus_fixture, write_request
from probe.__main__ import run

_FIXTURES = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]


def _request_artifact(fid: str, out: Path, stream: bool = False) -> dict:
    out.mkdir(parents=True, exist_ok=True)
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
    _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    return json.loads(Path(manifest["request_path"]).read_text(encoding="utf-8"))


def test_every_request_sets_store_false(tmp_path):
    for fid in _FIXTURES:
        d = tmp_path / fid
        art = _request_artifact(fid, d, stream=(fid == "STREAM-001"))
        assert art["store"] is False, f"{fid} did not set store=false"


def test_no_previous_interaction_id_anywhere(tmp_path):
    for fid in _FIXTURES:
        art = _request_artifact(fid, tmp_path / fid, stream=(fid == "STREAM-001"))
        assert "previous_interaction_id" not in art  # no server-state identifier reused


def test_no_hidden_default_enables_storage(tmp_path):
    # Even with nothing about storage in the fixture, the translated request is store=false.
    from probe.translate import to_operation

    op, _ = to_operation(json.loads(corpus_fixture("GEN-001").read_text(encoding="utf-8")), "m")
    assert op["store"] is False


def test_no_credential_value_in_artifacts(tmp_path):
    fid = "GEN-001"
    req = write_request(
        tmp_path / "req.json",
        corpus_fixture(fid),
        tmp_path,
        controls={"timeout_ms": 30000, "max_attempts": 1, "mock_mode": True},
    )
    env_key = "AIzaSyDONOTLEAK0000000000000000000000000"
    old = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = env_key
    try:
        _, manifest = run(json.loads(Path(req).read_text(encoding="utf-8")))
    finally:
        if old is None:
            os.environ.pop("GEMINI_API_KEY", None)
        else:
            os.environ["GEMINI_API_KEY"] = old
    blob = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "raw").glob("*"))
    assert env_key not in blob  # credential value never serialized into evidence
