"""Preliminary offline lane comparison (openai-native vs langchain), implementation-shape only."""

from __future__ import annotations

import pytest

from alms_audit.config import approved_fixtures, load_config_path, load_raw
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.pricing import load_snapshots
from alms_audit.reporting.compare import DISCLAIMER, compare_lanes
from alms_audit.runner import run
from alms_audit.schemas import default_root
from alms_audit.selection import resolve_model, select_fixtures, select_lane

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]
_MODEL = "gpt-5.4-nano-2026-03-17"
_OPENAI_PROBE = default_root() / "probes" / "openai-native"
_LANGCHAIN_PROBE = default_root() / "probes" / "langchain"

_venvs_present = (_OPENAI_PROBE / ".venv").exists() and (_LANGCHAIN_PROBE / ".venv").exists()


def _run_lane(corpus_root, lane_id, probe_dir, run_id):
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), lane_id), _MODEL)
    fixtures = select_fixtures(
        load_fixtures(corpus_root), _APPROVED, lane=lane, approved_fixtures=approved_fixtures(raw)
    )
    return run(
        run_id=run_id,
        fixtures=fixtures,
        lanes=load_lanes(corpus_root),
        config=load_config_path(cfg_path),
        offline_execute=True,
        selected_lane=lane,
        model=_MODEL,
        pricing=load_snapshots(raw).get(_MODEL),
        config_digest="d",
        command_line="test",
        root=corpus_root,
        probe_dir=probe_dir,
    )


@pytest.mark.skipif(not _venvs_present, reason="both probe venvs required for comparison")
def test_offline_comparison_is_disclaimered_and_captures_framework_differences(corpus_root):
    oai = _run_lane(corpus_root, "openai-native", _OPENAI_PROBE, "cmp-oai")
    lc = _run_lane(corpus_root, "langchain-openai", _LANGCHAIN_PROBE, "cmp-lc")

    report = compare_lanes(oai.run_dir, lc.run_dir, _APPROVED)

    # The comparison must never be read as live semantic evidence.
    assert report["disclaimer"] == DISCLAIMER
    assert "not live provider semantic evidence" in report["disclaimer"]
    assert [f["fixture_id"] for f in report["fixtures"]] == _APPROVED

    by_id = {f["fixture_id"]: f for f in report["fixtures"]}

    # Structured output: openai-native captured no explicit strategy label (native json_schema),
    # LangChain recorded a function_calling strategy — a real, framework-API-caused difference.
    assert by_id["STR-001"]["structured_strategy_differs"] is True
    assert by_id["STR-001"]["langchain"]["structured_output_strategy"] == "function_calling"

    # Streaming: LangChain added a framework-synthesized event the native lane did not.
    assert by_id["STREAM-001"]["framework_added_extension"] is True

    # Both lanes ran offline_mock and named their own probe.
    assert by_id["GEN-001"]["openai_native"]["probe_id"] == "openai-native"
    assert by_id["GEN-001"]["langchain"]["probe_id"] == "langchain"
    assert by_id["GEN-001"]["langchain"]["execution_mode"] == "offline_mock"
