"""Lane dispatch + full offline LangChain simulation through the REAL probe subprocess.

Drives CLI selection -> planner -> runner -> REAL langchain probe subprocess -> probe MOCK
mode -> raw capture -> LangChain normalization -> result records -> run summary, with ZERO
provider calls and ZERO network. Evidence is labelled offline_mock, never live.
"""

from __future__ import annotations

import json

import pytest

from alms_audit.config import approved_fixtures, load_config_path, load_raw
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.pricing import load_snapshots
from alms_audit.runner import _probe_id_for_lane, run
from alms_audit.schemas import default_root, is_valid
from alms_audit.selection import resolve_model, select_fixtures, select_lane

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]
_MODEL = "gpt-5.4-nano-2026-03-17"
_ANTHROPIC_MODEL = "claude-synthetic-p06a"
_GEMINI_MODEL = "gemini-synthetic-p06b"
_LANGCHAIN_PROBE = default_root() / "probes" / "langchain"
_ANTHROPIC_PROBE = default_root() / "probes" / "anthropic-native"
_GEMINI_PROBE = default_root() / "probes" / "gemini-native"


def test_probe_id_derived_from_runtime_layer():
    assert _probe_id_for_lane({"runtime_layer": "langchain"}) == "langchain"
    assert _probe_id_for_lane({"runtime_layer": "openai"}) == "openai-native"
    assert _probe_id_for_lane({"runtime_layer": "anthropic"}) == "anthropic-native"
    assert _probe_id_for_lane({"runtime_layer": "google-genai"}) == "gemini-native"


def _offline_langchain_run(corpus_root, run_id="lc-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    config = load_config_path(cfg_path)
    pricing = load_snapshots(raw).get(_MODEL)
    lane = resolve_model(select_lane(load_lanes(corpus_root), "langchain-openai"), _MODEL)
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
        model=_MODEL,
        pricing=pricing,
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_LANGCHAIN_PROBE,  # real synced probe venv (corpus_root is a tmp copy)
    )


@pytest.mark.skipif(
    not (_LANGCHAIN_PROBE / ".venv").exists(),
    reason="langchain probe venv missing; run `uv sync --frozen` in probes/langchain",
)
def test_full_offline_langchain_simulation_all_six(corpus_root):
    summary = _offline_langchain_run(corpus_root)
    assert summary.mode == "offline"
    assert summary.expected_call_count == 6
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert [f["fixture_id"] for f in run_summary["fixtures"]] == _APPROVED
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "langchain-openai"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["selected_lanes"] == ["langchain-openai"]
    assert "langchain" in manifest["probe_lock_hashes"]  # langchain probe lock recorded

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "langchain"
        assert probe_resp["execution_mode"] == "offline_mock"  # never live
        assert probe_resp["package_versions"]["langchain-openai"] == "1.3.5"
        assert probe_resp["retry_count_observed"] == 0  # measured, single attempt
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


@pytest.mark.skipif(
    not (_LANGCHAIN_PROBE / ".venv").exists(),
    reason="langchain probe venv missing; run `uv sync --frozen` in probes/langchain",
)
def test_langchain_stream_surfaces_framework_extension(corpus_root):
    summary = _offline_langchain_run(corpus_root, run_id="lc-stream", ids=["STREAM-001"])
    tr = json.loads(
        (summary.run_dir / "fixtures" / "STREAM-001" / "normalized-transcript.json").read_text(
            "utf-8"
        )
    )
    types = [e["type"] for e in tr["events"]]
    # LangChain synthesized an extra terminal chunk; preserved as framework_extension, and the
    # fixture's terminal status reflects it distinctly from a plain PASS.
    assert "framework_extension" in types
    assert summary.entries[0]["status"] == "PASS_WITH_EXTENSION"


