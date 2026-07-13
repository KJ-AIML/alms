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
_GEMINI_PROBE = default_root() / "probes" / "gemini-native"
_LITELLM_PROBE = default_root() / "probes" / "litellm-sdk"
_LITELLM_MODEL = "openai/gpt-synthetic-p07a"
_PYDANTICAI_PROBE = default_root() / "probes" / "pydantic-ai-agent"
_PYDANTICAI_MODEL = "openai:gpt-synthetic-p07b"

_venvs_present = (_OPENAI_PROBE / ".venv").exists() and (_LANGCHAIN_PROBE / ".venv").exists()
_three_present = _venvs_present and (_ANTHROPIC_PROBE / ".venv").exists()
_four_present = _three_present and (_GEMINI_PROBE / ".venv").exists()
_five_present = _four_present and (_LITELLM_PROBE / ".venv").exists()
_six_present = _five_present and (_PYDANTICAI_PROBE / ".venv").exists()


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


@pytest.mark.skipif(not _four_present, reason="all four probe venvs required")
def test_four_lane_diversity_comparison(corpus_root):
    oai = _run_lane(corpus_root, "openai-native", _OPENAI_PROBE, "d4-oai")
    lc = _run_lane(corpus_root, "langchain-openai", _LANGCHAIN_PROBE, "d4-lc")
    an = _run_lane(corpus_root, "anthropic-native", _ANTHROPIC_PROBE, "d4-an", model="claude-syn-x")
    gm = _run_lane(corpus_root, "gemini-native", _GEMINI_PROBE, "d4-gm", model="gemini-syn-x")

    report = compare_runs(
        {
            "openai-native": oai.run_dir,
            "langchain": lc.run_dir,
            "anthropic-native": an.run_dir,
            "gemini-native": gm.run_dir,
        },
        _APPROVED,
    )

    assert report["disclaimer"] == DISCLAIMER
    assert "not live provider semantic evidence" in report["disclaimer"]
    assert set(report["lanes"]) == {
        "openai-native",
        "langchain",
        "anthropic-native",
        "gemini-native",
    }
    by_id = {f["fixture_id"]: f for f in report["fixtures"]}

    gen = by_id["GEN-001"]["by_lane"]
    assert gen["gemini-native"]["probe_id"] == "gemini-native"
    assert gen["gemini-native"]["execution_mode"] == "offline_mock"

    # Structured-output mechanisms across four lanes: three native JSON-schema mechanisms
    # (OpenAI Responses json_schema, Anthropic output_config.format, Gemini response_format)
    # versus LangChain's framework function_calling.
    strategies = by_id["STR-001"]["structured_strategies"]
    assert strategies["gemini-native"] == "response_format.text.json_schema"
    assert strategies["langchain"] == "function_calling"
    native = by_id["STR-001"]["native_json_schema_lanes"]
    assert "gemini-native" in native and "anthropic-native" in native and "openai-native" in native
    assert "langchain" not in native

    # Gemini exposes a native Interactions step lifecycle (provider_extension) the others do not
    # surface the same way; a framework label is never used for Gemini-native data.
    gm_stream = by_id["STREAM-001"]["by_lane"]["gemini-native"]["extension_events"]
    assert gm_stream["provider_extension"] >= 1
    assert gm_stream["framework_extension"] == 0


@pytest.mark.skipif(not _five_present, reason="all five probe venvs required")
def test_five_lane_diversity_comparison(corpus_root):
    oai = _run_lane(corpus_root, "openai-native", _OPENAI_PROBE, "d5-oai")
    lc = _run_lane(corpus_root, "langchain-openai", _LANGCHAIN_PROBE, "d5-lc")
    an = _run_lane(corpus_root, "anthropic-native", _ANTHROPIC_PROBE, "d5-an", model="claude-syn-x")
    gm = _run_lane(corpus_root, "gemini-native", _GEMINI_PROBE, "d5-gm", model="gemini-syn-x")
    ll = _run_lane(corpus_root, "litellm-sdk", _LITELLM_PROBE, "d5-ll", model=_LITELLM_MODEL)

    report = compare_runs(
        {
            "openai-native": oai.run_dir,
            "langchain": lc.run_dir,
            "anthropic-native": an.run_dir,
            "gemini-native": gm.run_dir,
            "litellm-sdk": ll.run_dir,
        },
        _APPROVED,
    )

    assert report["disclaimer"] == DISCLAIMER
    assert "not live provider semantic evidence" in report["disclaimer"]
    assert "litellm-sdk" in report["lanes"]
    by_id = {f["fixture_id"]: f for f in report["fixtures"]}

    gen = by_id["GEN-001"]["by_lane"]["litellm-sdk"]
    assert gen["probe_id"] == "litellm-sdk"
    assert gen["execution_mode"] == "offline_mock"

    # Structured output: LiteLLM's response_format is framework-mediated, NOT native provider
    # JSON-schema. It joins LangChain on the framework side; the three native lanes stay native.
    mechanisms = by_id["STR-001"]["structured_mechanisms"]
    assert mechanisms["litellm-sdk"].startswith("framework_response_format")
    native = by_id["STR-001"]["native_json_schema_lanes"]
    assert "litellm-sdk" not in native
    assert set(native) == {"openai-native", "anthropic-native", "gemini-native"}

    # Model identity: LiteLLM strips the provider prefix, so requested != observed (a recorded
    # offline mismatch); its source is framework-derived (offline: fixture_expected), never
    # provider_native.
    mi = by_id["GEN-001"]["model_identity_by_lane"]["litellm-sdk"]
    assert mi["requested_model"] == _LITELLM_MODEL
    assert mi["observed_returned_model"] == "gpt-synthetic-p07a"
    assert mi["requested_observed_exact_match"] == "false"

    # LiteLLM auxiliary metadata is framework_extension, never provider_extension.
    ll_ext = by_id["GEN-001"]["by_lane"]["litellm-sdk"]["extension_events"]
    assert ll_ext["framework_extension"] >= 1
    assert ll_ext["provider_extension"] == 0

    # Evidence accuracy: the comparison reports per-fixture execution paths, and they are NOT
    # identical across the litellm-sdk fixtures. GEN-001 uses the completion mock path; TOOL-001 is
    # the partial request-transform + response-object-injection path (not full completion(tools=)).
    gen_path = by_id["GEN-001"]["execution_path_by_lane"]["litellm-sdk"]
    tool_path = by_id["TOOL-001"]["execution_path_by_lane"]["litellm-sdk"]
    assert gen_path["components"] == ["completion_mock_response"]
    assert tool_path["full_completion_tools_path_exercised"] is False
    assert gen_path["components"] != tool_path["components"]  # paths differ across fixtures
    # Native lanes do not classify execution paths (litellm-specific evidence).
    assert by_id["GEN-001"]["execution_path_by_lane"]["openai-native"] is None


