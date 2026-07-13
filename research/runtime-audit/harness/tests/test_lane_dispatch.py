"""Lane dispatch + full offline LangChain simulation through the REAL probe subprocess.

Drives CLI selection -> planner -> runner -> REAL langchain probe subprocess -> probe MOCK
mode -> raw capture -> LangChain normalization -> result records -> run summary, with ZERO
provider calls and ZERO network. Evidence is labelled offline_mock, never live.
"""

from __future__ import annotations

import json

import pytest

from alms_audit import provenance
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
# LiteLLM routes by provider prefix; the offline lane requires a provider-qualified model string.
_LITELLM_MODEL = "openai/gpt-synthetic-p07a"
# PydanticAI: the requested model is NOT the offline observed model (the FunctionModel exposes a
# synthetic model_name), so requested != observed is expected offline.
_PYDANTICAI_MODEL = "openai:gpt-synthetic-p07b"
_OPENAI_PROBE = default_root() / "probes" / "openai-native"
_LANGCHAIN_PROBE = default_root() / "probes" / "langchain"
_ANTHROPIC_PROBE = default_root() / "probes" / "anthropic-native"
_GEMINI_PROBE = default_root() / "probes" / "gemini-native"
_LITELLM_PROBE = default_root() / "probes" / "litellm-sdk"
_PYDANTICAI_PROBE = default_root() / "probes" / "pydantic-ai-agent"


def _assert_model_identity(result, requested):
    """P0.6D four-lane regression: every offline result carries the neutral model-identity
    contract (requested + observed-or-unavailable + central-vocab source + raw_ref-when-observed +
    offline_mock execution mode)."""
    mi = result["observed_model_identity"]
    assert mi["requested_model"] == requested
    assert mi["execution_mode"] == "offline_mock"
    assert mi["observed_returned_model_source"] in provenance.MODEL_IDENTITY_SOURCES
    if mi["observed_returned_model"] is not None:
        assert mi["observed_returned_model_raw_ref"]  # raw ref required when observed present
        assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED  # offline
    else:
        assert mi["observed_returned_model_source"] == provenance.UNAVAILABLE


def test_probe_id_derived_from_runtime_layer():
    assert _probe_id_for_lane({"runtime_layer": "langchain"}) == "langchain"
    assert _probe_id_for_lane({"runtime_layer": "openai"}) == "openai-native"
    assert _probe_id_for_lane({"runtime_layer": "anthropic"}) == "anthropic-native"
    assert _probe_id_for_lane({"runtime_layer": "google-genai"}) == "gemini-native"
    assert _probe_id_for_lane({"runtime_layer": "litellm-sdk"}) == "litellm-sdk"
    assert _probe_id_for_lane({"runtime_layer": "pydantic-ai-agent"}) == "pydantic-ai-agent"


def _offline_openai_run(corpus_root, run_id="oai-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), "openai-native"), _MODEL)
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
        model=_MODEL,
        pricing=load_snapshots(raw).get(_MODEL),
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_OPENAI_PROBE,  # real synced probe venv (corpus_root is a tmp copy)
    )


@pytest.mark.skipif(
    not (_OPENAI_PROBE / ".venv").exists(),
    reason="openai-native probe venv missing; run `uv sync --frozen` in probes/openai-native",
)
def test_full_offline_openai_simulation_all_six(corpus_root):
    # Parity with the langchain/anthropic/gemini full-sim tests: the OpenAI native lane is driven
    # through the SAME real-subprocess path (CLI selection -> planner -> runner -> real
    # openai-native probe subprocess in mock mode -> raw -> OpenAI normalizer -> results ->
    # summary) across all six base fixtures, with zero provider calls / network / credential.
    summary = _offline_openai_run(corpus_root)
    assert summary.mode == "offline"
    assert summary.expected_call_count == 6
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert [f["fixture_id"] for f in run_summary["fixtures"]] == _APPROVED
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "openai-native"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["selected_lanes"] == ["openai-native"]
    assert "openai-native" in manifest["probe_lock_hashes"]

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "openai-native"
        assert probe_resp["execution_mode"] == "offline_mock"  # never live
        assert "openai" in probe_resp["package_versions"]
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        _assert_model_identity(result, _MODEL)
        # Existing normalizer behavior: OpenAI offline outcomes are PASS or PASS_WITH_EXTENSION.
        assert result["status"] in ("PASS", "PASS_WITH_EXTENSION")
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


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
        _assert_model_identity(result, _MODEL)
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
        _assert_model_identity(result, _ANTHROPIC_MODEL)
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
        _assert_model_identity(result, _GEMINI_MODEL)
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