def _offline_anthropic_run(corpus_root, run_id="an-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), "anthropic-native"), _ANTHROPIC_MODEL)
    fixtures = select_fixtures(
        load_fixtures(corpus_root), ids, lane=lane, approved_fixtures=approved_fixtures(raw)
    )
    return run(
        run_id=run_id,
        fixtures=fixtures,
        lanes=load_lanes(corpus_root),
        config=load_config_path(cfg_path),
        offline_execute=True,
        selected_lane=lane,
        model=_ANTHROPIC_MODEL,
        pricing=None,  # no live-cost gate needed for an offline run
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_ANTHROPIC_PROBE,
    )


@pytest.mark.skipif(
    not (_ANTHROPIC_PROBE / ".venv").exists(),
    reason="anthropic probe venv missing; run `uv sync --frozen` in probes/anthropic-native",
)
def test_full_offline_anthropic_simulation_all_six(corpus_root):
    summary = _offline_anthropic_run(corpus_root)
    assert summary.mode == "offline"
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "anthropic-native"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert "anthropic-native" in manifest["probe_lock_hashes"]

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "anthropic-native"
        assert probe_resp["provider"] == "anthropic"
        assert probe_resp["execution_mode"] == "offline_mock"
        assert probe_resp["package_versions"]["anthropic"] == "0.116.0"
        assert probe_resp["retry_count_observed"] == 0
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


@pytest.mark.skipif(
    not (_ANTHROPIC_PROBE / ".venv").exists(),
    reason="anthropic probe venv missing; run `uv sync --frozen` in probes/anthropic-native",
)
def test_anthropic_stream_preserves_native_lifecycle(corpus_root):
    summary = _offline_anthropic_run(corpus_root, run_id="an-stream", ids=["STREAM-001"])
    tr = json.loads(
        (summary.run_dir / "fixtures" / "STREAM-001" / "normalized-transcript.json").read_text(
            "utf-8"
        )
    )
    types = [e["type"] for e in tr["events"]]
    # Anthropic's native content-block lifecycle + ping are retained as provider_extension
    # (native behavior), never framework_extension, and the terminal state stays observable.
    assert "provider_extension" in types
    assert "framework_extension" not in types
    assert "response_completed" in types
    assert summary.entries[0]["status"] == "PASS_WITH_EXTENSION"


def _offline_gemini_run(corpus_root, run_id="gm-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), "gemini-native"), _GEMINI_MODEL)
    fixtures = select_fixtures(
        load_fixtures(corpus_root), ids, lane=lane, approved_fixtures=approved_fixtures(raw)
    )
    return run(
        run_id=run_id,
        fixtures=fixtures,
        lanes=load_lanes(corpus_root),
        config=load_config_path(cfg_path),
        offline_execute=True,
        selected_lane=lane,
        model=_GEMINI_MODEL,
        pricing=None,  # offline needs no pricing snapshot (cost gate is live-only)
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_GEMINI_PROBE,
    )


@pytest.mark.skipif(
    not (_GEMINI_PROBE / ".venv").exists(),
    reason="gemini probe venv missing; run `uv sync --frozen` in probes/gemini-native",
)
def test_full_offline_gemini_simulation_all_six(corpus_root):
    summary = _offline_gemini_run(corpus_root)
    assert summary.mode == "offline"
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "gemini-native"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert "gemini-native" in manifest["probe_lock_hashes"]

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "gemini-native"
        assert probe_resp["provider"] == "google"
        assert probe_resp["execution_mode"] == "offline_mock"
        assert probe_resp["package_versions"]["google-genai"] == "2.11.0"
        assert probe_resp["retry_count_observed"] == 0
        # store=false must be present on every request artifact
        req = json.loads((fx_dir / "raw" / "gemini_request.json").read_text("utf-8"))
        assert req["store"] is False
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


@pytest.mark.skipif(
    not (_GEMINI_PROBE / ".venv").exists(),
    reason="gemini probe venv missing; run `uv sync --frozen` in probes/gemini-native",
)
def test_gemini_stream_preserves_native_lifecycle(corpus_root):
    summary = _offline_gemini_run(corpus_root, run_id="gm-stream", ids=["STREAM-001"])
    tr = json.loads(
        (summary.run_dir / "fixtures" / "STREAM-001" / "normalized-transcript.json").read_text(
            "utf-8"
        )
    )
    types = [e["type"] for e in tr["events"]]
    # Interactions-native step lifecycle + unknown event retained as provider_extension.
    assert "provider_extension" in types
    assert "framework_extension" not in types
    assert "response_completed" in types
    assert summary.entries[0]["status"] == "PASS_WITH_EXTENSION"
