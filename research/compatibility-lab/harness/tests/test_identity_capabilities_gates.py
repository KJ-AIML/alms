"""Identity, provenance, capability, and gate preservation tests."""

from __future__ import annotations

from alms_compat.capability import empty_profile, set_capability
from alms_compat.gates import (
    PHASE0_PRESERVED,
    assert_gates_preserved,
    custom_lanes_absent_from_native,
)
from alms_compat.identity import (
    ENDPOINT_BOUNDARY,
    PROVENANCE_DECISION,
    build_identity,
    forbid_provider_native_for_custom,
)
from alms_compat.normalizers import normalize_openai_compatible


def test_gateway_claim_not_provider_identity() -> None:
    identity = build_identity(
        endpoint_id="e1",
        endpoint_family="openai_compatible",
        boundary_kind="gateway",
        sdk_family="openai",
        provider_claim="claimed-openai",
        gateway_claim="claimed-gateway",
        requested_model="m1",
        observed_returned_model="m1",
        observed_returned_model_source=ENDPOINT_BOUNDARY,
        execution_mode="offline_sdk_transport",
    )
    assert identity.configured_provider_claim == "claimed-openai"
    assert identity.configured_gateway_claim == "claimed-gateway"
    assert identity.configured_provider_claim != identity.endpoint_id


def test_model_name_not_provider_identity() -> None:
    identity = build_identity(
        endpoint_id="e1",
        endpoint_family="openai_compatible",
        boundary_kind="unknown",
        sdk_family="openai",
        provider_claim=None,
        gateway_claim=None,
        requested_model="gpt-looking-name",
        observed_returned_model="gpt-looking-name",
        observed_returned_model_source=ENDPOINT_BOUNDARY,
        execution_mode="offline_sdk_transport",
    )
    assert identity.configured_provider_claim is None


def test_requested_and_returned_model_separate() -> None:
    identity = build_identity(
        endpoint_id="e1",
        endpoint_family="openai_compatible",
        boundary_kind="custom_endpoint",
        sdk_family="openai",
        provider_claim=None,
        gateway_claim=None,
        requested_model="requested-model",
        observed_returned_model="returned-model",
        observed_returned_model_source=ENDPOINT_BOUNDARY,
        execution_mode="offline_sdk_transport",
    )
    assert identity.requested_model == "requested-model"
    assert identity.observed_returned_model == "returned-model"
    assert identity.model_identity_match is False


def test_missing_returned_model_unavailable() -> None:
    identity = build_identity(
        endpoint_id="e1",
        endpoint_family="openai_compatible",
        boundary_kind="custom_endpoint",
        sdk_family="openai",
        provider_claim=None,
        gateway_claim=None,
        requested_model="requested-model",
        observed_returned_model=None,
        observed_returned_model_source="unavailable",
        execution_mode="offline_sdk_transport",
    )
    assert identity.observed_returned_model is None
    assert identity.model_identity_match is None
    assert identity.observed_returned_model_source == "unavailable"


def test_mismatch_non_failing() -> None:
    identity = build_identity(
        endpoint_id="e1",
        endpoint_family="openai_compatible",
        boundary_kind="custom_endpoint",
        sdk_family="openai",
        provider_claim=None,
        gateway_claim=None,
        requested_model="a",
        observed_returned_model="b",
        observed_returned_model_source=ENDPOINT_BOUNDARY,
        execution_mode="offline_sdk_transport",
    )
    assert identity.model_identity_match is False


def test_no_provider_native_fabrication() -> None:
    assert forbid_provider_native_for_custom("live_custom_endpoint", "provider_native") is False
    assert forbid_provider_native_for_custom("live_custom_endpoint", ENDPOINT_BOUNDARY) is True
    result = normalize_openai_compatible(
        {"response": {"model": "m", "usage": {"prompt_tokens": 1}}},
        identity_kwargs={
            "endpoint_id": "e1",
            "endpoint_family": "openai_compatible",
            "boundary_kind": "gateway",
            "sdk_family": "openai",
            "provider_claim": None,
            "gateway_claim": "g",
            "requested_model": "m",
            "execution_mode": "offline_sdk_transport",
        },
    )
    assert result["usage"]["source"] == ENDPOINT_BOUNDARY
    assert result["usage"]["source"] != "provider_native"
    assert PROVENANCE_DECISION == "B"


def test_declared_vs_observed_capability_separation() -> None:
    profile = empty_profile(
        "openai-compatible-custom",
        "openai_compatible",
        "openai",
        "unknown",
    )
    set_capability(profile, "text_generation", "declared", "config only")
    set_capability(profile, "streaming", "observed_offline", "wire transport")
    set_capability(profile, "request_cancellation", "not_tested")
    set_capability(profile, "cache_usage", "unsupported", "no cache fields")
    set_capability(profile, "reasoning_metadata", "inconclusive", "ambiguous field")
    data = profile.to_dict()
    assert data["capabilities"]["text_generation"] == "declared"
    assert data["capabilities"]["streaming"] == "observed_offline"
    assert data["capabilities"]["request_cancellation"] == "not_tested"
    assert data["capabilities"]["cache_usage"] == "unsupported"
    assert data["capabilities"]["reasoning_metadata"] == "inconclusive"
    assert "G2" in data["disclaimer"]


def test_gate_preservation() -> None:
    assert_gates_preserved(dict(PHASE0_PRESERVED))
    assert custom_lanes_absent_from_native(
        {
            "openai-native",
            "anthropic-native",
            "gemini-native",
            "langchain",
            "litellm-sdk",
            "pydantic-ai-agent",
        }
    )
