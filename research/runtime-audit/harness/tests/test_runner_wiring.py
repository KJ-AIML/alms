"""Full offline acceptance simulation + result/secret-scan unit tests (DevSpec Sections 40, 41).

The end-to-end test drives the CLI selection -> planner -> runner -> REAL subprocess ->
OpenAI probe MOCK mode -> raw capture -> normalization -> result records -> run summary,
with ZERO provider network calls and ZERO real OpenAI SDK requests. A synthetic credential
is present in the environment to exercise the run-level secret scan; it must never leak.
"""

from __future__ import annotations

import importlib.util
import json

import pytest

from alms_audit.config import approved_fixtures, load_config_path, load_raw
from alms_audit.environment import scan_for_secret_shapes, scan_for_secrets
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.pricing import load_snapshots
from alms_audit.results import interpret
from alms_audit.runner import RunError, run
from alms_audit.schemas import default_root, is_valid, validation_errors
from alms_audit.selection import resolve_model, select_fixtures, select_lane

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]
_SYNTHETIC_KEY = "sk-synthetic-test-key-DO-NOT-USE-0000000000"


def _offline_run(corpus_root, run_id="wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    config = load_config_path(cfg_path)
    pricing = load_snapshots(raw).get("gpt-5.4-nano")
    lane = resolve_model(select_lane(load_lanes(corpus_root), "openai-native"), "gpt-5.4-nano")
    fixtures = select_fixtures(
        load_fixtures(corpus_root), ids, lane=lane, approved_fixtures=approved_fixtures(raw)
    )
    return run(
        run_id=run_id,
        fixtures=fixtures,
        lanes=load_lanes(corpus_root),
        config=config,
        offline_execute=True,
        selected_lane=lane,
        model="gpt-5.4-nano",
        pricing=pricing,
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=default_root() / "probes" / "openai-native",
    )


@pytest.fixture
def _synthetic_credential(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", _SYNTHETIC_KEY)


def test_full_offline_simulation_all_six_fixtures(corpus_root, _synthetic_credential):
    summary = _offline_run(corpus_root)

    assert summary.mode == "offline"
    assert summary.expected_call_count == 6
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED
    # Every selected fixture appears in the run summary with a terminal status.
    assert all(e["status"] in {"PASS", "PASS_WITH_EXTENSION"} for e in summary.entries)

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert [f["fixture_id"] for f in run_summary["fixtures"]] == _APPROVED
    assert run_summary["secret_scan"] == "clean"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert is_valid("run-manifest", manifest, corpus_root)
    assert manifest["model_configuration"]["execution_mode"] == "offline"
    assert manifest["credential_presence"]["OPENAI_API_KEY"] is True  # synthetic key present

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        # Raw evidence exists (written by the probe BEFORE normalization).
        assert (fx_dir / "raw").is_dir()
        raw_files = list((fx_dir / "raw").glob("openai_*.json"))
        assert raw_files, f"{fx_id}: no raw artifact"
        # Normalized + result exist and validate.
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript, corpus_root)
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result, corpus_root), validation_errors(
            "result", result, corpus_root
        )
        # Evidence is labelled offline_mock, never live.
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["execution_mode"] == "offline_mock"


def test_offline_simulation_makes_no_secret_leak(corpus_root, _synthetic_credential):
    summary = _offline_run(corpus_root, run_id="wire-secret")
    # Neither the exact synthetic value nor any credential-shaped string appears in evidence.
    assert scan_for_secrets(summary.run_dir, {_SYNTHETIC_KEY}) == []
    assert scan_for_secret_shapes(summary.run_dir) == []


def test_same_run_id_cannot_overwrite_evidence(corpus_root, _synthetic_credential):
    _offline_run(corpus_root, run_id="wire-dup")
    with pytest.raises(RunError, match="immutable"):
        _offline_run(corpus_root, run_id="wire-dup")


def test_harness_cannot_import_openai():
    assert importlib.util.find_spec("openai") is None


# --- secret scan unit behavior ---


def test_secret_scan_detects_planted_secret(tmp_path):
    (tmp_path / "leak.json").write_text(f'{{"k": "{_SYNTHETIC_KEY}"}}', encoding="utf-8")
    hits = scan_for_secrets(tmp_path, {_SYNTHETIC_KEY})
    assert len(hits) == 1


def test_secret_scan_ignores_blank_needle(tmp_path):
    (tmp_path / "f.txt").write_text("anything", encoding="utf-8")
    assert scan_for_secrets(tmp_path, {"", "   "}) == []


def test_shape_scan_detects_key_shaped_string_without_a_needle(tmp_path):
    (tmp_path / "leak.txt").write_text(f"key={_SYNTHETIC_KEY}", encoding="utf-8")
    assert len(scan_for_secret_shapes(tmp_path)) == 1
    (tmp_path / "leak.txt").unlink()
    (tmp_path / "clean.txt").write_text("model=gpt-5.4-nano id=resp_mock_1", encoding="utf-8")
    assert scan_for_secret_shapes(tmp_path) == []


# --- results.interpret: distinct terminal states ---


def _resp(usage=True, refusal=False):
    content = (
        [{"type": "refusal", "refusal": "no"}]
        if refusal
        else [{"type": "output_text", "text": "hi"}]
    )
    r = {"status": "completed", "output": [{"type": "message", "content": content}]}
    if usage:
        r["usage"] = {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}
    return r


def _interp(capture_kind, raw_obj):
    return interpret(
        capture_kind=capture_kind,
        raw_obj=raw_obj,
        run_id="r",
        fixture_id="F",
        lane_id="L",
        raw_manifest_ref="m.json",
        response_ref="raw/x.json",
        normalized_ref="n.json",
        pricing=None,
        root=default_root(),
    )


def test_success_is_pass_with_reported_usage():
    out = _interp("response", _resp())
    assert out.status == "PASS"
    assert out.result["usage"]["provenance"] == "reported"
    assert is_valid("result", out.result)


def test_missing_usage_stays_absent_not_zero():
    out = _interp("response", _resp(usage=False))
    u = out.result["usage"]
    assert u["provenance"] == "absent"
    assert u["input_tokens"] is None and u["output_tokens"] is None  # not coerced to 0


def test_provider_error_is_error_runtime():
    out = _interp("error", {"exception_type": "NotFoundError", "status_code": 404})
    assert out.status == "ERROR_RUNTIME"
    assert "provider_error" in out.notes


def test_refusal_is_pass_with_extension_and_distinct():
    out = _interp("response", _resp(refusal=True))
    assert out.status == "PASS_WITH_EXTENSION"
    assert "provider_refusal" in out.notes


def test_normalization_failure_preserves_raw_and_is_inconclusive():
    # A non-dict raw payload makes the normalizer raise; raw stays, transcript is None.
    out = _interp("response", "not-a-valid-response-object")
    assert out.status == "INCONCLUSIVE"
    assert out.normalized is None
    assert out.result["normalized_transcript"] is None
    assert any("normalization_failed" in n for n in out.notes)
