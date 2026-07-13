"""Structured output: NativeOutput is selected EXPLICITLY via a synthetic profile, no fallback."""

from __future__ import annotations

from conftest import run_fixture
from probe.client import native_output_profile


def test_native_output_mode_selected():
    capture, _op, _scenario = run_fixture("STR-001")
    assert capture.structured["strategy_requested"] == "native_output"
    assert capture.structured["output_mode_observed"] == "native"
    assert capture.structured["is_native"] is True


def test_synthetic_profile_recorded_not_inferred_from_provider():
    capture, _op, _scenario = run_fixture("STR-001")
    prof = capture.synthetic_profile
    assert prof["supports_json_schema_output"] is True
    assert prof["source"] == "synthetic_offline_configuration"
    assert prof["inferred_from_real_provider"] is False


def test_generated_json_schema_retained():
    capture, _op, _scenario = run_fixture("STR-001")
    schema = capture.structured["generated_json_schema"]
    assert schema is not None
    assert set(schema.get("required", [])) == {"name", "age"}


def test_parsed_output_distinct_and_provider_validation_deferred():
    capture, _op, _scenario = run_fixture("STR-001")
    assert capture.structured["parsed_output"] == {"name": "Alice", "age": 30}
    assert capture.structured["parse_error"] is None
    assert capture.structured["schema_validation"] == "framework_validated_offline"
    # Offline validity is NOT proof a real provider requested/followed native JSON schema.
    assert capture.structured["provider_validation"] == "unverified_until_live"


def test_no_silent_fallback_to_tool_or_prompted():
    capture, _op, _scenario = run_fixture("STR-001")
    # NativeOutput registers no output tool; a tool/prompted fallback would show output_tools.
    assert capture.agent_info["output_tools"] == []
    assert capture.output_type != "DeferredToolRequests"


def test_native_selection_is_grounded_in_probe_supplied_profile():
    # The offline native-output selection is grounded in a profile the PROBE supplies explicitly,
    # recorded as synthetic offline configuration - not read from any real provider. (FunctionModel
    # is permissive by default, so declaring the capability explicitly is what makes the evidence
    # honest: the flag is ours, labelled synthetic.)
    capture, _op, _scenario = run_fixture("STR-001")
    assert capture.synthetic_profile is not None
    assert capture.synthetic_profile["supports_json_schema_output"] is True
    assert capture.synthetic_profile["inferred_from_real_provider"] is False
    assert capture.structured["output_mode_observed"] == "native"


def test_synthetic_profile_helper_flags():
    profile, record = native_output_profile()
    # ModelProfile(...) is a TypedDict; the capability flag is a key.
    assert profile["supports_json_schema_output"] is True
    assert record["inferred_from_real_provider"] is False
