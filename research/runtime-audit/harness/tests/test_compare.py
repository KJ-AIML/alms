"""Preliminary offline lane comparison (openai-native vs langchain), implementation-shape only."""

from __future__ import annotations

import pytest

from alms_audit.config import approved_fixtures, load_config_path, load_raw
from alms_audit.fixtures import load_fixtures
from alms_audit.lanes import load_lanes
from alms_audit.pricing import load_snapshots
from alms_audit.reporting.compare import DISCLAIMER, compare_lanes, compare_runs
from alms_audit.runner import run
from alms_audit.schemas import default_root
from alms_audit.selection import resolve_model, select_fixtures, select_lane

_APPROVED = ["GEN-001", "ROLE-001", "STR-001", "TOOL-001", "STREAM-001", "USAGE-001"]
_MODEL = "gpt-5.4-nano-2026-03-17"
_OPENAI_PROBE = default_root() / "probes" / "openai-native"
_LANGCHAIN_PROBE = default_root() / "probes" / "langchain"
_ANTHROPIC_PROBE = default_root() / "probes" / "anthropic-native"

_venvs_present = (_OPENAI_PROBE / ".venv").exists() and (_LANGCHAIN_PROBE / ".venv").exists()
_three_present = _venvs_present and (_ANTHROPIC_PROBE / ".venv").exists()


def _run_lane(corpus_root, lane_id, probe_dir, run_id, model=_MODEL):
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), lane_id), model)
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
        model=model,
        pricing=load_snapshots(raw).get(model),  # None offline is fine (cost gate is live-only)
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


@pytest.mark.skipif(not _three_present, reason="all three probe venvs required")
def test_three_lane_diversity_comparison(corpus_root):
    oai = _run_lane(corpus_root, "openai-native", _OPENAI_PROBE, "d3-oai")
    lc = _run_lane(corpus_root, "langchain-openai", _LANGCHAIN_PROBE, "d3-lc")
    an = _run_lane(corpus_root, "anthropic-native", _ANTHROPIC_PROBE, "d3-an", model="claude-syn-x")

    report = compare_runs(
        {
            "openai-native": oai.run_dir,
            "langchain": lc.run_dir,
            "anthropic-native": an.run_dir,
        },
        _APPROVED,
    )

    assert report["disclaimer"] == DISCLAIMER
    assert set(report["lanes"]) == {"openai-native", "langchain", "anthropic-native"}
    by_id = {f["fixture_id"]: f for f in report["fixtures"]}

    # Each lane named its own probe and ran offline_mock.
    gen = by_id["GEN-001"]["by_lane"]
    assert gen["anthropic-native"]["probe_id"] == "anthropic-native"
    assert gen["anthropic-native"]["execution_mode"] == "offline_mock"

    # After the correction: BOTH native lanes expose provider-native JSON-schema structured
    # output (OpenAI Responses json_schema; Anthropic Messages output_config.format), while the
    # LangChain offline lane selected a framework-mediated function_calling strategy. The three
    # mechanisms are NOT all different — the native lanes share the native-JSON-schema family.
    strategies = by_id["STR-001"]["structured_strategies"]
    assert strategies["anthropic-native"] == "output_config.format"  # not strict_tool_use
    assert strategies["langchain"] == "function_calling"

    mechanisms = by_id["STR-001"]["structured_mechanisms"]
    assert mechanisms["openai-native"].startswith("native_json_schema")
    assert mechanisms["anthropic-native"].startswith("native_json_schema")
    assert mechanisms["langchain"] == "framework_function_calling"

    native_lanes = by_id["STR-001"]["native_json_schema_lanes"]
    assert native_lanes == ["anthropic-native", "openai-native"]  # both native, langchain not

    # Streaming: Anthropic exposes an explicit content-block lifecycle (provider_extension),
    # a native representation the OpenAI Responses stream does not surface the same way.
    an_stream_events = by_id["STREAM-001"]["by_lane"]["anthropic-native"]["extension_events"]
    assert an_stream_events["provider_extension"] >= 1
    assert an_stream_events["framework_extension"] == 0