@pytest.mark.skipif(
    not _six_present, reason="all six probe venvs required for the six-lane comparison"
)
def test_six_lane_diversity_comparison(corpus_root):
    oai = _run_lane(corpus_root, "openai-native", _OPENAI_PROBE, "d6-oai")
    lc = _run_lane(corpus_root, "langchain-openai", _LANGCHAIN_PROBE, "d6-lc")
    an = _run_lane(corpus_root, "anthropic-native", _ANTHROPIC_PROBE, "d6-an", model="claude-syn-x")
    gm = _run_lane(corpus_root, "gemini-native", _GEMINI_PROBE, "d6-gm", model="gemini-syn-x")
    ll = _run_lane(corpus_root, "litellm-sdk", _LITELLM_PROBE, "d6-ll", model=_LITELLM_MODEL)
    pa = _run_lane(
        corpus_root, "pydantic-ai-agent", _PYDANTICAI_PROBE, "d6-pa", model=_PYDANTICAI_MODEL
    )

    report = compare_runs(
        {
            "openai-native": oai.run_dir,
            "langchain": lc.run_dir,
            "anthropic-native": an.run_dir,
            "gemini-native": gm.run_dir,
            "litellm-sdk": ll.run_dir,
            "pydantic-ai-agent": pa.run_dir,
        },
        _APPROVED,
    )

    assert report["disclaimer"] == DISCLAIMER
    assert "pydantic-ai-agent" in report["lanes"]
    by_id = {f["fixture_id"]: f for f in report["fixtures"]}

    gen = by_id["GEN-001"]["by_lane"]["pydantic-ai-agent"]
    assert gen["probe_id"] == "pydantic-ai-agent"
    assert gen["execution_mode"] == "offline_mock"

    # Structured output: PydanticAI NativeOutput is framework-mediated offline (framework selects
    # native mode + generates schema); it is NOT provider-native JSON-schema proof, so it does NOT
    # join the native_json_schema family (only the three native SDK lanes do).
    mechanisms = by_id["STR-001"]["structured_mechanisms"]
    assert mechanisms["pydantic-ai-agent"] == "framework_native_output (pydanticai)"
    native = by_id["STR-001"]["native_json_schema_lanes"]
    assert "pydantic-ai-agent" not in native
    assert set(native) == {"openai-native", "anthropic-native", "gemini-native"}

    # Three frameworks are compared WITHOUT being treated as equivalent: langchain uses
    # function-calling, litellm a translated response_format, pydantic-ai native-output - three
    # DISTINCT framework-mediated mechanisms, none of them provider-native.
    assert mechanisms["langchain"] != mechanisms["litellm-sdk"] != mechanisms["pydantic-ai-agent"]
    assert mechanisms["langchain"] != mechanisms["pydantic-ai-agent"]

    # Model identity: the offline FunctionModel exposes a synthetic model_name distinct from the
    # requested model -> a recorded mismatch, framework-derived (fixture_expected), never provider.
    mi = by_id["GEN-001"]["model_identity_by_lane"]["pydantic-ai-agent"]
    assert mi["requested_model"] == _PYDANTICAI_MODEL
    assert mi["observed_returned_model"] == "function:offline-synthetic-model"
    assert mi["requested_observed_exact_match"] == "false"
    assert mi["observed_returned_model_source"] == "fixture_expected"

    # PydanticAI Agent metadata (graph nodes / Agent info) is framework_extension, never
    # provider_extension (a framework lane emits no provider_extension event).
    pa_ext = by_id["GEN-001"]["by_lane"]["pydantic-ai-agent"]["extension_events"]
    assert pa_ext["framework_extension"] >= 1
    assert pa_ext["provider_extension"] == 0

    # Deferred tool: TOOL-001 defers (approval-required); the terminal is requires_action and no
    # tool executed - distinct from lanes that represent a direct tool call.
    tool_view = by_id["TOOL-001"]["by_lane"]["pydantic-ai-agent"]
    assert tool_view["status"] in ("PASS", "PASS_WITH_EXTENSION")