def _offline_litellm_run(corpus_root, run_id="ll-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(select_lane(load_lanes(corpus_root), "litellm-sdk"), _LITELLM_MODEL)
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
        model=_LITELLM_MODEL,
        pricing=None,  # offline needs no pricing snapshot (cost gate is live-only)
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_LITELLM_PROBE,
    )


@pytest.mark.skipif(
    not (_LITELLM_PROBE / ".venv").exists(),
    reason="litellm-sdk probe venv missing; run `uv sync --frozen` in probes/litellm-sdk",
)
def test_full_offline_litellm_simulation_all_six(corpus_root):
    # Parity with the other lanes: CLI selection -> planner -> runner -> real litellm-sdk probe
    # subprocess in mock mode -> raw litellm evidence -> LiteLLM normalizer -> results -> summary,
    # across all six base fixtures, with zero provider calls / network / credential.
    summary = _offline_litellm_run(corpus_root)
    assert summary.mode == "offline"
    assert summary.expected_call_count == 6
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "litellm-sdk"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["selected_lanes"] == ["litellm-sdk"]
    assert "litellm-sdk" in manifest["probe_lock_hashes"]

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "litellm-sdk"
        assert probe_resp["provider"] == "openai"
        assert probe_resp["execution_mode"] == "offline_mock"  # never live
        assert probe_resp["package_versions"]["litellm"] == "1.92.0"
        assert probe_resp["retry_count_observed"] == 0  # measured, single attempt, no retry
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        _assert_model_identity(result, _LITELLM_MODEL)
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


@pytest.mark.skipif(
    not (_LITELLM_PROBE / ".venv").exists(),
    reason="litellm-sdk probe venv missing; run `uv sync --frozen` in probes/litellm-sdk",
)
def test_litellm_prefix_stripping_is_a_recorded_mismatch_not_error(corpus_root):
    # LiteLLM strips the provider prefix on the returned model field (openai/x -> x), so the
    # requested and observed models differ. That mismatch is RECORDED (model_identity_match=false),
    # never turned into an error, and never provider-native (framework abstraction). N-05 stress.
    summary = _offline_litellm_run(corpus_root, run_id="ll-prefix", ids=["GEN-001"])
    result = json.loads(
        (summary.run_dir / "fixtures" / "GEN-001" / "result.json").read_text("utf-8")
    )
    mi = result["observed_model_identity"]
    assert mi["requested_model"] == "openai/gpt-synthetic-p07a"
    assert mi["observed_returned_model"] == "gpt-synthetic-p07a"  # prefix stripped by litellm
    assert mi["model_identity_match"] == "false"  # recorded, not corrected
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED  # offline synthetic
    assert result["status"] in ("PASS", "PASS_WITH_EXTENSION")  # a mismatch is NOT an error


@pytest.mark.skipif(
    not (_LITELLM_PROBE / ".venv").exists(),
    reason="litellm-sdk probe venv missing; run `uv sync --frozen` in probes/litellm-sdk",
)
def test_litellm_usage_is_framework_native_not_provider(corpus_root):
    # LiteLLM's OpenAI-shaped usage is framework-normalized (offline it is token-counter
    # synthesized), so it must be labelled framework_native, NEVER provider_native. N-01 stress.
    summary = _offline_litellm_run(corpus_root, run_id="ll-usage", ids=["USAGE-001"])
    result = json.loads(
        (summary.run_dir / "fixtures" / "USAGE-001" / "result.json").read_text("utf-8")
    )
    assert result["usage"]["source"] == provenance.FRAMEWORK_NATIVE
    assert result["usage"]["input_tokens"] is not None  # present, synthesized


@pytest.mark.skipif(
    not (_LITELLM_PROBE / ".venv").exists(),
    reason="litellm-sdk probe venv missing; run `uv sync --frozen` in probes/litellm-sdk",
)
def test_litellm_metadata_is_framework_extension_never_provider(corpus_root):
    # LiteLLM auxiliary metadata (hidden params / routing) is a framework abstraction artifact, so
    # it surfaces as framework_extension, never provider_extension. A litellm lane never emits a
    # provider_extension event.
    summary = _offline_litellm_run(corpus_root, run_id="ll-ext", ids=["GEN-001"])
    tr = json.loads(
        (summary.run_dir / "fixtures" / "GEN-001" / "normalized-transcript.json").read_text("utf-8")
    )
    types = [e["type"] for e in tr["events"]]
    assert "framework_extension" in types
    assert "provider_extension" not in types
    assert summary.entries[0]["status"] == "PASS_WITH_EXTENSION"


def _execution_path(transcript):
    for e in transcript["events"]:
        if e["type"] == "framework_extension" and "execution_path" in e.get("data", {}):
            return e["data"]["execution_path"]
    return None


@pytest.mark.skipif(
    not (_LITELLM_PROBE / ".venv").exists(),
    reason="litellm-sdk probe venv missing; run `uv sync --frozen` in probes/litellm-sdk",
)
def test_litellm_execution_path_recorded_and_tool_is_partial(corpus_root):
    # Evidence accuracy (P0.7A amendment): the per-fixture execution path is surfaced in the
    # transcript, and TOOL-001 is a PARTIAL path (request transform + response-object injection),
    # NOT the full completion(tools=...) path.
    summary = _offline_litellm_run(corpus_root, run_id="ll-path", ids=["GEN-001", "TOOL-001"])
    gen_tr = json.loads(
        (summary.run_dir / "fixtures" / "GEN-001" / "normalized-transcript.json").read_text("utf-8")
    )
    tool_tr = json.loads(
        (summary.run_dir / "fixtures" / "TOOL-001" / "normalized-transcript.json").read_text(
            "utf-8"
        )
    )
    gen_ep = _execution_path(gen_tr)
    tool_ep = _execution_path(tool_tr)
    assert gen_ep is not None and tool_ep is not None
    # GEN and TOOL used DIFFERENT paths (not identical across fixtures).
    assert gen_ep["components"] == ["completion_mock_response"]
    assert tool_ep["components"] == [
        "framework_request_transformation",
        "framework_response_object_injection",
    ]
    assert tool_ep["full_completion_tools_path_exercised"] is False
    assert gen_ep["components"] != tool_ep["components"]


def _offline_pydanticai_run(corpus_root, run_id="p7b-wire-1", ids=None):
    ids = ids or _APPROVED
    cfg_path = corpus_root / "configs" / "first-live.override.toml"
    raw = load_raw(cfg_path)
    lane = resolve_model(
        select_lane(load_lanes(corpus_root), "pydantic-ai-agent"), _PYDANTICAI_MODEL
    )
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
        model=_PYDANTICAI_MODEL,
        pricing=None,
        config_digest="test-digest",
        command_line="test",
        root=corpus_root,
        probe_dir=_PYDANTICAI_PROBE,
    )


@pytest.mark.skipif(
    not (_PYDANTICAI_PROBE / ".venv").exists(),
    reason="pydantic-ai-agent probe venv missing; run `uv sync --frozen` in probes/pydantic-ai-agent",
)
def test_full_offline_pydanticai_simulation_all_six(corpus_root):
    # Parity with the other lanes: CLI selection -> planner -> runner -> real pydantic-ai-agent
    # probe subprocess in mock mode -> raw Agent evidence -> PydanticAI normalizer -> results ->
    # summary, across all six base fixtures, with zero provider calls / network / credential /
    # tool executions.
    summary = _offline_pydanticai_run(corpus_root)
    assert summary.mode == "offline"
    assert summary.expected_call_count == 6
    assert [e["fixture_id"] for e in summary.entries] == _APPROVED

    run_summary = json.loads(summary.summary_path.read_text(encoding="utf-8"))
    assert run_summary["secret_scan"] == "clean"
    assert run_summary["lane_id"] == "pydantic-ai-agent"

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))
    assert manifest["selected_lanes"] == ["pydantic-ai-agent"]
    assert "pydantic-ai-agent" in manifest["probe_lock_hashes"]

    for fx_id in _APPROVED:
        fx_dir = summary.run_dir / "fixtures" / fx_id
        probe_resp = json.loads((fx_dir / "probe-response.json").read_text("utf-8"))
        assert probe_resp["probe_id"] == "pydantic-ai-agent"
        assert probe_resp["provider"] == "openai"
        assert probe_resp["execution_mode"] == "offline_mock"  # never live
        assert probe_resp["package_versions"]["pydantic_ai"] == "2.9.0"
        assert probe_resp["retry_count_observed"] == 0  # measured, single request, no retry
        result = json.loads((fx_dir / "result.json").read_text("utf-8"))
        assert is_valid("result", result)
        # Agent RunUsage aggregation is framework-owned, never provider-native.
        assert result["usage"]["source"] == provenance.FRAMEWORK_NATIVE
        _assert_model_identity(result, _PYDANTICAI_MODEL)
        transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
        assert is_valid("normalized-transcript", transcript)


@pytest.mark.skipif(
    not (_PYDANTICAI_PROBE / ".venv").exists(),
    reason="pydantic-ai-agent probe venv missing; run `uv sync --frozen` in probes/pydantic-ai-agent",
)
def test_pydanticai_offline_model_identity_is_synthetic_mismatch(corpus_root):
    # The offline FunctionModel exposes a synthetic model_name distinct from the requested model,
    # so requested != observed is RECORDED (model_identity_match=false), non-failing, offline
    # source fixture_expected, framework-owned. N-05 stress under a framework lane.
    summary = _offline_pydanticai_run(corpus_root, run_id="p7b-mi", ids=["GEN-001"])
    result = json.loads(
        (summary.run_dir / "fixtures" / "GEN-001" / "result.json").read_text("utf-8")
    )
    mi = result["observed_model_identity"]
    assert mi["requested_model"] == _PYDANTICAI_MODEL
    assert mi["observed_returned_model"] == "function:offline-synthetic-model"
    assert mi["model_identity_match"] == "false"  # requested != observed, recorded not error
    assert mi["observed_returned_model_source"] == provenance.FIXTURE_EXPECTED
    assert result["status"] in ("PASS", "PASS_WITH_EXTENSION")  # a mismatch is never an error


@pytest.mark.skipif(
    not (_PYDANTICAI_PROBE / ".venv").exists(),
    reason="pydantic-ai-agent probe venv missing; run `uv sync --frozen` in probes/pydantic-ai-agent",
)
def test_pydanticai_deferred_tool_is_requires_action_no_execution(corpus_root):
    # TOOL-001 defers (approval-required): the terminal state is requires_action, the tool body is
    # never executed, and the deferral is a framework_extension (never provider-native).
    summary = _offline_pydanticai_run(corpus_root, run_id="p7b-tool", ids=["TOOL-001"])
    fx_dir = summary.run_dir / "fixtures" / "TOOL-001"
    result = json.loads((fx_dir / "result.json").read_text("utf-8"))
    assert result["observed_terminal_state"]["native"] == "tool_call"
    assert result["observed_terminal_state"]["category"] == "requires_action"
    transcript = json.loads((fx_dir / "normalized-transcript.json").read_text("utf-8"))
    types = [e["type"] for e in transcript["events"]]
    assert "tool_call_completed" in types
    assert "provider_extension" not in types
    completed = next(e for e in transcript["events"] if e["type"] == "tool_call_completed")
    assert completed["data"]["deferred"] is True
    assert completed["data"]["name"] == "get_weather"
